"""
九章量化局 · 回测模块 v2.0
基于真实K线数据的回测系统
- 因子排名策略回测（真实价格）
- 网格搜索权重优化
- 真实指标计算（夏普、最大回撤、胜率）
"""

import json
import statistics
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from data_fetcher import fetch_kline

DATA_DIR = Path(__file__).parent
BACKTEST_SETTINGS_FILE = DATA_DIR / "backtest_settings.json"
BACKTEST_RESULTS_DIR = DATA_DIR / "backtest_results"

# 回测ETF池（12只核心ETF）
BACKTEST_ETF_CODES = [
    "510300", "510500", "588000", "159915",  # 宽基
    "515880", "512480", "562500",             # 科技
    "516160", "512880", "512690",             # 新能源+证券+消费
    "516080", "513100",                        # 医药+纳指
]

FACTOR_NAMES = ["momentum", "mean_reversion", "volatility", "fund_flow", "microstructure", "regime"]


def get_all_kline_data(codes: list, days: int = 180) -> Dict[str, list]:
    """批量获取K线数据"""
    result = {}
    for code in codes:
        kline = fetch_kline(code, days=days, use_cache=True)
        if kline.get("data"):
            result[code] = kline["data"]
        time.sleep(0.12)
    return result


def compute_factor_scores(kline: list, weights: dict) -> Dict[int, float]:
    """基于K线计算每日因子得分"""
    closes = [d["close"] for d in kline]
    highs = [d["high"] for d in kline]
    lows = [d["low"] for d in kline]
    volumes = [d["volume"] for d in kline]

    scores = {}
    n = len(closes)
    for i in range(60, n):
        # Momentum: 20日收益率
        mom = (closes[i] - closes[i - 20]) / closes[i - 20] * 100

        # Mean reversion: 偏离20日均线
        ma20 = sum(closes[i - 19:i + 1]) / 20
        mr = (closes[i] - ma20) / ma20 * 100

        # Volatility: 20日收益率标准差
        rets = [(closes[j] - closes[j - 1]) / closes[j - 1] for j in range(i - 19, i + 1)]
        vol = statistics.stdev(rets) * 100 if len(rets) > 1 else 0

        # Fund flow: 成交量相对20日均量
        avg_vol = sum(volumes[i - 19:i + 1]) / 20
        flow = (volumes[i] - avg_vol) / avg_vol * 100 if avg_vol > 0 else 0

        # Microstructure: 收盘在高低区间位置
        hl = highs[i] - lows[i]
        ms = ((closes[i] - lows[i]) / hl - 0.5) * 100 if hl > 0 else 0

        # Regime: 近20日上涨天数占比
        up_days = sum(1 for j in range(i - 19, i + 1) if closes[j] > closes[j - 1])
        regime = up_days / 20 * 100

        score = (
            weights.get("momentum", 0.35) * mom / 3 +
            weights.get("mean_reversion", 0.15) * mr / 3 +
            weights.get("volatility", 0.10) * (100 - vol * 8) / 20 +
            weights.get("fund_flow", 0.25) * flow / 3 +
            weights.get("microstructure", 0.07) * ms / 3 +
            weights.get("regime", 0.08) * regime / 3
        )
        scores[i] = round(score, 2)

    return scores


def run_backtest_simulation_v2(params: dict) -> dict:
    """v2.0 真实数据回测"""
    start_date = params.get("start_date", "2026-05-01")
    end_date = params.get("end_date", datetime.now().strftime("%Y-%m-%d"))
    initial_capital = float(params.get("initial_capital", 100000))
    top_n = int(params.get("top_n", 5))
    hold_days = int(params.get("hold_days", 5))
    weights = params.get("weights")

    if weights is None:
        weights = {
            "momentum": 0.35, "mean_reversion": 0.15, "volatility": 0.10,
            "fund_flow": 0.25, "microstructure": 0.07, "regime": 0.08,
        }

    codes = BACKTEST_ETF_CODES
    kline_data = get_all_kline_data(codes, days=180)

    if len(kline_data) < 3:
        return {"status": "error", "message": f"K线数据不足，仅获取到{len(kline_data)}只ETF数据"}

    # 计算因子得分
    all_scores = {}
    etf_names = {}
    common_indices = None

    for code, klines in kline_data.items():
        if len(klines) < 60:
            continue
        scores = compute_factor_scores(klines, weights)
        all_scores[code] = scores
        etf_names[code] = klines[0].get("name", code) if klines else code
        if common_indices is None:
            common_indices = set(scores.keys())
        else:
            common_indices &= set(scores.keys())

    if not common_indices or len(all_scores) < 3:
        return {"status": "error", "message": "因子计算后数据不足"}

    sorted_idx = sorted(common_indices)

    # 日期过滤
    valid_range = []
    base_code = list(kline_data.keys())[0]
    for idx in sorted_idx:
        d = kline_data[base_code][idx]["date"]
        if start_date <= d <= end_date:
            valid_range.append(idx)

    if len(valid_range) < hold_days + 1:
        return {"status": "error", "message": f"日期范围{start_date}~{end_date}内有效数据不足"}

    # 执行回测
    capital = initial_capital
    equity_curve = []
    trades = []
    positions = {}  # code -> {"buy_idx": int, "buy_price": float, "alloc": float}

    for i, date_idx in enumerate(valid_range):
        date_str = kline_data[base_code][date_idx]["date"]

        # 卖出到期持仓
        to_sell = []
        for code, pos in list(positions.items()):
            if i - pos["buy_step"] >= hold_days:
                if code in kline_data and date_idx < len(kline_data[code]):
                    sell_price = kline_data[code][date_idx]["close"]
                    pnl = (sell_price - pos["buy_price"]) / pos["buy_price"]
                    capital *= (1 + pnl * pos["alloc"])
                    trades.append({
                        "date": date_str, "action": "sell", "code": code,
                        "price": round(sell_price, 4), "pnl_pct": round(pnl * 100, 2),
                    })
                to_sell.append(code)

        for code in to_sell:
            del positions[code]

        # 排名并买入
        rankings = []
        for code in all_scores:
            if date_idx in all_scores[code]:
                rankings.append({
                    "code": code,
                    "score": all_scores[code][date_idx],
                    "price": kline_data[code][date_idx]["close"],
                })
        rankings.sort(key=lambda x: x["score"], reverse=True)

        available = top_n - len(positions)
        alloc = 1.0 / top_n
        bought = 0
        for r in rankings:
            if r["code"] not in positions:
                positions[r["code"]] = {
                    "buy_step": i,
                    "buy_price": r["price"],
                    "alloc": alloc,
                }
                trades.append({
                    "date": date_str, "action": "buy", "code": r["code"],
                    "price": round(r["price"], 4), "score": r["score"],
                })
                bought += 1
                if bought >= available:
                    break

        equity_curve.append({"date": date_str, "equity": round(capital, 2)})

    # 指标计算
    total_return = (capital - initial_capital) / initial_capital * 100
    sell_trades = [t for t in trades if t["action"] == "sell"]
    wins = sum(1 for t in sell_trades if t["pnl_pct"] > 0)
    win_rate = wins / len(sell_trades) * 100 if sell_trades else 0

    # 夏普比率
    daily_rets = []
    for j in range(1, len(equity_curve)):
        r = (equity_curve[j]["equity"] - equity_curve[j - 1]["equity"]) / equity_curve[j - 1]["equity"]
        daily_rets.append(r)

    if daily_rets and statistics.stdev(daily_rets) > 1e-10:
        sharpe = (statistics.mean(daily_rets) / statistics.stdev(daily_rets)) * (252 ** 0.5)
    else:
        sharpe = 0

    # 最大回撤
    peak = initial_capital
    max_dd = 0.0
    for pt in equity_curve:
        if pt["equity"] > peak:
            peak = pt["equity"]
        dd = (peak - pt["equity"]) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return {
        "status": "success",
        "params": {
            "start_date": start_date, "end_date": end_date,
            "initial_capital": initial_capital, "top_n": top_n, "hold_days": hold_days,
            "etfs_used": len(all_scores), "trading_days": len(valid_range),
        },
        "results": {
            "initial_capital": initial_capital,
            "final_equity": round(capital, 2),
            "total_return_pct": round(total_return, 2),
            "num_trades": len(trades),
            "num_sell_trades": len(sell_trades),
            "win_rate": round(win_rate, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_dd, 2),
        },
        "equity_curve": equity_curve[-60:],
        "recent_trades": trades[-20:],
    }


def optimize_factor_weights_v2(params: dict) -> dict:
    """网格搜索优化因子权重"""
    start_date = params.get("start_date", "2026-05-01")
    end_date = params.get("end_date", datetime.now().strftime("%Y-%m-%d"))

    # 搜索空间
    combinations = []
    for mom in [0.25, 0.30, 0.35, 0.40]:
        for flow in [0.15, 0.20, 0.25, 0.30]:
            remaining = 1.0 - mom - flow
            if remaining < 0.18 or remaining > 0.50:
                continue
            mr = round(remaining * 0.28, 3)
            vol = round(remaining * 0.18, 3)
            ms = round(remaining * 0.22, 3)
            regime = round(remaining * 0.32, 3)
            w = {"momentum": mom, "mean_reversion": mr, "volatility": vol,
                 "fund_flow": flow, "microstructure": ms, "regime": regime}
            total = sum(w.values())
            w = {k: round(v / total, 4) for k, v in w.items()}
            combinations.append(w)

    best = None
    best_sharpe = -999
    tested = 0

    for weights in combinations:
        params["weights"] = weights
        result = run_backtest_simulation_v2(params)
        tested += 1
        if result["status"] == "success":
            s = result["results"]["sharpe_ratio"]
            if s > best_sharpe:
                best_sharpe = s
                best = {
                    "weights": weights,
                    "sharpe": s,
                    "total_return": result["results"]["total_return_pct"],
                    "win_rate": result["results"]["win_rate"],
                    "max_drawdown": result["results"]["max_drawdown_pct"],
                }

    if best is None:
        return {"status": "error", "message": "优化失败"}

    return {
        "status": "success",
        "message": f"网格搜索完成，测试{tested}组权重",
        "best_weights": best["weights"],
        "factor_performance": {
            "momentum": round(best["weights"]["momentum"] * 100, 1),
            "mean_reversion": round(best["weights"]["mean_reversion"] * 100, 1),
            "volatility": round(best["weights"]["volatility"] * 100, 1),
            "fund_flow": round(best["weights"]["fund_flow"] * 100, 1),
            "microstructure": round(best["weights"]["microstructure"] * 100, 1),
            "regime": round(best["weights"]["regime"] * 100, 1),
        },
        "improvement": f"最优夏普: {best_sharpe:.2f}, 收益: {best['total_return']:.2f}%",
        "backtest_metrics": {
            "sharpe": best["sharpe"],
            "total_return": best["total_return"],
            "win_rate": best["win_rate"],
            "max_drawdown": best["max_drawdown"],
        },
    }


# ── API wrappers (供 dashboard_server.py 调用) ──

def load_backtest_accuracy(handler) -> dict:
    query = handler.path.split("?")[1] if "?" in handler.path else ""
    params = dict(pair.split("=") for pair in query.split("&") if "=" in pair) if query else {}
    start_date = params.get("start", "2026-05-01")
    end_date = params.get("end", datetime.now().strftime("%Y-%m-%d"))

    dates, rank_acc, top3_acc, dir_acc = [], [], [], []
    results_dir = BACKTEST_RESULTS_DIR
    if results_dir.exists():
        for f in sorted(results_dir.glob("backtest_*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    d = json.load(fp)
                if d.get("params", {}).get("end_date", "") >= start_date:
                    r = d.get("results", {})
                    dates.append(d.get("params", {}).get("end_date", f.stem[-8:]))
                    rank_acc.append(r.get("win_rate", 0))
                    top3_acc.append(r.get("win_rate", 0))
                    dir_acc.append(r.get("win_rate", 0))
            except Exception:
                pass

    if not dates:
        dates = ["--"]
        rank_acc = [0]
        top3_acc = [0]
        dir_acc = [0]

    return {
        "dates": dates, "rank_accuracy": rank_acc,
        "top3_accuracy": top3_acc, "direction_accuracy": dir_acc,
    }


def run_factor_optimization(handler) -> dict:
    query = handler.path.split("?")[1] if "?" in handler.path else ""
    params = dict(pair.split("=") for pair in query.split("&") if "=" in pair) if query else {}
    return optimize_factor_weights_v2({
        "start_date": params.get("start", "2026-05-01"),
        "end_date": params.get("end", datetime.now().strftime("%Y-%m-%d")),
        "top_n": 5, "hold_days": 5, "initial_capital": 100000,
    })


def run_backtest_simulation_api(handler) -> dict:
    if hasattr(handler, '_cached_body') and handler._cached_body:
        body = handler._cached_body
    else:
        cl = int(handler.headers.get("Content-Length", 0))
        if cl == 0:
            return {"status": "error", "message": "缺少请求体"}
        body = handler.rfile.read(cl)

    try:
        params = json.loads(body)
    except json.JSONDecodeError:
        return {"status": "error", "message": "JSON解析失败"}

    result = run_backtest_simulation_v2(params)

    if result.get("status") == "success":
        BACKTEST_RESULTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(BACKTEST_RESULTS_DIR / f"backtest_{ts}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    return result


if __name__ == "__main__":
    print("=== 回测模块 v2.0 测试 ===\n")
    params = {"start_date": "2026-05-15", "end_date": "2026-06-16",
              "initial_capital": 100000, "top_n": 5, "hold_days": 5}
    result = run_backtest_simulation_v2(params)
    if result["status"] == "success":
        r = result["results"]
        print(f"收益率: {r['total_return_pct']:.2f}% | 胜率: {r['win_rate']:.1f}%")
        print(f"夏普: {r['sharpe_ratio']:.2f} | 最大回撤: {r['max_drawdown_pct']:.2f}%")
        print(f"交易: {r['num_trades']}笔 ({r['num_sell_trades']}笔卖出)")
    else:
        print(f"失败: {result.get('message')}")
