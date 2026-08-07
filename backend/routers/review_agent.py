from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai_workflow.agent_graph import REVIEW_BATCH_LIMIT, run_ad_review_agent
from database import get_db
from models import AgentRun

router = APIRouter()


class AdReviewRunInput(BaseModel):
    limit: int | None = None
    force: bool = False


@router.post("/run")
def run_ad_review(payload: AdReviewRunInput | None = None, db: Session = Depends(get_db)):
    """一键复盘：自动扫描并复盘所有未复盘的投流数据，建议直接返回。"""
    limit = payload.limit if payload else None
    force = bool(payload.force) if payload else False
    return run_ad_review_agent(db, int(limit) if limit else REVIEW_BATCH_LIMIT, force=force)


@router.get("/logs")
def ad_review_logs(limit: int = 10, db: Session = Depends(get_db)):
    """最近投流复盘智能体运行记录。"""
    import json

    rows = db.query(AgentRun).filter(AgentRun.run_type == "ad_review").order_by(AgentRun.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "status": r.status,
            "products_processed": r.products_processed,
            "summary": json.loads(r.summary) if r.summary else {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
