# Track B Agent 工作流指南

## 调用时机
每次周度扫描 Phase 2（量化1哥估值筛选）时，必须同时执行 Track B。

## 执行步骤

### Step 1: 拉取K线数据
```
对每只候选ETF，调用 mcp__tdx-connector__tdx_kline:
  - code: ETF代码（如 515880）
  - setcode: 1（沪市）或 0（深市）
  - category: 2（日线）
  - start: 0（最近）
  - count: 60（取60个交易日）
```

### Step 2: 拉取实时行情
```
对每只候选ETF，调用 mcp__tdx-connector__tdx_quotes:
  - code: ETF代码
  - setcode: 1 或 0
  - hasCalcInfo: 1
```

### Step 3: 计算因子打分
```
将K线数据格式化后，调用 factor_calculator.py 中的函数:
  - 计算动量因子: mom_60d, risk_adj_mom, dual_momentum
  - 计算均值回归: dist_from_ma20, rsi_14
  - 计算波动率: vol_20d, max_drawdown_20d
  - 计算资金流: 从quotes中提取
  - 计算微观结构: 指数调仓冲击系数
  - 计算市场状态: regime_classifier
```

### Step 4: 打分排序
```
使用 FactorCalculator.calculate_all_etf(etf_data) 得到Track B排名
```

### Step 5: 写入看板
```
调用 update_bridge.py 的 push() 函数，将结果写入 data.json
看板自动刷新显示最新数据
```

### Step 6: 与Track A融合
```
调用 fusion_engine.py 的 fuse() 函数
输出最终融合排名
```

## ETF代码映射表
| ETF名称 | 代码 | 市场 | setcode |
|---------|------|------|---------|
| 通信ETF | 515880 | 沪 | 1 |
| 科创50ETF | 588000 | 沪 | 1 |
| 半导体设备ETF | 560780 | 沪 | 1 |
| 机器人ETF | 562500 | 沪 | 1 |
| 新能源ETF | 516160 | 沪 | 1 |
| 创新药ETF | 516080 | 沪 | 1 |

## 注意事项
1. K线数据必须取至少60个交易日（用于计算60日动量）
2. 波动率计算需要日收益率序列
3. 资金流数据从quotes的m_inFlow字段提取
4. 每次计算完必须调用 update_bridge.push() 更新看板
