# 九章量化局 · 历史数据库设计

## 数据文件结构

### 1. 每日预测记录 (`dashboard/history.jsonl`)

JSONL格式，每行一个交易日：

```jsonl
{
  "date": "2026-06-16",
  "market_state": {
    "L0": "loose",
    "L0_details": {
      "omo_mlf": 2850,
      "dr007": 1.65,
      "north_bound": 58.3
    },
    "L4b": {
      "rebalance": true,
      "impact_coefficient": 4.1
    }
  },
  "predictions": [
    {
      "rank": 1,
      "code": "515880",
      "name": "通信ETF",
      "track_a_score": 82.5,
      "track_b_score": 78.3,
      "fused_score": 84.9,
      "pred_rank": 1,
      "actual_change": 6.63,
      "actual_rank": 1,
      "direction_correct": true,
      "rank_error": 0
    }
  ],
  "accuracy": {
    "rank_accuracy": 0.7,
    "top3_accuracy": 0.67,
    "top5_accuracy": 0.8,
    "direction_accuracy": 0.8
  },
  "recap_triggered": false,
  "recap_version": null
}
```

### 2. 因子权重历史 (`dashboard/weight_history.jsonl`)

追踪因子权重变化（复盘后更新）：

```jsonl
{
  "date": "2026-06-16",
  "version": "v2.1",
  "trigger": "accuracy < 95%",
  "weights_before": {
    "momentum": 0.35,
    "mean_reversion": 0.15,
    "volatility": 0.10,
    "capital_flow": 0.25,
    "microstructure": 0.10,
    "market_regime": 0.05
  },
  "weights_after": {
    "momentum": 0.30,
    "mean_reversion": 0.20,
    "volatility": 0.10,
    "capital_flow": 0.25,
    "microstructure": 0.10,
    "market_regime": 0.05
  },
  "L0_adjustment": {
    "loose_before": 0.10,
    "loose_after": 0.12,
    "tight_before": -0.20,
    "tight_after": -0.18
  },
  "L4b_adjustment": {
    "impact_threshold_before": 3.0,
    "impact_threshold_after": 2.5,
    "weight_before": 0.25,
    "weight_after": 0.30
  }
}
```

### 3. 复盘报告索引 (`dashboard/recap_index.json`)

```json
{
  "total_recaps": 3,
  "recaps": [
    {
      "date": "2026-06-15",
      "version": "v2.1",
      "trigger": "rank_accuracy=0.6",
      "root_cause": "低估L4b调仓效应",
      "file": "artifacts/2026-06-15/recap_report.md"
    }
  ]
}
```

---

## 回测系统设计方案

### 功能需求

1. **历史预测准确率分析**
   - 按日期范围查询准确率
   - 按ETF类型分组统计
   - 按市场状态（L0宽松/紧张）分组统计

2. **因子权重优化模拟**
   - 模拟不同权重组合的历史表现
   - 找到最佳权重配置

3. **策略回测**
   - 模拟按照预测结果买卖ETF的收益
   - 对比基准（沪深300、持有ETF等）

### 技术实现

**后端API**（新增到 `dashboard_server.py`）：

```
GET /api/backtest/accuracy?start=2026-06-01&end=2026-06-30
  → 返回指定日期范围的准确率曲线

GET /api/backtest/factor-optimize?start=...&end=...
  → 返回最佳因子权重配置

POST /api/backtest/run
  Body: {
    "start_date": "2026-06-01",
    "end_date": "2026-06-30",
    "initial_capital": 100000,
    "top_n": 5,
    "hold_days": 5
  }
  → 返回回测结果（收益率、夏普比率、最大回撤）
```

**前端页面**（新增 `dashboard/backtest.html`）：

1. 准确率趋势图（Chart.js折线图）
2. 因子权重优化器（交互式滑块）
3. 策略回测面板（输入参数，运行回测）

---

## 数据沉淀价值

### 短期（1个月）
- 积累20个交易日数据
- 识别系统性偏差（哪些因子预测不准）
- 第一次权重优化

### 中期（3个月）
- 积累60个交易日数据
- 建立因子有效性排名
- 适应不同市场状态（牛市/熊市/震荡）

### 长期（6个月+）
- 积累120+交易日数据
- 机器学习模型训练数据充足
- 预测准确率稳定在95%+

---

## 下一步

1. ✅ 创建每日收盘复盘自动化（已完成）
2. ⏳ 创建 `history.jsonl` 数据文件（待做）
3. ⏳ 开发回测API（待做）
4. ⏳ 开发回测前端页面（待做）
5. ⏳ 集成到看板"历史复盘"Tab（待做）

---

**文件位置**：`docs/history_database_design.md`
**创建时间**：2026-06-16 08:25
**作者**：元宝(desktop)
