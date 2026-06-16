"""
九章量化局 - GitHub API访问脚本
用于豆宝（Coze云端）读取代码和数据
"""
import requests
import json
import os
from datetime import datetime

class GitHubAPI:
    """GitHub API访问器"""
    
    def __init__(self, token=None):
        self.token = token or os.environ.get('GITHUB_TOKEN')
        self.repo = 'let2free/joke-quant-bureau'
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def get_file_content(self, file_path: str) -> str:
        """获取文件内容"""
        url = f'{self.base_url}/repos/{self.repo}/contents/{file_path}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            import base64
            return base64.b64decode(data['content']).decode('utf-8')
        else:
            raise Exception(f"获取文件失败: {response.status_code}")
    
    def get_file_list(self, path: str = '') -> list:
        """获取目录文件列表"""
        url = f'{self.base_url}/repos/{self.repo}/contents/{path}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"获取目录失败: {response.status_code}")
    
    def get_latest_data(self) -> dict:
        """获取最新数据"""
        try:
            # 获取主数据文件
            data_content = self.get_file_content('dashboard/data.json')
            return json.loads(data_content)
        except Exception as e:
            return {'error': str(e)}
    
    def get_accuracy_history(self) -> list:
        """获取准确率历史"""
        try:
            content = self.get_file_content('dashboard/accuracy_history.json')
            return json.loads(content)
        except Exception as e:
            return [{'error': str(e)}]
    
    def get_artifacts_list(self) -> list:
        """获取分析产物列表"""
        try:
            files = self.get_file_list('dashboard/artifacts')
            return [f['name'] for f in files if f['type'] == 'dir']
        except Exception as e:
            return [str(e)]

# 单例
github_api = GitHubAPI()

if __name__ == '__main__':
    # 测试
    api = GitHubAPI()
    print("获取最新数据...")
    data = api.get_latest_data()
    print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
