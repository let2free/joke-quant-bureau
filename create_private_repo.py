#!/usr/bin/env python3
"""
九章量化局 - GitHub私有仓库创建脚本（本地运行）
使用方法：
1. 保存此脚本到本地
2. 在终端运行：python create_private_repo.py
3. 按提示输入GitHub Token（输入时不显示，安全）
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import getpass

def create_private_repo(token):
    """创建GitHub私有仓库"""
    url = "https://api.github.com/user/repos"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": "joke-quant-bureau",
        "description": "九章量化局 - AI+数学双轨制量化预测系统",
        "private": True,  # 私有仓库
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            print()
            print("✅ 私有仓库创建成功！")
            print()
            print(f"仓库地址：<ADDRESS_REMOVED>
            print(f"克隆地址：<ADDRESS_REMOVED>
            print(f"SSH地址：<ADDRESS_REMOVED>
            print()
            print("下一步：")
            print("1. 复制上面的克隆地址")
            print("2. 在另一个终端运行：")
            print(f"   cd /c/Users/let2free/joke-quant-bureau")
            print(f"   git remote add origin {result.get('clone_url')}")
            print(f"   git push -u origin master")
            print()
            
            return result.get('clone_url')
    
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_msg)
            print(f"❌ 创建失败：{error_data.get('message', '未知错误')}")
        except:
            print(f"❌ 创建失败：HTTP {e.code}")
            print(f"错误详情：{error_msg}")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ 创建失败：{str(e)}")
        sys.exit(1)

def main():
    print("=" * 60)
    print("  九章量化局 - GitHub私有仓库创建工具")
    print("=" * 60)
    print()
    print("说明：")
    print("1. 你需要一个GitHub Personal Access Token")
    print("2. Token需要'repo'权限")
    print("3. 获取地址：<ADDRESS_REMOVED>
    print("4. 输入Token时不会显示，这是正常的安全机制")
    print()
    
    # 安全输入Token
    try:
        token = getpass.getpass("请输入你的GitHub Personal Access Token: ")
    except:
        # Windows兼容
        import maskpass
        token = maskpass.askpass(mode="password")
    
    if not token:
        print("❌ Token不能为空！")
        sys.exit(1)
    
    print()
    print("正在创建私有仓库...")
    print()
    
    clone_url = create_private_repo(token)
    
    # 询问是否自动推送
    print("=" * 60)
    print()
    auto_push = input("是否自动配置远程仓库并推送代码？(y/N): ").strip().lower()
    
    if auto_push == 'y':
        print()
        print("正在配置...")
        
        # 保存Token到临时环境变量
        os.environ['GITHUB_TOKEN'] = token
        
        # 配置credential helper
        os.system('git config --global credential.helper store')
        
        # 添加远程仓库
        os.system(f'git remote add origin {clone_url}')
        
        # 推送代码
        print("推送代码到GitHub...")
        push_cmd = f'git -c credential.helper= -c credential.username= -c credential.password={token} push -u origin master'
        os.system(push_cmd)
        
        print()
        print("✅ 完成！代码已推送到GitHub私有仓库")
        print(f"访问：https://github.com/LobsterHub/joke-quant-bureau")
    else:
        print()
        print("已取消自动推送")
        print("你可以稍后手动推送：")
        print(f"  git remote add origin {clone_url}")
        print(f"  git push -u origin master")

if __name__ == "__main__":
    main()
