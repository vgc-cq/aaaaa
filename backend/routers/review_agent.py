from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai_workflow.agent_graph import execute_agent, run_agent
from database import get_db

router = APIRouter()


class AgentRunInput(BaseModel):
    goal: str = "Review all ad data and create prioritized optimization actions"
    video_id: int | None = None


class AgentExecuteInput(BaseModel):
    plan: dict
    approved_indexes: list[int] = []


@router.post("/run")
def run_autonomous_agent(payload: AgentRunInput, db: Session = Depends(get_db)):
    result = run_agent(db, payload.goal, payload.video_id)
    if result.get("status") == "empty":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/execute")
def execute_autonomous_agent(payload: AgentExecuteInput, db: Session = Depends(get_db)):
    if not payload.approved_indexes:
        raise HTTPException(status_code=400, detail="Select at least one approved action")
    return execute_agent(db, payload.plan, payload.approved_indexes)
