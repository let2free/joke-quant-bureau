"""
数据更新桥接脚本
Agent每次调用TDX后，把结果写入data.json供看板读取
用法: import update_dashboard; update_dashboard.push(data_dict)
"""
import json, os
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data.json"

def push(data: dict):
    """Agent调用此函数更新看板数据"""
    data["updated_at"] = datetime.now().isoformat()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return f"看板数据已更新 @ {data['updated_at']}"

def load():
    """读取当前看板数据"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def merge_etf(etf_code: str, **kwargs):
    """合并更新单只ETF数据（不覆盖其他ETF）"""
    data = load()
    if "etfs" not in data:
        data["etfs"] = {}
    if etf_code not in data["etfs"]:
        data["etfs"][etf_code] = {}
    data["etfs"][etf_code].update(kwargs)
    return push(data)

def update_factors(**kwargs):
    """更新因子状态"""
    data = load()
    if "factors" not in data:
        data["factors"] = {}
    data["factors"].update(kwargs)
    return push(data)

if __name__ == "__main__":
    # 测试：写入示例数据
    sample = {
        "indices": {
            "上证指数": {"code": "000001", "price": 4096.00, "chg_pct": 1.61},
            "深证成指": {"code": "399001", "price": 14963.41, "chg_pct": 3.79},
            "创业板指": {"code": "399006", "price": 4033.00, "chg_pct": 5.30},
            "科创50":   {"code": "000688", "price": 1680.00, "chg_pct": 5.12},
        },
        "etfs": {
            "515880": {"name": "通信ETF",   "price": 3.450, "chg_pct": 6.63, "score_b": 76.0,
                       "factor_mom": 92, "factor_mr": 45, "factor_flow": 88, "factor_ms": 20, "factor_vol": 65, "factor_regime": 70},
            "588000": {"name": "科创50ETF", "price": 1.850, "chg_pct": 5.01, "score_b": 79.0,
                       "factor_mom": 85, "factor_mr": 52, "factor_flow": 75, "factor_ms": 95, "factor_vol": 60, "factor_regime": 70},
            "560780": {"name": "半导体设备ETF", "price": 3.100, "chg_pct": 4.75, "score_b": 73.7,
                       "factor_mom": 88, "factor_mr": 48, "factor_flow": 72, "factor_ms": 15, "factor_vol": 70, "factor_regime": 70},
            "562500": {"name": "机器人ETF", "price": 0.920, "chg_pct": 3.13, "score_b": 68.0,
                       "factor_mom": 55, "factor_mr": 60, "factor_flow": 45, "factor_ms": 10, "factor_vol": 55, "factor_regime": 70},
            "516160": {"name": "新能源ETF", "price": 2.300, "chg_pct": 2.06, "score_b": 62.0,
                       "factor_mom": 40, "factor_mr": 70, "factor_flow": 35, "factor_ms": 5,  "factor_vol": 50, "factor_regime": 70},
            "516080": {"name": "创新药ETF", "price": 0.570, "chg_pct": -0.51, "score_b": 55.0,
                       "factor_mom": 20, "factor_mr": 80, "factor_flow": 25, "factor_ms": 5,  "factor_vol": 40, "factor_regime": 70},
        },
        "factors": {
            "L0_liquidity": "🟡 中性偏宽松（置信度70%）",
            "L4b_events": [{"etf": "科创50ETF", "event": "指数调仓效应已发生（6/12）", "impact": "🟢 强"}],
            "market_regime": "🟡 震荡偏多",
            "fomc_prob": {"dove": 40, "neutral": 35, "hawk": 25},
        },
        "agent_status": {
            "指挥官": "🟢 在线", "大A": "🟡 待命", "老美": "🟡 待命",
            "军机处": "🟡 待命", "量化1哥": "🟡 待命", "包青天": "🟡 待命",
        }
    }
    print(push(sample))
