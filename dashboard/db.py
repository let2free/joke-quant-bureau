"""
九章量化局 · SQLite数据持久化模块 v1.0
替代 JSON 文件存储：accuracy_history / collab_log / agents_status / conflicts / artifacts
"""

import sqlite3
import json
import threading
from datetime import datetime
from pathlib import Path

DB_FILE = Path(__file__).parent / "jiuzhang.db"
_lock = threading.Lock()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accuracy_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    accuracy REAL DEFAULT 0,
    etfs_count INTEGER DEFAULT 0,
    recap_triggered INTEGER DEFAULT 0,
    details TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS collab_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent TEXT DEFAULT '',
    action TEXT DEFAULT '',
    detail TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents_status (
    agent_id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'idle',
    current_task TEXT,
    last_update TEXT NOT NULL,
    tasks_completed INTEGER DEFAULT 0,
    accuracy REAL
);

CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT DEFAULT '',
    description TEXT DEFAULT '',
    resolved INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
    key TEXT PRIMARY KEY,
    data_json TEXT DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accuracy_date ON accuracy_history(date);
CREATE INDEX IF NOT EXISTS idx_collab_created ON collab_log(created_at);
CREATE INDEX IF NOT EXISTS idx_conflicts_created ON conflicts(created_at);
"""


def _get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db():
    """初始化数据库（幂等）"""
    with _lock:
        conn = _get_conn()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()


def _now():
    return datetime.now().isoformat()


# ── 准确率历史 ──────────────────────────

def get_accuracy_history(limit=30):
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM accuracy_history ORDER BY date DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_accuracy(date, accuracy, etfs_count, recap_triggered=False, details=None):
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO accuracy_history 
                   (date, accuracy, etfs_count, recap_triggered, details, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (date, accuracy, etfs_count, int(recap_triggered),
                 json.dumps(details or {}, ensure_ascii=False), _now())
            )
            conn.commit()
        finally:
            conn.close()


def save_accuracy_history(data):
    """批量保存准确率历史（兼容旧API）"""
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM accuracy_history")
            for item in data:
                conn.execute(
                    """INSERT INTO accuracy_history 
                       (date, accuracy, etfs_count, recap_triggered, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (item.get("date", ""), item.get("accuracy", 0),
                     item.get("etfs_count", 0), int(item.get("recap_triggered", False)),
                     item.get("created_at", _now()))
                )
            conn.commit()
        finally:
            conn.close()


# ── 协同日志 ──────────────────────────

def get_collab_log(limit=100):
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM collab_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def append_collab_log(entry):
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                """INSERT INTO collab_log (agent, action, detail, created_at)
                   VALUES (?, ?, ?, ?)""",
                (entry.get("agent", ""), entry.get("action", ""),
                 json.dumps(entry.get("detail", {}), ensure_ascii=False),
                 entry.get("created_at", _now()))
            )
            conn.commit()
        finally:
            conn.close()


# ── Agent状态 ──────────────────────────

def get_agents_status():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM agents_status").fetchall()
        agents = {}
        for r in rows:
            d = dict(r)
            agents[d.pop("agent_id")] = d
        return {"agents": agents, "last_updated": _now()}
    finally:
        conn.close()


def save_agents_status(data):
    with _lock:
        conn = _get_conn()
        try:
            agents = data.get("agents", {})
            for agent_id, info in agents.items():
                conn.execute(
                    """INSERT OR REPLACE INTO agents_status 
                       (agent_id, status, current_task, last_update, tasks_completed, accuracy)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (agent_id, info.get("status", "idle"),
                     info.get("current_task"), info.get("last_update", _now()),
                     info.get("tasks_completed", 0), info.get("accuracy"))
                )
            conn.commit()
        finally:
            conn.close()


# ── 冲突记录 ──────────────────────────

def get_conflicts(limit=50):
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM conflicts ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_conflicts(data):
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("DELETE FROM conflicts")
            for item in data:
                conn.execute(
                    """INSERT INTO conflicts (type, description, resolved, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (item.get("type", ""), item.get("description", ""),
                     int(item.get("resolved", False)),
                     item.get("created_at", _now()))
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ── 分析产物 ──────────────────────────

def get_artifacts():
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM artifacts").fetchall()
        return {r["key"]: json.loads(r["data_json"]) for r in rows}
    finally:
        conn.close()


def save_artifacts(data):
    with _lock:
        conn = _get_conn()
        try:
            for key, value in data.items():
                conn.execute(
                    """INSERT OR REPLACE INTO artifacts (key, data_json, updated_at)
                       VALUES (?, ?, ?)""",
                    (key, json.dumps(value, ensure_ascii=False), _now())
                )
            conn.commit()
        finally:
            conn.close()


# ── 数据迁移 ──────────────────────────

def migrate_from_json():
    """启动时自动从旧JSON文件迁移到SQLite"""
    data_dir = Path(__file__).parent
    migrated = False

    # 迁移准确率历史
    acc_file = data_dir / "accuracy_history.json"
    if acc_file.exists():
        try:
            with open(acc_file, "r", encoding="utf-8") as f:
                acc_data = json.load(f)
            if acc_data:
                save_accuracy_history(acc_data)
                migrated = True
        except Exception:
            pass

    # 迁移Agent状态
    ag_file = data_dir / "agents_status.json"
    if ag_file.exists():
        try:
            with open(ag_file, "r", encoding="utf-8") as f:
                ag_data = json.load(f)
            if ag_data:
                save_agents_status(ag_data)
                migrated = True
        except Exception:
            pass

    # 迁移协同日志
    collab_file = data_dir / "collab_log.jsonl"
    if collab_file.exists():
        try:
            with open(collab_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        append_collab_log(entry)
            if collab_file.stat().st_size > 0:
                migrated = True
        except Exception:
            pass

    # 迁移冲突
    conf_file = data_dir / "conflicts.json"
    if conf_file.exists():
        try:
            with open(conf_file, "r", encoding="utf-8") as f:
                conf_data = json.load(f)
            if conf_data:
                save_conflicts(conf_data)
                migrated = True
        except Exception:
            pass

    # 迁移产物
    art_file = data_dir / "artifacts.json"
    if art_file.exists():
        try:
            with open(art_file, "r", encoding="utf-8") as f:
                art_data = json.load(f)
            if art_data:
                save_artifacts(art_data)
                migrated = True
        except Exception:
            pass

    return migrated


# ── 数据库统计 ──────────────────────────

def get_db_stats():
    """获取数据库统计信息"""
    conn = _get_conn()
    try:
        tables = ["accuracy_history", "collab_log", "agents_status", "conflicts", "artifacts"]
        stats = {}
        for t in tables:
            row = conn.execute(f"SELECT COUNT(*) as cnt FROM {t}").fetchone()
            stats[t] = row["cnt"]
        stats["db_size_kb"] = round(DB_FILE.stat().st_size / 1024, 1) if DB_FILE.exists() else 0
        return stats
    finally:
        conn.close()
