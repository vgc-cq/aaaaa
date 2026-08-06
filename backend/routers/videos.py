import json
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Script, Video
from schemas import VideoCreate, VideoOut
from services.jimeng import JimengClient, JimengError

router = APIRouter()


@router.get("/", response_model=List[VideoOut])
def list_videos(skip: int = 0, limit: int = 500, publish_status: str = None, db: Session = Depends(get_db)):
    query = db.query(Video)
    if publish_status:
        query = query.filter(Video.publish_status == publish_status)
    return query.order_by(Video.id.asc()).offset(skip).limit(limit).all()


@router.get("/{video_id:int}", response_model=VideoOut)
def get_video(video_id: int, db: Session = Depends(get_db)):
    item = db.query(Video).filter(Video.id == video_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="视频不存在")
    return item


@router.post("/", response_model=VideoOut)
def create_video(item: VideoCreate, db: Session = Depends(get_db)):
    db_item = Video(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{video_id:int}", response_model=VideoOut)
def update_video(video_id: int, item: VideoCreate, db: Session = Depends(get_db)):
    db_item = db.query(Video).filter(Video.id == video_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="视频不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{video_id:int}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Video).filter(Video.id == video_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="视频不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}


from pydantic import BaseModel


class BatchDeleteIn(BaseModel):
    ids: list[int] = []


@router.post("/batch_delete")
def batch_delete_videos(data: BatchDeleteIn, db: Session = Depends(get_db)):
    ids = data.ids
    if not ids:
        raise HTTPException(status_code=400, detail="请先勾选要删除的视频")
    items = db.query(Video).filter(Video.id.in_(ids)).all()
    if not items:
        raise HTTPException(status_code=400, detail="没有可删除的视频")
    db.query(Video).filter(Video.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"已删除 {len(items)} 条视频任务记录"}


@router.get("/view/kanban")
def kanban_view(db: Session = Depends(get_db)):
    """按状态看板"""
    videos = db.query(Video).all()
    kanban = {}
    for v in videos:
        kanban.setdefault(v.publish_status, []).append({
            "id": v.id, "code": v.video_code, "editor": v.editor
        })
    return kanban


class JimengGenerateIn(BaseModel):
    script_id: int
    video_id: int | None = None
    duration: int = 5
    watermark: bool = False


def _next_video_code(db: Session) -> str:
    rows = db.query(Video.video_code).filter(Video.video_code.like("V%")).all()
    max_num = 0
    for (code,) in rows:
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"V{max_num + 1:03d}"


@router.post("/jimeng/generate")
def generate_video_with_jimeng(payload: JimengGenerateIn, db: Session = Depends(get_db)):
    script = db.query(Script).filter(Script.id == payload.script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="脚本分镜不存在")

    client = JimengClient()
    if not client.configured():
        raise HTTPException(status_code=503, detail="即梦AI密钥未配置，请在 backend/.env 中配置 JIMENG_ACCESS_KEY_ID 和 JIMENG_ACCESS_KEY_SECRET")

    prompt = "\n".join([
        f"Title: {script.title or ''}",
        f"Scene: {script.scene_desc or ''}",
        f"Voiceover: {script.voiceover or ''}",
        f"Subtitle: {script.subtitle or ''}",
        f"Camera: {script.camera_move or ''}",
        f"Materials: {script.material_req or ''}",
        f"Generation prompt: {script.ai_prompt or ''}",
        "Create a short e-commerce video. Keep product details realistic and avoid exaggerated claims.",
    ])
    try:
        result = client.submit_text_to_video(prompt, payload.duration, payload.watermark)
    except JimengError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    task_id = (
        result.get("data", {}).get("task_id")
        or result.get("task_id")
        or result.get("data", {}).get("id")
    )
    if not task_id:
        raise HTTPException(status_code=502, detail=f"即梦AI未返回任务ID：{result}")

    video = db.query(Video).filter(Video.id == payload.video_id).first() if payload.video_id else None
    if not video:
        video = Video(
            video_code=_next_video_code(db),
            script_id=script.id,
            material_status="生成中",
            generate_tool="即梦AI",
            editor="AI视频生成",
            version="v1",
            publish_status="未发布",
        )
        db.add(video)
    else:
        video.script_id = script.id
        video.material_status = "生成中"
        video.generate_tool = "即梦AI"
    video.notes = f"{video.notes or ''}\n即梦AI任务ID：{task_id}".strip()
    db.commit()
    db.refresh(video)
    return {"message": "即梦AI视频任务已提交", "task_id": task_id, "video": video}


@router.get("/jimeng/result/{task_id}")
def get_jimeng_video_result(task_id: str):
    client = JimengClient()
    if not client.configured():
        raise HTTPException(status_code=503, detail="即梦AI密钥未配置")
    try:
        return client.get_text_to_video_result(task_id)
    except JimengError as exc:
        raise HTTPException(status_code=502, detail=str(exc))




def _extract_jimeng_task_id(notes: str | None) -> str | None:
    match = re.search(r"(?:??AI??ID|ID)[:?]\s*([^\s\n]+)", notes or "")
    return match.group(1) if match else None


def _normalize_jimeng_progress(data: dict) -> dict:
    raw = json.dumps(data, ensure_ascii=False)
    lowered = raw.lower()
    done = any(x in lowered for x in ["done", "success", "finish", "completed"]) or "???" in raw or "??" in raw
    failed = any(x in lowered for x in ["fail", "error"]) or "??" in raw

    def find_progress(obj):
        if isinstance(obj, dict):
            for key in ["progress", "percent", "percentage"]:
                if key in obj:
                    try:
                        value = float(obj[key])
                        return int(max(0, min(100, value if value > 1 else value * 100)))
                    except Exception:
                        pass
            for value in obj.values():
                got = find_progress(value)
                if got is not None:
                    return got
        if isinstance(obj, list):
            for value in obj:
                got = find_progress(value)
                if got is not None:
                    return got
        return None

    progress = find_progress(data)
    if done:
        return {"status": "completed", "status_text": "???", "progress": 100, "raw": data}
    if failed:
        return {"status": "failed", "status_text": "????", "progress": progress or 0, "raw": data}
    return {"status": "running", "status_text": "???", "progress": progress or 50, "raw": data}


@router.get("/jimeng/progress/{video_id:int}")
def get_jimeng_video_progress(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="???????")
    task_id = _extract_jimeng_task_id(video.notes)
    if not task_id:
        raise HTTPException(status_code=404, detail="???????????ID")
    client = JimengClient()
    if not client.configured():
        raise HTTPException(status_code=503, detail="??AI?????")
    try:
        data = client.get_text_to_video_result(task_id)
    except JimengError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    normalized = _normalize_jimeng_progress(data)
    if normalized["status"] == "completed":
        video.material_status = "???"
    elif normalized["status"] == "failed":
        video.material_status = "????"
    else:
        video.material_status = "???"
    db.commit()
    return {"task_id": task_id, "video_id": video.id, **normalized}
