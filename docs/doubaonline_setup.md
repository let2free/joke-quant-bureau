# 豆宝在线程序配置指南

## 概述

豆宝（Coze云端）通过GitHub API读取九章量化局的代码和数据，部署在线API服务，与元宝本地程序协同工作。

## 配置步骤

### 1. 获取GitHub Personal Access Token

1. 访问：https://github.com/settings/tokens
2. 点击：**Generate new token (classic)**
3. 勾选权限：
   - ✅ **repo** (完整仓库权限)
   - ✅ **workflow** (如果需要GitHub Actions)
4. 设置过期时间：建议90天
5. 点击：**Generate token**
6. **立即复制Token**（只显示一次！）

### 2. 配置豆宝环境

在豆宝（Coze云端）中设置环境变量：

```bash
# 设置GitHub Token
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 设置仓库名称
export GITHUB_REPO="let2free/joke-quant-bureau"
```

### 3. 使用GitHub API访问数据

#### 获取最新数据

```python
from scripts.github_api import github_api

# 获取最新市场数据
data = github_api.get_latest_data()
print(data)
```

#### 获取准确率历史

```python
# 获取准确率历史
accuracy = github_api.get_accuracy_history()
print(accuracy)
```

#### 获取分析产物列表

```python
# 获取分析产物列表
artifacts = github_api.get_artifacts_list()
print(artifacts)
```

### 4. 部署在线API服务

豆宝可以部署以下API接口：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/data` | GET | 获取最新市场数据 |
| `/api/accuracy` | GET | 获取准确率历史 |
| `/api/artifacts` | GET | 获取分析产物列表 |
| `/api/import` | POST | 导入历史数据 |
| `/api/export` | GET | 导出数据 |

### 5. 与元宝本地程序协同

#### 数据同步

1. **元宝本地程序**：每日09:30自动运行双轨预测
2. **豆宝在线程序**：通过GitHub API读取预测结果
3. **数据更新**：预测结果自动推送到GitHub

#### 协同工作流

```
元宝本地程序 (09:30)
    ↓ 执行双轨预测
    ↓ 生成fusion_report.json
    ↓ 推送到GitHub
豆宝在线程序
    ↓ 通过GitHub API读取数据
    ↓ 提供在线查询服务
    ↓ 支持多设备访问
```

## 注意事项

1. **Token安全**：不要在代码中硬编码Token，使用环境变量
2. **API限制**：GitHub API有频率限制（每小时5000次）
3. **数据同步**：确保元宝本地程序先推送数据，豆宝再读取
4. **错误处理**：添加重试机制和错误日志

## 故障排除

### 问题1：GitHub API返回401

**原因**：Token无效或过期

**解决**：
1. 检查Token是否正确
2. 检查Token是否过期
3. 重新生成Token

### 问题2：GitHub API返回403

**原因**：API频率限制

**解决**：
1. 等待一小时后重试
2. 使用条件请求（ETag/Last-Modified）
3. 缓存数据减少API调用

### 问题3：GitHub API返回404

**原因**：文件或仓库不存在

**解决**：
1. 检查仓库名称是否正确
2. 检查文件路径是否正确
3. 检查仓库是否为私有仓库

## 示例代码

### 完整示例

```python
import os
import json
from scripts.github_api import github_api

def main():
    # 设置Token
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("错误：未设置GITHUB_TOKEN环境变量")
        return
    
    # 初始化API
    api = GitHubAPI(token)
    
    # 获取最新数据
    print("获取最新数据...")
    data = api.get_latest_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # 获取准确率历史
    print("\n获取准确率历史...")
    accuracy = api.get_accuracy_history()
    print(json.dumps(accuracy, indent=2, ensure_ascii=False))
    
    # 获取分析产物列表
    print("\n获取分析产物列表...")
    artifacts = api.get_artifacts_list()
    print(artifacts)

if __name__ == '__main__':
    main()
```

## 下一步

1. 配置豆宝环境变量
2. 测试GitHub API访问
3. 部署在线API服务
4. 与元宝本地程序联调
