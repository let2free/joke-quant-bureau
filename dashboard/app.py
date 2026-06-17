"""
九章量化局 · Flask服务器 v2.0
SQLite持久化 + 路由表 + 统一错误 + 日志系统
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import PORT, BIND_ADDR, DEBUG, ETF_CACHE_TTL, CALIBRATION_FACTOR, DEFAULT_WEIGHTS, ARTIFACTS_DIR, LOGS_DIR
from database import (
    get_predictions, save_predictions, get_accuracy_history, save_accuracy,
    get_factors, save_factors, get_market_snapshots, save_market_snapshot,
    save_backtest_result, get_stats, get_db
)
from etf_data import (
    generate_etf_data, get_watchlist_data, calculate_rankings,
    load_watchlist, add_to_watchlist, remove_from_watchlist, search_etfs
)
from backtest import calculate_accuracy, optimize_factor_weights, run_backtest_simulation

# ── 日志系统 ──
LOGS_DIR.mkdir(exist_ok=True)
log_file = LOGS_DIR / f"jiuzhang_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler(str(log_file), encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ── Flask App ──
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ── ETF数据缓存 ──
_cached_etf = {}
_cached_etf_time = None

def get_etf_cache():
    global _cached_etf, _cached_etf_time
    if not _cached_etf or (datetime.now() - _cached_etf_time).seconds > ETF_CACHE_TTL:
        _cached_etf = generate_etf_data(use_cache=True)
        _cached_etf_time = datetime.now()
    return _cached_etf

# 后台预加载
threading.Thread(target=get_etf_cache, daemon=True).start()

# ── 统一错误响应 ──
def ok(data): return jsonify(data)
def err(msg, code=500): return jsonify({"status": "error", "message": str(msg)}), code

# ═══════════════════════════════════════════
#  页面路由
# ═══════════════════════════════════════════
@app.route('/')
@app.route('/dashboard.html')
def index(): return send_from_directory('.', 'dashboard.html')

@app.route('/<page>.html')
def pages(page):
    pages = ['jiuzhang','etf_monitor','topology','backtest','history','lobster_collab']
    if page in pages: return send_from_directory('.', f'{page}.html')
    return err("Page not found", 404)

# ═══════════════════════════════════════════
#  API路由
# ═══════════════════════════════════════════
@app.route('/api/status')
def api_status():
    etf = get_etf_cache()
    return ok({"status":"ok","port":PORT,"bind":BIND_ADDR,"etf_count":len(etf),"cache_ttl":ETF_CACHE_TTL})

@app.route('/api/etf/rankings')
def api_rankings():
    data = get_etf_cache()
    sort = request.args.get('sort','change_pct')
    top = int(request.args.get('top',10))
    result = calculate_rankings(data, sort, top)
    return ok(result)

@app.route('/api/etf/watchlist')
def api_watchlist():
    try:
        return ok(get_watchlist_data())
    except Exception as e:
        logger.error(f"Watchlist加载失败: {e}")
        # 返回空列表而非500
        return ok({"a_share": [], "us": []})

@app.route('/api/etf/watchlist/add', methods=['POST'])
def api_watchlist_add():
    data = request.get_json()
    result = add_to_watchlist(data.get('code',''), data.get('name',''),
                              data.get('market','1'), data.get('category','a_share'))
    return ok({"success":True,"watchlist":result})

@app.route('/api/etf/watchlist/remove', methods=['POST'])
def api_watchlist_remove():
    data = request.get_json()
    result = remove_from_watchlist(data.get('code',''), data.get('market','a_share'))
    return ok({"success":True,"watchlist":result})

@app.route('/api/etf/refresh')
def api_refresh():
    global _cached_etf, _cached_etf_time
    _cached_etf = None; _cached_etf_time = None
    data = get_etf_cache()
    return ok({"success":True,"count":len(data),"updated_at":datetime.now().isoformat()})

@app.route('/api/etf/search')
def api_etf_search():
    q = request.args.get('q','')
    if len(q) < 2: return ok([])
    return ok(search_etfs(q, 20))

@app.route('/api/etf/monitor/config')
def api_monitor_config():
    return ok({
        "total_etfs": 1563, "monitoring": load_watchlist(),
        "refresh_interval": ETF_CACHE_TTL, "data_source": "缓存/模拟",
        "last_update": datetime.now().isoformat()
    })

# ── 预测API ──
@app.route('/api/predictions/latest')
def api_predictions_latest():
    rows = get_predictions()
    if rows:
        latest_date = rows[0].get('date','')
        rankings = [r for r in rows if r['date'] == latest_date]
        # 从artifacts读详细数据
        fusion_file = ARTIFACTS_DIR / latest_date / "fusion_report.json"
        if fusion_file.exists():
            with open(fusion_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['date'] = latest_date
                return ok(data)
        return ok({"date": latest_date, "rankings": rankings})
    # 回退到JSON
    for d in sorted(ARTIFACTS_DIR.iterdir(), reverse=True):
        if d.is_dir():
            f = d / "fusion_report.json"
            if f.exists():
                data = json.loads(f.read_text(encoding='utf-8'))
                data['date'] = d.name
                return ok(data)
    return ok({})

@app.route('/api/predictions/history')
def api_predictions_history():
    result = []
    if ARTIFACTS_DIR.exists():
        for d in sorted(ARTIFACTS_DIR.iterdir(), reverse=True)[:10]:
            if d.is_dir():
                f = d / "fusion_report.json"
                if f.exists():
                    data = json.loads(f.read_text(encoding='utf-8'))
                    data['date'] = d.name
                    result.append(data)
    return ok(result)

# ── 准确率API ──
@app.route('/api/accuracy/history')
def api_accuracy_history():
    db_data = get_accuracy_history()
    if db_data: return ok(db_data)
    # JSON回退
    acc_file = Path(__file__).parent / "accuracy_history.json"
    if acc_file.exists(): return ok(json.loads(acc_file.read_text(encoding='utf-8')))
    return ok([])

@app.route('/api/accuracy/save', methods=['POST'])
def api_accuracy_save():
    data = request.get_json()
    save_accuracy(
        data.get('date',''), data.get('direction_accuracy',0),
        data.get('avg_error',0), data.get('best_prediction',''),
        data.get('worst_prediction',''), data.get('etfs_count',6)
    )
    return ok({"success":True})

# ── 因子API ──
@app.route('/api/factors/latest')
def api_factors_latest():
    rows = get_factors(1)
    return ok(rows[0] if rows else DEFAULT_WEIGHTS)

@app.route('/api/factors/history')
def api_factors_history():
    return ok(get_factors(30))

# ── 市场快照API ──
@app.route('/api/market/snapshots')
def api_market_snapshots():
    return ok(get_market_snapshots(30))

@app.route('/api/market/save', methods=['POST'])
def api_market_save():
    save_market_snapshot(request.get_json())
    return ok({"success":True})

# ── 回测API ──
@app.route('/api/backtest/accuracy')
def api_backtest_accuracy():
    try:
        from backtest import load_history
        history = load_history()
        return ok(calculate_accuracy(history))
    except Exception as e:
        return err(e)

@app.route('/api/backtest/factor-optimize')
def api_factor_optimize():
    try:
        from backtest import load_history
        return ok(optimize_factor_weights(load_history()))
    except Exception as e:
        return err(e)

@app.route('/api/backtest/run', methods=['POST'])
def api_backtest_run():
    try:
        result = run_backtest_simulation(request.get_json())
        if result.get('status') == 'success':
            save_backtest_result(request.get_json(), result.get('results',{}))
        return ok(result)
    except Exception as e:
        return err(e)

# ── 统计API ──
@app.route('/api/stats')
def api_stats():
    db_stats = get_stats()
    etf = get_etf_cache()
    return ok({
        **db_stats,
        "etf_monitored": len(etf),
        "server_version": "v2.0",
        "cache_ttl": ETF_CACHE_TTL,
        "calibration_factor": CALIBRATION_FACTOR
    })

# ═══════════════════════════════════════════
#  启动
# ═══════════════════════════════════════════
if __name__ == '__main__':
    logger.info(f"九章量化局 v2.0 启动 -> http://localhost:{PORT}")
    logger.info(f"日志文件: {log_file}")
    app.run(host=BIND_ADDR, port=PORT, debug=DEBUG, threaded=True)
