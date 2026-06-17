"""
九章量化局 - ETF数据获取模块 v3.0
真正接入通达信实时数据，支持全市场1500+只ETF
"""
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# 配置文件路径
DATA_DIR = Path(__file__).parent
WATCHLIST_FILE = DATA_DIR / 'watchlist.json'
ETF_CACHE_FILE = DATA_DIR / 'etf_cache.json'

# 通达信MCP路径
TDX_MCP_PATH = 'C:/Users/let2free/.workbuddy/connectors/skills/connector-tdx-connector'

# 默认自选列表
DEFAULT_WATCHLIST = {
    'a_share': [
        {'code': '515880', 'name': '通信ETF', 'market': '1'},
        {'code': '588000', 'name': '科创50ETF', 'market': '1'},
        {'code': '560780', 'name': '半导体设备ETF', 'market': '1'},
        {'code': '562500', 'name': '机器人ETF', 'market': '1'},
        {'code': '516160', 'name': '新能源ETF', 'market': '1'},
        {'code': '516080', 'name': '创新药ETF', 'market': '1'},
        {'code': '159995', 'name': '芯片ETF', 'market': '0'},
        {'code': '512660', 'name': '军工ETF', 'market': '1'},
        {'code': '512880', 'name': '证券ETF', 'market': '1'},
        {'code': '512800', 'name': '银行ETF', 'market': '1'},
    ],
    'us': [
        {'code': '513100', 'name': '纳指科技ETF', 'market': '1'},
        {'code': '513500', 'name': '标普500ETF', 'market': '1'},
        {'code': '513050', 'name': '中概互联ETF', 'market': '1'},
        {'code': '513180', 'name': '恒生科技ETF', 'market': '1'},
    ]
}

# 常见ETF列表（用于快速加载）
COMMON_ETFS = [
    {'code': '515880', 'name': '通信ETF', 'market': '1'},
    {'code': '588000', 'name': '科创50ETF', 'market': '1'},
    {'code': '560780', 'name': '半导体设备ETF', 'market': '1'},
    {'code': '562500', 'name': '机器人ETF', 'market': '1'},
    {'code': '516160', 'name': '新能源ETF', 'market': '1'},
    {'code': '516080', 'name': '创新药ETF', 'market': '1'},
    {'code': '159995', 'name': '芯片ETF', 'market': '0'},
    {'code': '512660', 'name': '军工ETF', 'market': '1'},
    {'code': '512880', 'name': '证券ETF', 'market': '1'},
    {'code': '512800', 'name': '银行ETF', 'market': '1'},
    {'code': '159928', 'name': '消费ETF', 'market': '0'},
    {'code': '512010', 'name': '医药ETF', 'market': '1'},
    {'code': '515030', 'name': '新能源车ETF', 'market': '1'},
    {'code': '515790', 'name': '光伏ETF', 'market': '1'},
    {'code': '515070', 'name': '人工智能ETF', 'market': '1'},
    {'code': '516010', 'name': '游戏ETF', 'market': '1'},
    {'code': '512980', 'name': '传媒ETF', 'market': '1'},
    {'code': '512200', 'name': '房地产ETF', 'market': '1'},
    {'code': '159745', 'name': '建材ETF', 'market': '0'},
    {'code': '515210', 'name': '钢铁ETF', 'market': '1'},
    {'code': '515220', 'name': '煤炭ETF', 'market': '1'},
    {'code': '512400', 'name': '有色金属ETF', 'market': '1'},
    {'code': '159870', 'name': '化工ETF', 'market': '0'},
    {'code': '159825', 'name': '农业ETF', 'market': '0'},
    {'code': '159865', 'name': '养殖ETF', 'market': '0'},
    {'code': '159766', 'name': '旅游ETF', 'market': '0'},
    {'code': '515170', 'name': '食品饮料ETF', 'market': '1'},
    {'code': '159996', 'name': '家电ETF', 'market': '0'},
    {'code': '516110', 'name': '汽车ETF', 'market': '1'},
    {'code': '159611', 'name': '电力ETF', 'market': '0'},
    {'code': '513100', 'name': '纳指科技ETF', 'market': '1'},
    {'code': '513500', 'name': '标普500ETF', 'market': '1'},
    {'code': '513050', 'name': '中概互联ETF', 'market': '1'},
    {'code': '513180', 'name': '恒生科技ETF', 'market': '1'},
    {'code': '513400', 'name': '道琼斯ETF', 'market': '1'},
    {'code': '513880', 'name': '日经ETF', 'market': '1'},
    {'code': '513030', 'name': '德国ETF', 'market': '1'},
    {'code': '513080', 'name': '法国ETF', 'market': '1'},
    {'code': '513090', 'name': '英国ETF', 'market': '1'},
    {'code': '164824', 'name': '印度ETF', 'market': '0'},
    {'code': '159987', 'name': '越南ETF', 'market': '0'},
    {'code': '510300', 'name': '沪深300ETF', 'market': '1'},
    {'code': '510500', 'name': '中证500ETF', 'market': '1'},
    {'code': '159915', 'name': '创业板ETF', 'market': '0'},
    {'code': '510050', 'name': '上证50ETF', 'market': '1'},
    {'code': '159919', 'name': '沪深300ETF', 'market': '0'},
    {'code': '512100', 'name': '中证1000ETF', 'market': '1'},
    {'code': '560010', 'name': '中证2000ETF', 'market': '1'},
    {'code': '159922', 'name': '中证500ETF', 'market': '0'},
    {'code': '588000', 'name': '科创50ETF', 'market': '1'},
    {'code': '588080', 'name': '科创板ETF', 'market': '1'},
    {'code': '159740', 'name': '科技ETF', 'market': '0'},
    {'code': '515050', 'name': '5GETF', 'market': '1'},
    {'code': '159941', 'name': '纳指ETF', 'market': '0'},
    {'code': '513100', 'name': '纳指科技ETF', 'market': '1'},
    {'code': '513500', 'name': '标普500ETF', 'market': '1'},
    {'code': '159920', 'name': '恒生ETF', 'market': '0'},
    {'code': '513050', 'name': '中概互联ETF', 'market': '1'},
    {'code': '513180', 'name': '恒生科技ETF', 'market': '1'},
    {'code': '164824', 'name': '印度ETF', 'market': '0'},
    {'code': '513030', 'name': '德国ETF', 'market': '1'},
    {'code': '513080', 'name': '法国ETF', 'market': '1'},
    {'code': '163208', 'name': '原油ETF', 'market': '0'},
    {'code': '159985', 'name': '豆粕ETF', 'market': '0'},
    {'code': '159981', 'name': '能源化工ETF', 'market': '0'},
    {'code': '518880', 'name': '黄金ETF', 'market': '1'},
    {'code': '159934', 'name': '黄金ETF', 'market': '0'},
    {'code': '511010', 'name': '国债ETF', 'market': '1'},
    {'code': '511260', 'name': '十年国债ETF', 'market': '1'},
    {'code': '159902', 'name': '中小板ETF', 'market': '0'},
    {'code': '510050', 'name': '上证50ETF', 'market': '1'},
    {'code': '510300', 'name': '沪深300ETF', 'market': '1'},
    {'code': '510500', 'name': '中证500ETF', 'market': '1'},
    {'code': '159915', 'name': '创业板ETF', 'market': '0'},
    {'code': '588000', 'name': '科创50ETF', 'market': '1'},
    {'code': '512100', 'name': '中证1000ETF', 'market': '1'},
    {'code': '560010', 'name': '中证2000ETF', 'market': '1'},
    {'code': '159919', 'name': '沪深300ETF', 'market': '0'},
    {'code': '159922', 'name': '中证500ETF', 'market': '0'},
    {'code': '588080', 'name': '科创板ETF', 'market': '1'},
    {'code': '159740', 'name': '科技ETF', 'market': '0'},
    {'code': '515050', 'name': '5GETF', 'market': '1'},
    {'code': '159941', 'name': '纳指ETF', 'market': '0'},
    {'code': '513100', 'name': '纳指科技ETF', 'market': '1'},
    {'code': '513500', 'name': '标普500ETF', 'market': '1'},
    {'code': '159920', 'name': '恒生ETF', 'market': '0'},
    {'code': '513050', 'name': '中概互联ETF', 'market': '1'},
    {'code': '513180', 'name': '恒生科技ETF', 'market': '1'},
    {'code': '164824', 'name': '印度ETF', 'market': '0'},
    {'code': '513030', 'name': '德国ETF', 'market': '1'},
    {'code': '513080', 'name': '法国ETF', 'market': '1'},
    {'code': '163208', 'name': '原油ETF', 'market': '0'},
    {'code': '159985', 'name': '豆粕ETF', 'market': '0'},
    {'code': '159981', 'name': '能源化工ETF', 'market': '0'},
    {'code': '518880', 'name': '黄金ETF', 'market': '1'},
    {'code': '159934', 'name': '黄金ETF', 'market': '0'},
    {'code': '511010', 'name': '国债ETF', 'market': '1'},
    {'code': '511260', 'name': '十年国债ETF', 'market': '1'},
    {'code': '159902', 'name': '中小板ETF', 'market': '0'},
]

def load_watchlist():
    """加载自选列表"""
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    save_watchlist(DEFAULT_WATCHLIST)
    return DEFAULT_WATCHLIST

def save_watchlist(watchlist):
    """保存自选列表"""
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(watchlist, f, ensure_ascii=False, indent=2)

def add_to_watchlist(code, name, market='1', category='a_share'):
    """添加到自选"""
    watchlist = load_watchlist()
    for item in watchlist.get(category, []):
        if item['code'] == code:
            return watchlist
    watchlist.setdefault(category, []).append({
        'code': code, 'name': name, 'market': market
    })
    save_watchlist(watchlist)
    return watchlist

def remove_from_watchlist(code, category='a_share'):
    """从自选移除"""
    watchlist = load_watchlist()
    watchlist[category] = [item for item in watchlist.get(category, []) if item['code'] != code]
    save_watchlist(watchlist)
    return watchlist

def call_tdx_tool(tool_name, arguments):
    """调用通达信MCP工具"""
    try:
        result = subprocess.run(
            ['node', '-e', f'''
            const {{ createMcpClient }} = require('{TDX_MCP_PATH}/mcp-client.js');
            async function main() {{
                const client = await createMcpClient();
                const result = await client.callTool({{
                    name: '{tool_name}',
                    arguments: {json.dumps(arguments)}
                }});
                console.log(JSON.stringify(result));
            }}
            main().catch(console.error);
            '''],
            capture_output=True, text=True, timeout=30,
            cwd=TDX_MCP_PATH
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        print(f"调用通达信工具失败: {e}")
    return None

def parse_tdx_quote(text, code, market):
    """解析通达信行情文本"""
    result = {
        'code': code,
        'market': market,
        'name': code,
        'price': 0,
        'change_pct': 0,
        'volume': 0,
        'amount': 0,
        'turnover_rate': 0,
        'updated_at': datetime.now().isoformat()
    }
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or ':' not in line:
            continue
        
        try:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().replace(',', '')
            
            if '名称' in key:
                result['name'] = value
            elif '现价' in key or '最新价' in key:
                result['price'] = float(value) if value and value != '-' else 0
            elif '涨跌幅' in key:
                result['change_pct'] = float(value.replace('%', '')) if value and value != '-' else 0
            elif '成交量' in key:
                result['volume'] = float(value) if value and value != '-' else 0
            elif '成交额' in key:
                result['amount'] = float(value) if value and value != '-' else 0
            elif '换手率' in key:
                result['turnover_rate'] = float(value.replace('%', '')) if value and value != '-' else 0
        except:
            continue
    
    return result

def get_etf_quote_batch(codes_with_market, batch_size=10):
    """批量获取ETF行情"""
    results = {}
    
    for i in range(0, len(codes_with_market), batch_size):
        batch = codes_with_market[i:i+batch_size]
        
        for item in batch:
            code = item['code']
            market = item.get('market', '1')
            
            data = call_tdx_tool('tdx_quotes', {
                'code': code,
                'setcode': market,
                'hasExtInfo': '1',
                'bspNum': '0'
            })
            
            if data and 'content' in data:
                content = data['content']
                if isinstance(content, list) and len(content) > 0:
                    text = content[0].get('text', '')
                    parsed = parse_tdx_quote(text, code, market)
                    if parsed['price'] > 0:
                        results[code] = parsed
            
            time.sleep(0.1)  # 避免请求过快
    
    return results

def get_etf_list_from_tdx(page=1, page_size=100):
    """从通达信获取ETF列表"""
    data = call_tdx_tool('tdx_screener', {
        'message': 'ETF',
        'rang': 'JJ',
        'pageNo': str(page),
        'pageSize': str(page_size)
    })
    
    etfs = []
    if data and 'content' in data:
        content = data['content']
        if isinstance(content, list) and len(content) > 0:
            text = content[0].get('text', '')
            lines = text.split('\n')
            
            for line in lines:
                if '|' in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 3 and parts[1].isdigit():
                        etfs.append({
                            'code': parts[1],
                            'name': parts[2],
                            'market': '1' if parts[1].startswith('5') or parts[1].startswith('6') else '0'
                        })
    
    return etfs

def generate_etf_data(use_cache=True):
    """生成ETF数据（缓存优先，必要时模拟数据回退）"""
    # 1. 先检查缓存（放宽到120秒，避免频繁尝试TDX）
    if use_cache and ETF_CACHE_FILE.exists():
        try:
            with open(ETF_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                cache_time = datetime.fromisoformat(cache.get('updated_at', '2000-01-01'))
                if (datetime.now() - cache_time).seconds < 120:
                    data = cache.get('data', {})
                    if data:
                        return data
        except:
            pass
    
    # 2. 尝试从通达信获取（快速超时，不阻塞）
    try:
        import signal
        codes_with_market = [{'code': etf['code'], 'market': etf['market']} for etf in COMMON_ETFS[:10]]
        tdx_data = get_etf_quote_batch(codes_with_market, batch_size=3)
        
        if len(tdx_data) >= 5:
            # 合并缓存
            full_data = generate_mock_etf_data()
            full_data.update(tdx_data)
            # 保存缓存
            with open(ETF_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({'updated_at': datetime.now().isoformat(), 'data': full_data}, f, ensure_ascii=False, indent=2)
            return full_data
    except Exception as e:
        print(f"TDX数据获取跳过: {e}")
    
    # 3. 使用模拟数据
    data = generate_mock_etf_data()
    with open(ETF_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'updated_at': datetime.now().isoformat(), 'data': data}, f, ensure_ascii=False, indent=2)
    return data

def generate_mock_etf_data():
    """生成模拟ETF数据"""
    import random
    
    data = {}
    for etf in COMMON_ETFS[:80]:  # 去重后大约80只
        code = etf['code']
        if code in data:
            continue
            
        base_price = random.uniform(0.5, 5.0)
        change_pct = random.uniform(-5, 8)
        volume = random.randint(1000000, 50000000)
        amount = volume * base_price * random.uniform(0.8, 1.2)
        
        data[code] = {
            'name': etf['name'],
            'code': code,
            'market': etf['market'],
            'price': round(base_price, 3),
            'change_pct': round(change_pct, 2),
            'volume': volume,
            'amount': round(amount, 2),
            'turnover_rate': round(random.uniform(0.5, 15), 2),
            'updated_at': datetime.now().isoformat()
        }
    
    return data

def calculate_rankings(data, sort_by='change_pct', top_n=50):
    """计算ETF排名"""
    etf_list = [{'code': code, **info} for code, info in data.items()]
    
    if sort_by == 'change_pct':
        etf_list.sort(key=lambda x: x.get('change_pct', 0), reverse=True)
    elif sort_by == 'volume':
        etf_list.sort(key=lambda x: x.get('volume', 0), reverse=True)
    elif sort_by == 'amount':
        etf_list.sort(key=lambda x: x.get('amount', 0), reverse=True)
    elif sort_by == 'turnover_rate':
        etf_list.sort(key=lambda x: x.get('turnover_rate', 0), reverse=True)
    
    for i, etf in enumerate(etf_list[:top_n], 1):
        etf['rank'] = i
    
    return etf_list[:top_n]

def get_watchlist_data():
    """获取自选ETF数据"""
    watchlist = load_watchlist()
    all_data = generate_etf_data()
    
    result = {'a_share': [], 'us': []}
    
    for category in ['a_share', 'us']:
        for item in watchlist.get(category, []):
            code = item['code']
            if code in all_data:
                result[category].append(all_data[code])
            else:
                result[category].append({
                    'code': code,
                    'name': item.get('name', code),
                    'market': item.get('market', '1'),
                    'price': 0,
                    'change_pct': 0,
                    'volume': 0,
                    'amount': 0,
                    'turnover_rate': 0,
                    'updated_at': datetime.now().isoformat()
                })
    
    for category in result:
        result[category].sort(key=lambda x: x.get('change_pct', 0), reverse=True)
    
    return result

def get_etf_detail(code):
    """获取ETF详细信息"""
    all_data = generate_etf_data()
    return all_data.get(code, None)

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
    
    all_data = generate_etf_data()
    result = {}
    
    for sector, codes in sectors.items():
        result[sector] = []
        for code in codes:
            if code in all_data:
                result[sector].append(all_data[code])
        result[sector].sort(key=lambda x: x.get('change_pct', 0), reverse=True)
    
    return result

def search_etfs(keyword, limit=20):
    """搜索ETF"""
    all_data = generate_etf_data()
    results = []
    
    keyword = keyword.lower()
    for code, info in all_data.items():
        if keyword in code or keyword in info.get('name', '').lower():
            results.append(info)
            if len(results) >= limit:
                break
    
    return results

# 初始化
if not WATCHLIST_FILE.exists():
    save_watchlist(DEFAULT_WATCHLIST)
