"""共享 AI 调用工具（商品库选品、脚本分镜生成、复盘分析共用）。"""

import json
import os

import httpx
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY", "sk-placeholder")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client():
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, http_client=httpx.Client())


def call_ai(prompt: str) -> str:
    """调用 AI API；未配置 Key 时返回本地演示标记。"""
    if not API_KEY or API_KEY == "sk-placeholder" or "在这里" in API_KEY:
        return json.dumps({"local_demo": True, "message": "未配置大模型，使用本地模拟流程"}, ensure_ascii=False)
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是一位专业的短视频电商运营专家，请始终以JSON格式输出结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": str(e), "fallback": True}, ensure_ascii=False)


def parse_ai_response(text: str) -> dict:
    """解析 AI 返回的 JSON"""
    try:
        # 尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 块
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        # 尝试找 { } 包裹的内容
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_text": text, "parse_error": True}
