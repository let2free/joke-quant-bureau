"""
九章量化局 · 实时看板服务器 v1.0
绑定 0.0.0.0，支持局域网多设备访问
"""

import http.server
import socketserver
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

# 配置
PORT = 7860
BIND_ADDR = "0.0.0.0"
DATA_FILE = Path(__file__).parent / "data.json"
LOG_FILE = Path(__file__).parent / "access.log"

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


def load_data():
    """读取最新数据文件，不存在则返回默认数据"""
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_DATA.copy()


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

        if path == "/" or path == "/index.html":
            # 返回主看板页面
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = (Path(__file__).parent / "dashboard.html").read_bytes()
            self.wfile.write(html)

        elif path == "/api/data":
            # 返回实时数据JSON
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = load_data()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        elif path == "/api/status":
            # 返回服务器状态
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

        elif path == "/log":
            # 查看访问日志（调试用）
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            if LOG_FILE.exists():
                self.wfile.write(LOG_FILE.read_bytes())
            else:
                self.wfile.write(b"No logs yet.")

        else:
            self.send_error(404, "Not Found")


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_server():
    """启动看板服务器"""
    os.chdir(Path(__file__).parent)

    with ReusableTCPServer((BIND_ADDR, PORT), DashboardHandler) as httpd:
        local_ip = __get_local_ip()
        print(f"\n{'='*60}")
        print(f"  九章量化局 · 实时看板服务器已启动")
        print(f"{'='*60}")
        print(f"  本机访问  : http://localhost:{PORT}")
        print(f"  局域网访问: http://{local_ip}:{PORT}")
        print(f"  API数据   : http://localhost:{PORT}/api/data")
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
    # 初始化数据文件
    if not DATA_FILE.exists():
        update_data_file(DEFAULT_DATA)
    start_server()
