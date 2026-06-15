"""
双轨融合引擎 v1.0
Track A (AI定性) + Track B (数学定量) → 最终ETF排序

用法:
  python fusion_engine.py                 # 使用data.json中的数据
  python fusion_engine.py --update        # 拉取TDX最新数据后融合
"""

import json, sys
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data.json"
REPORT_FILE = Path(__file__).parent / "fusion_report.json"


# ── Track A: AI体系权重（来自systematic-factor-monitor Skill）──
TRACK_A_WEIGHTS = {
    "L0_liquidity": {"宽松": 1.10, "中性": 1.00, "收紧": 0.80},
    "L4b_rebalance": 1.25,   # 指数调仓效应
    "L1_sector": 1.00,
    "L4_supply_demand": 1.00,
    "L5_catalyst": 1.00,
}


# ── Track B: 数学体系权重（来自quant-math-engine Skill）──
TRACK_B_WEIGHTS = {
    "momentum": 0.35,
    "mean_reversion": 0.15,
    "volatility": 0.10,
    "fund_flow": 0.25,
    "microstructure": 0.10,
    "regime": 0.05,
}


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


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
            "score_b": score,
            "chg_pct": data.get("chg_pct", 0),
            "price": data.get("price", 0),
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
    """
    双轨融合
    tracks: Track B排名结果
    factors: 因子状态（L0/L4b等）
    返回: 融合后的最终排名
    """
    # Track A权重调整
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
        # 基础分 = Track B得分
        base = t["score_b"]
        # 流动性调整
        adj_liq = base * (liq_mult - 1.0)
        # 调仓调整（仅对有调仓事件的ETF）
        adj_reb = 0
        if events:
            for ev in events:
                if t["name"] in ev.get("etf", ""):
                    adj_reb = base * (rebalance_mult - 1.0)
                    break
        # 最终融合分
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
        advice.append(f"🟢 FOMC鸽派概率{fp.get('dove',0)}%，可持仓")
    if factors.get("L4b_events"):
        advice.append("📅 近期有指数调仓事件，相关ETF提前布局")

    report = {
        "generated_at": datetime.now().isoformat(),
        "fusion_type": "Track A + Track B 双轨融合",
        "rankings": tracks,
        "factors": factors,
        "advice": advice,
        "weights": {
            "track_b": TRACK_B_WEIGHTS,
            "track_a": TRACK_A_WEIGHTS,
        }
    }
    return report


def print_report(report: dict):
    """打印融合报告（Windows安全输出）"""
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print(f"\n{'='*60}")
    print(f"  双轨融合报告 | {report['generated_at']}")
    print(f"{'='*60}\n")
    print(f"{'排名':<4} {'ETF':<14} {'融合分':<8} {'Track B':<10} {'流动性adj':<10} {'调仓adj':<10} {'涨跌%':<8}")
    print(f"{'-'*64}")
    for t in report["rankings"]:
        print(f"#{t['rank_fused']:<3} {t['name']:<12} {t['score_fused']:<8.1f} "
              f"{t['score_b']:<10.1f} {t.get('adj_liq',0):<+10.1f} {t.get('adj_reb',0):<+10.1f} "
              f"{t['chg_pct']:<+8.2f}")
    print(f"\n操作建议:")
    for a in report.get("advice", []):
        print(f"  {a}")
    print()


if __name__ == "__main__":
    data = load_data()
    etfs = data.get("etfs", {})
    factors = data.get("factors", {})

    # Track B排名
    tracks = rank_by_track_b(etfs)
    # 双轨融合
    fused = fuse(tracks, factors)
    # 生成报告
    report = generate_report(fused, factors)
    # 打印
    print_report(report)
    # 保存
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告已保存: {REPORT_FILE}")
