"""Qwen-VL-Max + DeepSeek 内容拆解服务

用途：
1. Qwen-VL-Max 看视频/图片，输出时间轴文字描述；
2. DeepSeek 基于文字描述，拆解钩子、结构、转化点和二创方向；
3. 可选写入内容拆解表。
"""

import json
import os
import re
import shutil
import base64
import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote, urlparse

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Content, Product

load_dotenv()

router = APIRouter()

DEEPSEEK_API_KEY = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

QWEN_VL_API_KEY = os.getenv("QWEN_VL_API_KEY", "")
QWEN_VL_BASE_URL = os.getenv("QWEN_VL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_VL_MODEL = os.getenv("QWEN_VL_MODEL", "qwen-vl-max")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".mp4", ".mov", ".avi", ".mkv", ".webm"}


class VisionBreakdownInput(BaseModel):
    source_type: str = "video_url"  # video_url / image_url / text
    source_url: Optional[str] = None
    text: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    save_to_table: bool = False


def build_file_url(request: Request, filename: str) -> str:
    """生成前端可访问的上传文件 URL；生产环境可用 PUBLIC_BASE_URL 覆盖。"""
    base = PUBLIC_BASE_URL or str(request.base_url).rstrip("/")
    return f"{base}/uploads/{quote(filename)}"


def detect_source_type(filename: str, content_type: str = "") -> str:
    ext = Path(filename).suffix.lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"} or content_type.startswith("image/"):
        return "image_url"
    if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm"} or content_type.startswith("video/"):
        return "video_url"
    raise HTTPException(status_code=400, detail="仅支持上传常见图片或视频文件")


def safe_upload_name(filename: str) -> str:
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", Path(filename).stem).strip("._") or "media"
    ext = Path(filename).suffix.lower()
    import uuid
    return f"{stem}_{uuid.uuid4().hex[:10]}{ext}"


def image_url_for_qwen(source_url: str, source_type: str) -> str:
    """本地上传图片转 data URL，避免云端模型无法访问 localhost；视频仍使用 URL。"""
    if source_type != "image_url" or "/uploads/" not in source_url:
        return source_url
    parsed = urlparse(source_url)
    filename = unquote(Path(parsed.path).name)
    local_path = UPLOAD_DIR / filename
    if not local_path.exists():
        return source_url
    mime = mimetypes.guess_type(str(local_path))[0] or "image/png"
    encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def local_video_url_for_qwen(source_url: str) -> str | None:
    """本地上传视频优先转 Base64 Data URL，避免 Qwen 云端无法访问 localhost。"""
    local_path = local_upload_path_from_url(source_url)
    if not local_path:
        return None
    raw = local_path.read_bytes()
    # 阿里云文档要求本地文件 Base64 后单个 data-uri 小于 10MB；保守限制 9.5MB。
    encoded_len = len(raw) * 4 / 3
    if encoded_len > 9.5 * 1024 * 1024:
        return None
    mime = mimetypes.guess_type(str(local_path))[0] or "video/mp4"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def local_upload_path_from_url(source_url: str) -> Path | None:
    """如果 URL 指向本机 /uploads 文件，返回本地文件路径。"""
    if not source_url or "/uploads/" not in source_url:
        return None
    parsed = urlparse(source_url)
    filename = unquote(Path(parsed.path).name)
    local_path = UPLOAD_DIR / filename
    return local_path if local_path.exists() else None


def extract_video_frame_data_urls(video_path: Path, max_frames: int = 6) -> list[str]:
    """从本地视频均匀抽帧，转成 base64 图片，供云端视觉模型分析。

    云端 Qwen 无法下载 localhost 视频，因此本地上传视频走抽帧方案。
    """
    try:
        import cv2
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"本地视频抽帧需要 OpenCV：{str(e)}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="本地视频打开失败，请确认文件格式是否为 mp4/mov/webm 等常见格式")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        total = max_frames
    positions = sorted({int(i * max(total - 1, 1) / max(max_frames - 1, 1)) for i in range(max_frames)})
    frames = []
    for pos in positions:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        h, w = frame.shape[:2]
        max_side = 768
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        if ok:
            frames.append("data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("ascii"))
    cap.release()
    if not frames:
        raise HTTPException(status_code=400, detail="未能从本地视频中抽取画面帧")
    return frames


def get_deepseek_client():
    return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL, http_client=httpx.Client())


def get_qwen_client():
    return OpenAI(api_key=QWEN_VL_API_KEY, base_url=QWEN_VL_BASE_URL, http_client=httpx.Client())


def parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {"raw_text": text}


def as_text(value) -> str:
    """把 AI 返回的 list/dict 等结构转成 SQLite 可保存的文本。"""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def next_code(db: Session, model, field_name: str, prefix: str) -> str:
    field = getattr(model, field_name)
    rows = db.query(field).filter(field.like(f"{prefix}%")).all()
    max_num = 0
    for (code,) in rows:
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"{prefix}{max_num + 1:03d}"


def qwen_describe_media(data: VisionBreakdownInput) -> str:
    if data.source_type == "text":
        return data.text or ""
    if not QWEN_VL_API_KEY:
        raise HTTPException(status_code=400, detail="未配置 Qwen-VL-Max API Key")
    if not data.source_url:
        raise HTTPException(status_code=400, detail="请填写视频或图片 URL")

    media_key = "video_url" if data.source_type == "video_url" else "image_url"
    qwen_url = image_url_for_qwen(data.source_url, data.source_type)
    qwen_video_data_url = local_video_url_for_qwen(data.source_url) if data.source_type == "video_url" else None
    local_video_path = local_upload_path_from_url(data.source_url) if data.source_type == "video_url" else None
    prompt = """
你是一位短视频电商内容拆解助理。请认真理解输入的视频/图片内容，输出中文结构化文字描述。
要求：
1. 如果是视频，请按时间顺序拆成 0-3秒、3-8秒、8-15秒、15秒以后等片段；
2. 描述画面、人物动作、商品展示、字幕/口播、镜头节奏；
3. 如果看不到音频或字幕，请明确说明“音频/字幕未识别”；
4. 输出适合交给文本模型继续分析的完整文字。
"""
    if qwen_video_data_url:
        user_content = [
            {"type": "text", "text": prompt + "\n注意：当前是本地上传视频，已转为 Base64 视频输入；如无法识别音频，请说明“音频未识别”。"},
            {"type": "video_url", "video_url": {"url": qwen_video_data_url, "fps": 1.0}},
        ]
    elif local_video_path:
        frame_urls = extract_video_frame_data_urls(local_video_path)
        user_content = [
            {
                "type": "text",
                "text": prompt + "\n注意：当前是本地上传视频，系统已抽取多个关键画面帧给你分析；如无法识别音频，请说明“音频未识别”。",
            },
            # DashScope/OpenAI 兼容模式中，视频抽帧列表应作为 type=video 传入，
            # 而不是拆成多条 image_url；否则部分模型会报多模态参数错误。
            {"type": "video", "video": frame_urls},
        ]
    else:
        user_content = [
            {"type": "text", "text": prompt},
            {"type": media_key, media_key: {"url": qwen_url}},
        ]
    try:
        res = get_qwen_client().chat.completions.create(
            model=QWEN_VL_MODEL,
            messages=[
                {"role": "system", "content": "你是专业的视频内容理解模型。"},
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            temperature=0.2,
            max_tokens=1800,
        )
        return res.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qwen-VL-Max 解析失败：{str(e)}")


@router.post("/vision/upload")
def upload_media(request: Request, file: UploadFile = File(...)):
    """上传本地视频/图片到 backend/uploads，并返回可访问 URL。"""
    source_type = detect_source_type(file.filename or "", file.content_type or "")
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in ALLOWED_MEDIA_EXTS:
        raise HTTPException(status_code=400, detail="不支持的素材格式")
    filename = safe_upload_name(file.filename or "media")
    target = UPLOAD_DIR / filename
    try:
        with target.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败：{str(e)}")
    finally:
        file.file.close()
    return {
        "filename": filename,
        "url": build_file_url(request, filename),
        "source_type": source_type,
        "content_type": file.content_type,
    }


def deepseek_breakdown(description: str, product_name: str = "") -> dict:
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=400, detail="未配置 DeepSeek API Key")
    prompt = f"""
你是一位短视频电商爆款内容拆解专家。请基于下面的视频/图片文字描述，输出严格 JSON，不要输出 Markdown。

商品/项目：{product_name or '未指定'}

视频/图片文字描述：
{description}

请输出 JSON，字段如下：
{{
  "hook": "前3秒钩子/开场吸引点",
  "scene": "主要场景",
  "target_group": "目标人群",
  "structure": "内容结构，尽量按时间线描述",
  "conversion_point": "转化点/下单引导/评论引导",
  "remix_angles": "可二创角度，至少3个方向",
  "risk_points": "合规风险/夸大宣传风险/需人工确认点",
  "summary": "一句话总结"
}}
"""
    try:
        res = get_deepseek_client().chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "你只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1800,
        )
        return parse_json(res.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DeepSeek 内容拆解失败：{str(e)}")


@router.post("/vision/content_breakdown")
def content_breakdown(data: VisionBreakdownInput, db: Session = Depends(get_db)):
    """Qwen-VL-Max 看视频/图片，再由 DeepSeek 做内容拆解。"""
    description = qwen_describe_media(data)
    product_name = data.product_name or ""
    product_id = data.product_id

    if product_id:
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product_name = product.name
    else:
        product = db.query(Product).filter(Product.name == product_name).first() if product_name else None

    breakdown = deepseek_breakdown(description, product_name)
    saved = None

    if data.save_to_table:
        content = Content(
            content_code=next_code(db, Content, "content_code", "C"),
            reference_link=data.source_url,
            hook=as_text(breakdown.get("hook")),
            scene=as_text(breakdown.get("scene")),
            target_group=as_text(breakdown.get("target_group")),
            structure=as_text(breakdown.get("structure")),
            conversion_point=as_text(breakdown.get("conversion_point")),
            remix_angles=as_text(breakdown.get("remix_angles")),
            risk_points=as_text(breakdown.get("risk_points")),
            product_id=product.id if product else None,
            analyst="Qwen-VL-Max + DeepSeek",
            status="已拆解",
            priority="P1",
            notes="由视觉模型识别后交给 DeepSeek 拆解，需人工复核",
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        saved = {"content_id": content.id, "content_code": content.content_code}
        # 手动视频拆解完成后，触发商品智能体为该商品自动生成脚本分镜
        if product:
            from ai_workflow.product_agent import trigger_product_agent_background
            trigger_product_agent_background()

    return {
        "source_type": data.source_type,
        "source_url": data.source_url,
        "vision_model": QWEN_VL_MODEL if data.source_type != "text" else "text_input",
        "analysis_model": DEEPSEEK_MODEL,
        "media_description": description,
        "breakdown": breakdown,
        "saved": saved,
    }
