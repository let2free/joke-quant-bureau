"""
九章量化局 · 数据获取层 v1.0
基于腾讯行情API，零依赖（纯urllib），Cache-first + Stale Fallback

数据源：
  - 实时行情：https://qt.gtimg.cn/q=sh510300,sh588000,...
  - K线历史：https://web.ifzq.gtimg.cn/appstock/app/fqkline/get

缓存策略：
  1. 读缓存 → 未过期直接返回
  2. 缓存过期 → 请求API → 成功则更新缓存
  3. API失败 → 返回过期缓存（标记stale=true）
  4. 无缓存+API失败 → 返回空数据（标记degraded=true）
"""

import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ──
DATA_DIR = Path(__file__).parent
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# 缓存TTL（秒）
CACHE_TTL_REALTIME = 30       # 实时行情30秒
CACHE_TTL_KLINE = 3600 * 4    # K线4小时
CACHE_TTL_STALE_MAX = 86400   # 过期缓存最多用24小时

# 请求超时
HTTP_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ── 腾讯行情API端点 ──
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
TENCENT_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


def _cache_path(key: str) -> Path:
    """获取缓存文件路径"""
    safe_key = key.replace("/", "_").replace(":", "_").replace(",", "_")
    return CACHE_DIR / f"{safe_key}.json"


def _read_cache(key: str, max_age: int):
    """读缓存，返回 (data, is_stale) 或 (None, False)"""
    path = _cache_path(key)
    if not path.exists():
        return None, False
    try:
        with open(path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        age = time.time() - cache.get("_cached_at", 0)
        if age < max_age:
            return cache.get("data"), False  # 未过期
        # 过期但未超过最大容忍时间
        if age < CACHE_TTL_STALE_MAX:
            return cache.get("data"), True   # 过期但可用
        return None, False  # 太旧，不用
    except Exception:
        return None, False


def _write_cache(key: str, data):
    """写缓存"""
    path = _cache_path(key)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_cached_at": time.time(), "data": data}, f, ensure_ascii=False)
    except Exception:
        pass


def _http_get(url: str, timeout: int = HTTP_TIMEOUT, encoding: str = "gbk") -> str:
    """通用HTTP GET"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return resp.read().decode(encoding, errors="replace")


# ═══════════════════════════════════════════════════════════════
#  实时行情
# ═══════════════════════════════════════════════════════════════

def _parse_tencent_quote(line: str) -> dict:
    """解析单行腾讯行情数据"""
    parts = line.split("~")
    if len(parts) < 35:
        return None
    try:
        price = float(parts[3]) if parts[3] else 0
        prev_close = float(parts[4]) if parts[4] else 0
        if price <= 0:
            return None
        return {
            "code": parts[2],
            "name": parts[1],
            "price": price,
            "prev_close": prev_close,
            "open": float(parts[5]) if parts[5] else 0,
            "high": float(parts[33]) if parts[33] else 0,
            "low": float(parts[34]) if parts[34] else 0,
            "change_pct": float(parts[32]) if parts[32] else 0,
            "change_abs": float(parts[31]) if parts[31] else 0,
            "volume": int(parts[6]) if parts[6] else 0,      # 成交量（股）
            "amount": float(parts[37]) if parts[37] else 0,   # 成交额（万元）
            "turnover_rate": float(parts[43]) if len(parts) > 43 and parts[43] else 0,
            "amplitude": float(parts[49]) if len(parts) > 49 and parts[49] else 0,
            "buy_volume": int(parts[7]) if parts[7] else 0,   # 外盘
            "sell_volume": int(parts[8]) if parts[8] else 0,  # 内盘
            "updated_at": parts[30] if len(parts) > 30 and parts[30] else datetime.now().strftime("%Y%m%d%H%M%S"),
        }
    except (ValueError, IndexError):
        return None


def fetch_realtime_quotes(codes: list, use_cache=True) -> dict:
    """
    批量获取实时行情
    
    Args:
        codes: 代码列表，格式 ["sh510300", "sh588000", "sz159915", ...]
               ETF代码自动转换：6位纯数字 → 沪市sh前缀（5开头）或深市sz前缀（1开头）
        use_cache: 是否使用缓存
    
    Returns:
        {
            "data": {"sh510300": {...}, "sh588000": {...}, ...},
            "meta": {"cache_hit": bool, "stale": bool, "degraded": bool, "fetched_at": str, "count": int}
        }
    """
    # 规范化代码
    norm_codes = []
    for c in codes:
        c = c.strip()
        if c.startswith("sh") or c.startswith("sz"):
            norm_codes.append(c)
        elif c.isdigit() and len(c) == 6:
            # 上证5开头或6开头 → sh，深证0/1/3开头 → sz
            if c[0] in ("5", "6", "9"):
                norm_codes.append(f"sh{c}")
            else:
                norm_codes.append(f"sz{c}")
        else:
            norm_codes.append(c)
    
    cache_key = f"rt_{'_'.join(sorted(norm_codes[:50]))}"
    
    # 1. 读缓存
    if use_cache:
        cached, stale = _read_cache(cache_key, CACHE_TTL_REALTIME)
        if cached is not None and not stale:
            return {"data": cached, "meta": {"cache_hit": True, "stale": False, "degraded": False, "fetched_at": "cached", "count": len(cached)}}
    
    # 2. 请求API
    try:
        url = TENCENT_QUOTE_URL + ",".join(norm_codes)
        raw = _http_get(url, encoding="gbk")
        
        result = {}
        for line in raw.split(";"):
            line = line.strip()
            if not line or "~" not in line:
                continue
            parsed = _parse_tencent_quote(line)
            if parsed:
                result[parsed["code"]] = parsed
        
        if result:
            _write_cache(cache_key, result)
            return {"data": result, "meta": {"cache_hit": False, "stale": False, "degraded": False, "fetched_at": datetime.now().isoformat(), "count": len(result)}}
    except Exception as e:
        print(f"[data_fetcher] 实时行情API失败: {e}")
    
    # 3. API失败，尝试返回过期缓存
    if use_cache:
        cached, stale = _read_cache(cache_key, CACHE_TTL_STALE_MAX)
        if cached is not None:
            return {"data": cached, "meta": {"cache_hit": True, "stale": True, "degraded": False, "fetched_at": "stale_cache", "count": len(cached)}}
    
    # 4. 全部失败
    return {"data": {}, "meta": {"cache_hit": False, "stale": False, "degraded": True, "fetched_at": "none", "count": 0}}


# ═══════════════════════════════════════════════════════════════
#  K线历史数据
# ═══════════════════════════════════════════════════════════════

def fetch_kline(code: str, days: int = 120, use_cache=True) -> dict:
    """
    获取K线历史数据（日线）
    
    Args:
        code: ETF代码，如 "sh510300" 或 "510300"
        days: 获取天数
        use_cache: 是否使用缓存
    
    Returns:
        {
            "data": [
                {"date": "2026-06-17", "open": 4.898, "close": 4.958, "high": 4.960, "low": 4.894, "volume": 13911870},
                ...
            ],
            "meta": {"cache_hit": bool, "stale": bool, "degraded": bool, "count": int}
        }
    """
    # 规范化代码
    if code.isdigit() and len(code) == 6:
        code = f"sh{code}" if code[0] in ("5", "6", "9") else f"sz{code}"
    
    cache_key = f"kline_{code}_{days}"
    
    # 1. 读缓存
    if use_cache:
        cached, stale = _read_cache(cache_key, CACHE_TTL_KLINE)
        if cached is not None and not stale:
            return {"data": cached, "meta": {"cache_hit": True, "stale": False, "degraded": False, "count": len(cached)}}
    
    # 2. 请求API
    try:
        url = f"{TENCENT_KLINE_URL}?param={code},day,,,{days},qfqa"
        raw = _http_get(url, encoding="utf-8")
        kdata = json.loads(raw)
        
        # 尝试多种key（day / qfqday）
        stock_data = kdata.get("data", {}).get(code, {})
        days_data = stock_data.get("day", stock_data.get("qfqday", []))
        
        if days_data:
            result = []
            for d in days_data:
                if len(d) >= 6:
                    result.append({
                        "date": d[0],
                        "open": float(d[1]),
                        "close": float(d[2]),
                        "high": float(d[3]),
                        "low": float(d[4]),
                        "volume": float(d[5]),
                    })
            if result:
                _write_cache(cache_key, result)
                return {"data": result, "meta": {"cache_hit": False, "stale": False, "degraded": False, "count": len(result)}}
    except Exception as e:
        print(f"[data_fetcher] K线API失败 ({code}): {e}")
    
    # 3. 返回过期缓存
    if use_cache:
        cached, stale = _read_cache(cache_key, CACHE_TTL_STALE_MAX)
        if cached is not None:
            return {"data": cached, "meta": {"cache_hit": True, "stale": True, "degraded": False, "count": len(cached)}}
    
    # 4. 全部失败
    return {"data": [], "meta": {"cache_hit": False, "stale": False, "degraded": True, "count": 0}}


def fetch_kline_batch(codes: list, days: int = 120, use_cache=True) -> dict:
    """
    批量获取K线数据
    
    Returns:
        {"sh510300": {"data": [...], "meta": {...}}, ...}
    """
    result = {}
    for code in codes:
        result[code] = fetch_kline(code, days, use_cache)
        time.sleep(0.15)  # 控制请求频率
    return result


# ═══════════════════════════════════════════════════════════════
#  指数行情（上证/深证/创业板/科创50）
# ═══════════════════════════════════════════════════════════════

INDEX_CODES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50":   "sh000688",
}


def fetch_indices(use_cache=True) -> dict:
    """获取主要指数行情"""
    codes = list(INDEX_CODES.values())
    result = fetch_realtime_quotes(codes, use_cache)
    
    # 映射回中文名
    indices = {}
    for name, code in INDEX_CODES.items():
        pure_code = code[2:]
        if pure_code in result["data"]:
            indices[name] = result["data"][pure_code]
        elif code in result["data"]:
            indices[name] = result["data"][code]
    
    return {"data": indices, "meta": result["meta"]}


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

def code_to_tencent(code: str) -> str:
    """ETF代码 → 腾讯格式（sh/sz前缀）"""
    if code.startswith("sh") or code.startswith("sz"):
        return code
    if code.isdigit() and len(code) == 6:
        if code[0] in ("5", "6", "9"):
            return f"sh{code}"
        else:
            return f"sz{code}"
    return code


def clear_cache():
    """清除所有缓存"""
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
    print(f"[data_fetcher] 缓存已清除 ({CACHE_DIR})")


if __name__ == "__main__":
    # 测试
    print("=== 测试实时行情 ===")
    result = fetch_realtime_quotes(["sh510300", "sh588000", "sz159915"])
    print(f"获取 {result['meta']['count']} 条数据")
    for code, data in result["data"].items():
        print(f"  {data['name']} ({code}): {data['price']} ({data['change_pct']:+.2f}%)")
    
    print("\n=== 测试K线 ===")
    kline = fetch_kline("sh510300", 60)
    print(f"获取 {kline['meta']['count']} 根K线")
    if kline["data"]:
        print(f"  最新: {kline['data'][-1]}")
    
    print("\n=== 测试指数 ===")
    indices = fetch_indices()
    for name, data in indices["data"].items():
        print(f"  {name}: {data['price']} ({data['change_pct']:+.2f}%)")
