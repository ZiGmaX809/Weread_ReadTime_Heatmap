#!/usr/bin/env python3
"""
微信读书认证工具 — Agent API Gateway 方式
通过 WEREAD_API_KEY 环境变量配置 Bearer Token 认证
"""

import json
import os
from typing import Dict, Tuple

import requests

# Agent API Gateway 地址
GATEWAY_URL = "https://i.weread.qq.com/api/agent/gateway"
SKILL_VERSION = "1.0.3"


class WeReadAuth:
    """微信读书认证管理器（API Key 方式）"""

    def __init__(self):
        self.api_key = os.getenv("WEREAD_API_KEY", "")
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://weread.qq.com/",
        }

    def has_api_key(self) -> bool:
        """检查是否配置了 API Key"""
        return bool(self.api_key)

    def get_gateway_headers(self) -> Dict[str, str]:
        """获取 Gateway API 请求头（Bearer Token 认证）"""
        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        return headers

    def call_gateway(self, api_name: str, **params) -> dict:
        """
        调用 Agent API Gateway
        参数平铺在 body 顶层，与 api_name、skill_version 同级
        """
        body = {"api_name": api_name, "skill_version": SKILL_VERSION, **params}
        headers = self.get_gateway_headers()
        resp = requests.post(GATEWAY_URL, json=body, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # 检查是否需要升级 skill 版本
        if "upgrade_info" in data:
            print(
                f"Skill 版本升级提示: "
                f"{data['upgrade_info'].get('message', '请升级')}"
            )

        if data.get("errcode", 0) != 0:
            raise Exception(
                f"Gateway API 错误: {data.get('errmsg', '未知错误')} "
                f"(errcode={data.get('errcode')})"
            )

        return data

    def init_auth(self) -> bool:
        """初始化认证，检查 API Key 是否已配置"""
        if self.has_api_key():
            print("使用 API Key 认证（Agent API Gateway）")
            return True
        print("未设置 WEREAD_API_KEY 环境变量")
        return False

    def test_auth(self) -> Tuple[bool, dict]:
        """测试认证是否有效，返回 (是否成功, 用户信息)"""
        try:
            resp = self.call_gateway("/user/getinfo")
            return True, resp
        except Exception as e:
            return False, {"error": str(e)}


def main():
    """测试认证是否有效"""
    auth = WeReadAuth()

    if not auth.init_auth():
        print("请设置环境变量: export WEREAD_API_KEY=<你的API Key>")
        return

    is_valid, info = auth.test_auth()
    if is_valid:
        print("认证成功！")
        print(f"用户信息: {json.dumps(info, ensure_ascii=False, indent=2)}")
    else:
        print("认证失败")
        print(f"错误信息: {json.dumps(info, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    main()
