from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Content
from schemas import ContentCreate, ContentOut

router = APIRouter()


@router.get("/", response_model=List[ContentOut])
def list_contents(skip: int = 0, limit: int = 500, product_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Content)
    if product_id:
        query = query.filter(Content.product_id == product_id)
    return query.order_by(Content.id.asc()).offset(skip).limit(limit).all()


@router.get("/{content_id}", response_model=ContentOut)
def get_content(content_id: int, db: Session = Depends(get_db)):
    item = db.query(Content).filter(Content.id == content_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="内容不存在")
    return item


@router.post("/", response_model=ContentOut)
def create_content(item: ContentCreate, db: Session = Depends(get_db)):
    db_item = Content(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{content_id}", response_model=ContentOut)
def update_content(content_id: int, item: ContentCreate, db: Session = Depends(get_db)):
    db_item = db.query(Content).filter(Content.id == content_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="内容不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{content_id}")
def delete_content(content_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Content).filter(Content.id == content_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="内容不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}


from pydantic import BaseModel


class BatchDeleteIn(BaseModel):
    ids: list[int] = []


@router.post("/batch_delete")
def batch_delete_contents(data: BatchDeleteIn, db: Session = Depends(get_db)):
    ids = data.ids
    if not ids:
        raise HTTPException(status_code=400, detail="请先勾选要删除的内容")
    items = db.query(Content).filter(Content.id.in_(ids)).all()
    if not items:
        raise HTTPException(status_code=400, detail="没有可删除的内容")
    db.query(Content).filter(Content.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"已删除 {len(items)} 条内容拆解记录"}

