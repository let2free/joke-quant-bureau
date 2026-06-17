# 九章量化局 · 项目文件

## 项目信息

| 项目 | 详情 |
|------|------|
| 名称 | 九章量化局 (Joke Quant Bureau) |
| 仓库 | github.com/let2free/joke-quant-bureau |
| 版本 | v2.0 |
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
├── PROJECT.md              # 本文件
├── start.bat               # 一键启动脚本
├── docs/                   # 文档
│   ├── architecture.md     # 架构设计
│   ├── collaboration.md    # 协同协议
│   └── jiuzhang_workflow.md # 九章工作流程
├── dashboard/              # 看板系统
│   ├── dashboard_server.py # HTTP服务器（端口7860）
│   ├── backtest.py         # 回测模块
│   ├── etf_data.py         # ETF数据获取（通达信）
│   ├── data_importer.py    # 数据导入
│   ├── *.html              # 7个前端页面
│   ├── *.json              # 持久化数据文件
│   └── artifacts/          # 按日期存储的预测/复盘
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

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| /api/status | GET | 服务器状态 | ✅ |
| /api/data | GET | 看板数据 | ✅ |
| /api/etf/rankings | GET | ETF排名 | ✅ |
| /api/etf/watchlist | GET | 自选列表 | 🔴 超时（TDX调用） |
| /api/etf/watchlist/add | POST | 添加自选 | 🟡 |
| /api/etf/watchlist/remove | POST | 移除自选 | 🟡 |
| /api/etf/refresh | GET | 刷新数据 | 🟡 |
| /api/etf/search | GET | 搜索ETF | 🟡 |
| /api/backtest/accuracy | GET | 回测准确率 | ✅ |
| /api/backtest/factor-optimize | GET | 因子优化 | ✅ |
| /api/backtest/run | POST | 运行回测 | ✅ |
| /api/predictions/latest | GET | 最新预测 | ✅ |
| /api/predictions/history | GET | 预测历史 | ✅ |
| /api/accuracy/history | GET | 准确率历史 | ✅ |
| /api/agents/status | GET | Agent状态 | 🟡 |

## 已知问题

| 编号 | 问题 | 优先级 | 
|------|------|--------|
| BUG-01 | ETF watchlist API调用TDX超时 | 🔴 |
| BUG-02 | ETF数据使用模拟数据非真实行情 | 🔴 |
| BUG-03 | ETF管理弹窗按钮无响应（已修复全角字符） | 🟢 |
| BUG-04 | 回测history.jsonl无数据 | 🟡 |
| BUG-05 | 实时看板准确率图表数据不更新 | 🟡 |
