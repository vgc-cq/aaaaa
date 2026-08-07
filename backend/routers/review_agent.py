import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai_workflow.agent_graph import run_ad_review_agent, stream_ad_review_agent
from database import get_db
from models import AgentMemory, AgentRun

router = APIRouter()


class AdReviewRunInput(BaseModel):
    limit: int | None = None
    force: bool = False


@router.post("/run")
def run_ad_review(payload: AdReviewRunInput | None = None, db: Session = Depends(get_db)):
    """一键复盘：扫描并复盘全部投流数据（不传 limit 时不再分批，全部处理）。"""
    force = bool(payload.force) if payload else False
    limit = int(payload.limit) if (payload and payload.limit) else None
    return run_ad_review_agent(db, limit, force=force)


@router.post("/run/stream")
def run_ad_review_stream(payload: AdReviewRunInput | None = None, db: Session = Depends(get_db)):
    """流式复盘：LangGraph 每个节点执行完就通过 SSE 推给前端，节点卡片实时点亮。"""
    force = bool(payload.force) if payload else False
    limit = int(payload.limit) if (payload and payload.limit) else None

    def event_stream():
        try:
            for event in stream_ad_review_agent(db, limit, force=force):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            # 流式过程中出错也要把错误推给前端，避免前端一直转圈
            yield f"data: {json.dumps({'event': 'error', 'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.get("/memories")
def review_memories(limit: int = 10, db: Session = Depends(get_db)):
    """智能体经验记忆：用户在复盘记录表里标记的"认可/不认可"反馈。

    这些记忆会在下次生成复盘结论时作为上下文参考（认可的继续沿用，不认可的避免类似输出）。
    """
    rows = db.query(AgentMemory).order_by(AgentMemory.id.desc()).limit(max(1, min(limit, 50))).all()
    return [
        {
            "id": m.id,
            "memory_type": m.memory_type,
            "rating": m.rating,
            "decision": m.decision,
            "summary": m.summary,
            "suggestions": m.suggestions,
            "problems": m.problems,
            "ad_id": m.ad_id,
            "video_id": m.video_id,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]
