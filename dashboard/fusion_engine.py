"""
双轨融合引擎 v2.0
Track A (AI定性) + Track B (数学定量) → 最终ETF排序

v2.0: 接入真实数据（etf_data.py → data_fetcher.py → 腾讯API）
"""

import json
import sys
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent
REPORT_FILE = DATA_DIR / "fusion_report.json"

# ── Track A: AI体系权重 ──
TRACK_A_WEIGHTS = {
    "L0_liquidity": {"宽松": 1.10, "中性": 1.00, "收紧": 0.80},
    "L4b_rebalance": 1.25,
    "L1_sector": 1.00,
    "L4_supply_demand": 1.00,
    "L5_catalyst": 1.00,
}

# ── Track B: 数学体系权重 ──
TRACK_B_WEIGHTS = {
    "momentum": 0.35,
    "mean_reversion": 0.15,
    "volatility": 0.10,
    "fund_flow": 0.25,
    "microstructure": 0.07,
    "regime": 0.08,
}


def calc_track_b_score(etf_data: dict) -> float:
    """计算单只ETF的Track B数学打分"""
    w = TRACK_B_WEIGHTS
    score = 0.0
    score += w["momentum"]       * (etf_data.get("factor_mom", 50) or 50)
    score += w["mean_reversion"] * (etf_data.get("factor_mr", 50) or 50)
    score += w["volatility"]     * (etf_data.get("factor_vol", 50) or 50)
    score += w["fund_flow"]      * (etf_data.get("factor_flow", 50) or 50)
    score += w["microstructure"] * (etf_data.get("factor_ms", 50) or 50)
    score += w["regime"]         * (etf_data.get("factor_regime", 50) or 50)
    return round(score, 1)


def rank_by_track_b(etfs: dict) -> list:
    """Track B排名"""
    results = []
    for code, data in etfs.items():
        score = calc_track_b_score(data)
        results.append({
            "code": code,
            "name": data.get("name", code),
            "category": data.get("category", ""),
            "score_b": score,
            "chg_pct": data.get("change_pct", 0),
            "price": data.get("price", 0),
            "volume": data.get("volume", 0),
            "amount": data.get("amount", 0),
            "factors": {
                "momentum": data.get("factor_mom", 0),
                "mean_reversion": data.get("factor_mr", 0),
                "volatility": data.get("factor_vol", 0),
                "fund_flow": data.get("factor_flow", 0),
                "microstructure": data.get("factor_ms", 0),
                "regime": data.get("factor_regime", 0),
            }
        })
    results.sort(key=lambda x: x["score_b"], reverse=True)
    for i, r in enumerate(results):
        r["rank_b"] = i + 1
    return results


def fuse(tracks: list, factors: dict) -> list:
    """双轨融合"""
    liquidity = factors.get("L0_liquidity", "")
    if "宽松" in liquidity:
        liq_mult = TRACK_A_WEIGHTS["L0_liquidity"]["宽松"]
    elif "收紧" in liquidity:
        liq_mult = TRACK_A_WEIGHTS["L0_liquidity"]["收紧"]
    else:
        liq_mult = TRACK_A_WEIGHTS["L0_liquidity"]["中性"]

    rebalance_mult = 1.0
    events = factors.get("L4b_events", [])
    if events:
        rebalance_mult = TRACK_A_WEIGHTS["L4b_rebalance"]

    for t in tracks:
        base = t["score_b"]
        adj_liq = base * (liq_mult - 1.0)
        adj_reb = 0
        if events:
            for ev in events:
                if t["name"] in ev.get("etf", ""):
                    adj_reb = base * (rebalance_mult - 1.0)
                    break
        t["score_fused"] = round(base + adj_liq + adj_reb, 1)
        t["adj_liq"] = round(adj_liq, 1)
        t["adj_reb"] = round(adj_reb, 1)

    tracks.sort(key=lambda x: x["score_fused"], reverse=True)
    for i, t in enumerate(tracks):
        t["rank_fused"] = i + 1

    return tracks


def generate_report(tracks: list, factors: dict) -> dict:
    """生成融合报告"""
    fp = factors.get("fomc_prob", {"dove": 40, "neutral": 35, "hawk": 25})
    advice = []
    top = tracks[0] if tracks else None
    if top and top.get("chg_pct", 0) > 3:
        advice.append(f"⚠️ {top['name']} 涨幅较大(+{top['chg_pct']:.2f}%)，注意回调")
    if fp.get("hawk", 0) >= 30:
        advice.append(f"🔴 FOMC鹰派概率{fp['hawk']}%，科技ETF减至5成")
    else:
        advice.append(f"🟢 FOMC鸽派概率{fp.get('dove', 0)}%，可持仓")
    if factors.get("L4b_events"):
        advice.append("📅 近期有指数调仓事件，相关ETF提前布局")

    report = {
        "generated_at": datetime.now().isoformat(),
        "fusion_type": "Track A + Track B 双轨融合",
        "data_source": "腾讯行情API（真实数据）",
        "rankings": tracks,
        "factors": factors,
        "advice": advice,
        "weights": {
            "track_b": TRACK_B_WEIGHTS,
            "track_a": TRACK_A_WEIGHTS,
        }
    }
    return report


def run_fusion(use_real_data: bool = True) -> dict:
    """
    执行完整融合流程
    
    Args:
        use_real_data: True=从etf_data获取真实数据，False=从data.json读取
    """
    if use_real_data:
        from etf_data import generate_etf_data
        etfs = generate_etf_data()
        # 因子状态（简化：基于市场整体判断）
        factors = _infer_market_factors(etfs)
    else:
        data = _load_json_data()
        etfs = data.get("etfs", {})
        factors = data.get("factors", {})
    
    tracks = rank_by_track_b(etfs)
    fused = fuse(tracks, factors)
    report = generate_report(fused, factors)
    return report


def _infer_market_factors(etfs: dict) -> dict:
    """基于ETF数据推断市场因子状态"""
    if not etfs:
        return {"L0_liquidity": "🟡 中性", "L4b_events": [], "market_regime": "🟡 震荡", "fomc_prob": {"dove": 40, "neutral": 35, "hawk": 25}}
    
    # 平均涨跌幅判断市场情绪
    avg_chg = sum(e.get("change_pct", 0) for e in etfs.values()) / len(etfs)
    
    if avg_chg > 2:
        regime = "🟢 强势上涨"
    elif avg_chg > 0.5:
        regime = "🟡 震荡偏多"
    elif avg_chg > -0.5:
        regime = "🟡 震荡"
    elif avg_chg > -2:
        regime = "🟡 震荡偏空"
    else:
        regime = "🔴 弱势下跌"
    
    # 上涨比例判断流动性
    up_count = sum(1 for e in etfs.values() if e.get("change_pct", 0) > 0)
    up_ratio = up_count / len(etfs)
    
    if up_ratio > 0.7:
        liquidity = "🟢 偏宽松"
    elif up_ratio > 0.4:
        liquidity = "🟡 中性"
    else:
        liquidity = "🔴 偏收紧"
    
    return {
        "L0_liquidity": liquidity,
        "L4b_events": [],
        "market_regime": regime,
        "fomc_prob": {"hold": 98.5, "hike": 1.5, "cut": 0.0},
        "fomc_note": "6/18沃什首秀·CME 98.5%维持不变·12月加息概率82%",
        "avg_change_pct": round(avg_chg, 2),
        "up_ratio": round(up_ratio * 100, 1),
    }


def _load_json_data():
    """从data.json读取（兼容旧模式）"""
    data_file = DATA_DIR / "data.json"
    if data_file.exists():
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def print_report(report: dict):
    """打印融合报告"""
    print(f"\n{'='*60}")
    print(f"  双轨融合报告 | {report['generated_at']}")
    print(f"  数据源: {report.get('data_source', '未知')}")
    print(f"{'='*60}\n")
    print(f"{'排名':<4} {'ETF':<14} {'分类':<8} {'融合分':<8} {'Track B':<10} {'涨跌%':<8}")
    print(f"{'-'*62}")
    for t in report["rankings"][:20]:
        print(f"#{t['rank_fused']:<3} {t['name']:<12} {t.get('category',''):<8} {t['score_fused']:<8.1f} "
              f"{t['score_b']:<10.1f} {t['chg_pct']:<+8.2f}")
    print(f"\n操作建议:")
    for a in report.get("advice", []):
        print(f"  {a}")
    print()


if __name__ == "__main__":
    report = run_fusion(use_real_data=True)
    print_report(report)
    
    # 保存报告
    report_dir = DATA_DIR / "artifacts" / datetime.now().strftime("%Y-%m-%d")
    report_dir.mkdir(parents=True, exist_ok=True)
    with open(report_dir / "fusion_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {REPORT_FILE}")
