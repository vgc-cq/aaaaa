import json
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai_workflow.workflow import call_ai, parse_ai_response
from database import get_db
from models import AdData, Content, Knowledge, Product, Review, Script, Video
from schemas import ReviewCreate, ReviewOut

router = APIRouter()


@router.get("/", response_model=List[ReviewOut])
def list_reviews(skip: int = 0, limit: int = 500, db: Session = Depends(get_db)):
    return db.query(Review).order_by(Review.id.asc()).offset(skip).limit(limit).all()


@router.get("/{review_id}", response_model=ReviewOut)
def get_review(review_id: int, db: Session = Depends(get_db)):
    item = db.query(Review).filter(Review.id == review_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review not found")
    return item


@router.post("/", response_model=ReviewOut)
def create_review(item: ReviewCreate, db: Session = Depends(get_db)):
    db_item = Review(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{review_id}", response_model=ReviewOut)
def update_review(review_id: int, item: ReviewCreate, db: Session = Depends(get_db)):
    db_item = db.query(Review).filter(Review.id == review_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Review not found")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{review_id}")
def delete_review(review_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Review).filter(Review.id == review_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(db_item)
    db.commit()
    return {"message": "deleted"}


class BatchDeleteIn(BaseModel):
    ids: list[int] = []


@router.post("/batch_delete")
def batch_delete_reviews(data: BatchDeleteIn, db: Session = Depends(get_db)):
    if not data.ids:
        raise HTTPException(status_code=400, detail="Select reviews first")
    items = db.query(Review).filter(Review.id.in_(data.ids)).all()
    if not items:
        raise HTTPException(status_code=400, detail="No reviews to delete")
    db.query(Review).filter(Review.id.in_(data.ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Deleted {len(items)} reviews"}


class ReviewAgentInput(BaseModel):
    scope: Optional[str] = "latest"
    review_id: Optional[int] = None
    product_id: Optional[int] = None
    video_id: Optional[int] = None
    review_period: Optional[str] = None
    save: Optional[bool] = False


def _num(value) -> float:
    if value is None:
        return 0.0
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else 0.0


def _calc_metrics(video: Video | None, ad: AdData | None) -> dict:
    play_count = int(getattr(ad, "play_count", 0) or 0)
    impressions = int(getattr(ad, "impressions", 0) or 0)
    clicks = int(getattr(ad, "clicks", 0) or 0)
    cart_clicks = int(getattr(ad, "cart_clicks", 0) or 0)
    spend = float(getattr(ad, "spend", 0) or 0)
    revenue = float(getattr(ad, "revenue", 0) or 0)
    orders = int(getattr(ad, "orders", 0) or 0)
    bounce_rate_2s = _num(getattr(ad, "bounce_rate_2s", None) or 0)
    completion_rate_5s = _num(getattr(ad, "completion_rate_5s", None) or 0)
    completion_rate = _num(getattr(ad, "completion_rate", None) or 0)
    ctr = round(clicks / impressions * 100, 2) if impressions else float(getattr(ad, "ctr", 0) or 0)
    cart_click_rate = round(cart_clicks / play_count * 100, 2) if play_count else 0
    cvr = round(orders / cart_clicks * 100, 2) if cart_clicks else 0
    roi = round(revenue / spend, 2) if spend else 0
    cpa = round(spend / orders, 2) if orders else None
    return {
        "play_count": play_count,
        "impressions": impressions,
        "clicks": clicks,
        "cart_clicks": cart_clicks,
        "spend": spend,
        "revenue": revenue,
        "orders": orders,
        "bounce_rate_2s": bounce_rate_2s,
        "completion_rate_5s": completion_rate_5s,
        "completion_rate": completion_rate,
        "ctr": ctr,
        "cart_click_rate": cart_click_rate,
        "cvr": cvr,
        "roi": roi,
        "cpa": cpa,
    }


def _decision_by_roi(roi: float) -> str:
    if roi >= 3:
        return "\u7ee7\u7eed\u653e\u91cf"
    if roi >= 1.5:
        return "\u5c0f\u5e45\u4f18\u5316\u540e\u52a0\u6295"
    if roi >= 1:
        return "\u89c2\u5bdf\u4f18\u5316"
    return "\u505c\u6295\u91cd\u505a"


def _next_knowledge_code(db: Session) -> str:
    rows = db.query(Knowledge.knowledge_code).filter(Knowledge.knowledge_code.like("K%")).all()
    max_num = 0
    for (code,) in rows:
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"K{max_num + 1:03d}"


def _object_dict(obj) -> dict:
    if not obj:
        return {}
    return {key: value for key, value in obj.__dict__.items() if key != "_sa_instance_state"}


@router.post("/agent/analyze")
def analyze_review_agent(payload: ReviewAgentInput, db: Session = Depends(get_db)):
    review = None
    if payload.review_id:
        review = db.query(Review).filter(Review.id == payload.review_id).first()
    if not review and payload.review_period:
        review = db.query(Review).filter(Review.review_period == payload.review_period).order_by(Review.id.desc()).first()
    if not review and payload.product_id:
        review = db.query(Review).filter(Review.product_id == payload.product_id).order_by(Review.id.desc()).first()
    if not review and payload.video_id:
        review = db.query(Review).filter(Review.video_id == payload.video_id).order_by(Review.id.desc()).first()
    if not review:
        review = db.query(Review).order_by(Review.id.desc()).first()
    if not review:
        raise HTTPException(status_code=404, detail="No review record available")

    product = db.query(Product).filter(Product.id == review.product_id).first() if review.product_id else None
    video = db.query(Video).filter(Video.id == review.video_id).first() if review.video_id else None
    ad = db.query(AdData).filter(AdData.video_id == review.video_id).order_by(AdData.id.desc()).first() if review.video_id else None
    script = db.query(Script).filter(Script.product_id == review.product_id).order_by(Script.id.desc()).first() if review.product_id else None
    content = db.query(Content).filter(Content.product_id == review.product_id).order_by(Content.id.desc()).first() if review.product_id else None

    metrics = _calc_metrics(video, ad)
    decision = _decision_by_roi(metrics["roi"])
    risk_flags = []
    if metrics["bounce_rate_2s"] > 50:
        risk_flags.append("\u524d3\u79d2\u94a9\u5b50\u504f\u5f31")
    if 0 < metrics["completion_rate"] < 15:
        risk_flags.append("\u5b8c\u64ad\u7387\u504f\u4f4e")
    if metrics["cart_clicks"] >= 50 and metrics["orders"] <= 3:
        risk_flags.append("\u8d2d\u7269\u8f66\u70b9\u51fb\u9ad8\u4f46\u6210\u4ea4\u5f31")
    if metrics["spend"] > 0 and metrics["roi"] < 1:
        risk_flags.append("\u6d88\u8017\u9ad8\u4e8e\u56de\u6536")

    prompt = f"""
You are a short-video e-commerce review agent. Return JSON only with these fields:
summary, risks, root_causes, actions, decision, next_review_focus, knowledge_points, key_metrics.
The decision must be one of: continue scaling, optimize then scale, observe and optimize, stop and remake.
Each action must include module, action, reason, priority.
Use the calculated metrics as the source of truth. Do not invent missing data.

Review period: {review.review_period}
Product: {json.dumps(_object_dict(product), ensure_ascii=False, default=str)}
Video: {json.dumps(_object_dict(video), ensure_ascii=False, default=str)}
Ad data: {json.dumps(_object_dict(ad), ensure_ascii=False, default=str)}
Script: {json.dumps(_object_dict(script), ensure_ascii=False, default=str)}
Content: {json.dumps(_object_dict(content), ensure_ascii=False, default=str)}
Calculated metrics: {json.dumps(metrics, ensure_ascii=False)}
Rule flags: {json.dumps(risk_flags, ensure_ascii=False)}
Existing notes: {review.product_performance or ''} | {review.content_performance or ''} | {review.video_performance or ''} | {review.ad_performance or ''} | {review.problem_analysis or ''} | {review.next_action or ''}
"""
    parsed = parse_ai_response(call_ai(prompt))
    if parsed.get("local_demo") or parsed.get("error") or parsed.get("parse_error"):
        parsed = {
            "summary": f"Rule-based review: {decision}",
            "risks": risk_flags,
            "root_causes": [],
            "actions": [{"module": "\u6295\u6d41", "action": decision, "reason": "\u57fa\u4e8e ROI \u548c\u5f02\u5e38\u89c4\u5219", "priority": "P1"}],
            "decision": decision,
            "next_review_focus": ["\u590d\u6838\u524d3\u79d2\u94a9\u5b50\u3001\u5b8c\u64ad\u7387\u548c\u6210\u4ea4\u8f6c\u5316"],
            "knowledge_points": risk_flags,
            "key_metrics": metrics,
        }

    return {
        "status": "ok",
        "data": {
            "review": {"id": review.id, "review_period": review.review_period, "product_id": review.product_id, "video_id": review.video_id, "owner": review.owner},
            "metrics": metrics,
            "rules": risk_flags,
            "decision": decision,
            "ai_output": parsed,
        },
    }


@router.post("/agent/save")
def save_review_agent(payload: dict, db: Session = Depends(get_db)):
    agent_data = payload.get("data") or {}
    review_info = agent_data.get("review") or {}
    metrics = agent_data.get("metrics") or {}
    ai_output = agent_data.get("ai_output") or {}
    decision = agent_data.get("decision") or metrics.get("decision") or "\u5f85\u5224\u65ad"

    review_id = review_info.get("id") or payload.get("review_id")
    review = db.query(Review).filter(Review.id == review_id).first() if review_id else None
    if not review:
        review = Review(review_period=review_info.get("review_period") or payload.get("review_period") or "AI\u81ea\u52a8\u590d\u76d8", product_id=review_info.get("product_id"), video_id=review_info.get("video_id"), owner=review_info.get("owner") or "AI\u590d\u76d8\u667a\u80fd\u4f53")
        db.add(review)

    summary = ai_output.get("summary") or f"\u81ea\u52a8\u590d\u76d8\u7ed3\u8bba\uff1a{decision}"
    risks = ai_output.get("risks") or []
    actions = ai_output.get("actions") or []
    root_causes = ai_output.get("root_causes") or []
    knowledge_points = ai_output.get("knowledge_points") or []

    review.product_performance = review.product_performance or summary
    review.content_performance = review.content_performance or json.dumps(risks, ensure_ascii=False)
    review.video_performance = review.video_performance or json.dumps(metrics, ensure_ascii=False)
    review.ad_performance = review.ad_performance or json.dumps(metrics, ensure_ascii=False)
    review.problem_analysis = review.problem_analysis or json.dumps(root_causes, ensure_ascii=False)
    review.next_action = review.next_action or json.dumps(actions, ensure_ascii=False)
    review.status = review.status or "\u5f85\u590d\u76d8"
    review.review_level = review.review_level or ("\u9ad8" if metrics.get("roi", 0) < 1 else "\u4e2d")
    review.priority = review.priority or "P1"

    knowledge_text = "\uff1b".join(str(x) for x in knowledge_points if str(x).strip()) if isinstance(knowledge_points, list) else str(knowledge_points or "")
    knowledge_saved = False
    if knowledge_text.strip():
        db.add(Knowledge(knowledge_code=_next_knowledge_code(db), category="\u590d\u76d8\u7ecf\u9a8c", source="\u590d\u76d8\u667a\u80fd\u4f53", applicable_scene=review.review_period or "\u6570\u636e\u590d\u76d8", content_summary=knowledge_text[:500], prompt_version="review-agent-v1", usage_effect=json.dumps({"decision": decision, "metrics": metrics}, ensure_ascii=False), updater=review.owner or "AI\u590d\u76d8\u667a\u80fd\u4f53", status="\u5f85\u9a8c\u8bc1", priority=review.priority or "P1", review_status="\u5f85\u5ba1\u6838", target_user="\u8fd0\u8425/\u6295\u6d41/\u5185\u5bb9\u56e2\u961f", notes="\u7531\u590d\u76d8\u667a\u80fd\u4f53\u81ea\u52a8\u6c89\u6dc0"))
        knowledge_saved = True

    db.commit()
    db.refresh(review)
    return {"message": "\u590d\u76d8\u5df2\u4fdd\u5b58\u5e76\u6c89\u6dc0\u77e5\u8bc6\u5e93" if knowledge_saved else "\u590d\u76d8\u5df2\u4fdd\u5b58", "review_id": review.id, "knowledge_saved": knowledge_saved, "decision": decision}


class BatchReviewAgentInput(BaseModel):
    limit: int = 100
    only_spend: bool = False


def _decision_label(roi: float) -> str:
    return _decision_by_roi(roi)


@router.post("/agent/batch_analyze")
def batch_analyze_review_agent(payload: BatchReviewAgentInput, db: Session = Depends(get_db)):
    """Analyze all available ad records without requiring a pre-created review row."""
    query = db.query(AdData).order_by(AdData.id.desc())
    if payload.only_spend:
        query = query.filter(AdData.spend > 0)
    ad_rows = query.limit(max(1, min(payload.limit, 500))).all()
    if not ad_rows:
        raise HTTPException(status_code=404, detail="No ad data available")

    items = []
    for ad in ad_rows:
        video = db.query(Video).filter(Video.id == ad.video_id).first()
        metrics = _calc_metrics(video, ad)
        items.append({
            "ad_id": ad.id,
            "video_id": ad.video_id,
            "video_code": getattr(video, "video_code", None),
            "content_direction": ad.content_direction,
            "metrics": metrics,
            "decision": _decision_label(metrics["roi"]),
            "feedback": ad.feedback,
        })

    items.sort(key=lambda item: (item["metrics"].get("roi", 0), item["metrics"].get("revenue", 0)), reverse=True)
    decision_counts = {}
    for item in items:
        key = item["decision"]
        decision_counts[key] = decision_counts.get(key, 0) + 1

    batch_prompt = f"""
You are a short-video e-commerce operations director agent.
Analyze this batch of ad records and return JSON only with:
summary, overall_risks, priorities, scaling_candidates, stop_candidates, next_actions, knowledge_points.
Each priority/action must include video_id or video_code, reason, and priority.
Use the calculated metrics as truth. Do not invent missing values.

Records:
{json.dumps(items, ensure_ascii=False, default=str)}
"""
    ai_output = parse_ai_response(call_ai(batch_prompt))
    if ai_output.get("local_demo") or ai_output.get("error") or ai_output.get("parse_error"):
        ai_output = {
            "summary": f"Batch analysis completed: {len(items)} ad records analyzed.",
            "overall_risks": ["Low ROI records require creative or targeting optimization."],
            "priorities": items[:3],
            "scaling_candidates": [x for x in items if x["metrics"]["roi"] >= 3],
            "stop_candidates": [x for x in items if x["metrics"]["roi"] < 1],
            "next_actions": [
                {"video_id": x["video_id"], "reason": x["decision"], "priority": "P1" if x["metrics"]["roi"] < 1 else "P2"}
                for x in items[:5]
            ],
            "knowledge_points": ["Use ROI, completion rate, bounce rate and cart-to-order conversion together for decisions."],
        }

    return {
        "status": "ok",
        "data": {
            "total": len(items),
            "decision_counts": decision_counts,
            "items": items,
            "ai_output": ai_output,
        },
    }


@router.post("/agent/batch_save")
def batch_save_review_agent(payload: dict, db: Session = Depends(get_db)):
    data = payload.get("data") or {}
    output = data.get("ai_output") or {}
    items = data.get("items") or []
    summary = output.get("summary") or f"Batch review analyzed {data.get('total', len(items))} ad records."
    risks = output.get("overall_risks") or []
    actions = output.get("next_actions") or []
    knowledge_points = output.get("knowledge_points") or []
    review = Review(
        review_period=payload.get("review_period") or "\u4eca\u65e5\u6295\u6d41\u6279\u91cf\u590d\u76d8",
        product_performance="Batch ad review generated by the review agent.",
        content_performance=json.dumps(risks, ensure_ascii=False),
        video_performance=json.dumps(items[:20], ensure_ascii=False),
        ad_performance=json.dumps(data.get("decision_counts") or {}, ensure_ascii=False),
        problem_analysis=json.dumps(risks, ensure_ascii=False),
        next_action=json.dumps(actions, ensure_ascii=False),
        owner="\u590d\u76d8\u667a\u80fd\u4f53",
        status="\u5f85\u590d\u76d8",
        priority="P1",
        review_level="\u9ad8" if any(x.get("metrics", {}).get("roi", 0) < 1 for x in items) else "\u4e2d",
    )
    db.add(review)
    knowledge_text = "\uff1b".join(str(x) for x in knowledge_points if str(x).strip()) if isinstance(knowledge_points, list) else str(knowledge_points or "")
    if knowledge_text:
        db.add(Knowledge(
            knowledge_code=_next_knowledge_code(db),
            category="\u590d\u76d8\u7ecf\u9a8c",
            source="\u590d\u76d8\u667a\u80fd\u4f53",
            applicable_scene="\u6295\u6d41\u6279\u91cf\u590d\u76d8",
            content_summary=knowledge_text[:500],
            prompt_version="review-agent-v2",
            usage_effect=summary[:500],
            updater="\u590d\u76d8\u667a\u80fd\u4f53",
            status="\u5f85\u9a8c\u8bc1",
            priority="P1",
            review_status="\u5f85\u5ba1\u6838",
            target_user="\u8fd0\u8425/\u6295\u6d41/\u5185\u5bb9\u56e2\u961f",
            notes="\u6279\u91cf\u590d\u76d8\u81ea\u52a8\u6c89\u6dc0",
        ))
    db.commit()
    db.refresh(review)
    return {"message": "Batch review saved", "review_id": review.id, "knowledge_saved": bool(knowledge_text)}
