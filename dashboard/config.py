"""
九章量化局 · 全局配置
"""

import os
from pathlib import Path

# ── 服务器配置 ──
PORT = int(os.environ.get("JIUZHANG_PORT", 7860))
BIND_ADDR = "0.0.0.0"

# ── 数据源配置 ──
# 优先级：腾讯行情API（免费、零依赖、覆盖全A股ETF）
DATA_SOURCE = "tencent"  # "tencent" | "mock"
TENCENT_REALTIME_URL = "http://qt.gtimg.cn/q="
TENCENT_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

# ── 缓存配置 ──
CACHE_TTL_REALTIME = 30        # 实时行情缓存30秒
CACHE_TTL_KLINE = 3600 * 4     # K线缓存4小时
CACHE_TTL_FACTOR = 600         # 因子缓存10分钟
CACHE_TTL_STALE_MAX = 86400    # 过期缓存最大容忍24小时

# ── 因子计算参数 ──
FACTOR_MOMENTUM_WINDOW = 20    # 动量因子窗口（天）
FACTOR_MR_WINDOW = 20          # 均值回归窗口
FACTOR_VOL_WINDOW = 20         # 波动率窗口
FACTOR_FLOW_WINDOW = 20        # 资金流窗口
FACTOR_MS_WINDOW = 10          # 微观结构窗口
FACTOR_REGIME_WINDOW = 60      # 市场环境窗口
KLINE_HISTORY_DAYS = 120       # K线获取天数

# ── 因子权重 ──
TRACK_B_WEIGHTS = {
    "momentum": 0.35,
    "mean_reversion": 0.15,
    "volatility": 0.10,
    "fund_flow": 0.25,
    "microstructure": 0.07,
    "regime": 0.08,
}

CALIBRATION_FACTOR = 0.6  # 校准系数

# ── 路径 ──
DATA_DIR = Path(__file__).parent
ARTIFACTS_DIR = DATA_DIR / "artifacts"
CACHE_DIR = DATA_DIR / "cache"
