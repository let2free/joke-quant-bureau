"""
九章量化局 - ETF数据获取模块
支持A股和美股ETF实时数据获取、排名计算
"""
import json
import os
from datetime import datetime
from pathlib import Path

# ETF基础数据配置
ETF_CONFIG = {
    'a_share': {
        '通信ETF': {'code': '515880', 'market': 'SH'},
        '科创50ETF': {'code': '588000', 'market': 'SH'},
        '半导体设备ETF': {'code': '560780', 'market': 'SH'},
        '机器人ETF': {'code': '562500', 'market': 'SH'},
        '新能源ETF': {'code': '516160', 'market': 'SH'},
        '创新药ETF': {'code': '516080', 'market': 'SH'},
        '芯片ETF': {'code': '159995', 'market': 'SZ'},
        '军工ETF': {'code': '512660', 'market': 'SH'},
        '证券ETF': {'code': '512880', 'market': 'SH'},
        '银行ETF': {'code': '512800', 'market': 'SH'},
        '消费ETF': {'code': '159928', 'market': 'SZ'},
        '医药ETF': {'code': '512010', 'market': 'SH'},
        '新能源车ETF': {'code': '515030', 'market': 'SH'},
        '光伏ETF': {'code': '515790', 'market': 'SH'},
        '人工智能ETF': {'code': '515070', 'market': 'SH'},
        '游戏ETF': {'code': '516010', 'market': 'SH'},
        '传媒ETF': {'code': '512980', 'market': 'SH'},
        '房地产ETF': {'code': '512200', 'market': 'SH'},
        '建材ETF': {'code': '159745', 'market': 'SZ'},
        '钢铁ETF': {'code': '515210', 'market': 'SH'},
        '煤炭ETF': {'code': '515220', 'market': 'SH'},
        '有色金属ETF': {'code': '512400', 'market': 'SH'},
        '化工ETF': {'code': '159870', 'market': 'SZ'},
        '农业ETF': {'code': '159825', 'market': 'SZ'},
        '养殖ETF': {'code': '159865', 'market': 'SZ'},
        '旅游ETF': {'code': '159766', 'market': 'SZ'},
        '食品饮料ETF': {'code': '515170', 'market': 'SH'},
        '家电ETF': {'code': '159996', 'market': 'SZ'},
        '汽车ETF': {'code': '516110', 'market': 'SH'},
        '电力ETF': {'code': '159611', 'market': 'SZ'},
    },
    'us': {
        '纳指科技ETF': {'code': '513100', 'market': 'SH'},
        '标普500ETF': {'code': '513500', 'market': 'SH'},
        '纳斯达克ETF': {'code': '513100', 'market': 'SH'},
        '道琼斯ETF': {'code': '513400', 'market': 'SH'},
        '中概互联ETF': {'code': '513050', 'market': 'SH'},
        '恒生科技ETF': {'code': '513180', 'market': 'SH'},
        '恒生ETF': {'code': '159920', 'market': 'SZ'},
        '日经ETF': {'code': '513880', 'market': 'SH'},
        '德国ETF': {'code': '513030', 'market': 'SH'},
        '法国ETF': {'code': '513080', 'market': 'SH'},
        '英国ETF': {'code': '513090', 'market': 'SH'},
        '印度ETF': {'code': '164824', 'market': 'SZ'},
        '越南ETF': {'code': '159987', 'market': 'SZ'},
    }
}

# 自选ETF列表（可配置）
WATCHLIST_FILE = Path(__file__).parent / 'watchlist.json'

def get_default_watchlist():
    """获取默认自选列表"""
    return {
        'a_share': ['515880', '588000', '560780', '562500', '516160', '516080'],
        'us': ['513100', '513500', '513050', '513180']
    }

def load_watchlist():
    """加载自选列表"""
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return get_default_watchlist()

def save_watchlist(watchlist):
    """保存自选列表"""
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)

def add_to_watchlist(etf_code, market='a_share'):
    """添加到自选"""
    watchlist = load_watchlist()
    if etf_code not in watchlist.get(market, []):
        watchlist.setdefault(market, []).append(etf_code)
        save_watchlist(watchlist)
    return watchlist

def remove_from_watchlist(etf_code, market='a_share'):
    """从自选移除"""
    watchlist = load_watchlist()
    if etf_code in watchlist.get(market, []):
        watchlist[market].remove(etf_code)
        save_watchlist(watchlist)
    return watchlist

def get_etf_list(market='all'):
    """获取ETF列表"""
    if market == 'all':
        return {**ETF_CONFIG['a_share'], **ETF_CONFIG['us']}
    elif market == 'a_share':
        return ETF_CONFIG['a_share']
    elif market == 'us':
        return ETF_CONFIG['us']
    return {}

def get_etf_info(code):
    """获取单个ETF信息"""
    for market in ETF_CONFIG.values():
        for name, info in market.items():
            if info['code'] == code:
                return {'name': name, **info}
    return None

def generate_mock_etf_data():
    """生成模拟ETF数据（实际使用时从通达信获取）"""
    import random
    
    etf_list = get_etf_list()
    data = {}
    
    for name, info in etf_list.items():
        code = info['code']
        market = info['market']
        
        # 生成模拟数据
        base_price = random.uniform(0.5, 5.0)
        change_pct = random.uniform(-5, 8)
        volume = random.randint(1000000, 50000000)
        amount = volume * base_price * random.uniform(0.8, 1.2)
        
        data[code] = {
            'name': name,
            'code': code,
            'market': market,
            'price': round(base_price, 3),
            'change_pct': round(change_pct, 2),
            'volume': volume,
            'amount': round(amount, 2),
            'open': round(base_price * (1 + random.uniform(-0.02, 0.02)), 3),
            'high': round(base_price * (1 + abs(change_pct/100) + random.uniform(0, 0.02)), 3),
            'low': round(base_price * (1 - abs(change_pct/100) - random.uniform(0, 0.02)), 3),
            'pre_close': round(base_price / (1 + change_pct/100), 3),
            'turnover_rate': round(random.uniform(0.5, 15), 2),
            'pe_ratio': round(random.uniform(10, 100), 2),
            'pb_ratio': round(random.uniform(0.5, 10), 2),
            'total_market_cap': round(random.uniform(100000000, 50000000000), 0),
            'updated_at': datetime.now().isoformat()
        }
    
    return data

def calculate_rankings(data, sort_by='change_pct', top_n=50):
    """计算ETF排名"""
    # 转换为列表
    etf_list = [{'code': code, **info} for code, info in data.items()]
    
    # 排序
    if sort_by == 'change_pct':
        etf_list.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
    elif sort_by == 'volume':
        etf_list.sort(key=lambda x: x.get('volume', 0), reverse=True)
    elif sort_by == 'amount':
        etf_list.sort(key=lambda x: x.get('amount', 0), reverse=True)
    elif sort_by == 'turnover_rate':
        etf_list.sort(key=lambda x: x.get('turnover_rate', 0), reverse=True)
    
    # 添加排名
    for i, etf in enumerate(etf_list[:top_n], 1):
        etf['rank'] = i
    
    return etf_list[:top_n]

def get_watchlist_data():
    """获取自选ETF数据"""
    watchlist = load_watchlist()
    all_data = generate_mock_etf_data()
    
    result = {
        'a_share': [],
        'us': []
    }
    
    for market, codes in watchlist.items():
        for code in codes:
            if code in all_data:
                result[market].append(all_data[code])
    
    # 按涨跌幅排序
    for market in result:
        result[market].sort(key=lambda x: x.get('change_pct', 0), reverse=True)
    
    return result

def get_etf_detail(code):
    """获取ETF详细信息"""
    all_data = generate_mock_etf_data()
    if code in all_data:
        return all_data[code]
    return None

def get_sector_etfs():
    """获取行业ETF分类"""
    sectors = {
        '科技': ['515880', '588000', '560780', '159995', '515070'],
        '新能源': ['516160', '515030', '515790'],
        '医药': ['516080', '512010'],
        '消费': ['159928', '515170', '159996'],
        '金融': ['512880', '512800'],
        '军工': ['512660'],
        '周期': ['515210', '515220', '512400', '159870'],
        '海外': ['513100', '513500', '513050', '513180']
    }
    
    all_data = generate_mock_etf_data()
    result = {}
    
    for sector, codes in sectors.items():
        result[sector] = []
        for code in codes:
            if code in all_data:
                result[sector].append(all_data[code])
        # 按涨跌幅排序
        result[sector].sort(key=lambda x: x.get('change_pct', 0), reverse=True)
    
    return result

# 初始化自选文件
if not WATCHLIST_FILE.exists():
    save_watchlist(get_default_watchlist())
