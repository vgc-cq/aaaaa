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
    return query.order_by(Video.id.desc()).offset(skip).limit(limit).all()


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

