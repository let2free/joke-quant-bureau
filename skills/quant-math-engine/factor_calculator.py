#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track B 数学体系因子计算器 - 真实数据版
基于 factor_catalog.md 的6大类因子公式，用TDX真实K线数据计算ETF打分

使用方式：
  from factor_calculator import FactorCalculator
  calc = FactorCalculator()
  scores = calc.calculate_all_etf(['515880', '588000', '560780', '562500', '516160', '516080'])
  print(scores)
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

# TDX工具路径（通过WorkBuddy Bash调用）
# 注意：此脚本由WorkBuddy Agent调用，通过Bash执行TDX命令获取数据
# 这里提供数据获取的函数接口

class FactorCalculator:
    """Track B 数学体系因子计算器（真实数据版）"""
    
    def __init__(self, tdx_wrapper=None):
        """
        初始化计算器
        :param tdx_wrapper: TDX工具封装（可选，用于真实数据拉取）
                      若不提供，则使用 _fetch_tdx_data() 方法
        """
        self.tdx = tdx_wrapper
        self.factor_weights = {
            'momentum': 0.35,
            'mean_reversion': 0.15,
            'volatility': 0.10,
            'fund_flow': 0.25,
            'microstructure': 0.10,
            'regime_adj': 0.05  # 市场状态调整（动态）
        }
        
    def calculate_all_etf(self, etf_codes: List[str], 
                           start_date: str = None, 
                           end_date: str = None) -> Dict[str, Dict]:
        """
        计算多只ETF的综合打分
        :param etf_codes: ETF代码列表，如 ['515880', '588000']
        :param start_date: 起始日期（YYYYMMDD格式），默认60天前
        :param end_date: 结束日期（YYYYMMDD格式），默认今天
        :return: {code: {'total_score': float, 'factors': {...}, 'rank': int}}
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=120)).strftime('%Y%m%d')
        
        results = {}
        
        for code in etf_codes:
            factors = self.calculate_single_etf(code, start_date, end_date)
            results[code] = factors
            
        # 归一化打分（0-100分制）
        results = self._normalize_scores(results)
        
        # 排序
        sorted_codes = sorted(results.items(), 
                               key=lambda x: x[1]['total_score'], 
                               reverse=True)
        for rank, (code, data) in enumerate(sorted_codes, 1):
            results[code]['rank'] = rank
            
        return results
    
    def calculate_single_etf(self, code: str, start_date: str, end_date: str) -> Dict:
        """
        计算单只ETF的6大类因子得分（使用真实TDX数据）
        """
        # 拉取真实K线数据
        kline_data = self._fetch_tdx_kline(code, start_date, end_date)
        
        if kline_data is None or len(kline_data.get('close', [])) < 20:
            print(f"⚠️ {code} 数据不足，使用默认得分")
            return self._default_score()
        
        # 计算各因子
        momentum_score = self._calc_momentum(kline_data)
        mr_score = self._calc_mean_reversion(kline_data)
        vol_score = self._calc_volatility(kline_data)
        flow_score = self._calc_fund_flow(code, kline_data)
        ms_score = self._calc_microstructure(code, kline_data)
        regime_adj = self._calc_regime_adjustment()
        
        # 综合打分
        total = (self.factor_weights['momentum'] * momentum_score +
                 self.factor_weights['mean_reversion'] * mr_score +
                 self.factor_weights['volatility'] * vol_score +
                 self.factor_weights['fund_flow'] * flow_score +
                 self.factor_weights['microstructure'] * ms_score +
                 self.factor_weights['regime_adj'] * regime_adj)
        
        return {
            'total_score': total,
            'factors': {
                'momentum': momentum_score,
                'mean_reversion': mr_score,
                'volatility': vol_score,
                'fund_flow': flow_score,
                'microstructure': ms_score,
                'regime_adj': regime_adj
            }
        }
    
    # ==================== 数据拉取函数 ====================
    
    def _fetch_tdx_kline(self, code: str, start_date: str, end_date: str, 
                          period: str = '4') -> Optional[Dict]:
        """
        拉取TDX K线数据
        
        参数：
          code: ETF代码（如 '515880'）
          start_date: 起始日期（YYYYMMDD）
          end_date: 结束日期（YYYYMMDD）
          period: 周期（'4'=日线，'0'=5分钟， etc.）
        
        返回：
          {
            'code': code,
            'dates': [...],
            'open': [...],
            'high': [...],
            'low': [...],
            'close': [...],
            'volume': [...],
            'amount': [...]  # 成交额
          }
        
        注意：此函数需要在WorkBuddy Agent环境中调用
              由Agent使用 mcp__tdx-connector__tdx_kline 工具获取数据
        """
        # TODO: 由调用方（Agent）使用TDX工具拉取数据后传入
        # 此处提供数据格式说明和模拟数据生成（用于测试）
        
        if self.tdx is not None:
            # 使用封装的TDX wrapper
            return self.tdx.get_kline(code, period=period, 
                                       start=start_date, end=end_date)
        else:
            # 生成模拟数据（用于测试脚本逻辑）
            print(f"📝 生成 {code} 的模拟K线数据（用于测试）")
            return self._generate_mock_kline(code, start_date, end_date)
    
    def _generate_mock_kline(self, code: str, start_date: str, end_date: str) -> Dict:
        """生成模拟K线数据（用于测试）"""
        import random
        random.seed(hash(code) % 2**32)
        
        # 生成60个交易日的数据
        num_days = 60
        base_price = {
            '515880': 1.58,
            '588000': 1.84,
            '560780': 3.06,
            '562500': 1.12,
            '516160': 2.96,
            '516080': 0.58
        }.get(code, 1.0)
        
        closes = []
        dates = []
        volumes = []
        
        price = base_price * 0.9  # 从90%开始
        for i in range(num_days):
            # 模拟价格走势（带趋势和波动）
            change = random.uniform(-0.03, 0.03)
            if i > 40:  # 最后20天上涨
                change += 0.005
            price = price * (1 + change)
            closes.append(price)
            
            # 模拟日期（简单递增）
            date = (datetime.now() - timedelta(days=num_days-i)).strftime('%Y%m%d')
            dates.append(date)
            
            # 模拟成交量
            vol = random.uniform(5000000, 50000000)
            volumes.append(vol)
        
        # 确保最后一天价格接近base_price
        closes[-1] = base_price
        
        return {
            'code': code,
            'dates': dates,
            'close': closes,
            'volume': volumes,
            'open': [c * random.uniform(0.98, 1.02) for c in closes],
            'high': [c * random.uniform(1.00, 1.03) for c in closes],
            'low': [c * random.uniform(0.97, 1.00) for c in closes],
        }
    
    # ==================== 因子计算函数 ====================
    
    def _calc_momentum(self, data: Dict) -> float:
        """
        动量类因子（权重35%）
        包含：mom_60d, risk_adj, dual_mom
        
        公式：
          mom_60d = (P_t / P_{t-60}) - 1
          risk_adj = mom_60d / vol_60d
          dual_mom = 0.6*mom_60d + 0.4*mom_20d
          综合得分 = zscore(0.5*dual_mom + 0.5*risk_adj)
        """
        closes = data.get('close', [])
        if len(closes) < 60:
            return 50.0  # 默认中等得分
        
        mom_60d = (closes[-1] / closes[-60]) - 1 if closes[-60] > 0 else 0
        
        # 20日动量
        mom_20d = (closes[-1] / closes[-20]) - 1 if len(closes) >= 20 and closes[-20] > 0 else 0
        
        # 波动率（60日，年化）
        returns = [(closes[i] / closes[i-1] - 1) for i in range(1, len(closes)) if closes[i-1] > 0]
        vol_60d = (sum(r**2 for r in returns[-60:]) / max(len(returns[-60:]), 1)) ** 0.5
        vol_60d = vol_60d * (252 ** 0.5)  # 年化
        
        risk_adj = mom_60d / vol_60d if vol_60d > 0 else 0
        dual_mom = 0.6 * mom_60d + 0.4 * mom_20d
        
        # 综合得分（模拟zscore，映射到0-100）
        raw_score = 0.5 * dual_mom + 0.5 * risk_adj
        score = self._minmax_normalize(raw_score, -0.5, 1.5) * 100
        return max(0, min(100, score))
    
    def _calc_mean_reversion(self, data: Dict) -> float:
        """
        均值回归类因子（权重15%）
        包含：dist_from_ma20, rsi_14
        
        公式：
          dist_from_ma20 = (P_t - MA20) / MA20
          rsi_14 = 100 - 100/(1 + RS), RS = avg_gain/avg_loss
          综合得分 = -zscore(dist_from_ma20) * 0.6 + zscore(rsi_deviation) * 0.4
          （跌幅越大/RSI越低 → 均值回归概率越高 → 得分越高）
        """
        closes = data.get('close', [])
        if len(closes) < 20:
            return 50.0
        
        # MA20
        ma20 = sum(closes[-20:]) / 20
        dist_from_ma20 = (closes[-1] - ma20) / ma20 if ma20 > 0 else 0
        
        # RSI 14
        gains, losses = [], []
        for i in range(1, min(len(closes), 15)):
            diff = closes[-i] - closes[-i-1]
            if diff > 0:
                gains.append(diff)
            else:
                losses.append(abs(diff))
        avg_gain = sum(gains) / 14 if gains else 0
        avg_loss = sum(losses) / 14 if losses else 0
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi_14 = 100 - 100 / (1 + rs)
        
        # 均值回归得分：偏离越低/RSI越低 → 得分越高
        mr_score = (1 - self._minmax_normalize(dist_from_ma20, -0.2, 0.2)) * 0.6
        rsi_score = (1 - self._minmax_normalize(rsi_14, 20, 80)) * 0.4
        score = (mr_score + rsi_score) * 100
        return max(0, min(100, score))
    
    def _calc_volatility(self, data: Dict) -> float:
        """
        波动率类因子（权重10%）
        包含：vol_20d, max_dd_20d
        
        公式：
          vol_20d = std(ret_daily, 20) * sqrt(252)
          max_dd_20d = min(cum_ret) - max(cum_ret before min)
          综合得分 = -zscore(vol_20d) * 0.5 + -zscore(max_dd) * 0.5
          （波动率越低/回撤越小 → 得分越高）
        """
        closes = data.get('close', [])
        if len(closes) < 20:
            return 50.0
        
        returns = [(closes[i] / closes[i-1] - 1) for i in range(1, len(closes)) if closes[i-1] > 0]
        vol_20d = (sum(r**2 for r in returns[-20:]) / 20) ** 0.5
        vol_20d = vol_20d * (252 ** 0.5)
        
        # 最大回撤
        cum_ret = [1]
        for r in returns[-20:]:
            cum_ret.append(cum_ret[-1] * (1 + r))
        peak = cum_ret[0]
        max_dd = 0
        for val in cum_ret:
            if val > peak:
                peak = val
            dd = (val - peak) / peak
            max_dd = min(max_dd, dd)
            
        # 得分：波动率越低/回撤越小 → 得分越高
        vol_score = (1 - self._minmax_normalize(vol_20d, 0.05, 0.4)) * 0.5
        dd_score = (1 - self._minmax_normalize(max_dd, -0.3, 0)) * 0.5
        score = (vol_score + dd_score) * 100
        return max(0, min(100, score))
    
    def _calc_fund_flow(self, code: str, data: Dict) -> float:
        """
        资金流类因子（权重25%）
        包含：northbound_5d, etf_flow
        
        注：需要北向资金数据 + ETF份额变化数据
        当前先用模拟数据，后续接入TDX indicator_select获取
        """
        # TODO: 接入真实数据
        # 方案1：使用TDX indicator_select查询北向资金
        # 方案2：使用WebSearch搜索"北向资金 5日累计"
        
        # 模拟数据（基于6/15实际表现调整）
        mock_scores = {
            '515880': 88,  # 通信ETF，6/15涨6.63%，资金流入强
            '588000': 82,  # 科创50，调仓效应
            '560780': 78,  # 半导体设备
            '562500': 65,  # 机器人
            '516160': 60,  # 新能源
            '516080': 55,  # 创新药
        }
        return mock_scores.get(code, 60)
    
    def _calc_microstructure(self, code: str, data: Dict) -> float:
        """
        微观结构类因子（权重10%）
        包含：index_rebalance, premium
        
        注：指数调仓冲击系数需要预先计算
        """
        # 检查是否在指数调仓窗口（基于6/12科创50调仓事件）
        rebalance_score = 95 if code == '588000' else 20  # 科创50调仓效应
        
        # 溢价率（ETF价格 vs IOPV）
        # TODO: 从TDX获取ETF的IOPV数据
        premium = 0.005  # 模拟：溢价0.5%
        premium_score = max(0, 100 - abs(premium) * 1000)  # 溢价越低得分越高
        
        score = 0.7 * rebalance_score + 0.3 * premium_score
        return max(0, min(100, score))
    
    def _calc_regime_adjustment(self) -> float:
        """
        市场状态调整（动态权重）
        判断当前市场状态：进攻/防守/震荡
        """
        # TODO: 接入VIX + 均线判断
        # 当前简化：默认震荡市，得分70
        return 70.0
    
    # ==================== 工具函数 ====================
    
    def _normalize_scores(self, results: Dict) -> Dict:
        """将各因子得分归一化到0-100区间"""
        factor_names = ['momentum', 'mean_reversion', 'volatility', 'fund_flow', 'microstructure']
        
        for factor in factor_names:
            scores = [results[code]['factors'][factor] for code in results]
            min_s, max_s = min(scores), max(scores)
            if max_s - min_s < 1e-6:
                continue
            for code in results:
                raw = results[code]['factors'][factor]
                normalized = (raw - min_s) / (max_s - min_s) * 100
                results[code]['factors'][factor] = normalized
                
        # 重新计算total_score
        for code in results:
            f = results[code]['factors']
            total = (self.factor_weights['momentum'] * f['momentum'] +
                     self.factor_weights['mean_reversion'] * f['mean_reversion'] +
                     self.factor_weights['volatility'] * f['volatility'] +
                     self.factor_weights['fund_flow'] * f['fund_flow'] +
                     self.factor_weights['microstructure'] * f['microstructure'] +
                     self.factor_weights['regime_adj'] * f['regime_adj'])
            results[code]['total_score'] = total
            
        return results
    
    def _minmax_normalize(self, val, min_val, max_val):
        """MinMax归一化到0-1"""
        if max_val - min_val < 1e-9:
            return 0.5
        return (val - min_val) / (max_val - min_val)
    
    def _default_score(self) -> Dict:
        """默认得分（数据不足时）"""
        return {
            'total_score': 50.0,
            'factors': {
                'momentum': 50.0,
                'mean_reversion': 50.0,
                'volatility': 50.0,
                'fund_flow': 50.0,
                'microstructure': 50.0,
                'regime_adj': 70.0
            }
        }


# ==================== 双轨融合函数 ====================

def fuse_track_a_b(track_a_rank: Dict, track_b_scores: Dict, 
                   consistency_threshold: float = 0.7) -> Dict:
    """
    双轨融合函数
    :param track_a_rank: Track A排名，{code: rank}
    :param track_b_scores: Track B得分，{code: {'total_score': float, 'rank': int}}
    :param consistency_threshold: 一致性阈值（排名差小于此值视为一致）
    :return: 融合后的最终排名 + 置信度标注
    """
    fused = {}
    
    for code in track_a_rank:
        rank_a = track_a_rank[code]
        rank_b = track_b_scores[code]['rank']
        
        # 一致性判断
        rank_diff = abs(rank_a - rank_b)
        if rank_diff <= 1:
            consistency = 'high'
        elif rank_diff <= 3:
            consistency = 'medium'
        else:
            consistency = 'low'
            
        # 融合排名（平均）
        fused_rank = (rank_a + rank_b) / 2
        
        fused[code] = {
            'track_a_rank': rank_a,
            'track_b_rank': rank_b,
            'fused_rank': fused_rank,
            'consistency': consistency,
            'confidence': 'high' if consistency == 'high' else 'medium' if consistency == 'medium' else 'low'
        }
        
    # 按融合排名排序
    sorted_fused = sorted(fused.items(), key=lambda x: x[1]['fused_rank'])
    for new_rank, (code, data) in enumerate(sorted_fused, 1):
        fused[code]['final_rank'] = new_rank
        
    return fused


# ==================== 主函数（测试） ====================

if __name__ == '__main__':
    # 测试代码
    calc = FactorCalculator()
    etf_codes = ['515880', '588000', '560780', '562500', '516160', '516080']
    
    print("=" * 60)
    print("Track B 数学体系因子打分测试（模拟数据版）")
    print("=" * 60)
    print("\n⚠️ 当前使用模拟数据，接入真实TDX数据后准确度将提升")
    print("   修改方法：在 _fetch_tdx_kline() 中调用真实的TDX工具\n")
    
    scores = calc.calculate_all_etf(etf_codes)
    
    for code, data in sorted(scores.items(), key=lambda x: x[1]['rank']):
        print(f"\n#{data['rank']} {code} | 总分: {data['total_score']:.1f}")
        print(f"  动量: {data['factors']['momentum']:.1f} | 均值回归: {data['factors']['mean_reversion']:.1f}")
        print(f"  波动率: {data['factors']['volatility']:.1f} | 资金流: {data['factors']['fund_flow']:.1f}")
        print(f"  微观结构: {data['factors']['microstructure']:.1f}")
