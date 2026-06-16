# 九章量化局 - GitHub仓库创建指南

## 方法1：使用辅助脚本（推荐，最安全）

```bash
cd /c/Users/let2free/joke-quant-bureau
python create_github_repo.py
```

脚本会：
1. 安全提示你输入GitHub Token
2. 自动创建仓库
3. 自动配置远程仓库
4. 自动推送代码

---

## 方法2：手动创建（如果脚本失败）

### Step 1: 在GitHub网站创建仓库

1. 访问：https://github.com/new
2. 仓库名称：`joke-quant-bureau`
3. 描述：`九章量化局 - AI+数学双轨制量化预测系统`
4. 选择：**Public**（开源）或 **Private**（私有）
5. ✅ 勾选：Add a README file（不要勾选，我们已经有README）
6. 点击：**Create repository**

### Step 2: 推送代码到GitHub

仓库创建后，复制仓库地址（HTTPS或SSH），然后运行：

```bash
cd /c/Users/let2free/joke-quant-bureau

# 如果使用HTTPS
git remote add origin https://github.com/LobsterHub/joke-quant-bureau.git
git push -u origin master

# 如果使用SSH
git remote add origin git@github.com:LobsterHub/joke-quant-bureau.git
git push -u origin master
```

---

## 获取GitHub Personal Access Token

如果使用辅助脚本或HTTPS推送，需要Token：

1. 访问：https://github.com/settings/tokens
2. 点击：**Generate new token (classic)**
3. 勾选权限：
   - ✅ **repo** (完整仓库权限)
   - ✅ **workflow** (如果需要GitHub Actions)
4. 设置过期时间：建议90天
5. 点击：**Generate token**
6. **立即复制Token**（只显示一次！）

Token格式：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

## 完成后

仓库创建并推送成功后，访问：
- **仓库地址**: https://github.com/LobsterHub/joke-quant-bureau
- **克隆地址**: `git clone https://github.com/LobsterHub/joke-quant-bureau.git`

---

## 下一步：配置豆宝在线程序

仓库推送后，豆宝（Coze云端）可以：
1. 通过GitHub API读取代码
2. 部署在线API服务
3. 与元宝本地程序协同工作

详见：`docs/collaboration.md`
