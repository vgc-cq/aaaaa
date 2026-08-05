from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import AdData
from schemas import AdDataCreate, AdDataOut

router = APIRouter()


@router.get("/", response_model=List[AdDataOut])
def list_ad_data(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    return db.query(AdData).order_by(AdData.id.asc()).offset(skip).limit(limit).all()


@router.get("/{ad_id}", response_model=AdDataOut)
def get_ad_data(ad_id: int, db: Session = Depends(get_db)):
    item = db.query(AdData).filter(AdData.id == ad_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="投流数据不存在")
    return item


@router.post("/", response_model=AdDataOut)
def create_ad_data(item: AdDataCreate, db: Session = Depends(get_db)):
    data = item.model_dump()
    if data.get("impressions") and data.get("clicks"):
        data["ctr"] = round(data["clicks"] / data["impressions"] * 100, 2)
    if data.get("spend") and data.get("revenue"):
        data["roi"] = round(data["revenue"] / data["spend"], 2) if data["spend"] > 0 else 0
    db_item = AdData(**data)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{ad_id}", response_model=AdDataOut)
def update_ad_data(ad_id: int, item: AdDataCreate, db: Session = Depends(get_db)):
    db_item = db.query(AdData).filter(AdData.id == ad_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="投流数据不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{ad_id}")
def delete_ad_data(ad_id: int, db: Session = Depends(get_db)):
    db_item = db.query(AdData).filter(AdData.id == ad_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="投流数据不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}


@router.get("/view/high_priority")
def high_priority_view(db: Session = Depends(get_db)):
    """高优先级问题视图：ROI < 1 或有异常的数据"""
    items = db.query(AdData).filter(
        (AdData.roi < 1) | (AdData.anomaly.isnot(None))
    ).all()
    return items

