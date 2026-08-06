from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Video
from schemas import VideoCreate, VideoOut

router = APIRouter()


@router.get("/", response_model=List[VideoOut])
def list_videos(skip: int = 0, limit: int = 500, publish_status: str = None, db: Session = Depends(get_db)):
    query = db.query(Video)
    if publish_status:
        query = query.filter(Video.publish_status == publish_status)
    return query.order_by(Video.id.asc()).offset(skip).limit(limit).all()


@router.get("/{video_id}", response_model=VideoOut)
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


@router.put("/{video_id}", response_model=VideoOut)
def update_video(video_id: int, item: VideoCreate, db: Session = Depends(get_db)):
    db_item = db.query(Video).filter(Video.id == video_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="视频不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{video_id}")
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

