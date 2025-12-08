#!/usr/bin/env python3
"""
微信读书 Cookie 认证工具
支持从 GitHub Secrets 读取 Cookie，实现完全自动化
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import requests
from urllib.parse import urlparse


class WeReadAuth:
    """微信读书认证管理器"""

    def __init__(self):
        self.base_url = "https://weread.qq.com"
        self.api_url = "https://i.weread.qq.com"
        self.cookies = {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://weread.qq.com/"
        }

    def load_cookies_from_string(self, cookie_string: str) -> bool:
        """
        从 cookie 字符串加载 cookies
        格式：wr_name=xxx; wr_vid=xxx; wr_skey=xxx; ...
        """
        try:
            cookie_pairs = cookie_string.split(';')
            for pair in cookie_pairs:
                if '=' in pair:
                    key, value = pair.strip().split('=', 1)
                    self.cookies[key] = value
            return True
        except Exception as e:
            print(f"解析 cookies 失败: {e}")
            return False

    def load_cookies_from_github_secrets(self) -> bool:
        """
        从 GitHub Secrets 加载 Cookie
        使用环境变量 WEREAD_COOKIE
        """
        cookie_string = os.getenv("WEREAD_COOKIE")

        if not cookie_string:
            print("错误: 未找到 WEREAD_COOKIE 环境变量")
            print("请在 GitHub Secrets 中添加 WEREAD_COOKIE")
            return False

        return self.load_cookies_from_string(cookie_string)

    def load_cookies_from_gist(self, gist_url: str) -> bool:
        """
        从 GitHub Gist 加载 cookies（可选方法，作为备用）
        Gist 应该包含一个名为 cookies 的字段
        """
        try:
            # 获取 Gist 原始内容
            raw_url = gist_url.replace('github.com', 'raw.githubusercontent.com')
            raw_url = raw_url.replace('/gist/', '/').replace('#raw-', '')

            response = requests.get(raw_url)
            response.raise_for_status()

            data = response.json()
            if 'cookies' in data:
                return self.load_cookies_from_string(data['cookies'])
            else:
                print("Gist 中未找到 cookies 字段")
                return False
        except Exception as e:
            print(f"从 Gist 加载 cookies 失败: {e}")
            return False

    def test_auth(self) -> Tuple[bool, dict]:
        """
        测试认证是否有效
        返回 (是否成功, 用户信息)
        """
        try:
            # 获取用户信息
            url = f"{self.api_url}/user/getinfo"
            headers = self.headers.copy()
            headers["Cookie"] = self._format_cookies()

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data.get('errCode') == 0:
                    return True, data
                else:
                    return False, data
            else:
                return False, {"error": f"HTTP {response.status_code}"}

        except Exception as e:
            return False, {"error": str(e)}

    def _format_cookies(self) -> str:
        """将 cookies 字典格式化为字符串"""
        return '; '.join([f"{k}={v}" for k, v in self.cookies.items()])

    def get_vid(self) -> Optional[str]:
        """获取 vid"""
        return self.cookies.get('wr_vid')

    def get_skey(self) -> Optional[str]:
        """获取 skey"""
        return self.cookies.get('wr_skey')

    def get_auth_headers(self) -> Dict[str, str]:
        """
        获取用于 API 请求的认证头
        兼容 Weread_ReadTime_Heatmap 的格式
        """
        headers = self.headers.copy()
        headers["Cookie"] = self._format_cookies()
        return headers

    def init_auth(self, gist_url: str = None) -> bool:
        """
        初始化认证，优先使用 GitHub Secrets，失败时尝试 Gist
        """
        # 优先尝试从 GitHub Secrets 加载
        if self.load_cookies_from_github_secrets():
            print("成功从 GitHub Secrets 加载 Cookie")
            return True

        # 如果设置了 Gist URL，尝试从 Gist 加载
        if gist_url:
            print("尝试从 Gist 加载 Cookie...")
            if self.load_cookies_from_gist(gist_url):
                print("成功从 Gist 加载 Cookie")
                return True

        print("无法加载 Cookie，请检查配置")
        return False


def main():
    """测试函数"""
    auth = WeReadAuth()

    # 从 GitHub Secrets 加载
    if auth.load_cookies_from_github_secrets():
        print("成功从 GitHub Secrets 加载 cookies")

        # 测试认证
        is_valid, info = auth.test_auth()
        if is_valid:
            print("认证成功！")
            print(f"用户信息: {json.dumps(info, ensure_ascii=False, indent=2)}")
        else:
            print("认证失败")
            print(f"错误信息: {json.dumps(info, ensure_ascii=False, indent=2)}")
    else:
        print("加载 cookies 失败")


if __name__ == "__main__":
    main()