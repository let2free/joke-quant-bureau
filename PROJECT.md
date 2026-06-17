# 九章量化局 · 项目文件

## 项目信息

| 项目 | 详情 |
|------|------|
| 名称 | 九章量化局 (Joke Quant Bureau) |
| 仓库 | github.com/let2free/joke-quant-bureau |
| 版本 | v3.2 |
| 负责人 | 云鹏（老大） |
| 技术栈 | Python + HTML/CSS/JS + 通达信TDX |

## 团队角色

| 角色 | Agent | 职责 |
|------|-------|------|
| 主理人 | 元宝(desktop) | 协调调度、前后端开发 |
| 部署 | 豆宝(Coze) | 在线部署、API集成 |
| 知识库 | 天宝(IMA) | 文档归档、数据存储 |
| 沙箱 | 云宝(sandbox) | 代码运行、测试环境 |
| 代码修复 | 修复师 | Bug修复、代码审查 |

## 目录结构

```
joke-quant-bureau/
├── README.md               # 项目说明
├── PROJECT.md              # 本文件
├── LICENSE                 # MIT许可证
├── .gitignore              # Git排除规则
├── requirements.txt        # Python依赖
├── start.bat               # Windows一键启动
├── start_dashboard.bat     # 看板启动脚本
├── docs/                   # 文档
│   ├── architecture.md     # 架构设计
│   ├── collaboration.md    # 协同协议
│   └── jiuzhang_workflow.md # 九章工作流程
├── dashboard/              # 看板系统（v3.2）
│   ├── dashboard_server.py # HTTP服务器 端口7860（多线程+日志轮转）
│   ├── db.py               # SQLite持久化模块（v3.2新增）
│   ├── backtest.py         # 回测模块（真实K线+网格搜索）
│   ├── data_fetcher.py     # 腾讯行情API数据获取（v3.1新增）
│   ├── fusion_engine.py    # 融合引擎（含FOMC FedWatch）
│   ├── config.py           # 六因子权重配置
│   ├── etf_data.py         # ETF数据获取（1563只全市场）
│   ├── data_importer.py    # 多平台数据导入
│   ├── *.html              # 7个前端页面（移动端适配）
│   ├── jiuzhang.db         # SQLite数据库（运行时）
│   └── artifacts/          # 按日期存储的预测/复盘
├── scripts/                # 工具脚本
├── skills/                 # WorkBuddy Skills定义
└── .git/                   # Git仓库
```

## 7个前端页面

| 页面 | 文件 | 功能 | 状态 |
|------|------|------|------|
| 实时看板 | dashboard.html | 复盘总结+次日预测+ETF排名+自选榜单 | 🟡 部分功能待修复 |
| 测算中心 | jiuzhang.html | 九章流程+因子分析+准确率 | 🟡 数据加载待优化 |
| ETF监测 | etf_monitor.html | ETF排名+自选管理+行业分析 | 🟡 管理弹窗待测试 |
| 拓扑分析 | topology.html | 资金流+行业热力+风险拓扑 | 🟢 正常 |
| 回测验证 | backtest.html | 历史回测+因子优化 | 🟡 API返回空数据 |
| 历史数据 | history.html | 数据导入/浏览 | 🟢 正常 |
| 龙虾协同 | lobster_collab.html | Agent协作状态 | 🟢 正常 |

## API清单

| 端点 | 方法 | 功能 | 版本 |
|------|------|------|------|
| /api/status | GET | 服务器状态 | v2.0 |
| /api/data | GET | 看板数据 | v2.0 |
| /api/etf/rankings | GET | ETF排名 | v2.0 |
| /api/etf/watchlist | GET | 自选列表 | v2.0 |
| /api/etf/watchlist/add | POST | 添加自选 | v2.0 |
| /api/etf/watchlist/remove | POST | 移除自选 | v2.0 |
| /api/etf/refresh | GET | 刷新数据 | v2.0 |
| /api/etf/search | GET | 搜索ETF | v2.0 |
| /api/etf/detail/{code} | GET | ETF详情 | v2.0 |
| /api/etf/sectors | GET | 行业分类 | v2.0 |
| /api/etf/universe | GET | 监控池配置 | v3.0 |
| /api/market/indices | GET | 指数实时行情 | v3.0 |
| /api/market/realtime | GET | 批量实时行情 | v3.0 |
| /api/market/kline | GET | K线数据 | v3.0 |
| /api/fusion/report | GET | 融合报告（实时计算） | v3.0 |
| /api/fusion/factors | GET | 因子详情 | v3.0 |
| /api/trends/volatility | GET | 波动率趋势 | v3.1 |
| /api/trends/factors | GET | 因子趋势 | v3.1 |
| /api/alerts | GET | 异常预警 | v3.1 |
| /api/backtest/accuracy | GET | 回测准确率 | v2.0 |
| /api/backtest/factor-optimize | GET | 因子优化 | v2.0 |
| /api/backtest/run | POST | 运行回测 | v2.0 |
| /api/backtest/settings | GET | 回测设置 | v3.1 |
| /api/predictions/latest | GET | 最新预测 | v2.0 |
| /api/predictions/history | GET | 预测历史 | v2.0 |
| /api/accuracy/history | GET | 准确率历史 | v2.0 |
| /api/agents/status | GET | Agent状态 | v2.0 |
| /api/db/stats | GET | 数据库统计 | v3.2 |
| /api/cache/clear | GET | 清除缓存 | v3.0 |
| /api/export | GET | 导出CSV | v2.0 |
| /api/import | POST | 导入数据 | v2.0 |
| /log | GET | 访问日志 | v2.0 |

## 版本演进

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| v1.0 | 2026-06-11 | 初始版本，硬编码数据 |
| v2.0 | 2026-06-12 | 双轨制架构，7页面看板，9Agent协同 |
| v3.0 | 2026-06-15 | 腾讯行情API，真实因子计算，融合引擎 |
| v3.1 | 2026-06-17 | 真实K线回测，FOMC FedWatch，异常预警，趋势API |
| v3.2 | 2026-06-17 | SQLite持久化，多线程服务器，日志轮转，移动端适配 |

## 已知问题

| 编号 | 问题 | 优先级 |
|------|------|--------|
| BUG-01 | 新闻情绪因子待接入 | 🟡 |
| BUG-02 | Cloudflare Tunnel URL重启后变化 | 🟡 |
| BUG-03 | 元宝BOT AI模型待配置API Key | 🟡 |
