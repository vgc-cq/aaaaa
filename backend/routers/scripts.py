from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Script
from schemas import ScriptCreate, ScriptOut

router = APIRouter()


@router.get("/", response_model=List[ScriptOut])
def list_scripts(skip: int = 0, limit: int = 500, product_id: int = None, content_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Script)
    if product_id:
        query = query.filter(Script.product_id == product_id)
    if content_id:
        query = query.filter(Script.content_id == content_id)
    return query.order_by(Script.id.asc()).offset(skip).limit(limit).all()


@router.get("/{script_id}", response_model=ScriptOut)
def get_script(script_id: int, db: Session = Depends(get_db)):
    item = db.query(Script).filter(Script.id == script_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="脚本不存在")
    return item


@router.post("/", response_model=ScriptOut)
def create_script(item: ScriptCreate, db: Session = Depends(get_db)):
    db_item = Script(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{script_id}", response_model=ScriptOut)
def update_script(script_id: int, item: ScriptCreate, db: Session = Depends(get_db)):
    db_item = db.query(Script).filter(Script.id == script_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="脚本不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Script).filter(Script.id == script_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="脚本不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}

