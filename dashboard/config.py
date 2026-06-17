"""
九章量化局 · 统一配置文件 v1.0
所有配置集中管理，替代散落的硬编码
"""
from pathlib import Path

# ── 服务器 ──
PORT = 7860
BIND_ADDR = "0.0.0.0"
DEBUG = False

# ── 目录 ──
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR
ARTIFACTS_DIR = BASE_DIR / "artifacts"
LOGS_DIR = BASE_DIR / "logs"

# ── 数据源 ──
TDX_ENABLED = False  # 关闭通达信subprocess，使用缓存+模拟
ETF_CACHE_TTL = 120   # ETF缓存有效期(秒)

# ── 预测参数 ──
CALIBRATION_FACTOR = 0.6
DEFAULT_WEIGHTS = {
    "momentum": 0.35,
    "fund_flow": 0.25,
    "mean_reversion": 0.15,
    "volatility": 0.08,
    "microstructure": 0.07,
    "regime": 0.10
}

# ── 自动化 ──
AUTO_PREDICT_TIME = "09:00"   # 自动预测时间
AUTO_RECAP_TIME = "15:30"     # 自动复盘时间

# ── 确保目录存在 ──
ARTIFACTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
