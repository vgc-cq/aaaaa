"""Autonomous review agent: plan -> approval -> tool execution."""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from models import AdData, Video, Review, Knowledge
from ai_workflow.workflow import call_ai, parse_ai_response


def metrics_for(ad: AdData) -> dict:
    spend = float(ad.spend or 0)
    revenue = float(ad.revenue or 0)
    orders = int(ad.orders or 0)
    cart_clicks = int(ad.cart_clicks or 0)
    impressions = int(ad.impressions or 0)
    clicks = int(ad.clicks or 0)
    return {
        "roi": round(revenue / spend, 2) if spend else 0,
        "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
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
            "content_direction": ad.content_direction,
            "metrics": metrics_for(ad),
            "feedback": ad.feedback,
            "current_status": ad.status,
        })
    return context


def fallback_plan(context: list[dict]) -> dict:
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


def create_plan(db: Session, goal: str, video_id: int | None = None) -> dict:
    context = collect_context(db, video_id)
    if not context:
        return {"status": "empty", "message": "No ad data available", "context": []}
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
    result = parse_ai_response(call_ai(prompt))
    if result.get("local_demo") or result.get("error") or result.get("parse_error") or not isinstance(result.get("actions"), list):
        result = fallback_plan(context)
    result["context"] = context
    result["generated_at"] = datetime.now().isoformat()
    result["status"] = "planned"
    return result


def execute_plan(db: Session, plan: dict, approved_indexes: list[int]) -> dict:
    actions = plan.get("actions") or []
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
            ad.status = {"stop_and_remake": "\u5df2\u505c\u6295", "scale": "\u6295\u653e\u4e2d", "observe_and_optimize": "\u89c2\u5bdf\u4f18\u5316"}.get(decision, "\u89c2\u5bdf\u4f18\u5316")
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
            video.material_status = "\u5f85\u4f18\u5316"
            executed.append({"index": index, "tool": tool, "id": video.id, "result": "video task updated"})
        elif tool == "create_review":
            payload = action.get("payload") or {}
            review = Review(review_period=payload.get("review_period") or "Agent review", product_id=payload.get("product_id"), video_id=action.get("video_id"), product_performance=payload.get("summary"), problem_analysis=action.get("reason"), next_action=json.dumps(payload.get("actions") or [], ensure_ascii=False), owner="Review agent", status="\u5f85\u590d\u76d8", priority=action.get("priority") or "P1")
            db.add(review)
            db.flush()
            executed.append({"index": index, "tool": tool, "id": review.id, "result": "review created"})
        elif tool == "save_knowledge":
            payload = action.get("payload") or {}
            knowledge = Knowledge(knowledge_code=f"KA{datetime.now().strftime('%m%d%H%M%S')}{index}", category="\u590d\u76d8\u7ecf\u9a8c", source="\u81ea\u4e3b\u590d\u76d8\u667a\u80fd\u4f53", applicable_scene=payload.get("scene") or "\u6295\u6d41\u590d\u76d8", content_summary=payload.get("content") or action.get("reason") or "Agent knowledge", prompt_version="review-agent-v3", usage_effect="\u5f85\u9a8c\u8bc1", updater="\u590d\u76d8\u667a\u80fd\u4f53", status="\u5f85\u9a8c\u8bc1", priority=action.get("priority") or "P1", review_status="\u5f85\u5ba1\u6838", target_user="\u8fd0\u8425\u56e2\u961f", notes="\u7528\u6237\u786e\u8ba4\u540e\u5199\u5165")
            db.add(knowledge)
            db.flush()
            executed.append({"index": index, "tool": tool, "id": knowledge.id, "result": "knowledge saved"})
        else:
            skipped.append({"index": index, "reason": f"tool not allowed: {tool}"})
    db.commit()
    return {"status": "executed", "executed": executed, "skipped": skipped}
