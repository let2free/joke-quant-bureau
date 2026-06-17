# 九章量化局 · 页面说明书 v1.0

## 首页 — 实时看板

| 板块 | 数据来源 | 刷新频率 |
|------|---------|---------|
| 大盘指数(上证/深证/创业板/科创50) | 通达信TDX API | 5秒 |
| 今日复盘总结 | accuracy_history.json | 60秒 |
| 预测跟踪(最新+历史) | artifacts/日期/fusion_report.json | 60秒 |
| ETF实时排名TOP10 | 通达信TDX(62只) | 30秒 |
| 自选ETF榜单(A股/美股) | watchlist.json + TDX | 30秒 |
| ETF全量数据表+双轨对比 | 通达信TDX | 30秒 |
| 🔄 板块轮动周期图(v2.0) | 模拟数据(交易时段切换真实) | 按需 |
| 🔥 ETF相关性矩阵(v2.0) | /api/etf/correlation | 按需 |
| 🎯 历史准确率趋势 | accuracy_history.json | 60秒 |

## 测算中心 — jiuzhang.html

| 板块 | 数据来源 |
|------|---------|
| 流程执行状态(Phase0-5) | 本地mock数据 |
| 核心指标(日期/准确率/校准/市场) | mock数据 |
| 预测排名表 | mock数据(接API实时更新) |
| 因子雷达图 | mock数据 |
| 准确率趋势 | mock数据 |
| 误差分析 | mock数据 |
| 风险提示 | mock数据 |

## ETF监测 — etf_monitor.html

| 板块 | 数据来源 |
|------|---------|
| 涨幅TOP10 | 通达信TDX |
| 行业分类(8类) | ETF名称自动分类 |
| 自选管理(添加/移除) | watchlist.json |
| ETF搜索 | 名称+代码匹配 |

## 拓扑分析 — topology.html

| 板块 | 数据来源 |
|------|---------|
| 核心指标(4格) | mock数据 |
| 行业资金流向 | mock数据 |
| 行业热力图 | mock数据 |
| 最新消息+影响 | mock数据 |
| 风险-消息-ETF拓扑SVG | mock数据 |
| 板块轮动折线 | 模拟数据 |

## 回测验证 — backtest.html

| 板块 | 数据来源 |
|------|---------|
| 回测参数设置 | backtest_settings.json |
| 回测结果 | /api/backtest/run |
| 准确率历史 | /api/backtest/accuracy |
| 因子优化 | /api/backtest/factor-optimize |

## 历史数据 — history.html

| 板块 | 数据来源 |
|------|---------|
| 数据上传 | 用户上传JSON/CSV |
| 数据浏览 | 本地history.jsonl |

## 龙虾协同 — lobster_collab.html

| 板块 | 数据来源 |
|------|---------|
| Agent状态(9个) | agents_status.json |
| 协同日志 | collab_log.jsonl |
| 预测产物 | artifacts.json |
| 冲突记录 | conflicts.json |
