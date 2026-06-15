# 因子目录与数学公式详解
# 版本：v1.0 | 最后更新：2026-06-16

---

## 一、动量类因子（Momentum Factors）

### 1.1 绝对动量（Absolute Momentum）

**公式**：
```
mom_n = (P_t / P_{t-n}) - 1
```
- `n = 5` → 1周动量
- `n = 20` → 1月动量（最常用的短期动量）
- `n = 60` → 3月动量（**核心**，etf-rotation-backtester 默认63日）
- `n = 120` → 6月动量（长期趋势确认）

**归一化**：
```
mom_score = (rank_mom - min_rank) / (max_rank - min_rank) × 100
```

**多周期动量复合**（推荐）：
```
mom_composite = 0.4 × mom_20 + 0.4 × mom_60 + 0.2 × mom_120
```

---

### 1.2 风险调整动量（Risk-Adjusted Momentum）

**公式**（类夏普比率）：
```
risk_adj_mom = mom_n / vol_n
```
其中：
- `mom_n` = 过去 n 日收益率
- `vol_n` = 过去 n 日收益率标准差（年化）

**改进版**（索提诺比率，只考虑下行波动）：
```
sortino = mom_n / downside_dev_n
```
其中 `downside_dev` = 只计算负收益的标准差

---

### 1.3 双重动量（Dual Momentum）

**逻辑**（Gary Antonacci 的经典方法）：
1. 绝对动量过滤：只保留 `mom_n > 0` 的 ETF
2. 相对动量排名：在保留的 ETF 中，按 `mom_n` 从高到低排名

**公式**：
```
if mom_120 > 0:
    score = mom_60
else:
    score = -999  # 过滤掉
```

---

### 1.4 跨资产动量（Cross-Asset Momentum）

**逻辑**：不只看 ETF 自身价格动量，还看其底层资产类别（股/债/商品）的动量

**公式**：
```
cross_asset_mom = w1 × ETF_price_mom + w2 × underlying_asset_mom
```

示例（商品 ETF）：
- ETF价格动量：+5%
- 商品期货动量：-2%
- 跨资产动量 = 0.5×(5) + 0.5×(-2) = +1.5%（更准确）

---

## 二、均值回归类因子（Mean Reversion Factors）

### 2.1 均线偏离度（Distance from Moving Average）

**公式**：
```
dev_n = (P_t - MA_n) / MA_n
```
- `dev_n < 0` → 价格低于均线（超卖，均值回归潜力大）
- `dev_n > 0` → 价格高于均线（超买，回归潜力小）

**打分**（均值回归逻辑：负偏离越大分越高）：
```
mr_score = -dev_n × 100  # 翻转符号
```

---

### 2.2 BOLL带位置（Bollinger Band Position）

**公式**：
```
boll_pos = (P_t - lower) / (upper - lower)
```
- `boll_pos ≈ 0` → 价格在下轨附近（超卖）
- `boll_pos ≈ 1` → 价格在上轨附近（超买）
- `boll_pos > 1` → 突破上轨（强势，但警惕反转）

**打分**：
```
mr_score = (1 - boll_pos) × 100  # 越靠近下轨分越高
```

---

### 2.3 RSI 超买超卖（Relative Strength Index）

**公式**：
```
RSI_n = 100 - [100 / (1 + RS)]
RS = avg_gain_n / avg_loss_n
```
- `RSI > 70` → 超买（均值回归候选：做空或等回调）
- `RSI < 30` → 超卖（均值回归候选：做多或反弹）

**打分**：
```
mr_score = (70 - RSI) if RSI > 70 else (RSI - 30) if RSI < 30 else 0
```

---

## 三、波动率类因子（Volatility Factors）

### 3.1 历史波动率（Historical Volatility）

**公式**（年化）：
```
vol_n = std(ret_daily, n) × sqrt(252)
```

**打分**（波动率越低分越高，因为低波 = 确定性高）：
```
vol_score = 100 - normalized_vol
```

---

### 3.2 波动率放大因子（Volatility Expansion）

**逻辑**：波动率从低位突然放大，往往预示趋势开始（或结束）

**公式**：
```
vol_ratio = vol_recent / vol_historical
```
- `vol_ratio > 1.5` → 波动率急剧放大（可能趋势启动）
- `vol_ratio < 0.8` → 波动率压缩（可能盘整即将结束）

**打分**：
```
vol_exp_score = (vol_ratio - 1) × 100  if vol_ratio > 1 else 0
```

---

### 3.3 最大回撤（Maximum Drawdown）

**公式**：
```
dd_t = (P_t - max(P_0...P_t)) / max(P_0...P_t)
max_dd = min(dd_t)  # 最负值
```

**打分**：
```
risk_score = 100 + max_dd × 100  # max_dd = -0.15 → score = 85
```

---

## 四、成交量/资金流类因子（Volume/Flow Factors）

### 4.1 量比（Volume Ratio）

**公式**：
```
vol_ratio = vol_t / avg(vol, n)
```
- `vol_ratio > 2` → 放量（可能突破或反转）
- `vol_ratio < 0.5` → 缩量（观望）

**打分**：
```
vol_score = min(vol_ratio, 3) × 20  # 最高分 = 60（vol_ratio=3）
```

---

### 4.2 资金流入强度（Fund Flow Intensity）

**逻辑**：用 ETF 份额变动近似资金流入（精确的需递归 ETF 持仓再算）

**公式**：
```
flow_n = (shares_t - shares_{t-n}) / shares_{t-n}  # 份额变动率
flow_score = flow_n × 100  # 正值 = 流入（加分），负值 = 流出（减分）
```

---

### 4.3 北向资金因子（Northbound Capital Flow，A股专属）

**公式**：
```
northbound_flow_n = sum(daily_northbound, n)
flow_score = rank(northbound_flow)  # 按流入金额排名
```

**数据获取**：TDX 工具查询（代码：869998 北向资金汇总）

---

## 五、微观结构类因子（Microstructure Factors）

### 5.1 指数调仓冲击系数（Index Rebalance Impact）

**公式**：
```
impact = |new_weight - old_weight| × AUM / adv
```
- `impact > 5` → 强烈买入/卖出信号（价格冲击显著）
- `impact 1-5` → 中等信号
- `impact < 1` → 可忽略

**打分**：
```
ms_score = min(impact, 10) × 10  # 最高分 = 100
```

---

### 5.2 ETF 溢价率（Premium/Discount to NAV）

**公式**：
```
premium = (ETF_price - NAV) / NAV
```
- `premium > 0.02` → 高溢价（谨慎，可能回调）
- `premium < -0.02` → 折价（机会，可能收敛）

**打分**：
```
if premium > 0.02:
    penalty = -abs(premium) × 1000  # 高溢价惩罚
else:
    penalty = 0
```

---

## 六、复合因子示例

### 6.1 "动量+波动率"组合（长期有效性最高）

```
composite = 0.5 × risk_adj_mom + 0.3 × (100 - normalized_vol) + 0.2 × mr_score
```

### 6.2 A股科技 ETF 专属组合

```
a_share_tech = 0.35 × mom_60 + 0.25 × northbound_flow_20 
              + 0.15 × (100 - normalized_vol) + 0.10 × index_rebalance_impact
              + 0.15 × (if premium < 0.01 then 100 else 0)
```

---

## 七、因子有效性检验（IC 分析）

**信息系数（Information Coefficient）**：
```
IC = correlation(rank(factor), rank(return_future))
```
- `IC > 0.1` → 因子有效
- `IC > 0.2` → 因子很强
- `IC < 0` → 因子无效（甚至反向）

**迭代规则**：
- 若某因子连续3次 IC < 0 → 自动剔除
- 若某新因子 IC > 0.3 → 提示人工审核后加入

---

*本文件会随着每次复盘自动更新，新增因子或修正公式。*
