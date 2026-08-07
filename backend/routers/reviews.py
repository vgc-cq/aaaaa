from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import AdData, AgentMemory, Knowledge, Review, Video
from schemas import ReviewCreate, ReviewOut

router = APIRouter()


@router.get("/", response_model=List[ReviewOut])
def list_reviews(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    rows = db.query(Review).order_by(Review.id.asc()).offset(skip).limit(limit).all()
    ad_ids = {r.ad_id for r in rows if r.ad_id}
    video_ids = {r.video_id for r in rows if r.video_id}
    ads = {a.id: a for a in db.query(AdData).filter(AdData.id.in_(ad_ids)).all()} if ad_ids else {}
    videos = {v.id: v for v in db.query(Video).filter(Video.id.in_(video_ids)).all()} if video_ids else {}
    result = []
    for r in rows:
        item = ReviewOut.model_validate(r)
        ad = ads.get(r.ad_id)
        video = videos.get(r.video_id)
        item.video_code = video.video_code if video else None
        item.content_direction = ad.content_direction if ad else None
        result.append(item)
    return result


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db)):
    item = db.query(Review).filter(Review.id == review_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review not found")
    return item


@router.post("/", response_model=ReviewOut)
def create_review(item: ReviewCreate, db: Session = Depends(get_db)):
    db_item = Review(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{review_id}", response_model=ReviewOut)
def update_review(review_id: int, item: ReviewCreate, db: Session = Depends(get_db)):
    db_item = db.query(Review).filter(Review.id == review_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Review not found")
    old_status = db_item.status
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    # 记忆：用户把状态改为"认可/不认可"时，把这次生成写入智能体经验记忆表
    if db_item.status in ("认可", "不认可") and db_item.status != old_status:
        db.add(AgentMemory(
            review_id=db_item.id,
            ad_id=db_item.ad_id,
            video_id=db_item.video_id,
            memory_type=db_item.status,
            rating=db_item.review_level,
            decision=db_item.decision,
            summary=db_item.summary,
            suggestions=db_item.next_action,
            problems=db_item.problem_analysis,
        ))
        # 知识库沉淀：状态改为"认可"= 人工验证通过，把结论沉淀为"已生效"知识，供全系统复用
        if db_item.status == "认可":
            notes_ref = f"来源复盘记录 #{db_item.id}（人工认可）"
            existed = db.query(Knowledge).filter(Knowledge.notes == notes_ref).first()
            if not existed and (db_item.summary or db_item.next_action):
                db.add(Knowledge(
                    knowledge_code=_next_knowledge_code(db),
                    category="复盘经验",
                    source="复盘智能体·人工认可",
                    applicable_scene="投流复盘",
                    content_summary=(db_item.summary or "")[:500],
                    prompt_version="review-agent-v3",
                    usage_effect=(db_item.next_action or "")[:500],
                    updater=db_item.owner or "投流复盘智能体",
                    status="已生效",
                    priority=db_item.priority or "P1",
                    review_status="已审核",
                    target_user="投流/运营/内容团队",
                    notes=notes_ref,
                ))
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Review).filter(Review.id == review_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(db_item)
    db.commit()
    return {"message": "deleted"}


class BatchDeleteIn(BaseModel):
    ids: list[int] = []


@router.post("/batch_delete")
def batch_delete_reviews(data: BatchDeleteIn, db: Session = Depends(get_db)):
    if not data.ids:
        raise HTTPException(status_code=400, detail="Select reviews first")
    items = db.query(Review).filter(Review.id.in_(data.ids)).all()
    if not items:
        raise HTTPException(status_code=400, detail="No reviews to delete")
    db.query(Review).filter(Review.id.in_(data.ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Deleted {len(items)} reviews"}


def _next_knowledge_code(db: Session) -> str:
    rows = db.query(Knowledge.knowledge_code).filter(Knowledge.knowledge_code.like("K%")).all()
    max_num = 0
    for (code,) in rows:
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"K{max_num + 1:03d}"


