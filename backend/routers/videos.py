import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Product, Script, Video
from schemas import VideoCreate, VideoOut
from services.wan_video import WanVideoClient, WanVideoError

router = APIRouter()


@router.get("/", response_model=List[VideoOut])
def list_videos(skip: int = 0, limit: int = 500, publish_status: str = None, db: Session = Depends(get_db)):
    query = db.query(Video)
    if publish_status:
        query = query.filter(Video.publish_status == publish_status)
    videos = query.order_by(Video.id.asc()).offset(skip).limit(limit).all()
    # 兼容早期数据：老记录没有冗余存储脚本标题/商品名，从关联表回填
    script_ids = {v.script_id for v in videos if v.script_id}
    scripts = {}
    if script_ids:
        scripts = {s.id: s for s in db.query(Script).filter(Script.id.in_(script_ids)).all()}
    product_ids = {s.product_id for s in scripts.values() if s.product_id}
    products = {}
    if product_ids:
        products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    for v in videos:
        s = scripts.get(v.script_id)
        if s:
            if not v.script_title:
                v.script_title = s.title
            p = products.get(s.product_id)
            if p and not v.product_name:
                v.product_name = p.name
                v.product_id = p.id
    return videos


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


class WanGenerateIn(BaseModel):
    script_id: int
    video_id: int | None = None
    resolution: str = "720P"
    ratio: str = "16:9"
    watermark: bool = False


def _next_video_code(db: Session) -> str:
    rows = db.query(Video.video_code).filter(Video.video_code.like("V%")).all()
    max_num = 0
    for (code,) in rows:
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"V{max_num + 1:03d}"


def _parse_shot_range(shot_time: str | None):
    """解析 '0-3秒' / '0.5-3.5s' 形式的镜头时间，返回 (start, end)。"""
    nums = re.findall(r"\d+(?:\.\d+)?", shot_time or "")
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    return None


def _load_script_group(script: Script, db: Session) -> List[Script]:
    """按脚本标题 + 商品把同一脚本组的全部镜头取出来，按时间轴排序。"""
    query = db.query(Script)
    if script.product_id:
        query = query.filter(Script.product_id == script.product_id, Script.title == script.title)
    else:
        query = query.filter(Script.title == script.title)
    shots = query.all()
    if not shots:
        shots = [script]

    def sort_key(item: Script):
        r = _parse_shot_range(item.shot_time)
        return r[0] if r else item.id

    return sorted(shots, key=sort_key)


def _build_multi_shot_prompt(shots: List[Script], product_name: str):
    """把一组镜头按时间轴拼成万相多镜头叙事的提示词，返回 (prompt, duration)。"""
    total_raw = 0
    for s in shots:
        r = _parse_shot_range(s.shot_time)
        if r:
            total_raw = max(total_raw, r[1])
    if total_raw <= 0:
        total_raw = len(shots) * 5
    # 通义万相单次最长 15 秒，超过则按比例压缩时间轴
    scale = min(1.0, 15.0 / total_raw)
    duration = max(2, min(15, round(total_raw * scale)))

    lines = [
        f"Generate a coherent multi-shot e-commerce product video for {product_name}, "
        f"total duration about {duration} seconds, with {len(shots)} shots in sequence:"
    ]
    cursor = 0.0
    for i, s in enumerate(shots):
        r = _parse_shot_range(s.shot_time)
        if r:
            start = cursor
            end = r[1] * scale
            cursor = end
        else:
            start = i * (duration / len(shots))
            end = (i + 1) * (duration / len(shots))
        desc = (s.ai_prompt or "").strip() or (s.scene_desc or "").strip() or f"Shot {i + 1}"
        lines.append(f"Shot {i + 1} [{round(start)}-{round(end)} seconds]: {desc}")
    lines.append("Ensure smooth transitions between shots, keep the product and visual style consistent, realistic product photography look, suitable for e-commerce.")
    return "\n".join(lines), duration


@router.post("/wan/generate")
def generate_video_with_wan(payload: WanGenerateIn, db: Session = Depends(get_db)):
    script = db.query(Script).filter(Script.id == payload.script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="脚本分镜不存在")

    client = WanVideoClient()
    if not client.configured():
        raise HTTPException(status_code=503, detail="未配置 DashScope API Key，请在 backend/.env 中配置 WAN_API_KEY 或 QWEN_VL_API_KEY")

    shots = _load_script_group(script, db)
    product = None
    if script.product_id:
        product = db.query(Product).filter(Product.id == script.product_id).first()
    product_name = product.name if product else "本商品"
    prompt, duration = _build_multi_shot_prompt(shots, product_name)
    try:
        result = client.submit_text_to_video(
            prompt,
            duration=duration,
            resolution=payload.resolution,
            ratio=payload.ratio,
            watermark=payload.watermark,
        )
    except WanVideoError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    task_id = result["task_id"]
    video = db.query(Video).filter(Video.id == payload.video_id).first() if payload.video_id else None
    if not video:
        video = Video(
            video_code=_next_video_code(db),
            script_id=script.id,
            script_title=script.title,
            product_id=product.id if product else script.product_id,
            product_name=product_name,
            material_status="生成中",
            generate_tool="通义万相",
            editor="AI视频生成",
            version="v1",
            publish_status="未发布",
        )
        db.add(video)
    else:
        video.script_id = script.id
        video.script_title = script.title
        video.product_id = product.id if product else script.product_id
        video.product_name = product_name
        video.material_status = "生成中"
        video.generate_tool = "通义万相"
    video.generate_task_id = task_id
    video.generate_status = "PENDING"
    video.video_url = None
    db.commit()
    db.refresh(video)
    return {"message": "通义万相视频任务已提交", "task_id": task_id, "video": video}


@router.get("/wan/progress/{video_id:int}")
def get_wan_video_progress(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频任务不存在")
    task_id = video.generate_task_id
    if not task_id:
        raise HTTPException(status_code=404, detail="该视频任务没有生成任务ID")

    client = WanVideoClient()
    if not client.configured():
        raise HTTPException(status_code=503, detail="未配置 DashScope API Key")
    try:
        result = client.get_result(task_id)
    except WanVideoError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    status = result.get("task_status", "UNKNOWN")
    video.generate_status = status
    if status == "SUCCEEDED":
        video.material_status = "已完成"
        if result.get("video_url"):
            video.video_url = result["video_url"]
    elif status == "FAILED":
        video.material_status = "待优化"
        fail_reason = result.get("message") or result.get("code") or "未知错误"
        video.notes = f"{video.notes or ''}\n万相生成失败：{fail_reason}".strip()
    else:
        video.material_status = "生成中"
    db.commit()
    return {
        "task_id": task_id,
        "video_id": video.id,
        "task_status": status,
        "video_url": video.video_url,
    }
