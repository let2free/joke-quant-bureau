"""
九章量化局 · ETF数据模块 v4.0
接入腾讯行情API，真实因子计算，6大类别40+只ETF

架构：
  data_fetcher.py → 实时行情 + K线历史
  etf_data.py    → ETF池管理 + 因子计算 + 排名
  无模拟数据，全部真实
"""

import json
import math
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from data_fetcher import (
    fetch_realtime_quotes, fetch_kline, fetch_kline_batch,
    fetch_indices, code_to_tencent
)

# ── 配置 ──
DATA_DIR = Path(__file__).parent
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
FACTOR_CACHE_FILE = DATA_DIR / "factor_cache.json"

# 因子缓存TTL（因子计算较重，缓存10分钟）
FACTOR_CACHE_TTL = 600

# ── 扩展ETF监控池：6大类别，每类Top 5-6 ──
ETF_UNIVERSE = {
    "宽基指数": [
        {"code": "510300", "name": "沪深300ETF", "market": "1"},
        {"code": "510500", "name": "中证500ETF", "market": "1"},
        {"code": "159915", "name": "创业板ETF", "market": "0"},
        {"code": "588000", "name": "科创50ETF", "market": "1"},
        {"code": "510050", "name": "上证50ETF", "market": "1"},
        {"code": "512100", "name": "中证1000ETF", "market": "1"},
    ],
    "科技": [
        {"code": "560780", "name": "半导体设备ETF", "market": "1"},
        {"code": "159995", "name": "芯片ETF", "market": "0"},
        {"code": "515070", "name": "人工智能ETF", "market": "1"},
        {"code": "515880", "name": "通信ETF", "market": "1"},
        {"code": "562500", "name": "机器人ETF", "market": "1"},
        {"code": "512660", "name": "军工ETF", "market": "1"},
    ],
    "新能源": [
        {"code": "516160", "name": "新能源ETF", "market": "1"},
        {"code": "515790", "name": "光伏ETF", "market": "1"},
        {"code": "515030", "name": "新能源车ETF", "market": "1"},
        {"code": "159755", "name": "碳中和ETF", "market": "0"},
        {"code": "159611", "name": "电力ETF", "market": "0"},
    ],
    "医药消费": [
        {"code": "516080", "name": "创新药ETF", "market": "1"},
        {"code": "512010", "name": "医药ETF", "market": "1"},
        {"code": "159928", "name": "消费ETF", "market": "0"},
        {"code": "515170", "name": "食品饮料ETF", "market": "1"},
        {"code": "159996", "name": "家电ETF", "market": "0"},
    ],
    "金融周期": [
        {"code": "512880", "name": "证券ETF", "market": "1"},
        {"code": "512800", "name": "银行ETF", "market": "1"},
        {"code": "512200", "name": "房地产ETF", "market": "1"},
        {"code": "515220", "name": "煤炭ETF", "market": "1"},
        {"code": "518880", "name": "黄金ETF", "market": "1"},
        {"code": "512400", "name": "有色金属ETF", "market": "1"},
    ],
    "海外债券": [
        {"code": "513100", "name": "纳指ETF", "market": "1"},
        {"code": "513500", "name": "标普500ETF", "market": "1"},
        {"code": "513180", "name": "恒生科技ETF", "market": "1"},
        {"code": "513050", "name": "中概互联ETF", "market": "1"},
        {"code": "511010", "name": "国债ETF", "market": "1"},
        {"code": "511260", "name": "十年国债ETF", "market": "1"},
    ],
}

# 扁平化：全部ETF列表
ALL_ETFS = []
ETF_CODE_TO_CATEGORY = {}
for cat, etfs in ETF_UNIVERSE.items():
    for etf in etfs:
        ALL_ETFS.append(etf)
        ETF_CODE_TO_CATEGORY[etf["code"]] = cat

# 默认自选（兼容旧接口）
DEFAULT_WATCHLIST = {
    "a_share": [e for e in ALL_ETFS if e["market"] in ("0", "1") and ETF_CODE_TO_CATEGORY.get(e["code"]) != "海外债券"],
    "us": [e for e in ALL_ETFS if ETF_CODE_TO_CATEGORY.get(e["code"]) == "海外债券"],
}


# ═══════════════════════════════════════════════════════════════
#  因子计算（基于K线历史数据，真实计算）
# ═══════════════════════════════════════════════════════════════

def calc_momentum_factor(klines: list, window: int = 20) -> float:
    """
    动量因子：过去window天的累计收益率
    归一化到0-100分
    """
    if len(klines) < window + 1:
        return 50.0  # 数据不足返回中性值
    
    closes = [k["close"] for k in klines[-(window+1):]]
    if closes[0] <= 0:
        return 50.0
    
    ret = (closes[-1] / closes[0] - 1) * 100  # 百分比收益
    
    # 归一化：-10%~+10% → 0~100
    score = max(0, min(100, (ret + 10) / 20 * 100))
    return round(score, 1)


def calc_mean_reversion_factor(klines: list, window: int = 20) -> float:
    """
    均值回归因子：当前价格相对MA的偏离度
    偏离越大，回归概率越高（越低于均线→分数越高=看多）
    """
    if len(klines) < window:
        return 50.0
    
    closes = [k["close"] for k in klines[-window:]]
    ma = sum(closes) / len(closes)
    current = closes[-1]
    
    if ma <= 0:
        return 50.0
    
    deviation = (current / ma - 1) * 100  # 偏离百分比
    
    # 越低于均线→分数越高（均值回归看多）
    # 偏离-10%~+10% → 60~40（低于均线高分，高于均线低分）
    score = 50 - deviation * 1.5  # 负偏离（低于均线）→ 高分
    return round(max(0, min(100, score)), 1)


def calc_volatility_factor(klines: list, window: int = 20) -> float:
    """
    波动率因子：过去window天的年化波动率
    适度波动（20-30%）得高分，过高或过低都扣分
    """
    if len(klines) < window + 1:
        return 50.0
    
    closes = [k["close"] for k in klines[-(window+1):]]
    returns = []
    for i in range(1, len(closes)):
        if closes[i-1] > 0:
            returns.append(math.log(closes[i] / closes[i-1]))
    
    if len(returns) < 5:
        return 50.0
    
    mean_ret = sum(returns) / len(returns)
    var = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = math.sqrt(var)
    annual_vol = daily_vol * math.sqrt(252) * 100  # 年化百分比
    
    # 最优波动率区间：15-30%
    if annual_vol < 10:
        score = 30  # 太低，流动性差
    elif annual_vol < 15:
        score = 40 + (annual_vol - 10) * 2  # 10-15% → 40-50
    elif annual_vol <= 30:
        score = 50 + (annual_vol - 15) * 2  # 15-30% → 50-80
    elif annual_vol <= 50:
        score = 80 - (annual_vol - 30) * 1.5  # 30-50% → 80-50
    else:
        score = max(20, 50 - (annual_vol - 50) * 0.5)  # >50% → 50-20
    
    return round(score, 1)


def calc_fund_flow_factor(klines: list, window: int = 20) -> float:
    """
    资金流因子：基于量价关系估算
    放量上涨→资金流入，放量下跌→资金流出
    用OBV（On Balance Volume）变体
    """
    if len(klines) < window + 1:
        return 50.0
    
    recent = klines[-(window+1):]
    obv_changes = []
    
    for i in range(1, len(recent)):
        vol = recent[i]["volume"]
        if recent[i]["close"] > recent[i-1]["close"]:
            obv_changes.append(vol)   # 上涨：正向量
        elif recent[i]["close"] < recent[i-1]["close"]:
            obv_changes.append(-vol)  # 下跌：负向量
        else:
            obv_changes.append(0)
    
    if not obv_changes:
        return 50.0
    
    # 累积OBV变化方向
    total = sum(obv_changes)
    avg_vol = sum(abs(v) for v in obv_changes) / len(obv_changes)
    
    if avg_vol <= 0:
        return 50.0
    
    # 归一化：OBV趋势
    obv_normalized = total / (avg_vol * len(obv_changes))
    
    # -1~+1 → 0~100
    score = (obv_normalized + 1) / 2 * 100
    return round(max(0, min(100, score)), 1)


def calc_microstructure_factor(klines: list, window: int = 10) -> float:
    """
    微观结构因子：基于近window天的量价模式
    成交量变化趋势 + 价格振幅
    """
    if len(klines) < window:
        return 50.0
    
    recent = klines[-window:]
    
    # 成交量趋势（线性回归斜率）
    volumes = [k["volume"] for k in recent]
    n = len(volumes)
    x_mean = (n - 1) / 2
    y_mean = sum(volumes) / n
    
    num = sum((i - x_mean) * (volumes[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    
    vol_trend = (num / den / y_mean * 100) if den > 0 and y_mean > 0 else 0
    
    # 价格振幅（近window天平均振幅）
    amplitudes = []
    for k in recent:
        if k["low"] > 0:
            amplitudes.append((k["high"] / k["low"] - 1) * 100)
    avg_amp = sum(amplitudes) / len(amplitudes) if amplitudes else 0
    
    # 综合评分：量增+适度振幅 = 高分
    score = 50 + vol_trend * 5 + (avg_amp - 2) * 5
    return round(max(0, min(100, score)), 1)


def calc_regime_factor(klines: list, window: int = 60) -> float:
    """
    市场环境因子：基于中长期趋势判断市场状态
    60天均线方向 + 价格相对位置
    """
    if len(klines) < window:
        return 50.0
    
    closes = [k["close"] for k in klines[-window:]]
    ma60 = sum(closes) / len(closes)
    ma20 = sum(closes[-20:]) / 20
    current = closes[-1]
    
    if ma60 <= 0:
        return 50.0
    
    # 趋势判断
    above_ma60 = current > ma60  # 在60日均线上方
    ma20_above_ma60 = ma20 > ma60  # 20日均线在60日均线上方（金叉）
    
    # 趋势强度
    trend_strength = (current / ma60 - 1) * 100
    
    score = 50
    if above_ma60 and ma20_above_ma60:
        score = 65 + min(trend_strength * 2, 20)  # 强势上涨
    elif above_ma60:
        score = 55 + min(trend_strength, 15)       # 弱势上涨
    elif not above_ma60 and not ma20_above_ma60:
        score = 35 + max(trend_strength * 2, -20)  # 强势下跌
    else:
        score = 45 + max(trend_strength, -10)      # 弱势下跌
    
    return round(max(0, min(100, score)), 1)


def calculate_all_factors(code: str, klines: list) -> dict:
    """计算单只ETF的全部因子"""
    return {
        "factor_mom": calc_momentum_factor(klines, 20),
        "factor_mr": calc_mean_reversion_factor(klines, 20),
        "factor_vol": calc_volatility_factor(klines, 20),
        "factor_flow": calc_fund_flow_factor(klines, 20),
        "factor_ms": calc_microstructure_factor(klines, 10),
        "factor_regime": calc_regime_factor(klines, 60),
    }


# ═══════════════════════════════════════════════════════════════
#  ETF数据获取 + 因子计算整合
# ═══════════════════════════════════════════════════════════════

# 全局缓存（线程安全）
_cache_lock = threading.Lock()
_etf_data_cache = {"data": None, "fetched_at": 0}
_factor_cache = {"data": None, "fetched_at": 0}


def generate_etf_data(use_cache=True) -> dict:
    """
    生成ETF全量数据（实时行情 + 因子）
    
    Returns:
        {
            "510300": {
                "name": "沪深300ETF", "code": "510300", "price": 4.958,
                "change_pct": 0.98, "volume": 13911870, ...,
                "factor_mom": 65.2, "factor_mr": 42.1, ...,
                "category": "宽基指数"
            }, ...
        }
    """
    global _etf_data_cache, _factor_cache
    
    now = time.time()
    
    # 检查内存缓存（30秒内，线程安全读）
    with _cache_lock:
        cache_hit = (use_cache and _etf_data_cache["data"] and (now - _etf_data_cache["fetched_at"]) < 30)
        if cache_hit:
            return _etf_data_cache["data"]
    
    # 1. 获取实时行情（所有ETF）
    codes = [etf["code"] for etf in ALL_ETFS]
    quote_result = fetch_realtime_quotes(codes, use_cache=True)
    quotes = quote_result["data"]
    
    # 2. 获取K线数据并计算因子（检查因子缓存，线程安全）
    with _cache_lock:
        factors_valid = (_factor_cache["data"] and (now - _factor_cache["fetched_at"]) < FACTOR_CACHE_TTL)
    
    if not factors_valid:
        # 批量获取K线（较慢，需控制频率）
        kline_data = fetch_kline_batch(codes, days=120, use_cache=True)
        
        # 计算因子
        factor_data = {}
        for code in codes:
            klines = kline_data.get(code, {}).get("data", [])
            if klines:
                factor_data[code] = calculate_all_factors(code, klines)
            else:
                factor_data[code] = {
                    "factor_mom": 50.0, "factor_mr": 50.0,
                    "factor_vol": 50.0, "factor_flow": 50.0,
                    "factor_ms": 50.0, "factor_regime": 50.0,
                }
        
        with _cache_lock:
            _factor_cache = {"data": factor_data, "fetched_at": now}
    else:
        with _cache_lock:
            factor_data = _factor_cache["data"]
    
    # 3. 合并行情 + 因子
    result = {}
    for etf in ALL_ETFS:
        code = etf["code"]
        quote = quotes.get(code, {})
        factors = factor_data.get(code, {})
        
        result[code] = {
            "code": code,
            "name": quote.get("name", etf["name"]),
            "market": etf["market"],
            "category": ETF_CODE_TO_CATEGORY.get(code, "其他"),
            "price": quote.get("price", 0),
            "prev_close": quote.get("prev_close", 0),
            "open": quote.get("open", 0),
            "high": quote.get("high", 0),
            "low": quote.get("low", 0),
            "change_pct": quote.get("change_pct", 0),
            "change_abs": quote.get("change_abs", 0),
            "volume": quote.get("volume", 0),
            "amount": quote.get("amount", 0),
            "turnover_rate": quote.get("turnover_rate", 0),
            "amplitude": quote.get("amplitude", 0),
            "buy_volume": quote.get("buy_volume", 0),
            "sell_volume": quote.get("sell_volume", 0),
            # 因子分数
            "factor_mom": factors.get("factor_mom", 50),
            "factor_mr": factors.get("factor_mr", 50),
            "factor_vol": factors.get("factor_vol", 50),
            "factor_flow": factors.get("factor_flow", 50),
            "factor_ms": factors.get("factor_ms", 50),
            "factor_regime": factors.get("factor_regime", 50),
            "updated_at": quote.get("updated_at", datetime.now().isoformat()),
        }
    
    _etf_data_cache["data"] = result
    _etf_data_cache["fetched_at"] = now
    
    return result


def calculate_rankings(data: dict, sort_by: str = "change_pct", top_n: int = 50) -> list:
    """计算ETF排名"""
    etf_list = [{"code": code, **info} for code, info in data.items()]
    
    sort_keys = {
        "change_pct": "change_pct",
        "volume": "volume",
        "amount": "amount",
        "turnover_rate": "turnover_rate",
        "score_b": "_score_b",
    }
    
    # 如果按score_b排序，先计算
    if sort_by == "score_b":
        for etf in etf_list:
            etf["_score_b"] = calc_track_b_score(etf)
    
    key = sort_keys.get(sort_by, sort_by)
    reverse = sort_by not in ("name",)
    etf_list.sort(key=lambda x: x.get(key, 0) if isinstance(x.get(key, 0), (int, float)) else 0, reverse=reverse)
    
    for i, etf in enumerate(etf_list[:top_n], 1):
        etf["rank"] = i
        if "_score_b" in etf:
            etf["score_b"] = etf.pop("_score_b")
    
    return etf_list[:top_n]


def calc_track_b_score(etf_data: dict) -> float:
    """计算单只ETF的Track B综合得分"""
    weights = {
        "momentum": 0.35,
        "mean_reversion": 0.15,
        "volatility": 0.10,
        "fund_flow": 0.25,
        "microstructure": 0.07,
        "regime": 0.08,
    }
    score = 0.0
    score += weights["momentum"]       * etf_data.get("factor_mom", 50)
    score += weights["mean_reversion"] * etf_data.get("factor_mr", 50)
    score += weights["volatility"]     * etf_data.get("factor_vol", 50)
    score += weights["fund_flow"]      * etf_data.get("factor_flow", 50)
    score += weights["microstructure"] * etf_data.get("factor_ms", 50)
    score += weights["regime"]         * etf_data.get("factor_regime", 50)
    return round(score, 1)


# ═══════════════════════════════════════════════════════════════
#  Watchlist 管理（兼容旧接口）
# ═══════════════════════════════════════════════════════════════

def load_watchlist():
    """加载自选列表"""
    if WATCHLIST_FILE.exists():
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    save_watchlist(DEFAULT_WATCHLIST)
    return DEFAULT_WATCHLIST


def save_watchlist(watchlist):
    """保存自选列表"""
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)


def add_to_watchlist(code, market="a_share"):
    """添加到自选"""
    watchlist = load_watchlist()
    cat = market if market in ("a_share", "us") else "a_share"
    for item in watchlist.get(cat, []):
        item_code = item if isinstance(item, str) else item.get("code", "")
        if item_code == code:
            return watchlist
    # 查找ETF名称
    etf_info = next((e for e in ALL_ETFS if e["code"] == code), None)
    name = etf_info["name"] if etf_info else code
    mkt = etf_info["market"] if etf_info else "1"
    watchlist.setdefault(cat, []).append({"code": code, "name": name, "market": mkt})
    save_watchlist(watchlist)
    return watchlist


def remove_from_watchlist(code, market="a_share"):
    """从自选移除"""
    watchlist = load_watchlist()
    cat = market if market in ("a_share", "us") else "a_share"
    watchlist[cat] = [item for item in watchlist.get(cat, [])
                      if (item if isinstance(item, str) else item.get("code", "")) != code]
    save_watchlist(watchlist)
    return watchlist


def get_watchlist_data():
    """获取自选ETF数据（含实时行情+因子）"""
    watchlist = load_watchlist()
    all_data = generate_etf_data()
    
    result = {"a_share": [], "us": []}
    
    for category in ["a_share", "us"]:
        for item in watchlist.get(category, []):
            # 兼容两种格式：纯代码字符串 或 {"code": "xxx", "name": "xxx"}
            if isinstance(item, str):
                code = item
                item_name = code
            else:
                code = item.get("code", "")
                item_name = item.get("name", code)
            if code in all_data:
                result[category].append(all_data[code])
            else:
                result[category].append({
                    "code": code,
                    "name": item_name,
                    "market": item.get("market", "1") if isinstance(item, dict) else "1",
                    "price": 0, "change_pct": 0, "volume": 0,
                    "factor_mom": 50, "factor_mr": 50, "factor_vol": 50,
                    "factor_flow": 50, "factor_ms": 50, "factor_regime": 50,
                })
    
    for category in result:
        result[category].sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    
    return result


def get_etf_detail(code):
    """获取ETF详细信息"""
    all_data = generate_etf_data()
    return all_data.get(code, None)


def get_sector_etfs():
    """获取行业ETF分类"""
    all_data = generate_etf_data()
    result = {}
    
    for cat, etfs in ETF_UNIVERSE.items():
        result[cat] = []
        for etf in etfs:
            code = etf["code"]
            if code in all_data:
                result[cat].append(all_data[code])
        result[cat].sort(key=lambda x: x.get("change_pct", 0), reverse=True)
    
    return result


def search_etfs(keyword, limit=20):
    """搜索ETF"""
    all_data = generate_etf_data()
    results = []
    keyword = keyword.lower()
    
    for code, info in all_data.items():
        if keyword in code or keyword in info.get("name", "").lower():
            results.append(info)
            if len(results) >= limit:
                break
    
    return results


# 初始化
if not WATCHLIST_FILE.exists():
    save_watchlist(DEFAULT_WATCHLIST)
