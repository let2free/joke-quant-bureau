"""
九章量化局 · 实时看板服务器 v3.2
绑定 0.0.0.0，支持局域网多设备访问
v3.0: 接入腾讯行情API，真实数据+真实因子计算
v3.1: 回测真实K线、FOMC FedWatch、异常预警、趋势API
v3.2: 线程池、日志轮转、SQLite持久化、移动端表格溢出修复
"""

import http.server
import socketserver
import json
import os
import threading
import time
import logging
from datetime import datetime
from pathlib import Path

# 导入回测模块
import backtest
from backtest import load_backtest_accuracy, run_factor_optimization, run_backtest_simulation_api

# 导入数据导入模块
from data_importer import importer

# 导入ETF数据模块（v4.0 + data_fetcher）
from etf_data import (
    generate_etf_data, calculate_rankings, get_watchlist_data,
    add_to_watchlist, remove_from_watchlist, get_etf_detail,
    get_sector_etfs, load_watchlist, search_etfs, calc_track_b_score
)
from data_fetcher import fetch_realtime_quotes, fetch_kline, fetch_indices, clear_cache
from fusion_engine import run_fusion, rank_by_track_b
from db import (
    init_db, migrate_from_json,
    get_accuracy_history as db_accuracy_history,
    save_accuracy_history as db_save_accuracy,
    get_collab_log as db_collab_log,
    append_collab_log as db_append_collab,
    get_agents_status as db_agents_status,
    save_agents_status as db_save_agents,
    get_conflicts as db_conflicts,
    save_conflicts as db_save_conflicts,
    get_artifacts as db_artifacts,
    save_artifacts as db_save_artifacts,
    add_accuracy, get_db_stats,
)

# 配置
PORT = 7860
BIND_ADDR = "0.0.0.0"
DATA_DIR = Path(__file__).parent
DATA_FILE = DATA_DIR / "data.json"
LOG_FILE = DATA_DIR / "access.log"
LOG_MAX_SIZE = 2 * 1024 * 1024  # 2MB轮转
LOG_BACKUP_COUNT = 3

# ── 日志轮转配置 ──────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_server_logger = logging.getLogger("dashboard")

# 新数据文件
AGENTS_STATUS_FILE = DATA_DIR / "agents_status.json"
COLLAB_LOG_FILE = DATA_DIR / "collab_log.jsonl"
ARTIFACTS_FILE = DATA_DIR / "artifacts.json"
ACCURACY_FILE = DATA_DIR / "accuracy_history.json"
CONFLICTS_FILE = DATA_DIR / "conflicts.json"

# ── 默认数据（服务启动时的初始值）──────────────────────────
DEFAULT_DATA = {
    "updated_at": datetime.now().isoformat(),
    "indices": {
        "上证指数": {"code": "000001", "price": 4096.00, "chg_pct": 1.61},
        "深证成指": {"code": "399001", "price": 14963.41, "chg_pct": 3.79},
        "创业板指": {"code": "399006", "price": 4033.00, "chg_pct": 5.30},
        "科创50":   {"code": "000688", "price": 1680.00, "chg_pct": 5.12},
    },
    "etfs": {
        "515880": {"name": "通信ETF",   "price": 3.45, "chg_pct": 6.63, "score_a": None, "score_b": 76.0},
        "588000": {"name": "科创50ETF", "price": 1.85, "chg_pct": 5.01, "score_a": None, "score_b": 79.0},
        "560780": {"name": "半导体设备ETF", "price": 3.10, "chg_pct": 4.75, "score_a": None, "score_b": 73.7},
        "562500": {"name": "机器人ETF", "price": 0.92, "chg_pct": 3.13, "score_a": None, "score_b": 68.0},
        "516160": {"name": "新能源ETF", "price": 2.30, "chg_pct": 2.06, "score_a": None, "score_b": 62.0},
        "516080": {"name": "创新药ETF", "price": 0.57, "chg_pct": -0.51, "score_a": None, "score_b": 55.0},
    },
    "factors": {
        "L0_liquidity": "🟡 中性偏宽松（置信度70%）",
        "L4b_events": [
            {"etf": "科创50ETF", "event": "指数调仓效应已发生（6/12）", "impact": "🟢 强"},
        ],
        "market_regime": "🟡 震荡偏多",
        "fomc_prob": {"dove": 40, "neutral": 35, "hawk": 25},
    },
    "agent_status": {
        "指挥官":  "🟢 在线",
        "大A":     "🟡 待命",
        "老美":     "🟡 待命",
        "军机处":   "🟡 待命",
        "量化1哥": "🟡 待命",
        "包青天":   "🟡 待命",
    }
}

DEFAULT_AGENTS_STATUS = {
    "agents": {
        "大A": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "老美": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "军机处": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "量化1哥": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "包青天": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "史官": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "执行者": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "风控": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
        "协调官": {"status": "idle", "current_task": None, "last_update": datetime.now().isoformat(), "tasks_completed": 0, "accuracy": None},
    },
    "last_updated": datetime.now().isoformat()
}

DEFAULT_ACCURACY_HISTORY = [
    {"date": "2026-06-12", "accuracy": 0.33, "etfs_count": 6, "recap_triggered": False},
    {"date": "2026-06-15", "accuracy": 0.50, "etfs_count": 6, "recap_triggered": True},
]


def load_data():
    """读取最新数据文件，不存在则返回默认数据"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_DATA.copy()


def load_agents_status():
    """读取Agent状态（SQLite）"""
    return db_agents_status()


def save_agents_status(data):
    """保存Agent状态（SQLite）"""
    db_save_agents(data)


def load_collab_log():
    """读取协同日志（SQLite）"""
    return db_collab_log()


def append_collab_log(entry):
    """追加一条协同日志（SQLite）"""
    db_append_collab(entry)


def load_artifacts():
    """读取分析产物（SQLite）"""
    return db_artifacts()


def save_artifacts(data):
    """保存分析产物（SQLite）"""
    db_save_artifacts(data)


def load_accuracy_history():
    """读取准确率历史（SQLite）"""
    data = db_accuracy_history()
    return data if data else DEFAULT_ACCURACY_HISTORY.copy()


def save_accuracy_history(data):
    """保存准确率历史（SQLite）"""
    db_save_accuracy(data)


def load_conflicts():
    """读取冲突记录（SQLite）"""
    return db_conflicts()


def save_conflicts(data):
    """保存冲突记录（SQLite）"""
    db_save_conflicts(data)


def log_access(client_ip, path):
    """记录访问日志（带轮转：超过2MB自动轮转，保留3个备份）"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {client_ip} -> {path}\n"
    try:
        # 检查是否需要轮转
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_SIZE:
            for i in range(LOG_BACKUP_COUNT - 1, 0, -1):
                old = DATA_DIR / f"access.log.{i}"
                new = DATA_DIR / f"access.log.{i + 1}"
                if old.exists():
                    old.rename(new)
            backup = DATA_DIR / "access.log.1"
            LOG_FILE.rename(backup)
            _server_logger.info(f"访问日志已轮转 → {backup}")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """自定义请求处理器"""

    def log_message(self, format, *args):
        """静默日志（避免控制台刷屏）"""
        log_access(self.client_address[0], args[0] if args else "-")

    def end_headers(self):
        """添加CORS和缓存控制头"""
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        client_ip = self.client_address[0]
        path = self.path.split("?")[0]

        # 主看板页面
        if path == "/" or path == "/dashboard.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (DATA_DIR / "dashboard.html").read_bytes()
            self.wfile.write(html)

        # 龙虾协同中心页面
        elif path == "/lobster_collab.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (DATA_DIR / "lobster_collab.html").read_bytes()
            self.wfile.write(html)

        # 拓扑分析页面
        elif path == "/topology.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (DATA_DIR / "topology.html").read_bytes()
            self.wfile.write(html)

        # 历史数据页面
        elif path == "/history.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (DATA_DIR / "history.html").read_bytes()
            self.wfile.write(html)

        # 回测页面
        elif path == "/backtest.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (DATA_DIR / "backtest.html").read_bytes()
            self.wfile.write(html)

        # ETF监测页面
        elif path == "/etf_monitor.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (DATA_DIR / "etf_monitor.html").read_bytes()
            self.wfile.write(html)

        # 九章量化局测算中心页面
        elif path == "/jiuzhang.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (DATA_DIR / "jiuzhang.html").read_bytes()
            self.wfile.write(html)

        # API: 实时数据
        elif path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = load_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 服务器状态
        elif path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status = {
                "status": "ok",
                "port": PORT,
                "bind": BIND_ADDR,
                "data_age_seconds": int(time.time() - os.path.getmtime(DATA_FILE)) if DATA_FILE.exists() else -1,
            }
            self.wfile.write(json.dumps(status).encode("utf-8"))

        # API: Agent状态
        elif path == "/api/agents/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = load_agents_status()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 协同日志
        elif path == "/api/collab/log":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            entries = load_collab_log()
            self.wfile.write(json.dumps(entries, ensure_ascii=False).encode("utf-8"))

        # API: 分析产物
        elif path == "/api/analysis/artifacts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = load_artifacts()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 准确率历史
        elif path == "/api/accuracy/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = load_accuracy_history()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 冲突记录
        elif path == "/api/conflicts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = load_conflicts()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 历史数据日期列表
        elif path == "/api/artifacts/list":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            artifacts_dir = DATA_DIR / "artifacts"
            dates = []
            if artifacts_dir.exists():
                dates = sorted([d.name for d in artifacts_dir.iterdir() if d.is_dir()], reverse=True)
            self.wfile.write(json.dumps({"dates": dates}, ensure_ascii=False).encode("utf-8"))

        # API: 导出数据
        elif path == "/api/export":
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Disposition", "attachment; filename=export.csv")
            self.end_headers()
            # 获取查询参数
            params = {}
            if "?" in self.path:
                query = self.path.split("?")[1]
                for pair in query.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
            date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
            # 读取数据并导出CSV
            fusion_file = DATA_DIR / "artifacts" / date / "fusion_report.json"
            if fusion_file.exists():
                with open(fusion_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                csv_content = "排名,ETF代码,ETF名称,Track_B得分,融合得分,涨跌幅\n"
                for r in data.get("rankings", []):
                    csv_content += f"{r.get('rank_fused', '')},{r.get('code', '')},{r.get('name', '')},{r.get('score_b', '')},{r.get('score_fused', '')},{r.get('chg_pct', '')}%\n"
                self.wfile.write(csv_content.encode("utf-8"))
            else:
                self.wfile.write(b"No data for this date.")

        # API: 回测 - 准确率历史
        elif path == "/api/backtest/accuracy":
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                data = load_backtest_accuracy(self)
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False).encode("utf-8"))

        # API: 回测 - 因子优化
        elif path == "/api/backtest/factor-optimize":
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                data = run_factor_optimization(self)
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False).encode("utf-8"))

        # API: ETF排名
        elif path == "/api/etf/rankings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # 获取查询参数
            params = {}
            if "?" in self.path:
                query = self.path.split("?")[1]
                for pair in query.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
            market = params.get('market', 'all')
            sort_by = params.get('sort', 'change_pct')
            top_n = int(params.get('top', '50'))
            data = generate_etf_data()
            rankings = calculate_rankings(data, sort_by, top_n)
            self.wfile.write(json.dumps(rankings, ensure_ascii=False).encode("utf-8"))

        # API: 自选ETF
        elif path == "/api/etf/watchlist":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = get_watchlist_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: ETF详情
        elif path.startswith("/api/etf/detail/"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            code = path.split("/")[-1]
            data = get_etf_detail(code)
            self.wfile.write(json.dumps(data or {}, ensure_ascii=False).encode("utf-8"))

        # API: 行业ETF分类
        elif path == "/api/etf/sectors":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = get_sector_etfs()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 添加自选
        elif path == "/api/etf/watchlist/add" and self.command == "POST":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            body_json = json.loads(body)
            code = body_json.get('code', '')
            market = body_json.get('market', 'a_share')
            result = add_to_watchlist(code, market)
            self.wfile.write(json.dumps({"success": True, "watchlist": result}, ensure_ascii=False).encode("utf-8"))

        # API: 移除自选
        elif path == "/api/etf/watchlist/remove" and self.command == "POST":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            body_json = json.loads(body)
            code = body_json.get('code', '')
            market = body_json.get('market', 'a_share')
            result = remove_from_watchlist(code, market)
            self.wfile.write(json.dumps({"success": True, "watchlist": result}, ensure_ascii=False).encode("utf-8"))

        # API: 刷新数据
        elif path == "/api/etf/refresh":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # 重新生成数据
            data = generate_etf_data()
            rankings = calculate_rankings(data, 'change_pct', 100)
            self.wfile.write(json.dumps({
                "success": True,
                "count": len(rankings),
                "updated_at": datetime.now().isoformat()
            }, ensure_ascii=False).encode("utf-8"))

        # API: 全市场ETF搜索
        elif path.startswith("/api/etf/search"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # 获取查询参数
            params = {}
            if "?" in self.path:
                query = self.path.split("?")[1]
                for pair in query.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
            keyword = params.get('q', '')
            # 搜索ETF
            results = search_etfs(keyword, 20)
            self.wfile.write(json.dumps(results, ensure_ascii=False).encode("utf-8"))

        # API: 获取监测范围配置
        elif path == "/api/etf/monitor/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            config = {
                "total_etfs": 1563,
                "monitoring": load_watchlist(),
                "refresh_interval": 30,
                "data_source": "通达信",
                "last_update": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(config, ensure_ascii=False).encode("utf-8"))

        # API: 预测历史
        elif path == "/api/predictions/history":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            artifacts_dir = DATA_DIR / "artifacts"
            predictions = []
            if artifacts_dir.exists():
                for date_dir in sorted(artifacts_dir.iterdir(), reverse=True):
                    if date_dir.is_dir():
                        fusion_file = date_dir / "fusion_report.json"
                        if fusion_file.exists():
                            try:
                                with open(fusion_file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                    data["date"] = date_dir.name
                                    predictions.append(data)
                            except:
                                pass
            self.wfile.write(json.dumps(predictions[:10], ensure_ascii=False).encode("utf-8"))

        # API: 最新预测
        elif path == "/api/predictions/latest":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            artifacts_dir = DATA_DIR / "artifacts"
            latest = {}
            if artifacts_dir.exists():
                for date_dir in sorted(artifacts_dir.iterdir(), reverse=True):
                    if date_dir.is_dir():
                        fusion_file = date_dir / "fusion_report.json"
                        if fusion_file.exists():
                            try:
                                with open(fusion_file, "r", encoding="utf-8") as f:
                                    latest = json.load(f)
                                    latest["date"] = date_dir.name
                                    break
                            except:
                                pass
            self.wfile.write(json.dumps(latest, ensure_ascii=False).encode("utf-8"))

        # ── 新增：实时数据API ──────────────────────────────────────

        # API: 主要指数实时行情
        elif path == "/api/market/indices":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                result = fetch_indices(use_cache=True)
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"data": {}, "meta": {"error": str(e)}}, ensure_ascii=False).encode("utf-8"))

        # API: 批量实时行情（GET参数codes=sh510300,sh588000,...）
        elif path == "/api/market/realtime":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            params = {}
            if "?" in self.path:
                for pair in self.path.split("?")[1].split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
            codes_str = params.get("codes", "")
            if codes_str:
                codes = [c.strip() for c in codes_str.split(",") if c.strip()]
                result = fetch_realtime_quotes(codes, use_cache=True)
            else:
                # 返回全部监控ETF
                all_data = generate_etf_data()
                result = {"data": {k: v for k, v in all_data.items()}, "meta": {"count": len(all_data)}}
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        # API: K线数据（GET参数code=sh510300&days=60）
        elif path == "/api/market/kline":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            params = {}
            if "?" in self.path:
                for pair in self.path.split("?")[1].split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
            code = params.get("code", "sh510300")
            days = int(params.get("days", "60"))
            result = fetch_kline(code, days, use_cache=True)
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

        # API: 融合报告（实时计算）
        elif path == "/api/fusion/report":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                report = run_fusion(use_real_data=True)
                # 保存到artifacts
                report_dir = DATA_DIR / "artifacts" / datetime.now().strftime("%Y-%m-%d")
                report_dir.mkdir(parents=True, exist_ok=True)
                with open(report_dir / "fusion_report.json", "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                self.wfile.write(json.dumps(report, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False).encode("utf-8"))

        # API: 因子详情（GET参数code=510300 或 不传返回全部）
        elif path == "/api/fusion/factors":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            params = {}
            if "?" in self.path:
                for pair in self.path.split("?")[1].split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
            code = params.get("code", "")
            all_data = generate_etf_data()
            if code:
                etf = all_data.get(code, {})
                factors = {
                    "code": code,
                    "name": etf.get("name", ""),
                    "factors": {k: v for k, v in etf.items() if k.startswith("factor_")},
                    "score_b": calc_track_b_score(etf),
                }
                self.wfile.write(json.dumps(factors, ensure_ascii=False).encode("utf-8"))
            else:
                factors_list = []
                for c, etf in all_data.items():
                    factors_list.append({
                        "code": c,
                        "name": etf.get("name", ""),
                        "category": etf.get("category", ""),
                        "factors": {k: v for k, v in etf.items() if k.startswith("factor_")},
                        "score_b": calc_track_b_score(etf),
                    })
                factors_list.sort(key=lambda x: x["score_b"], reverse=True)
                self.wfile.write(json.dumps(factors_list, ensure_ascii=False).encode("utf-8"))

        # API: 清除数据缓存（强制刷新）
        elif path == "/api/cache/clear":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            clear_cache()
            self.wfile.write(json.dumps({"success": True, "message": "缓存已清除"}, ensure_ascii=False).encode("utf-8"))

        # API: 异常预警
        elif path == "/api/alerts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                all_data = generate_etf_data()
                alerts = []
                for code, etf in all_data.items():
                    chg = etf.get("change_pct", 0)
                    vol = etf.get("turnover_rate", 0)
                    score_b = calc_track_b_score(etf)
                    if abs(chg) > 5:
                        alerts.append({"code": code, "name": etf.get("name", ""), "type": "extreme_move",
                                        "message": f"{'暴涨' if chg > 0 else '暴跌'} {chg:+.2f}%", "severity": "high"})
                    elif vol > 15:
                        alerts.append({"code": code, "name": etf.get("name", ""), "type": "high_turnover",
                                        "message": f"换手率 {vol:.1f}%", "severity": "medium"})
                    elif score_b < 30:
                        alerts.append({"code": code, "name": etf.get("name", ""), "type": "weak_score",
                                        "message": f"TrackB得分仅{score_b:.0f}", "severity": "low"})
                indices = fetch_indices(use_cache=True)
                for name, idx in indices.get("data", {}).items():
                    if abs(idx.get("change_pct", 0)) > 3:
                        alerts.append({"code": name, "name": name, "type": "index_extreme",
                                        "message": f"{name} {'涨' if idx['change_pct'] > 0 else '跌'} {idx['change_pct']:+.2f}%",
                                        "severity": "high"})
                self.wfile.write(json.dumps({"alerts": alerts, "count": len(alerts),
                    "updated_at": datetime.now().isoformat()}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"alerts": [], "error": str(e)}, ensure_ascii=False).encode("utf-8"))

        # API: 波动率趋势（基于真实K线）
        elif path == "/api/trends/volatility":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                from backtest import get_all_kline_data
                kline = get_all_kline_data(["510300", "159915", "588000"], days=30)
                dates = []
                sse_vol = []
                cyb_vol = []
                kc_vol = []
                import statistics
                for code, key in [("510300", sse_vol), ("159915", cyb_vol), ("588000", kc_vol)]:
                    if code in kline:
                        data = kline[code]
                        for i in range(1, len(data)):
                            if i == 1:
                                dates.append(data[i]["date"][-5:])
                            rets = []
                            start = max(0, i - 5)
                            for j in range(start, i):
                                if data[j]["close"] > 0:
                                    rets.append((data[j+1]["close"] - data[j]["close"]) / data[j]["close"])
                            if rets:
                                key.append(round(statistics.stdev(rets) * 100, 2) if len(rets) > 1 else 0)
                self.wfile.write(json.dumps({
                    "dates": dates[-14:],
                    "上证指数": sse_vol[-14:] if sse_vol else [],
                    "创业板指": cyb_vol[-14:] if cyb_vol else [],
                    "科创50": kc_vol[-14:] if kc_vol else [],
                }, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))

        # API: 因子趋势（近7日）
        elif path == "/api/trends/factors":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                from backtest import get_all_kline_data, compute_factor_scores, BACKTEST_ETF_CODES
                from config import TRACK_B_WEIGHTS
                kline = get_all_kline_data(BACKTEST_ETF_CODES[:6], days=30)
                factor_history = {"momentum": [], "mean_reversion": [], "volatility": [], "fund_flow": [], "microstructure": [], "regime": []}
                dates = []
                for code, klines in kline.items():
                    if len(klines) < 10:
                        continue
                    scores = compute_factor_scores(klines, TRACK_B_WEIGHTS)
                    sorted_idx = sorted(scores.keys())
                    if not dates:
                        dates = [klines[i]["date"][-5:] for i in sorted_idx[-7:]]
                    for i in sorted_idx[-7:]:
                        idx = sorted_idx[-7:].index(i)
                        for fname in factor_history:
                            val = scores[i]
                            if len(factor_history[fname]) <= idx:
                                factor_history[fname].append(val)
                            else:
                                factor_history[fname][idx] += val
                    break  # 取第一只ETF
                result = {"dates": dates}
                for fname in factor_history:
                    result[fname] = [round(v, 1) for v in factor_history[fname]] if factor_history[fname] else []
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))

        # API: 回测设置（backtest.html用）
        elif path == "/api/backtest/settings":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            from config import TRACK_B_WEIGHTS
            self.wfile.write(json.dumps({
                "backtest_settings": {"initial_capital": 100000, "top_n": 5, "hold_days": 5},
                "weights_history": [{"weights": TRACK_B_WEIGHTS}],
            }, ensure_ascii=False).encode("utf-8"))

        # API: 监控池配置（扩展后）
        elif path == "/api/etf/universe":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            from etf_data import ETF_UNIVERSE, ALL_ETFS
            universe = {cat: [e["code"] for e in etfs] for cat, etfs in ETF_UNIVERSE.items()}
            self.wfile.write(json.dumps({
                "total": len(ALL_ETFS),
                "categories": universe,
                "data_source": "腾讯行情API",
                "refresh_interval": 30,
            }, ensure_ascii=False).encode("utf-8"))

        # API: 数据库统计（v3.2新增）
        elif path == "/api/db/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(get_db_stats(), ensure_ascii=False).encode("utf-8"))

        # ── 原有API保持不变 ──

        # 访问日志
        elif path == "/log":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            if LOG_FILE.exists():
                self.wfile.write(LOG_FILE.read_bytes())
            else:
                self.wfile.write(b"No logs yet.")

        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        """处理CORS预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        """处理POST请求（更新数据）"""
        path = self.path.split("?")[0]
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'

        # API: 更新Agent状态
        if path == "/api/agents/status":
            try:
                data = json.loads(body)
                save_agents_status(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))

        # API: 追加协同日志
        elif path == "/api/collab/log":
            try:
                entry = json.loads(body)
                append_collab_log(entry)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))

        # API: 更新分析产物
        elif path == "/api/analysis/artifacts":
            try:
                data = json.loads(body)
                save_artifacts(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))

        # API: 更新准确率历史
        elif path == "/api/accuracy/history":
            try:
                data = json.loads(body)
                save_accuracy_history(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))

        # API: 更新冲突记录
        elif path == "/api/conflicts":
            try:
                data = json.loads(body)
                save_conflicts(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, str(e))

        # API: 回测 - 运行回测
        elif path == "/api/backtest/run":
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                # 将body注入handler供backtest模块读取
                self._cached_body = body
                data = run_backtest_simulation_api(self)
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False).encode("utf-8"))

        # API: 导入历史数据
        elif path == "/api/import":
            try:
                # 解析multipart/form-data
                content_type = self.headers.get('Content-Type', '')
                if 'multipart/form-data' not in content_type:
                    raise ValueError("Expected multipart/form-data")
                
                # 提取boundary
                boundary = content_type.split('boundary=')[1].encode()
                
                # 解析body
                parts = body.split(b'--' + boundary)
                form_data = {}
                file_data = None
                file_name = None
                
                for part in parts:
                    if b'Content-Disposition' not in part:
                        continue
                    if b'filename=' in part:
                        # 文件部分
                        header_end = part.find(b'\r\n\r\n')
                        header = part[:header_end].decode()
                        file_name = header.split('filename="')[1].split('"')[0]
                        file_data = part[header_end + 4:-2]  # 去掉末尾的\r\n
                    else:
                        # 表单字段
                        header_end = part.find(b'\r\n\r\n')
                        header = part[:header_end].decode()
                        name = header.split('name="')[1].split('"')[0]
                        value = part[header_end + 4:-2].decode()
                        form_data[name] = value
                
                platform = form_data.get('platform', 'csv')
                date = form_data.get('date', datetime.now().strftime('%Y-%m-%d'))
                
                # 保存上传的文件
                if file_data and file_name:
                    upload_dir = DATA_DIR / "uploads"
                    upload_dir.mkdir(exist_ok=True)
                    file_path = upload_dir / file_name
                    with open(file_path, "wb") as f:
                        f.write(file_data)
                    
                    # 根据平台类型导入
                    import_func = {
                        'tdx': importer.import_tdx,
                        'ths': importer.import_ths,
                        'eastmoney': importer.import_eastmoney,
                        'wind': importer.import_wind,
                        'joinquant': importer.import_joinquant,
                        'csv': importer.import_csv
                    }.get(platform, importer.import_csv)
                    
                    result = import_func(str(file_path), date)
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
                else:
                    raise ValueError("No file uploaded")
                    
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode("utf-8"))

        else:
            self.send_error(404, "Not Found")


class ThreadingDashboardServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """多线程看板服务器（每请求一线程，避免单线程阻塞）"""
    allow_reuse_address = True
    daemon_threads = True  # 子线程随主进程退出
    request_queue_size = 50  # 增大请求队列


def start_server():
    """启动看板服务器"""
    os.chdir(DATA_DIR)

    # 初始化SQLite数据库 & 迁移旧JSON数据
    init_db()
    migrated = migrate_from_json()
    if migrated:
        _server_logger.info("JSON → SQLite 数据迁移完成")
    
    # 初始化数据文件（仅data.json保留，其余已迁移到SQLite）
    if not DATA_FILE.exists():
        update_data_file(DEFAULT_DATA)
    if not AGENTS_STATUS_FILE.exists():
        save_agents_status(DEFAULT_AGENTS_STATUS)
    if not ACCURACY_FILE.exists():
        save_accuracy_history(DEFAULT_ACCURACY_HISTORY)
    if not CONFLICTS_FILE.exists():
        save_conflicts([])

    with ThreadingDashboardServer((BIND_ADDR, PORT), DashboardHandler) as httpd:
        local_ip = __get_local_ip()
        print(f"\n{'='*60}")
        print(f"  九章量化局 · 实时看板服务器 v3.0")
        print(f"  数据源: 腾讯行情API（真实数据 + 真实因子计算）")
        print(f"{'='*60}")
        print(f"  本机访问  : http://localhost:{PORT}")
        print(f"  局域网访问: http://{local_ip}:{PORT}")
        print(f"  实时行情  : http://localhost:{PORT}/api/market/realtime")
        print(f"  融合报告  : http://localhost:{PORT}/api/fusion/report")
        print(f"  K线数据  : http://localhost:{PORT}/api/market/kline?code=sh510300")
        print(f"{'='*60}\n")
        print(f"  等待请求...（Ctrl+C 停止）\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止。")


def __get_local_ip():
    """获取本机局域网IP"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def update_data_file(new_data: dict):
    """由Agent调用，更新数据文件"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print(f"[看板] 数据已更新：{DATA_FILE}")


if __name__ == "__main__":
    start_server()
