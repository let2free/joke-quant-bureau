"""
九章量化局 · 实时看板服务器 v2.0
绑定 0.0.0.0，支持局域网多设备访问
新增：龙虾协同中心API接口
"""

import http.server
import socketserver
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

# 导入回测模块
import backtest

# 配置
PORT = 7860
BIND_ADDR = "0.0.0.0"
DATA_DIR = Path(__file__).parent
DATA_FILE = DATA_DIR / "data.json"
LOG_FILE = DATA_DIR / "access.log"

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
    """读取Agent状态"""
    if AGENTS_STATUS_FILE.exists():
        try:
            with open(AGENTS_STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_AGENTS_STATUS.copy()


def save_agents_status(data):
    """保存Agent状态"""
    with open(AGENTS_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_collab_log():
    """读取协同日志（JSONL格式）"""
    entries = []
    if COLLAB_LOG_FILE.exists():
        try:
            with open(COLLAB_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def append_collab_log(entry):
    """追加一条协同日志"""
    with open(COLLAB_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_artifacts():
    """读取分析产物"""
    if ARTIFACTS_FILE.exists():
        try:
            with open(ARTIFACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_artifacts(data):
    """保存分析产物"""
    with open(ARTIFACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_accuracy_history():
    """读取准确率历史"""
    if ACCURACY_FILE.exists():
        try:
            with open(ACCURACY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_ACCURACY_HISTORY.copy()


def save_accuracy_history(data):
    """保存准确率历史"""
    with open(ACCURACY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_conflicts():
    """读取冲突记录"""
    if CONFLICTS_FILE.exists():
        try:
            with open(CONFLICTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_conflicts(data):
    """保存冲突记录"""
    with open(CONFLICTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log_access(client_ip, path):
    """记录访问日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {client_ip} -> {path}\n"
    try:
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

        # API: 回测 - 准确率历史
        elif path == "/api/backtest/accuracy":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = load_backtest_accuracy(self)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 回测 - 因子优化
        elif path == "/api/backtest/factor-optimize":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = run_factor_optimization(self)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        # API: 回测 - 运行回测
        elif path == "/api/backtest/run" and self.command == "POST":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = run_backtest_simulation(self)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

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

        else:
            self.send_error(404, "Not Found")


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def start_server():
    """启动看板服务器"""
    os.chdir(DATA_DIR)

    # 初始化数据文件
    if not DATA_FILE.exists():
        update_data_file(DEFAULT_DATA)
    if not AGENTS_STATUS_FILE.exists():
        save_agents_status(DEFAULT_AGENTS_STATUS)
    if not ACCURACY_FILE.exists():
        save_accuracy_history(DEFAULT_ACCURACY_HISTORY)
    if not CONFLICTS_FILE.exists():
        save_conflicts([])

    with ReusableTCPServer((BIND_ADDR, PORT), DashboardHandler) as httpd:
        local_ip = __get_local_ip()
        print(f"\n{'='*60}")
        print(f"  九章量化局 · 实时看板服务器 v2.0")
        print(f"{'='*60}")
        print(f"  本机访问  : http://localhost:{PORT}")
        print(f"  局域网访问: http://{local_ip}:{PORT}")
        print(f"  协同中心  : http://localhost:{PORT}/lobster_collab.html")
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
