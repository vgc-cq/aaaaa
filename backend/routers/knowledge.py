from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Knowledge
from schemas import KnowledgeCreate, KnowledgeOut

router = APIRouter()


@router.get("/", response_model=List[KnowledgeOut])
def list_knowledge(skip: int = 0, limit: int = 500, category: str = None, db: Session = Depends(get_db)):
    query = db.query(Knowledge)
    if category:
        query = query.filter(Knowledge.category == category)
    return query.order_by(Knowledge.id.asc()).offset(skip).limit(limit).all()


@router.get("/{knowledge_id}", response_model=KnowledgeOut)
def get_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    item = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    return item


@router.post("/", response_model=KnowledgeOut)
def create_knowledge(item: KnowledgeCreate, db: Session = Depends(get_db)):
    db_item = Knowledge(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{knowledge_id}", response_model=KnowledgeOut)
def update_knowledge(knowledge_id: int, item: KnowledgeCreate, db: Session = Depends(get_db)):
    db_item = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{knowledge_id}")
def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="知识条目不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}


@router.get("/categories/list")
def list_categories(db: Session = Depends(get_db)):
    """列出所有知识库分类"""
    items = db.query(Knowledge.category).distinct().all()
    return [item[0] for item in items if item[0]]

