"""LangGraph 版投流数据复盘智能体。

目标：自动扫描"还没有复盘建议"的投流数据，逐条计算指标、识别异常、
生成复盘结论与优化建议并写回（ad_data.review_suggestion + 复盘记录表）。
支持一键触发与后台定时自动巡检，建议直接给出，无需人工审批。

图结构（5 个节点）：
  START → load_data → analyze → review → save → record → END
  1. load_data  扫描未复盘投流记录（review_suggestion 为空）
  2. analyze    规则计算指标/异常/决策（不调 LLM）
  3. review     ChatOpenAI(DeepSeek) 生成复盘结论与建议；无 Key 时规则兜底
  4. save       写回复盘建议 + 创建复盘记录
  5. record     写入 agent_runs 运行日志

对外接口：
  run_ad_review_agent(db, limit)  → 跑完整图，返回每条投流数据的复盘结果
  start_review_scheduler()        → 启动后台定时自动复盘
"""

import json
import os
import operator
import re
import threading
from datetime import datetime
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import AdData, AgentMemory, AgentRun, Content, Knowledge, Product, Review, Script, Video
from services.analysis import calculate_metrics, generate_decision, judge_anomaly

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

REVIEW_INTERVAL_MINUTES = int(os.getenv("REVIEW_INTERVAL_MINUTES", "10"))
PASS_SCORE = 60          # 自检及格线
MAX_GENERATE_ATTEMPTS = 3  # 自检不通过最多重新生成次数

_review_lock = threading.Lock()
_review_stop = threading.Event()


class AdReviewState(TypedDict, total=False):
    ad_records: list
    results: list
    trace: Annotated[list, operator.add]
    message: str
    run_log_id: int | None
    saved_count: int
    processed: int


def scan_unreviewed_ads(db: Session, limit: int | None = None, force: bool = False) -> list[AdData]:
    """扫描待复盘投流记录；force=True 时忽略"已复盘"标记，全部重新复盘。"""
    query = db.query(AdData).order_by(AdData.id.asc())
    if not force:
        query = query.filter(or_(
            AdData.review_suggestion.is_(None),
            AdData.review_suggestion == "",
        ))
    rows = query.all()

    # 自主决策：优先复盘"差"的投流（花费>0 且 ROI<1 或 2秒跳出率>50 最优先），
    # 其次按 ROI 从低到高（越差越先复盘），再按 ID 稳定排序。
    def _priority(ad: AdData):
        roi = float(ad.roi or 0)
        critical = 1 if (ad.spend and float(ad.spend) > 0 and (roi < 1 or float(ad.bounce_rate_2s or 0) > 50)) else 0
        return (0 - critical, roi, ad.id)

    rows.sort(key=_priority)
    return rows if not limit else rows[:limit]


def build_review_prompt(record: dict) -> str:
    m = record.get("metrics") or {}
    issues = record.get("issues") or []
    memory_text = ""
    if record.get("memory_context"):
        memory_text = "\n\n历史经验参考（用户反馈的记忆）：\n" + record["memory_context"]
    knowledge_text = ""
    if record.get("knowledge_context"):
        knowledge_text = "\n\n知识库已生效经验（人工认可沉淀）：\n" + record["knowledge_context"]
    return f"""你是一位千川投流数据复盘专家。请对下面这条投流记录进行复盘，只输出 JSON，不要 Markdown。

视频编号：{record.get('video_code') or '-'}
内容方向：{record.get('content_direction') or '-'}
关键指标：ROI={m.get('roi')}，CTR={m.get('ctr')}%，购物车到成交转化率={m.get('conversion_rate')}%，CPA={m.get('cpa')}，2秒跳出率={m.get('bounce_rate_2s')}%，完播率={m.get('completion_rate')}%
规则异常判断：{json.dumps(issues, ensure_ascii=False)}
规则决策：{record.get('decision')}
用户反馈：{record.get('feedback') or '无'}
{memory_text}
{knowledge_text}

输出前先自检，按以下评分标准给自己打分（0-100）：
- 评级/决策与数据一致（0-30分）
- 问题判断具体、有依据（0-25分）
- 优化建议可落地、可执行（0-25分）
- 总体判断简明准确（0-20分）
低于 60 分必须改进后重新输出。

输出 JSON：
{{"rating": "优秀/良好/一般/较差", "summary": "一两句话的总体判断", "problems": ["问题1", "问题2"], "suggestions": ["优化建议1", "优化建议2"], "decision": "放量/小幅优化/观察调整/停投重做", "self_score": 0-100, "self_reason": "自检理由"}}"""


def _recent_memories(db: Session, memory_type: str, video_id: int | None, limit: int = 3) -> list[AgentMemory]:
    """取最近的记忆；有视频时优先取同视频的经验，不足再补最近的通用经验。"""
    query = db.query(AgentMemory).filter(AgentMemory.memory_type == memory_type)
    if not video_id:
        return query.order_by(AgentMemory.id.desc()).limit(limit).all()
    same = query.filter(AgentMemory.video_id == video_id).order_by(AgentMemory.id.desc()).limit(limit).all()
    if len(same) >= limit:
        return same
    seen = {m.id for m in same}
    others = db.query(AgentMemory).filter(AgentMemory.memory_type == memory_type).order_by(AgentMemory.id.desc()).limit(limit).all()
    for m in others:
        if m.id not in seen:
            same.append(m)
            seen.add(m.id)
        if len(same) >= limit:
            break
    return same


def _build_memory_context(db: Session, record: dict) -> str:
    """把历史"认可/不认可"经验拼成提示词上下文，指导本次生成。"""
    video_id = record.get("video_id")
    lines = []
    for m in _recent_memories(db, "认可", video_id):
        lines.append(
            f"[认可经验] 评级{m.rating or '-'}，决策{m.decision or '-'}，"
            f"结论：{m.summary or ''}，建议：{m.suggestions or ''}"
        )
    for m in _recent_memories(db, "不认可", video_id):
        lines.append(
            f"[不认可经验] 评级{m.rating or '-'}，决策{m.decision or '-'}，"
            f"结论：{m.summary or ''}。用户不认可这类结论，请避免输出类似内容"
        )
    return "\n".join(lines)


def _build_knowledge_context(db: Session, limit: int = 3) -> str:
    """把最近沉淀为"已生效"的复盘经验知识拼成上下文，指导本次生成。"""
    rows = db.query(Knowledge).filter(
        Knowledge.category == "复盘经验",
        Knowledge.status == "已生效",
    ).order_by(Knowledge.id.desc()).limit(limit).all()
    lines = []
    for k in rows:
        effect = (k.usage_effect or "").strip()
        line = f"[已沉淀知识] {k.source or '知识库'}：{k.content_summary or ''}"
        if effect:
            line += f"（建议：{effect[:200]}）"
        lines.append(line)
    return "\n".join(lines)


def _fallback_self_score(review: dict) -> int:
    """规则兜底的自检评分：按字段完整度打分。"""
    score = 100
    if not review.get("rating"):
        score -= 20
    if not review.get("summary") or len(str(review.get("summary"))) < 10:
        score -= 15
    if not review.get("problems"):
        score -= 15
    if not review.get("suggestions") or len(review.get("suggestions")) < 2:
        score -= 15
    if not review.get("decision"):
        score -= 10
    return max(0, score)


def fallback_review(record: dict) -> dict:
    """规则兜底：无 Key 或 LLM 失败时，按指标阈值生成复盘结论。"""
    m = record.get("metrics") or {}
    roi = m.get("roi") or 0
    rating = "优秀" if roi >= 3 else "良好" if roi >= 1.5 else "一般" if roi >= 1 else "较差"
    issues = record.get("issues") or []
    problems = [i.get("detail") or i.get("type") for i in issues if (i.get("detail") or i.get("type"))] or ["核心指标在可接受范围"]
    suggestions = [f"优先处理：{p}" for p in problems[:3]] or ["保持当前投放节奏，持续观察"]
    review = {
        "rating": rating,
        "summary": f"ROI={roi}，规则决策：{record.get('decision')}",
        "problems": problems,
        "suggestions": suggestions,
        "decision": record.get("decision"),
    }
    review["self_score"] = _fallback_self_score(review)
    review["self_reason"] = "规则生成：字段完整，指标与评级一致"
    return review


def _parse_json_text(text: str) -> dict:
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


def _call_llm_review(record: dict, feedback: str = "") -> dict:
    """ChatOpenAI 接 DeepSeek 生成复盘结论（带自检）；无 Key / 失败返回空 dict。"""
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-placeholder" or "在这里" in OPENAI_API_KEY:
        return {}
    try:
        prompt = build_review_prompt(record)
        if feedback:
            prompt += f"\n\n上次自检未通过，请改进后再输出：{feedback}"
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
            model=OPENAI_MODEL,
            temperature=0.3,
            max_tokens=2000,
            timeout=60,
        )
        response = llm.invoke(prompt)
        plan = _parse_json_text(response.content or "")
        if plan.get("suggestions"):
            return plan
    except Exception:
        pass
    return {}


def _generate_with_self_check(record: dict) -> dict:
    """生成复盘结论并自检：self_score 低于及格线则带着反馈重新生成，最多 3 次。"""
    review = None
    feedback = ""
    for attempt in range(MAX_GENERATE_ATTEMPTS):
        candidate = _call_llm_review(record, feedback)
        if not candidate:
            candidate = fallback_review(record)
        score = candidate.get("self_score")
        if isinstance(score, (int, float)) and score < PASS_SCORE and attempt < MAX_GENERATE_ATTEMPTS - 1:
            feedback = f"你上次的自检评分只有 {score} 分：{candidate.get('self_reason', '')}。请针对性改进后再输出一版。"
            continue
        review = candidate
        break
    return review or fallback_review(record)


def _trace_step(state: AdReviewState, tool: str, args: dict, result: dict, index: int = 1) -> dict:
    return {
        "round": len(state.get("trace") or []) + index,
        "tool": tool,
        "args": args,
        "result": result,
        "status": "success",
    }


def build_graph(db: Session, limit: int | None = None, force: bool = False):
    def load_data_node(state):
        ads = scan_unreviewed_ads(db, limit, force)
        records = []
        for ad in ads:
            video = db.query(Video).filter(Video.id == ad.video_id).first() if ad.video_id else None
            records.append({
                "ad": ad,
                "video": video,
                "ad_id": ad.id,
                "video_id": ad.video_id,
                "video_code": video.video_code if video else None,
                "content_direction": ad.content_direction,
                "feedback": ad.feedback,
                "current_status": ad.status,
            })
        message = f"扫描到 {len(records)} 条未复盘的投流数据，开始复盘" if records else "没有未复盘的投流数据，无需复盘"
        return {
            "ad_records": records,
            "message": message,
            "trace": [_trace_step(state, "load_data", {"limit": limit}, {"count": len(records)})],
        }

    def analyze_node(state):
        records = []
        steps = []
        for i, rec in enumerate(state["ad_records"], 1):
            ad = rec["ad"]
            rec["metrics"] = calculate_metrics(ad)
            rec["issues"] = judge_anomaly(ad, rec["video"]) if rec["video"] else []
            rec["decision"] = generate_decision(ad, rec["issues"])
            records.append(rec)
            steps.append(_trace_step(state, "analyze_metrics", {"ad_id": ad.id}, {
                "roi": rec["metrics"].get("roi"),
                "issues": len(rec["issues"]),
                "decision": rec["decision"],
            }, index=i))
        return {"ad_records": records, "trace": steps}

    def review_node(state):
        results = []
        for rec in state["ad_records"]:
            rec["memory_context"] = _build_memory_context(db, rec)
            rec["knowledge_context"] = _build_knowledge_context(db)
            review = _generate_with_self_check(rec)
            rec["review"] = review
            results.append({
                "ad_id": rec["ad_id"],
                "video_id": rec["video_id"],
                "video_code": rec["video_code"],
                "content_direction": rec["content_direction"],
                "metrics": rec["metrics"],
                "issues": rec["issues"],
                "review": review,
            })
        return {
            "results": results,
            "trace": [_trace_step(state, "review", {}, {"count": len(results)}, index=len(state.get("trace") or []) + 1)],
        }

    def save_node(state):
        for rec in state["ad_records"]:
            ad = rec["ad"]
            review = rec.get("review") or fallback_review(rec)
            ad.review_suggestion = json.dumps({
                "rating": review.get("rating"),
                "summary": review.get("summary"),
                "suggestions": review.get("suggestions", []),
            }, ensure_ascii=False)
            if rec.get("issues"):
                ad.anomaly = json.dumps(rec["issues"], ensure_ascii=False)

            # 通过 投流 → 视频 → 脚本 → 商品/内容 反查关联信息，让复盘记录可追溯
            video = rec.get("video")
            product = None
            content = None
            if video and video.script_id:
                script = db.query(Script).filter(Script.id == video.script_id).first()
                if script:
                    product = db.query(Product).filter(Product.id == script.product_id).first() if script.product_id else None
                    content = db.query(Content).filter(Content.id == script.content_id).first() if script.content_id else None
            ad_perf = dict(rec.get("metrics") or {})
            ad_perf["ad_id"] = ad.id
            ad_perf["plan_name"] = ad.plan_name

            db.add(Review(
                review_period=f"{datetime.now():%Y-%m-%d} 投流复盘",
                ad_id=ad.id,
                video_id=ad.video_id,
                product_id=product.id if product else None,
                product_performance=f"商品：{product.name}（{product.product_code}）" if product else None,
                content_performance=f"内容方向：{content.remix_angles or content.hook}" if content else None,
                video_performance=(f"视频：{video.video_code}，素材状态：{video.material_status}，发布状态：{video.publish_status}，质检：{video.quality_items or '无'}" if video else "投流数据未关联视频"),
                ad_performance=json.dumps(ad_perf, ensure_ascii=False),
                problem_analysis="；".join(review.get("problems") or []),
                next_action="；".join(review.get("suggestions") or []),
                owner="投流复盘智能体",
                status="待处理",
                priority="P1",
                review_level=review.get("rating"),
                decision=review.get("decision"),
                summary=review.get("summary"),
            ))
        db.commit()
        return {
            "saved_count": len(state["ad_records"]),
            "trace": [_trace_step(state, "save_review", {}, {"count": len(state["ad_records"])}, index=len(state.get("trace") or []) + 1)],
        }

    def record_node(state):
        log = AgentRun(
            run_type="ad_review",
            status="completed",
            products_processed=len(state.get("results") or []),
            summary=json.dumps({"message": state.get("message", ""), "results": state.get("results", [])}, ensure_ascii=False, default=str),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return {
            "run_log_id": log.id,
            "processed": len(state.get("results") or []),
            "trace": [_trace_step(state, "record_log", {}, {"run_id": log.id, "processed": len(state.get("results") or [])}, index=len(state.get("trace") or []) + 1)],
        }

    def route_after_load(state):
        return "analyze" if state.get("ad_records") else "end"

    graph = StateGraph(AdReviewState)
    graph.add_node("load_data", load_data_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("review", review_node)
    graph.add_node("save", save_node)
    graph.add_node("record", record_node)
    graph.add_edge(START, "load_data")
    graph.add_conditional_edges("load_data", route_after_load, {"analyze": "analyze", "end": END})
    graph.add_edge("analyze", "review")
    graph.add_edge("review", "save")
    graph.add_edge("save", "record")
    graph.add_edge("record", END)
    return graph.compile()


def run_ad_review_agent(db: Session, limit: int | None = None, force: bool = False) -> dict:
    """跑完整图，返回每条投流数据的复盘结果（建议直接给出）。"""
    app = build_graph(db, limit, force)
    result = app.invoke({"ad_records": [], "results": [], "trace": [], "message": "", "run_log_id": None})
    return {
        "status": "completed",
        "message": result.get("message", ""),
        "processed": len(result.get("results") or []),
        "results": result.get("results") or [],
        "run_id": result.get("run_log_id"),
        "trace": result.get("trace") or [],
    }


def _safe_float(value):
    try:
        return round(float(value), 2) if value is not None else None
    except (TypeError, ValueError):
        return None


def _serialize_node_output(node: str, output: dict) -> dict:
    """把单个节点的 stream 输出转成前端节点卡片可渲染的 JSON。"""
    if node == "load_data":
        records = output.get("ad_records") or []
        items = []
        for rec in records:
            ad = rec.get("ad")
            video = rec.get("video")
            items.append({
                "ad_id": rec.get("ad_id"),
                "video_id": rec.get("video_id"),
                "video_code": getattr(video, "video_code", None) if video is not None else rec.get("video_code"),
                "content_direction": getattr(ad, "content_direction", None) if ad is not None else None,
                "spend": _safe_float(getattr(ad, "spend", None) if ad is not None else None),
                "revenue": _safe_float(getattr(ad, "revenue", None) if ad is not None else None),
            })
        return {"message": output.get("message", ""), "count": len(items), "items": items}

    if node == "analyze":
        records = output.get("ad_records") or []
        items = []
        for rec in records:
            metrics = rec.get("metrics") or {}
            items.append({
                "ad_id": rec.get("ad_id"),
                "video_code": rec.get("video_code"),
                "roi": metrics.get("roi"),
                "ctr": metrics.get("ctr"),
                "conversion_rate": metrics.get("conversion_rate"),
                "cpa": metrics.get("cpa"),
                "bounce_rate_2s": metrics.get("bounce_rate_2s"),
                "issues": len(rec.get("issues") or []),
                "decision": rec.get("decision"),
            })
        return {"count": len(items), "items": items}

    if node == "review":
        results = output.get("results") or []
        items = []
        for rec in results:
            review = rec.get("review") or {}
            items.append({
                "ad_id": rec.get("ad_id"),
                "video_code": rec.get("video_code"),
                "rating": review.get("rating"),
                "decision": review.get("decision"),
                "summary": review.get("summary"),
                "suggestions": review.get("suggestions") or [],
                "problems": review.get("problems") or [],
                "self_score": review.get("self_score"),
            })
        return {"count": len(items), "items": items}

    if node == "save":
        return {"saved_count": output.get("saved_count", 0)}

    if node == "record":
        return {"run_log_id": output.get("run_log_id"), "processed": output.get("processed", 0)}

    return {"note": "该节点无可展示数据"}


def stream_ad_review_agent(db: Session, limit: int | None = None, force: bool = False):
    """按 LangGraph 节点逐个产出真实输出（供前端节点卡片实时点亮）。

    每个节点完成后 yield：{"event": "node", "node": 节点名, "output": 可渲染数据}
    全部节点跑完后 yield：{"event": "complete", ...最终结果}
    """
    app = build_graph(db, limit, force)
    initial = {"ad_records": [], "results": [], "trace": [], "message": "", "run_log_id": None}
    final_state = {}
    for mode, data in app.stream(initial, stream_mode=["updates", "values"]):
        if mode == "updates":
            for node_name, node_output in data.items():
                yield {
                    "event": "node",
                    "node": node_name,
                    "output": _serialize_node_output(node_name, node_output),
                }
        else:
            final_state = data or {}
    yield {
        "event": "complete",
        "status": "completed",
        "message": final_state.get("message", ""),
        "processed": len(final_state.get("results") or []),
        "results": final_state.get("results") or [],
        "run_id": final_state.get("run_log_id"),
        "trace": final_state.get("trace") or [],
    }


def _scheduler_loop():
    while not _review_stop.wait(REVIEW_INTERVAL_MINUTES * 60):
        try:
            from database import SessionLocal
            db = SessionLocal()
            try:
                with _review_lock:
                    # 后台自动复盘：处理全部"未复盘"的投流数据（不再分批）
                    run_ad_review_agent(db, None)
            finally:
                db.close()
        except Exception:
            # 自动复盘失败不影响主服务
            pass


def start_review_scheduler():
    """启动后台定时自动复盘（守护线程；间隔<=0 则不启动）。"""
    if REVIEW_INTERVAL_MINUTES <= 0:
        return
    threading.Thread(target=_scheduler_loop, daemon=True, name="review-scheduler").start()


def trigger_ad_review_background(limit: int | None = None):
    """异步触发一轮投流复盘（供新增/导入投流数据后调用，不阻塞请求）。"""
    def _run():
        try:
            from database import SessionLocal
            db = SessionLocal()
            try:
                with _review_lock:
                    # 数据进来后自动复盘：处理全部"未复盘"的投流数据（不再分批）
                    run_ad_review_agent(db, None)
            finally:
                db.close()
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True, name="review-trigger").start()
