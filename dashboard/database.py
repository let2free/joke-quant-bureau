"""
九章量化局 · SQLite数据库模块 v1.0
替代JSON文件存储，支持并发安全读写
"""
import sqlite3
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path(__file__).parent / "jiuzhang.db"
_lock = threading.Lock()

def get_db():
    """获取数据库连接（线程安全）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """初始化数据库表"""
    with _lock:
        conn = get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                pred_rank INTEGER,
                pred_pct REAL,
                actual_pct REAL,
                score_b REAL,
                score_fused REAL,
                confidence TEXT,
                reason TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(date, code)
            );

            CREATE TABLE IF NOT EXISTS accuracy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                direction_accuracy REAL,
                avg_error REAL,
                best_prediction TEXT,
                worst_prediction TEXT,
                etfs_count INTEGER DEFAULT 6,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS factors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                momentum REAL,
                fund_flow REAL,
                mean_reversion REAL,
                volatility REAL,
                microstructure REAL,
                regime REAL,
                created_at TEXT DEFAULT (datetime('now','localtime')),
                UNIQUE(date)
            );

            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                sh_index REAL,
                sz_index REAL,
                cyb_index REAL,
                kc50_index REAL,
                volume_total REAL,
                north_flow REAL,
                market_state TEXT,
                L0_liquidity TEXT,
                L4b_impact TEXT,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL,
                params TEXT,
                initial_capital REAL,
                final_equity REAL,
                total_return REAL,
                win_rate REAL,
                sharpe REAL,
                max_drawdown REAL,
                num_trades INTEGER,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_pred_date ON predictions(date);
            CREATE INDEX IF NOT EXISTS idx_pred_code ON predictions(code);
            CREATE INDEX IF NOT EXISTS idx_accuracy_date ON accuracy(date);
            CREATE INDEX IF NOT EXISTS idx_factors_date ON factors(date);
            CREATE INDEX IF NOT EXISTS idx_market_date ON market_snapshots(date);
        """)
        conn.commit()
        conn.close()

# ── 预测数据 ──
def save_predictions(date: str, rankings: List[Dict]):
    """保存预测数据（覆盖当日）"""
    with _lock:
        conn = get_db()
        conn.execute("DELETE FROM predictions WHERE date=?", (date,))
        for r in rankings:
            conn.execute("""
                INSERT INTO predictions (date, code, name, pred_rank, pred_pct, score_b, score_fused, confidence, reason)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (date, r['code'], r['name'], r.get('rank',0), r.get('calibrated_prediction',0),
                  r.get('score_b',0), r.get('score_fused',0), r.get('confidence','中'), r.get('reason','')))
        conn.commit()
        conn.close()

def get_predictions(date: str = None) -> List[Dict]:
    """获取预测数据"""
    conn = get_db()
    if date:
        rows = conn.execute("SELECT * FROM predictions WHERE date=? ORDER BY pred_rank", (date,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM predictions ORDER BY date DESC, pred_rank LIMIT 50").fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

# ── 准确率数据 ──
def save_accuracy(date: str, direction_accuracy: float, avg_error: float, best: str, worst: str, count: int = 6):
    """保存准确率"""
    with _lock:
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO accuracy (date, direction_accuracy, avg_error, best_prediction, worst_prediction, etfs_count)
            VALUES (?,?,?,?,?,?)
        """, (date, direction_accuracy, avg_error, best, worst, count))
        conn.commit()
        conn.close()

def get_accuracy_history(limit: int = 30) -> List[Dict]:
    """获取准确率历史"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM accuracy ORDER BY date ASC LIMIT ?", (limit,)).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

# ── 因子数据 ──
def save_factors(date: str, weights: Dict):
    """保存因子权重"""
    with _lock:
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO factors (date, momentum, fund_flow, mean_reversion, volatility, microstructure, regime)
            VALUES (?,?,?,?,?,?,?)
        """, (date, weights.get('momentum',0.35), weights.get('fund_flow',0.25),
              weights.get('mean_reversion',0.15), weights.get('volatility',0.08),
              weights.get('microstructure',0.07), weights.get('regime',0.10)))
        conn.commit()
        conn.close()

def get_factors(limit: int = 30) -> List[Dict]:
    """获取因子历史"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM factors ORDER BY date ASC LIMIT ?", (limit,)).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

# ── 市场快照 ──
def save_market_snapshot(data: Dict):
    """保存市场快照"""
    with _lock:
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO market_snapshots (date, sh_index, sz_index, cyb_index, kc50_index, volume_total, north_flow, market_state, L0_liquidity, L4b_impact)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (data.get('date',''), data.get('sh_index'), data.get('sz_index'),
              data.get('cyb_index'), data.get('kc50_index'), data.get('volume_total'),
              data.get('north_flow'), data.get('market_state'),
              data.get('L0_liquidity'), data.get('L4b_impact')))
        conn.commit()
        conn.close()

def get_market_snapshots(limit: int = 30) -> List[Dict]:
    """获取市场快照历史"""
    conn = get_db()
    rows = conn.execute("SELECT * FROM market_snapshots ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

# ── 回测结果 ──
def save_backtest_result(params: Dict, results: Dict):
    """保存回测结果"""
    with _lock:
        conn = get_db()
        conn.execute("""
            INSERT INTO backtest_results (run_at, params, initial_capital, final_equity, total_return, win_rate, sharpe, max_drawdown, num_trades)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (datetime.now().isoformat(), json.dumps(params),
              results.get('initial_capital',0), results.get('final_equity',0),
              results.get('total_return_pct',0), results.get('win_rate',0),
              results.get('sharpe_ratio',0), results.get('max_drawdown_pct',0),
              results.get('num_trades',0)))
        conn.commit()
        conn.close()

# ── 统计查询 ──
def get_stats() -> Dict:
    """获取总体统计"""
    conn = get_db()
    total_predictions = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    total_dates = conn.execute("SELECT COUNT(DISTINCT date) FROM predictions").fetchone()[0]
    latest_acc = conn.execute("SELECT * FROM accuracy ORDER BY date DESC LIMIT 1").fetchone()
    avg_error_all = conn.execute("SELECT AVG(avg_error) FROM accuracy").fetchone()[0]
    conn.close()
    
    return {
        "total_predictions": total_predictions,
        "total_trading_days": total_dates,
        "latest_accuracy": dict(latest_acc) if latest_acc else {},
        "avg_error_all_time": round(avg_error_all * 100, 2) if avg_error_all else 0
    }

# 启动时自动初始化
init_db()
print(f"数据库初始化完成: {DB_PATH}")
