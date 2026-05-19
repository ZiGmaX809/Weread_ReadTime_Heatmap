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

        try:
            resp = requests.post(GATEWAY_URL, json=body, headers=headers, timeout=30)
        except requests.Timeout:
            raise Exception("Gateway API 请求超时（30s）")
        except requests.ConnectionError as e:
            raise Exception(f"Gateway API 连接失败: {e}")

        # 尝试解析 JSON 响应体（即使 HTTP 状态码非 2xx）
        try:
            data = resp.json()
        except ValueError:
            # 响应不是 JSON，打印原始内容以便排查
            body_preview = resp.text[:500]
            raise Exception(
                f"Gateway 返回非 JSON 响应 "
                f"(HTTP {resp.status_code}): {body_preview}"
            )

        # 检查是否需要升级 skill 版本
        if "upgrade_info" in data:
            print(
                f"Skill 版本升级提示: "
                f"{data['upgrade_info'].get('message', '请升级')}"
            )

        # HTTP 非 2xx 时，优先用 JSON 中的错误信息
        if not resp.ok:
            errmsg = data.get("errmsg", data.get("message", "未知错误"))
            errcode = data.get("errcode", resp.status_code)
            raise Exception(
                f"Gateway API 错误 (HTTP {resp.status_code}): "
                f"{errmsg} (errcode={errcode})"
            )

        if data.get("errcode", 0) != 0:
            raise Exception(
                f"Gateway API 业务错误: {data.get('errmsg', '未知错误')} "
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
        """
        测试认证是否有效。
        先尝试 /_list（轻量接口），再尝试 /user/getinfo。
        返回 (是否成功, 用户信息)
        """
        try:
            # 先用 /_list 测试连通性和认证
            print("测试 Gateway 连通性...")
            resp = self.call_gateway("/_list")
            print("Gateway 连通正常")
            return True, resp
        except Exception as e:
            return False, {"error": str(e)}


def main():
    """测试认证是否有效"""
    auth = WeReadAuth()

    if not auth.init_auth():
        print("请设置环境变量: export WEREAD_API_KEY=<你的API Key>")
        return

    # 打印部分 Key 信息用于排查（只显示前几位）
    key_preview = auth.api_key[:8] + "***" if len(auth.api_key) > 8 else "***"
    print(f"API Key: {key_preview}")

    is_valid, info = auth.test_auth()
    if is_valid:
        print("认证成功！")
        # /_list 返回可能很大，只打印 keys
        if isinstance(info, dict):
            print(f"可用接口数: {len(info)}")
            if "errcode" in info:
                print(f"errcode: {info['errcode']}")
    else:
        print("认证失败")
        print(f"错误信息: {info.get('error', '未知错误')}")


if __name__ == "__main__":
    main()
