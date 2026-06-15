#!/usr/bin/env python3
"""
indicators.py - 九章量化局 · 技术指标计算引擎
计算 MACD、RSI、布林带、均线系统、支撑阻力位
输入：股票代码 + 周期
输出：JSON格式的技术指标
"""

import sys
import json
import argparse
from datetime import datetime, timedelta

def calculate_ma(prices, window):
    """计算移动平均线"""
    if len(prices) < window:
        return []
    return [sum(prices[i-window:i]) / window for i in range(window, len(prices)+1)]

def calculate_rsi(prices, window=14):
    """计算RSI指标"""
    if len(prices) < window + 1:
        return []
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    
    rsi_values = []
    for i in range(window, len(gains)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        rsi_values.append(rsi)
    
    return rsi_values

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """计算MACD指标"""
    if len(prices) < slow:
        return {"DIF": [], "DEA": [], "MACD": []}
    
    def ema(data, period):
        ema_values = [data[0]]
        k = 2 / (period + 1)
        for price in data[1:]:
            ema_values.append(price * k + ema_values[-1] * (1 - k))
        return ema_values
    
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    
    # 对齐长度
    min_len = min(len(ema_fast), len(ema_slow))
    ema_fast = ema_fast[-min_len:]
    ema_slow = ema_slow[-min_len:]
    
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    
    # 计算DEA（DIF的9日EMA）
    dea = []
    k = 2 / (signal + 1)
    dea.append(dif[0])
    for i in range(1, len(dif)):
        dea.append(dif[i] * k + dea[-1] * (1 - k))
    
    macd = [(d - e) * 2 for d, e in zip(dif, dea)]
    
    return {
        "DIF": dif,
        "DEA": dea,
        "MACD": macd
    }

def calculate_bollinger(prices, window=20, num_std=2):
    """计算布林带"""
    if len(prices) < window:
        return {"upper": [], "middle": [], "lower": []}
    
    middle = []
    upper = []
    lower = []
    
    for i in range(window - 1, len(prices)):
        slice = prices[i - window + 1 : i + 1]
        mid = sum(slice) / window
        std = (sum((x - mid) ** 2 for x in slice) / window) ** 0.5
        
        middle.append(mid)
        upper.append(mid + num_std * std)
        lower.append(mid - num_std * std)
    
    return {
        "upper": upper,
        "middle": middle,
        "lower": lower
    }

def find_support_resistance(prices, window=5):
    """识别支撑阻力位（局部高低点）"""
    support = []
    resistence = []
    
    for i in range(window, len(prices) - window):
        # 局部低点 = 支撑位
        if all(prices[i] <= prices[j] for j in range(i - window, i + window + 1) if j != i):
            support.append({"index": i, "price": prices[i]})
        
        # 局部高点 = 阻力位
        if all(prices[i] >= prices[j] for j in range(i - window, i + window + 1) if j != i):
            resistence.append({"index": i, "price": prices[i]})
    
    # 去重（相近的价格合并）
    def merge_levels(levels, threshold=0.01):
        if not levels:
            return []
        merged = []
        current_group = [levels[0]]
        
        for level in levels[1:]:
            if abs(level["price"] - current_group[0]["price"]) / current_group[0]["price"] < threshold:
                current_group.append(level)
            else:
                merged.append({
                    "price": sum(l["price"] for l in current_group) / len(current_group),
                    "count": len(current_group)
                })
                current_group = [level]
        
        merged.append({
            "price": sum(l["price"] for l in current_group) / len(current_group),
            "count": len(current_group)
        })
        return merged
    
    support_sorted = sorted(support, key=lambda x: x["price"])
    resistence_sorted = sorted(resistence, key=lambda x: x["price"])
    
    return {
        "support": merge_levels(support_sorted),
        "resistence": merge_levels(resistence_sorted)
    }

def get_kline_data(code, days=30):
    """
    获取K线数据
    优先使用 tdx-connector，失败后使用 yfinance/akshare 兜底
    """
    try:
        # 尝试使用 yfinance (支持美股/港股/A股)
        import yfinance as yf
        
        # 代码格式转换
        if code.endswith(".SH") or code.endswith(".SS"):
            ticker = code
        elif code.endswith(".SZ"):
            ticker = code
        elif code.isdigit() and len(code) == 6:
            # A股代码，尝试上交所/深交所
            if code.startswith("6"):
                ticker = f"{code}.SS"
            else:
                ticker = f"{code}.SZ"
        elif ".HK" in code:
            ticker = code
        else:
            ticker = code
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")
        
        if hist.empty:
            raise Exception("No data from yfinance")
        
        prices = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        volumes = hist["Volume"].tolist()
        
        return {
            "success": True,
            "source": "yfinance",
            "ticker": ticker,
            "prices": prices,
            "highs": highs,
            "lows": lows,
            "volumes": volumes,
            "dates": hist.index.strftime("%Y-%m-%d").tolist()
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "数据获取失败，请检查股票代码或网络连接"
        }

def main():
    parser = argparse.ArgumentParser(description="九章量化局 · 技术指标计算")
    parser.add_argument("--code", type=str, required=True, help="股票代码 (如 600519, 00700.HK, TSLA)")
    parser.add_argument("--days", type=int, default=30, help="分析周期（天数）")
    parser.add_argument("--output", type=str, help="输出文件路径（可选，默认输出到stdout）")
    
    args = parser.parse_args()
    
    # 获取数据
    data = get_kline_data(args.code, args.days)
    
    if not data["success"]:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        sys.exit(1)
    
    prices = data["prices"]
    
    # 计算技术指标
    result = {
        "code": args.code,
        "days": args.days,
        "data_source": data["source"],
        "current_price": prices[-1],
        "indicators": {
            "MA": {
                "MA5": calculate_ma(prices, 5)[-1] if len(prices) >= 5 else None,
                "MA10": calculate_ma(prices, 10)[-1] if len(prices) >= 10 else None,
                "MA20": calculate_ma(prices, 20)[-1] if len(prices) >= 20 else None,
                "MA60": calculate_ma(prices, 60)[-1] if len(prices) >= 60 else None,
            },
            "RSI": {
                "RSI_6": calculate_rsi(prices, 6)[-1] if len(prices) >= 7 else None,
                "RSI_12": calculate_rsi(prices, 12)[-1] if len(prices) >= 13 else None,
                "RSI_24": calculate_rsi(prices, 24)[-1] if len(prices) >= 25 else None,
            },
            "MACD": calculate_macd(prices),
            "Bollinger": calculate_bollinger(prices),
            "Support_Resistence": find_support_resistence(prices)
        },
        "raw_data": {
            "prices": prices,
            "highs": data["highs"],
            "lows": data["lows"],
            "volumes": data["volumes"],
            "dates": data["dates"]
        }
    }
    
    # 输出结果
    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"✓ 指标计算完成，结果已保存至 {args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()
