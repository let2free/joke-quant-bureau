---
name: quant-vibe-only
description: Vibe-Trading单独分析Skill。当用户说「Vibe分析XX」/「大模型V分析」/「vibe分析」时触发。调用Vibe-Trading CLI进行AI量化分析，监控进度并返回报告。适用场景：快速初筛、多股票对比、AI驱动分析。
agent_created: true
---

# Vibe-Trading 单独分析

## 概述

本Skill调用Vibe-Trading CLI进行AI量化分析，适用于快速初筛和AI驱动的深度分析。

- **核心工具**：Vibe-Trading CLI（`vibe-trading.exe run`）
- **服务管理**：通过 `vibe_service.ps1` 统一管理大模型V的启动/关闭/重启
- **分析模式**：支持技术分析、基本面分析、资金流向分析、风险评估

## 触发条件

当用户提出以下意图时，使用本Skill：
- 「Vibe分析茅台」
- 「用大模型V分析XX股票」
- 「vibe分析XX」
- 「用AI分析XX股票」

## 执行流程

### 步骤1：检查大模型V状态

调用PowerShell检查服务状态：

```powershell
powershell -ExecutionPolicy Bypass -File "C:/Users/let2free/WorkBuddy/Claw/vibe_service.ps1" status
```

**可能状态**：
- ✅ 正在运行（PID: XXXX）
- ❌ 未运行

如果未运行，先启动服务：

```powershell
powershell -ExecutionPolicy Bypass -File "C:/Users/let2free/WorkBuddy/Claw/vibe_service.ps1" start
```

等待5秒确认启动成功。

### 步骤2：构造分析Prompt

根据用户意图构造分析Prompt，建议包含以下要素：

```
全量分析<股票名称>(<代码>)：
1. 技术分析（MACD/RSI/布林带/支撑阻力）
2. 基本面分析（PE/PB/ROE/营收增速/利润率）
3. 资金流向分析（主力进出/成交量变化）
4. 风险评估（激进/中立/保守三档）
5. 操作建议（买入/持有/卖出）和目标价位
```

**简化Prompt**（快速初筛）：
```
快速分析<股票名称>(<代码>)：给出综合评级和操作建议
```

### 步骤3：调用Vibe-Trading CLI

执行分析命令：

```bash
cd C:/Users/let2free/.vibe-trading
C:/Users/let2free/.workbuddy/binaries/python/envs/vibe-trading/Scripts/vibe-trading.exe run -p "<Prompt>" --no-rich
```

**参数说明**：
- `-p`：分析Prompt
- `--no-rich`：禁用富文本输出（便于解析）
- `--skills <skill_name>`：（可选）指定加载的skill（如 `akshare`）

**超时设置**：
- 建议超时：300秒（5分钟）
- 如果超时，检查：
  1. 大模型V是否正常（查看 http://localhost:8080/health）
  2. DeepSeek API Key是否有效（查看 `.env` 文件）
  3. 网络是否通畅（akshare数据源可能限速）

### 步骤4：监控进度

Vibe-Trading CLI执行过程中会输出：

```
Preflight: 正在准备...
✔ Preflight 完成
✔ 加载 skills 完成
✔ 连接 LLM 完成
正在分析...
[SSE Stream] ...
分析完成！
```

**如果卡住**：
1. 等待超时（300秒）
2. 如果超时，检查 `.env` 配置（`DEFAULT_SKILL` 是否注释掉）
3. 重启大模型V服务

### 步骤5：解析输出

Vibe-Trading CLI输出为文本格式，包含：

```
## 技术分析
...

## 基本面分析
...

## 资金流向
...

## 风险评估
...

## 操作建议
...
```

**解析重点**：
- 综合评级：买入/持有/卖出
- 目标价：¥XXX - ¥XXX
- 风险评级：低/中/高
- 建议仓位：XX%

### 步骤6：生成报告

将分析结果保存为Markdown报告：

```
Claw/Vibe分析_<股票代码>_<日期>.md
```

**报告结构**：

```markdown
# <股票名称>(<代码>) Vibe-Trading分析报告

## 核心结论
- 综合评级：
- 目标价：
- 风险评级：
- 建议仓位：

## 详细分析
（完整的Vibe-Trading输出）

## 数据来源
- Vibe-Trading CLI
- 分析时间：YYYY-MM-DD HH:MM
- 模型：DeepSeek (deepseek-chat)
```

## 依赖检查

执行前检查以下依赖：

| 依赖 | 检查方式 | 缺失处理 |
|------|---------|---------|
| Vibe-Trading CLI | 检查 `vibe-trading.exe` 是否存在 | 提示用户安装 |
| 大模型V服务 | 调用 `vibe_service.ps1 status` | 自动启动 |
| DeepSeek API Key | 读取 `.env` 文件 | 提示用户配置 |
| akshare skill | Vibe-Trading自动加载 | 无需手动处理 |

## 常见问题

### 问题1：Vibe-Trading CLI卡住

**症状**：执行30秒以上无输出

**根因**：
1. `DEFAULT_SKILL=akshare` 导致每次对话自动拉数据
2. 默认超时太短（300秒）

**修复**：
1. 注释掉 `.env` 中的 `DEFAULT_SKILL=akshare`
2. 增加超时参数：
   ```
   SWARM_WORKER_TIMEOUT=600
   SWARM_TIMEOUT=3600
   ```

### 问题2：API Key认证失败

**症状**：报 `401 Unauthorized`

**根因**：`.env` 变量名错误

**正确配置**：
```
LANGCHAIN_PROVIDER=deepseek
DEEPSEEK_API_KEY=<your_key>
LANGCHAIN_MODEL_NAME=deepseek-chat
```

### 问题3：输出乱码

**症状**：中文显示为乱码

**修复**：使用 `--no-rich` 参数禁用富文本输出

## 输出格式

### 文本格式（对话中返回）

```
✅ Vibe-Trading分析完成

## 核心结论
- 综合评级：持有/逢低加仓（置信度75%）
- 目标价：¥1350 - ¥1400
- 风险评级：中等
- 建议仓位：30-40%

## 操作建议
- 入场位1：¥1250-¥1260（第一批30%）
- 入场位2：¥1220-¥1230（第二批20%）
- 止损位：¥1200
- 止盈位1：¥1350（减仓30%）

完整报告：Claw/Vibe分析_600519_20260612.md
```

### Markdown报告（文件）

保存到 `Claw/Vibe分析_<股票代码>_<日期>.md`，包含完整分析过程。

## 注意事项

1. **大模型V必须运行**：Vibe-Trading CLI依赖后台服务，执行前务必检查
2. **超时设置**：建议300秒，复杂分析可能需要更长时间
3. **网络依赖**：akshare数据源可能限速，建议耐心等待
4. **输出解析**：Vibe-Trading输出为自由文本，解析时需注意格式变化

## 示例

**用户输入**：
```
Vibe分析茅台
```

**执行步骤**：
1. 检查大模型V状态 → 未运行 → 启动
2. 构造Prompt → "全量分析贵州茅台(600519)：技术分析、基本面分析、资金流向、风险评估，给出操作建议和目标价"
3. 调用Vibe-Trading CLI → 等待分析完成（约3-5分钟）
4. 解析输出 → 提取核心结论
5. 生成报告 → 保存到文件

**输出**：
```
✅ Vibe-Trading分析完成

## 核心结论
- 综合评级：持有/逢低加仓（置信度75%）
- 目标价：¥1350 - ¥1400
- 风险评级：中等
- 建议仓位：30-40%

完整报告：Claw/Vibe分析_600519_20260612.md
```
