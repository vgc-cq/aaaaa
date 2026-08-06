"""LangGraph 版自主复盘智能体

状态图结构：
  START → collect_context → plan → approval(人工审批判断)
            ├─ 未审批（/run 入口）→ END，返回计划等待确认
            └─ 已审批（/execute 入口，带 approved_indexes）→ execute_tools → finalize → END

LLM 通过 langchain-openai 的 ChatOpenAI 接 DeepSeek（OpenAI 兼容接口），
未配置 Key 或调用失败时自动回退到规则计划（fallback_plan），保证演示链路可跑通。

对外接口与旧版保持一致：
  run_agent(db, goal, video_id)      → 跑到审批节点，返回计划
  execute_agent(db, plan, indexes)   → 带上已审批动作继续执行
"""

import json
import os
import re
from datetime import datetime
from typing import Literal, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from models import AdData, Knowledge, Review, Video

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")


class AgentState(TypedDict, total=False):
    goal: str
    video_id: int | None
    context: list[dict]
    plan: dict
    actions: list[dict]
    approved_indexes: list[int]
    executed: list[dict]
    skipped: list[dict]
    generated_at: str
    status: str


def metrics_for(ad: AdData) -> dict:
    """根据单条投流数据计算复盘指标（规则计算，不走 LLM）。"""
    spend = float(ad.spend or 0)
    revenue = float(ad.revenue or 0)
    orders = int(ad.orders or 0)
    cart_clicks = int(ad.cart_clicks or 0)
    impressions = int(ad.impressions or 0)
    clicks = int(ad.clicks or 0)
    return {
        "roi": round(revenue / spend, 2) if spend else 0,
        "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
        "cpm": round(spend / impressions * 1000, 2) if impressions else 0,
        "cpc": round(spend / clicks, 2) if clicks else None,
        "cart_rate": round(cart_clicks / clicks * 100, 2) if clicks else 0,
        "cart_to_order_cvr": round(orders / cart_clicks * 100, 2) if cart_clicks else 0,
        "cpa": round(spend / orders, 2) if orders else None,
        "spend": spend,
        "revenue": revenue,
        "orders": orders,
        "cart_clicks": cart_clicks,
        "bounce_rate_2s": float(ad.bounce_rate_2s or 0),
        "completion_rate": float(ad.completion_rate or 0),
    }


def collect_context(db: Session, video_id: int | None = None) -> list[dict]:
    """收集投流数据 + 关联视频信息，并计算每条的复盘指标。"""
    query = db.query(AdData).order_by(AdData.id.desc())
    if video_id:
        query = query.filter(AdData.video_id == video_id)
    rows = query.limit(100).all()
    context = []
    for ad in rows:
        video = db.query(Video).filter(Video.id == ad.video_id).first()
        context.append({
            "ad_id": ad.id,
            "video_id": ad.video_id,
            "video_code": video.video_code if video else None,
            "plan_name": ad.plan_name,
            "content_direction": ad.content_direction,
            "metrics": metrics_for(ad),
            "feedback": ad.feedback,
            "current_status": ad.status,
        })
    return context


def fallback_plan(context: list[dict]) -> dict:
    """规则兜底计划：按指标阈值给出放量/优化/停投判断，不依赖 LLM。"""
    actions = []
    risks = []
    for row in context:
        m = row["metrics"]
        if m["roi"] < 1 and m["spend"] > 0:
            decision = "stop_and_remake"
            risks.append({"video_id": row["video_id"], "reason": "ROI below 1"})
        elif m["roi"] >= 3:
            decision = "scale"
        else:
            decision = "observe_and_optimize"
        actions.append({
            "tool": "update_ad_status",
            "video_id": row["video_id"],
            "ad_id": row["ad_id"],
            "decision": decision,
            "reason": f"ROI={m['roi']}",
            "priority": "P0" if decision == "stop_and_remake" else "P1",
        })
        if m["bounce_rate_2s"] > 50:
            actions.append({
                "tool": "create_video_task",
                "video_id": row["video_id"],
                "decision": "rewrite_hook",
                "reason": "2-second bounce rate above 50%",
                "priority": "P0",
            })
    return {
        "goal": "autonomous ad review",
        "summary": f"Analyzed {len(context)} ad records and generated an execution plan.",
        "risks": risks,
        "actions": actions,
        "requires_confirmation": True,
    }


def _parse_llm_plan(text: str) -> dict:
    """从 LLM 返回文本中解析 JSON 计划。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _call_llm_plan(goal: str, context: list[dict]) -> dict:
    """用 ChatOpenAI 接 DeepSeek 生成执行计划；无 Key / 失败时返回空 dict。"""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-placeholder" or "在这里" in OPENAI_API_KEY:
        return {}
    prompt = f"""
You are an autonomous short-video e-commerce operations agent.
Goal: {goal}
You can only choose tools from this allowlist:
1. update_ad_status: update an ad record status based on evidence.
2. create_video_task: update an existing video task with a concrete optimization task.
3. create_review: create a review record.
4. save_knowledge: save a reusable rule or lesson.
Return JSON only:
{{
  "summary": "",
  "risks": [],
  "actions": [{{"tool":"", "ad_id":0, "video_id":0, "reason":"", "payload":{{}}, "priority":"P0|P1|P2"}}],
  "requires_confirmation": true
}}
Rules: use only ids present in the data; do not invent metrics; never delete data; all actions require user confirmation.
Data:\n{json.dumps(context, ensure_ascii=False)}
"""
    try:
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model=OPENAI_MODEL,
            temperature=0.7,
            max_tokens=4000,
        )
        response = llm.invoke(prompt)
        plan = _parse_llm_plan(response.content or "")
        if isinstance(plan.get("actions"), list):
            return plan
    except Exception:
        pass
    return {}


# ---------- LangGraph 节点 ----------

def _collect_context_node(state: AgentState, db: Session) -> dict:
    context = collect_context(db, state.get("video_id"))
    return {"context": context}


def _plan_node(state: AgentState, db: Session) -> dict:
    context = state.get("context") or []
    goal = state.get("goal") or "Review all ad data and create prioritized optimization actions"
    if not context:
        return {"plan": {"status": "empty", "message": "没有可分析的投流数据"}, "status": "empty", "actions": []}
    plan = _call_llm_plan(goal, context)
    if not plan or not isinstance(plan.get("actions"), list):
        plan = fallback_plan(context)
    plan["context"] = context
    plan["generated_at"] = datetime.now().isoformat()
    plan["status"] = "planned"
    return {
        "plan": plan,
        "actions": plan.get("actions") or [],
        "generated_at": plan["generated_at"],
        "status": "planned",
    }


def _approval_node(state: AgentState) -> dict:
    """人工审批节点：图在此分叉。未审批则返回计划等待确认；已审批则放行执行。"""
    return {}


def _initial_route(state: AgentState) -> str:
    """入口路由：/execute 直接带 actions 跳审批；/run 先收集数据再规划。"""
    return "approve" if state.get("actions") else "collect"


def _approval_route(state: AgentState) -> Literal["execute", "end"]:
    return "execute" if state.get("approved_indexes") else "end"


def _execute_tools_node(state: AgentState, db: Session) -> dict:
    actions = state.get("actions") or []
    approved_indexes = state.get("approved_indexes") or []
    executed = []
    skipped = []
    for index in approved_indexes:
        if index < 0 or index >= len(actions):
            skipped.append({"index": index, "reason": "invalid action index"})
            continue
        action = actions[index]
        tool = action.get("tool")
        if tool == "update_ad_status":
            ad = db.query(AdData).filter(AdData.id == action.get("ad_id")).first()
            if not ad:
                skipped.append({"index": index, "reason": "ad record not found"})
                continue
            decision = action.get("decision") or action.get("payload", {}).get("decision") or "observe_and_optimize"
            ad.status = {"stop_and_remake": "已停投", "scale": "投放中", "observe_and_optimize": "观察优化"}.get(decision, "观察优化")
            ad.review_suggestion = action.get("reason") or ad.review_suggestion
            executed.append({"index": index, "tool": tool, "id": ad.id, "result": ad.status})
        elif tool == "create_video_task":
            video = db.query(Video).filter(Video.id == action.get("video_id")).first()
            if not video:
                skipped.append({"index": index, "reason": "video record not found"})
                continue
            note = action.get("reason") or action.get("payload", {}).get("task") or "Agent optimization task"
            video.notes = f"{video.notes or ''}\n[Agent task] {note}".strip()
            video.priority = action.get("priority") or "P0"
            video.material_status = "待优化"
            executed.append({"index": index, "tool": tool, "id": video.id, "result": "video task updated"})
        elif tool == "create_review":
            payload = action.get("payload") or {}
            review = Review(
                review_period=payload.get("review_period") or "Agent review",
                product_id=payload.get("product_id"),
                video_id=action.get("video_id"),
                product_performance=payload.get("summary"),
                problem_analysis=action.get("reason"),
                next_action=json.dumps(payload.get("actions") or [], ensure_ascii=False),
                owner="Review agent",
                status="待复盘",
                priority=action.get("priority") or "P1",
            )
            db.add(review)
            db.flush()
            executed.append({"index": index, "tool": tool, "id": review.id, "result": "review created"})
        elif tool == "save_knowledge":
            payload = action.get("payload") or {}
            knowledge = Knowledge(
                knowledge_code=f"KA{datetime.now().strftime('%m%d%H%M%S')}{index}",
                category="复盘经验",
                source="自主复盘智能体",
                applicable_scene=payload.get("scene") or "投流复盘",
                content_summary=payload.get("content") or action.get("reason") or "Agent knowledge",
                prompt_version="agent-graph-v1",
                usage_effect="待验证",
                updater="复盘智能体",
                status="待验证",
                priority=action.get("priority") or "P1",
                review_status="待审核",
                target_user="运营团队",
                notes="用户确认后写入",
            )
            db.add(knowledge)
            db.flush()
            executed.append({"index": index, "tool": tool, "id": knowledge.id, "result": "knowledge saved"})
        else:
            skipped.append({"index": index, "reason": f"tool not allowed: {tool}"})
    db.commit()
    return {"executed": executed, "skipped": skipped}


def _finalize_node(state: AgentState) -> dict:
    executed = state.get("executed") or []
    skipped = state.get("skipped") or []
    return {
        "status": "finalized",
        "summary": f"执行完成：成功 {len(executed)} 个动作，跳过 {len(skipped)} 个。",
    }


def build_graph(db: Session):
    """构建 LangGraph 状态图：收集 → 规划 → 人工审批 → 执行 → 收尾。"""
    graph = StateGraph(AgentState)
    graph.add_node("collect_context", lambda s: _collect_context_node(s, db))
    graph.add_node("plan", lambda s: _plan_node(s, db))
    graph.add_node("approval", _approval_node)
    graph.add_node("execute_tools", lambda s: _execute_tools_node(s, db))
    graph.add_node("finalize", _finalize_node)

    graph.add_conditional_edges(START, _initial_route, {"collect": "collect_context", "approve": "approval"})
    graph.add_edge("collect_context", "plan")
    graph.add_edge("plan", "approval")
    graph.add_conditional_edges("approval", _approval_route, {"execute": "execute_tools", "end": END})
    graph.add_edge("execute_tools", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


def run_agent(db: Session, goal: str, video_id: int | None = None) -> dict:
    """跑到审批节点，返回计划（与旧 create_plan 返回结构一致）。"""
    state = build_graph(db).invoke({"goal": goal, "video_id": video_id})
    if state.get("status") == "empty":
        return {"status": "empty", "message": "没有可分析的投流数据", "context": []}
    return state.get("plan") or {}


def execute_agent(db: Session, plan: dict, approved_indexes: list[int]) -> dict:
    """带上已审批动作继续执行（与旧 execute_plan 返回结构一致）。"""
    state = build_graph(db).invoke({
        "actions": plan.get("actions") or [],
        "approved_indexes": approved_indexes,
    })
    return {
        "status": "executed",
        "executed": state.get("executed") or [],
        "skipped": state.get("skipped") or [],
    }
