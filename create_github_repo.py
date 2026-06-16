#!/usr/bin/env python3
"""
九章量化局 - GitHub仓库自动创建脚本
使用方法：python create_github_repo.py
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error

def create_github_repo(token, repo_name="joke-quant-bureau", description="九章量化局 - AI+数学双轨制量化预测系统", is_private=False):
    """
    使用GitHub API创建仓库
    
    Args:
        token: GitHub Personal Access Token (需要repo权限)
        repo_name: 仓库名称
        description: 仓库描述
        is_private: 是否私有仓库
    
    Returns:
        dict: {"success": bool, "message": str, "repo_url": str}
    """
    url = "https://api.github.com/user/repos"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": repo_name,
        "description": description,
        "private": is_private,
        "auto_init": False,
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
            
            return {
                "success": True,
                "message": "仓库创建成功！",
                "repo_url": result.get("html_url"),
                "clone_url": result.get("clone_url"),
                "ssh_url": result.get("ssh_url")
            }
    
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        try:
            error_data = json.loads(error_msg)
            return {
                "success": False,
                "message": f"创建失败：{error_data.get('message', '未知错误')}",
                "error": error_msg
            }
        except:
            return {
                "success": False,
                "message": f"创建失败：HTTP {e.code}",
                "error": error_msg
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"创建失败：{str(e)}",
            "error": str(e)
        }

def main():
    print("=" * 60)
    print("  九章量化局 - GitHub仓库创建工具")
    print("=" * 60)
    print()
    print("提示：你需要一个GitHub Personal Access Token（需要repo权限）")
    print("获取地址：<ADDRESS_REMOVED>
    print()
    
    # 安全输入Token
    token = input("请输入你的GitHub Personal Access Token: ").strip()
    
    if not token:
        print("❌ Token不能为空！")
        sys.exit(1)
    
    if not token.startswith("ghp_"):
        print("⚠️  警告：GitHub PAT通常以'ghp_'开头，请确认你的Token是否正确")
        confirm = input("继续？(y/N): ").strip().lower()
        if confirm != 'y':
            print("已取消")
            sys.exit(0)
    
    print()
    print("开始创建仓库...")
    print()
    
    # 创建仓库
    result = create_github_repo(token)
    
    if result["success"]:
        print("✅ " + result["message"])
        print()
        print(f"仓库地址：<ADDRESS_REMOVED>
        print(f"克隆地址：<ADDRESS_REMOVED>
        print(f"SSH地址：<ADDRESS_REMOVED>
        print()
        print("下一步：")
        print("1. 添加远程仓库：")
        print(f"   git remote add origin {result['clone_url']}")
        print("2. 推送代码：")
        print("   git push -u origin master")
        print()
        
        # 询问是否自动配置
        auto_config = input("是否自动配置远程仓库并推送？(Y/n): ").strip().lower()
        if auto_config != 'n':
            print()
            print("开始配置...")
            
            # 保存Token到临时文件（供git使用）
            git_credentials = f"https://{token}@github.com"
            os.system(f"git config --global credential.helper store")
            os.system(f"echo '{git_credentials}' > ~/.git-credentials")
            
            # 添加远程仓库
            os.system(f"git remote add origin {result['clone_url']}")
            
            # 推送代码
            print("推送代码到GitHub...")
            os.system("git push -u origin master")
            
            print()
            print("✅ 完成！代码已推送到GitHub")
            print(f"访问：{result['repo_url']}")
        
    else:
        print("❌ " + result["message"])
        print()
        if "error" in result:
            print("详细错误：")
            print(result["error"])
        print()
        print("可能的原因：")
        print("1. Token权限不足（需要repo权限）")
        print("2. 仓库名称已存在")
        print("3. Token已过期")
        sys.exit(1)

if __name__ == "__main__":
    main()
