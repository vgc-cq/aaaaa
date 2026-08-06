"""通义万相 Wan2.7 文生视频服务

调用阿里云百炼（DashScope）异步视频生成接口：
1. 提交任务：POST {base}/api/v1/services/aigc/video-generation/video-synthesis
2. 轮询结果：GET  {base}/api/v1/tasks/{task_id}

鉴权使用 DashScope API Key（Bearer），可直接复用 QWEN_VL_API_KEY，
也可单独配置 WAN_API_KEY。接口为异步任务，通常 1-5 分钟出片。
"""

import json
import os

import httpx


class WanVideoError(RuntimeError):
    pass


class WanVideoClient:
    def __init__(self):
        self.api_key = (os.getenv("WAN_API_KEY", "") or os.getenv("QWEN_VL_API_KEY", "")).strip()
        self.base = os.getenv("WAN_API_BASE_URL", "https://dashscope.aliyuncs.com").rstrip("/")
        self.model = os.getenv("WAN_VIDEO_MODEL", "wan2.7-t2v").strip()

    def configured(self) -> bool:
        return bool(self.api_key)

    def submit_text_to_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "720P",
        ratio: str = "16:9",
        watermark: bool = False,
        negative_prompt: str | None = None,
        seed: int | None = None,
    ):
        if not self.configured():
            raise WanVideoError("未配置 DashScope API Key，请在 backend/.env 中配置 WAN_API_KEY 或 QWEN_VL_API_KEY")
        input_data = {"prompt": prompt}
        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        parameters = {
            "resolution": resolution,
            "ratio": ratio,
            "duration": max(2, min(int(duration), 15)),
            "prompt_extend": True,
            "watermark": bool(watermark),
        }
        if seed is not None:
            parameters["seed"] = int(seed)
        payload = {"model": self.model, "input": input_data, "parameters": parameters}
        url = f"{self.base}/api/v1/services/aigc/video-generation/video-synthesis"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=120)
        except httpx.HTTPError as exc:
            raise WanVideoError(f"通义万相请求失败：{exc}")
        if response.status_code >= 400:
            raise WanVideoError(f"通义万相 HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        if data.get("code"):
            raise WanVideoError(data.get("message") or json.dumps(data, ensure_ascii=False)[:500])
        output = data.get("output") or {}
        task_id = output.get("task_id")
        if not task_id:
            raise WanVideoError(f"通义万相未返回任务ID：{data}")
        return {
            "task_id": task_id,
            "task_status": output.get("task_status", "PENDING"),
        }

    def get_result(self, task_id: str) -> dict:
        if not self.configured():
            raise WanVideoError("未配置 DashScope API Key")
        url = f"{self.base}/api/v1/tasks/{task_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = httpx.get(url, headers=headers, timeout=120)
        except httpx.HTTPError as exc:
            raise WanVideoError(f"通义万相查询失败：{exc}")
        if response.status_code >= 400:
            raise WanVideoError(f"通义万相 HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        if data.get("code"):
            raise WanVideoError(data.get("message") or json.dumps(data, ensure_ascii=False)[:500])
        output = data.get("output") or {}
        return {
            "task_id": output.get("task_id") or task_id,
            "task_status": output.get("task_status", "UNKNOWN"),
            "video_url": output.get("video_url"),
            "message": output.get("message"),
            "code": output.get("code"),
            "raw": data,
        }
