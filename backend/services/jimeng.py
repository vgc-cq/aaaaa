import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx


class JimengError(RuntimeError):
    pass


class JimengClient:
    def __init__(self):
        self.access_key = os.getenv("JIMENG_ACCESS_KEY_ID", "").strip()
        self.secret_key = os.getenv("JIMENG_ACCESS_KEY_SECRET", "").strip()
        self.host = os.getenv("JIMENG_API_HOST", "visual.volcengineapi.com").strip()
        self.region = os.getenv("JIMENG_REGION", "cn-north-1").strip()
        self.service = os.getenv("JIMENG_SERVICE", "cv").strip()
        self.version = os.getenv("JIMENG_API_VERSION", "2024-06-06").strip()
        self.req_key = os.getenv("JIMENG_T2V_REQ_KEY", "jimeng_t2v_v30").strip()

    def configured(self):
        return bool(self.access_key and self.secret_key)

    @staticmethod
    def _hmac(key, value):
        return hmac.new(key, value.encode("utf-8"), hashlib.sha256).digest()

    def _signed_headers(self, action: str, body: bytes):
        if not self.configured():
            raise JimengError("Jimeng API credentials are not configured")
        now = datetime.now(timezone.utc)
        x_date = now.strftime("%Y%m%dT%H%M%SZ")
        short_date = x_date[:8]
        query = urlencode(sorted({"Action": action, "Version": self.version}.items()))
        payload_hash = hashlib.sha256(body).hexdigest()
        canonical_headers = f"content-type:application/json\nhost:{self.host}\nx-content-sha256:{payload_hash}\nx-date:{x_date}\n"
        signed_headers = "content-type;host;x-content-sha256;x-date"
        canonical_request = f"POST\n/\n{query}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        scope = f"{short_date}/{self.region}/{self.service}/request"
        string_to_sign = "HMAC-SHA256\n{}\n{}\n{}".format(x_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest())
        k_date = self._hmac(("VOLC" + self.secret_key).encode(), short_date)
        k_region = self._hmac(k_date, self.region)
        k_service = self._hmac(k_region, self.service)
        k_signing = self._hmac(k_service, "request")
        signature = hmac.new(k_signing, string_to_sign.encode(), hashlib.sha256).hexdigest()
        authorization = f"HMAC-SHA256 Credential={self.access_key}/{scope}, SignedHeaders={signed_headers}, Signature={signature}"
        return query, {
            "Content-Type": "application/json",
            "Host": self.host,
            "X-Date": x_date,
            "X-Content-Sha256": payload_hash,
            "Authorization": authorization,
        }

    def request(self, action: str, payload: dict):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        query, headers = self._signed_headers(action, body)
        url = f"https://{self.host}/?{query}"
        response = httpx.post(url, content=body, headers=headers, timeout=120)
        if response.status_code >= 400:
            raise JimengError(f"Jimeng HTTP {response.status_code}: {response.text[:500]}")
        data = response.json()
        if data.get("code") not in (None, 0, "0"):
            raise JimengError(data.get("message") or data.get("msg") or json.dumps(data, ensure_ascii=False)[:500])
        return data

    def submit_text_to_video(self, prompt: str, duration: int = 5, watermark: bool = False):
        payload = {
            "req_key": self.req_key,
            "prompt": prompt,
            "frames": max(1, min(int(duration), 10)) * 24,
            "watermark": watermark,
        }
        return self.request("JimengT2VV30SubmitTask", payload)

    def get_text_to_video_result(self, task_id: str):
        return self.request("JimengT2VV30GetResult", {"req_key": self.req_key, "task_id": task_id})
