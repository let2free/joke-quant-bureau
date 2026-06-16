"""
九章量化局 - 历史数据导入模块
支持：通达信、同花顺、东方财富、Wind、聚宽
"""
import json
import csv
import os
from datetime import datetime
from pathlib import Path

class DataImporter:
    """历史数据导入器"""
    
    SUPPORTED_PLATFORMS = {
        'tdx': '通达信',
        'ths': '同花顺',
        'eastmoney': '东方财富',
        'wind': 'Wind',
        'joinquant': '聚宽',
        'csv': '通用CSV'
    }
    
    def __init__(self, data_dir='artifacts'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
    
    def import_tdx(self, file_path: str, date: str = None) -> dict:
        """
        导入通达信数据
        支持：.txt, .csv 格式
        格式：日期,开盘,最高,最低,收盘,成交量,成交额
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        records = []
        with open(file_path, 'r', encoding='gbk') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) >= 6:
                    records.append({
                        'date': parts[0],
                        'open': float(parts[1]),
                        'high': float(parts[2]),
                        'low': float(parts[3]),
                        'close': float(parts[4]),
                        'volume': float(parts[5]),
                        'amount': float(parts[6]) if len(parts) > 6 else 0
                    })
        
        return self._save_import(date, 'tdx', records)
    
    def import_ths(self, file_path: str, date: str = None) -> dict:
        """
        导入同花顺数据
        支持：.xls, .csv 格式
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    'date': row.get('日期', row.get('date', '')),
                    'open': float(row.get('开盘', row.get('open', 0))),
                    'high': float(row.get('最高', row.get('high', 0))),
                    'low': float(row.get('最低', row.get('low', 0))),
                    'close': float(row.get('收盘', row.get('close', 0))),
                    'volume': float(row.get('成交量', row.get('volume', 0))),
                    'amount': float(row.get('成交额', row.get('amount', 0)))
                })
        
        return self._save_import(date, 'ths', records)
    
    def import_eastmoney(self, file_path: str, date: str = None) -> dict:
        """
        导入东方财富数据
        支持：.csv 格式
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    'date': row.get('日期', row.get('date', '')),
                    'open': float(row.get('开盘', row.get('open', 0))),
                    'high': float(row.get('最高', row.get('high', 0))),
                    'low': float(row.get('最低', row.get('low', 0))),
                    'close': float(row.get('收盘', row.get('close', 0))),
                    'volume': float(row.get('成交量', row.get('volume', 0))),
                    'amount': float(row.get('成交额', row.get('amount', 0)))
                })
        
        return self._save_import(date, 'eastmoney', records)
    
    def import_wind(self, file_path: str, date: str = None) -> dict:
        """
        导入Wind数据
        支持：.csv, .xlsx 格式
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    'date': row.get('TRADE_DATE', row.get('date', '')),
                    'open': float(row.get('OPEN', row.get('open', 0))),
                    'high': float(row.get('HIGH', row.get('high', 0))),
                    'low': float(row.get('LOW', row.get('low', 0))),
                    'close': float(row.get('CLOSE', row.get('close', 0))),
                    'volume': float(row.get('VOLUME', row.get('volume', 0))),
                    'amount': float(row.get('AMOUNT', row.get('amount', 0)))
                })
        
        return self._save_import(date, 'wind', records)
    
    def import_joinquant(self, file_path: str, date: str = None) -> dict:
        """
        导入聚宽数据
        支持：.csv 格式
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append({
                    'date': row.get('date', row.get('日期', '')),
                    'open': float(row.get('open', row.get('开盘', 0))),
                    'high': float(row.get('high', row.get('最高', 0))),
                    'low': float(row.get('low', row.get('最低', 0))),
                    'close': float(row.get('close', row.get('收盘', 0))),
                    'volume': float(row.get('volume', row.get('成交量', 0))),
                    'amount': float(row.get('money', row.get('成交额', 0)))
                })
        
        return self._save_import(date, 'joinquant', records)
    
    def import_csv(self, file_path: str, date: str = None, mapping: dict = None) -> dict:
        """
        导入通用CSV数据
        可自定义列映射
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if mapping is None:
            mapping = {
                'date': ['日期', 'date', 'Date', 'DATE', '时间'],
                'open': ['开盘', 'open', 'Open', 'OPEN'],
                'high': ['最高', 'high', 'High', 'HIGH'],
                'low': ['最低', 'low', 'Low', 'LOW'],
                'close': ['收盘', 'close', 'Close', 'CLOSE'],
                'volume': ['成交量', 'volume', 'Volume', 'VOLUME'],
                'amount': ['成交额', 'amount', 'Amount', 'AMOUNT', 'money']
            }
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = {}
                for field, aliases in mapping.items():
                    for alias in aliases:
                        if alias in row:
                            record[field] = float(row[alias]) if field != 'date' else row[alias]
                            break
                    if field not in record:
                        record[field] = 0 if field != 'date' else ''
                records.append(record)
        
        return self._save_import(date, 'csv', records)
    
    def _save_import(self, date: str, platform: str, records: list) -> dict:
        """保存导入数据到artifacts目录"""
        date_dir = self.data_dir / date
        date_dir.mkdir(exist_ok=True)
        
        # 保存原始数据
        output_file = date_dir / f'import_{platform}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'platform': platform,
                'platform_name': self.SUPPORTED_PLATFORMS.get(platform, platform),
                'import_time': datetime.now().isoformat(),
                'record_count': len(records),
                'data': records
            }, f, ensure_ascii=False, indent=2)
        
        return {
            'success': True,
            'platform': platform,
            'platform_name': self.SUPPORTED_PLATFORMS.get(platform, platform),
            'date': date,
            'record_count': len(records),
            'file_path': str(output_file)
        }
    
    def get_import_history(self) -> list:
        """获取所有导入历史"""
        history = []
        for date_dir in sorted(self.data_dir.iterdir()):
            if date_dir.is_dir():
                for file in date_dir.glob('import_*.json'):
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        history.append({
                            'date': date_dir.name,
                            'platform': data.get('platform'),
                            'platform_name': data.get('platform_name'),
                            'record_count': data.get('record_count'),
                            'import_time': data.get('import_time')
                        })
        return history

# 单例
importer = DataImporter()
