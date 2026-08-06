from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Lead
from schemas import LeadCreate, LeadOut

router = APIRouter()


@router.get("/", response_model=List[LeadOut])
def list_leads(skip: int = 0, limit: int = 500, follow_status: str = None, db: Session = Depends(get_db)):
    query = db.query(Lead)
    if follow_status:
        query = query.filter(Lead.follow_status == follow_status)
    return query.order_by(Lead.id.asc()).offset(skip).limit(limit).all()


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    item = db.query(Lead).filter(Lead.id == lead_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="线索不存在")
    return item


@router.post("/", response_model=LeadOut)
def create_lead(item: LeadCreate, db: Session = Depends(get_db)):
    db_item = Lead(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, item: LeadCreate, db: Session = Depends(get_db)):
    db_item = db.query(Lead).filter(Lead.id == lead_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="线索不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Lead).filter(Lead.id == lead_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="线索不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}


from pydantic import BaseModel


class BatchDeleteIn(BaseModel):
    ids: list[int] = []


@router.post("/batch_delete")
def batch_delete_leads(data: BatchDeleteIn, db: Session = Depends(get_db)):
    ids = data.ids
    if not ids:
        raise HTTPException(status_code=400, detail="请先勾选要删除的线索")
    items = db.query(Lead).filter(Lead.id.in_(ids)).all()
    if not items:
        raise HTTPException(status_code=400, detail="没有可删除的线索")
    db.query(Lead).filter(Lead.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"已删除 {len(items)} 条客服私域线索记录"}


@router.get("/view/today")
def today_follow_up(db: Session = Depends(get_db)):
    """今日待跟进"""
    from datetime import datetime
    today = datetime.now().date()
    return db.query(Lead).filter(Lead.follow_status == "待跟进").all()

