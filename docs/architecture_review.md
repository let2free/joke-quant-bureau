# 九章量化局 · 架构审查报告
## 审查日期：2026-06-17 | 审查人：代码审查员

---

## 📊 整体评估

> 整体架构清晰，模块划分合理，快速原型阶段质量不错。主要有 2 个阻塞项需要修复（后端架构 + 数据可靠性），4 个建议项可大幅提升稳定性和可维护性。

**代码量**：~8,931 行（Python 2,143 行 + HTML/JS 5,217 行 + 文档 1,572 行）

---

## 🔴 阻塞项（影响稳定性/数据可靠性）

### 🔴 1. 后端架构：单线程 SimpleHTTPRequestHandler

**现状**：`dashboard_server.py` 继承 `http.server.SimpleHTTPRequestHandler`，每个请求同步处理。

**问题**：
- 一个慢请求（如 ETF 数据刷新）阻塞所有其他请求
- 今天已修了缓存问题，但根本架构瓶颈还在
- 无并发处理能力，无法横向扩展

**建议**：
```python
# 方案A：轻量升级（推荐，1小时）
from wsgiref.simple_server import make_server
# 或使用 Flask：pip install flask
from flask import Flask, jsonify

# 方案B：生产级（未来考虑）
# FastAPI + uvicorn，异步I/O，自动生成API文档
```

### 🔴 2. 数据可靠性：无数据库持久化

**现状**：所有数据存储在 JSON 文件中（data.json, accuracy_history.json 等）。

**问题**：
- 并发写入可能损坏数据（无锁机制）
- 历史数据多了之后，读取整个 JSON 文件到内存效率低
- 无法做复杂查询（"过去30天通信ETF的预测准确率变化"）

**建议**：
```python
# 方案A：SQLite（推荐，2小时）
import sqlite3
db = sqlite3.connect('jiuzhang.db')
# 表：predictions(date, code, name, pred_pct, actual_pct, ...)
# 表：factors(date, momentum, fund_flow, ...)
# 表：watchlist(code, name, category)

# 方案B：轻量 ORM
# pip install peewee -> 写少量代码升级
```

---

## 🟡 建议项（提升可维护性/扩展性）

### 🟡 1. 前端：7个独立页面 → 共享组件体系

**现状**：7 个 HTML 文件各自独立，导航栏、CSS、图表配置大量重复。

**影响**：
- 改一个样式要改 7 个文件
- 导航栏不一致问题反复出现
- 新增页面复制粘贴大量模板代码

**建议**：
```javascript
// 方案A：抽出共享组件（不需要框架，3小时）
// 1. 创建 dashboard/common.js - 共享函数
// 2. 创建 dashboard/common.css - 统一样式（当前每个页面都内嵌<style>）
// 3. 创建 dashboard/template.html - 统一布局模板

// 方案B：轻量Web组件（未来）
// <nav-bar active="dashboard"></nav-bar>
// <predict-card date="2026-06-17"></predict-card>
```

### 🟡 2. 预测/复盘流程：手动触发 → 事件驱动

**现状**：九章流程 Phase 0-5 需要手动说"启动看板"或"做预测"。

**建议**：
```python
# 方案A：定时任务（1小时）
# 用 schedule 库在开盘前自动运行预测
import schedule
schedule.every().monday.at("09:00").do(run_jiuzhang_prediction)
schedule.every().day.at("15:30").do(run_jiuzhang_recap)

# 方案B：事件驱动（未来）
# TDX数据更新 → 触发预测
# 收盘数据到达 → 触发复盘
```

### 🟡 3. API设计：RESTful 规范化

**现状**：API 路径散乱在 `do_GET` 的 if-elif 链中，没有统一错误响应格式。

**建议**：
```python
# 当前：if path == "/api/xxx": ... elif path == "/api/yyy": ...
# 建议：使用字典路由表
ROUTES = {
    ("GET", "/api/etf/rankings"): handle_rankings,
    ("POST", "/api/etf/watchlist/add"): handle_add_watchlist,
}

# 统一错误响应
def error_response(status, message):
    return {"status": "error", "code": status, "message": message}
```

### 🟡 4. ETF数据质量：模拟数据 → 真实行情

**现状**：ETF涨跌幅使用 `random.uniform(-5, 8)` 模拟。

**建议**：
```python
# 方案A：通达信批量缓存（已修复缓存问题，下一步）
# 开盘后先用subprocess批量获取50只→缓存30分钟
# 非关键数据用模拟，只对自选ETF用真实数据

# 方案B：多数据源备份
# 通达信不行 → 东方财富API → 新浪财经API → 模拟数据
```

---

## 💭 小改进（锦上添花）

### 💭 1. 热力图/看板增强
- 国内成熟ETF量化平台参考（果仁、聚宽、BigQuant）
- 建议添加：ETF相关性矩阵、资金流向热力图、波动率锥

### 💭 2. 日志系统
```python
# 当前：print() 到标准输出
# 建议：logging 模块 + 按日期滚动
import logging
logging.basicConfig(filename=f'logs/jiuzhang_{date}.log', level=logging.INFO)
```

### 💭 3. 配置文件统一
```python
# 当前：散落在 dashboard_server.py 和 etf_data.py 的变量
# 建议：创建 config.py 或 config.json 统一管理
```

### 💭 4. 测试覆盖
- 当前：0 个测试（靠手动 curl 测试）
- 建议：至少加 API 集成测试

---

## 📋 国内ETF量化方案参考

| 平台 | 核心功能 | 可借鉴 |
|------|----------|--------|
| **果仁网** | 因子选股+回测+组合优化 | 因子权重自动优化(网格搜索) |
| **聚宽** | Python策略编写+分钟级回测 | API设计、策略模板 |
| **BigQuant** | AI量化平台+可视化 | 因子IC分析、机器学习预测 |
| **RiceQuant** | 在线回测+模拟交易 | 模拟交易引擎 |
| **Wind** | 专业数据终端 | 数据质量标准 |

### 建议新增功能（优先级排序）

| 优先级 | 功能 | 参考 | 工作量 |
|--------|------|------|--------|
| P0 | ETF相关性矩阵 | 避免同时持有高相关ETF | 3h |
| P1 | 波动率锥/风险指标 | 量化标配 | 4h |
| P1 | 因子IC滚动分析 | BigQuant风格 | 3h |
| P2 | 资金流向热力图 | 聚宽风格 | 5h |
| P2 | 模拟交易引擎 | RiceQuant风格 | 8h |

---

## 📊 架构升级路线图

### 第一阶段：稳定（本周）
- [x] 修复 ETF API 阻塞（后台缓存）✅
- [x] 统一导航栏 ✅
- [ ] SQLite 替换 JSON 存储 🔴
- [ ] Flask/FastAPI 重构后端 🔴
- [ ] 共享 CSS/JS 组件 🟡

### 第二阶段：增强（下周）
- [ ] ETF 相关性矩阵
- [ ] 因子 IC 滚动分析
- [ ] 定时自动预测
- [ ] 统一配置管理

### 第三阶段：产品化（下月）
- [ ] WebSocket 实时推送
- [ ] 用户认证
- [ ] Docker 一键部署
- [ ] 完整测试覆盖

---

**审查完成**：2026-06-17 09:15
