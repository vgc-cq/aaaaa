from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Review
from schemas import ReviewCreate, ReviewOut

router = APIRouter()


@router.get("/", response_model=List[ReviewOut])
def list_reviews(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    return db.query(Review).order_by(Review.id.asc()).offset(skip).limit(limit).all()


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db)):
    item = db.query(Review).filter(Review.id == review_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="复盘记录不存在")
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
        raise HTTPException(status_code=404, detail="复盘记录不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Review).filter(Review.id == review_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="复盘记录不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}


from pydantic import BaseModel


class BatchDeleteIn(BaseModel):
    ids: list[int] = []


@router.post("/batch_delete")
def batch_delete_reviews(data: BatchDeleteIn, db: Session = Depends(get_db)):
    ids = data.ids
    if not ids:
        raise HTTPException(status_code=400, detail="请先勾选要删除的复盘")
    items = db.query(Review).filter(Review.id.in_(ids)).all()
    if not items:
        raise HTTPException(status_code=400, detail="没有可删除的复盘")
    db.query(Review).filter(Review.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"已删除 {len(items)} 条复盘记录"}

