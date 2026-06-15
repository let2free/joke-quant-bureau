# 九章量化局 (Joke Quant Bureau)

> AI + 数学双轨制量化预测系统 —— 开源协同开发工作组

![Version](https://img.shields.io/badge/version-2.0-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![Status](https://img.shields.io/badge/status-beta-orange)

---

## 🎯 项目简介

**九章量化局**是一套完整的A股/美股ETF预测系统，采用**双轨制架构**：

- **Track A（AI定性）**：基于大语言模型的智能分析，理解市场情绪、政策影响、行业趋势
- **Track B（数学定量）**：6大类因子打分模型（动量、资金流、均值回归、波动率、微观结构、市场状态）
- **融合引擎**：自动融合双轨预测，输出标准化报告
- **实时看板**：7种可视化图表，支持多端访问

**核心目标**：通过AI与数学的双重验证，提升ETF预测准确率至95%以上。

---

## 🏗️ 系统架构

```
九章量化局 v2.0
├── 九章Agent协同系统 (quant-agent-orchestra)
│   ├── 大A（A股哨兵）
│   ├── 老美（美股侦察兵）
│   ├── 军机处（宏观情报）
│   ├── 量化1哥（数学模型）
│   ├── 包青天（合规审计）
│   └── ... (共9个角色)
│
├── 双轨制预测引擎
│   ├── Track A: AI定性分析 (quant-vibe-only, quant-analyst)
│   ├── Track B: 数学因子打分 (quant-math-engine)
│   └── 融合引擎 (fusion_engine.py)
│
├── 系统性因子监测 (systematic-factor-monitor)
│   ├── L0: 流动性检测（央行OMO/MLF、DR007、北向资金）
│   └── L4b: 微观结构冲击检测（指数调仓、被动资金流入）
│
├── 自动复盘迭代系统 (quant-recap-engine)
│   └── 预测失败自动触发R1-R6复盘流程
│
└── 实时看板 (dashboard/)
    ├── Flask服务器（端口7860）
    ├── Chart.js可视化（7种图表）
    └── 局域网多端访问
```

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/LobsterHub/joke-quant-bureau.git
cd joke-quant-bureau
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置WorkBuddy Skills

将 `skills/` 目录下的所有Skills复制到你的 `~/.workbuddy/skills/` 目录：

```bash
cp -r skills/* ~/.workbuddy/skills/
```

### 4. 启动实时看板

```bash
cd dashboard
python dashboard_server.py
```

访问：
- 本地：`http://localhost:7860`
- 局域网：`http://你的IP:7860`

---

## 📚 核心功能

### ✅ 已完成

- [x] 双轨制预测架构（AI + 数学）
- [x] 9个Agent协同工作台
- [x] L0流动性 + L4b微观结构检测
- [x] 实时可视化看板（7种图表）
- [x] 自动复盘迭代机制
- [x] 因子打分模型（6大类、20+子因子）

### 🔄 进行中

- [ ] Backtrader回测系统搭建
- [ ] 因子权重历史校准（需3-4周数据积累）
- [ ] 8种补充图表开发（K线图、热力图等）
- [ ] 豆宝在线程序（Coze云端版本）

### 📋 待开发

- [ ] 实盘交易接口（模拟盘优先）
- [ ] 多资产类别扩展（个股、期货、期权）
- [ ] 机器学习因子挖掘
- [ ] 风险模型（VaR、CVaR）

---

## 🤝 协作指南

### 龙虾团队角色分工

| 角色 | 名称 | 职责 | 环境 |
|------|------|------|------|
| **Hub** | 元宝(desktop) | 架构设计、本地开发 | Windows WorkBuddy |
| **Executor** | 豆宝 | 在线程序、API服务 | Coze云端 |
| **Knowledge** | 天宝 | 知识库维护、文档管理 | IMA云端 |
| **Sandbox** | 云宝 | 测试验证、沙箱执行 | Cloud WorkBuddy |
| **Code** | CODEX | 代码审计、复核 | 本地LLM |

### 工作流程

1. **任务派发**：老大在WorkBuddy中派发任务
2. **协同开发**：各龙虾按角色分工（见 `docs/collaboration.md`）
3. **代码审查**：CODEX自动审计，包青天合规检查
4. **部署上线**：豆宝负责云端部署，元宝负责本地集成

### 贡献规范

- **分支策略**：`main` (稳定版) / `dev` (开发版) / `feature/*` (功能分支)
- **提交规范**：遵循 [Conventional Commits](https://www.conventionalcommits.org/)
- **代码审查**：所有PR必须至少1人Review
- **测试覆盖**：新功能必须包含单元测试

---

## 📊 性能表现

### 预测准确率追踪

| 日期 | ETF数量 | 预测准确率 | 改进点 |
|------|---------|-----------|--------|
| 2026-06-12 | 6 | 33% | 初始版本 |
| 2026-06-15 | 6 | 50% | 修复L4b调仓权重 |
| 2026-06-16 | 6 | **测试中** | 双轨制融合 |

**目标**：>95%

---

## 📖 文档目录

- [架构说明](docs/architecture.md) - 系统详细设计
- [协作指南](docs/collaboration.md) - 龙虾团队工作流
- [API参考](docs/api-reference.md) - 接口文档
- [因子目录](skills/quant-math-engine/references/factor_catalog.md) - 6大类因子公式

---

## 🛠️ 技术栈

- **后端**：Python 3.11+, Flask, Backtrader（计划中）
- **前端**：HTML5, Chart.js, Bootstrap 5
- **AI**：WorkBuddy (Claude/GPT/GLM), TDX Connector
- **数据**：AKShare, Tushare, 通联数据（计划中）
- **部署**：本地Flask + 云端Coze（豆宝）

---

## 📄 许可证

[MIT License](LICENSE) - 开源免费使用

---

## 👥 联系人

- **项目负责人**：云鹏（老大）
- **技术负责人**：元宝(desktop)
- **在线程序**：豆宝（Coze云端）
- **Issues**：[GitHub Issues](https://github.com/LobsterHub/joke-quant-bureau/issues)

---

## 🙏 致谢

感谢以下开源项目：
- [WorkBuddy](https://github.com/workbuddy/workbuddy) - AI协同开发平台
- [Backtrader](https://github.com/mementum/backtrader) - Python量化回测框架
- [AKShare](https://github.com/akfamily/akshare) - 免费财经数据接口
- [Chart.js](https://www.chartjs.org/) - JavaScript图表库

---

**⚡ 让AI与数学共同守护你的投资！**
