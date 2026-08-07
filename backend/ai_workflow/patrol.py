"""商品巡检智能体。

能力：
  1. 扫描商品库，找出"缺少内容拆解"或"缺少脚本分镜"的商品；
  2. 逐批调用脚本生成助手自动补齐（复用 LangGraph 六节点智能体）；
  3. 支持一键触发（POST /api/agents/patrol/run）和后台定时自动巡检；
  4. 每次巡检写入 agent_runs 日志表，前端可查看最近巡检记录。
"""

import json
import os
import threading

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import AgentRun, Content, Product, Script

router = APIRouter()

PATROL_BATCH_LIMIT = int(os.getenv("PATROL_BATCH_LIMIT", "3"))
PATROL_INTERVAL_MINUTES = int(os.getenv("PATROL_INTERVAL_MINUTES", "10"))

_patrol_lock = threading.Lock()
_scheduler_stop = threading.Event()

STATUS_ORDER = {"已选品": 0, "待评估": 1}


def has_real_key() -> bool:
    from ai_workflow.agents import API_KEY
    return bool(API_KEY) and API_KEY != "sk-placeholder" and "在这里" not in API_KEY


def scan_products_needing_work(db: Session, limit: int | None = None) -> list[dict]:
    """扫描缺少内容拆解或脚本分镜的商品（跳过已淘汰），按业务优先级排序。"""
    products = [p for p in db.query(Product).all() if p.status != "已淘汰"]
    products.sort(key=lambda p: (STATUS_ORDER.get(p.status, 9), p.id))
    pending = []
    for p in products:
        has_content = db.query(Content.id).filter(Content.product_id == p.id).first() is not None
        has_script = db.query(Script.id).filter(Script.product_id == p.id).first() is not None
        if has_content and has_script:
            continue
        missing = []
        if not has_content:
            missing.append("内容拆解")
        if not has_script:
            missing.append("脚本分镜")
        pending.append({
            "product_id": p.id,
            "product_code": p.product_code,
            "name": p.name,
            "status": p.status,
            "missing": missing,
        })
        if limit and len(pending) >= limit:
            break
    return pending


def _save_log(db: Session, run_type: str, status: str, processed: int, summary: dict) -> AgentRun:
    log = AgentRun(
        run_type=run_type,
        status=status,
        products_processed=processed,
        summary=json.dumps(summary, ensure_ascii=False),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def run_patrol(db: Session, limit: int | None = None) -> dict:
    """执行一轮巡检：扫描 → 逐商品调用脚本生成助手补齐 → 写运行日志。"""
    from ai_workflow.agents import script_gen_agent

    pending = scan_products_needing_work(db, limit)
    base = {"status": "completed", "results": []}

    if not pending:
        log = _save_log(db, "patrol", "completed", 0, {"message": "商品库数据齐全，无需处理", "pending": 0})
        return {
            **base,
            "mode": "scan",
            "processed": 0,
            "skipped": 0,
            "message": "商品库数据齐全，无需处理",
            "run_id": log.id,
            "created_at": log.created_at.isoformat(),
        }

    if not has_real_key():
        results = [{**item, "result": "skipped", "note": "未配置大模型 Key，仅扫描未执行"} for item in pending]
        log = _save_log(db, "patrol", "scan_only", 0, {"message": "未配置大模型 Key，仅扫描未执行", "pending": len(pending)})
        return {
            **base,
            "mode": "scan_only",
            "processed": 0,
            "skipped": len(pending),
            "results": results,
            "message": "未配置大模型 Key，仅扫描未执行",
            "run_id": log.id,
            "created_at": log.created_at.isoformat(),
        }

    results = []
    processed = 0
    for item in pending:
        try:
            res = script_gen_agent({"product_id": item["product_id"], "duration": 30}, db)
            trace = res.get("trace") or []
            saved_step = next((t for t in trace if t.get("tool") == "save_script" and t.get("status") == "success"), None)
            saved = saved_step.get("result") if saved_step else None
            results.append({
                **item,
                "result": "success",
                "script_codes": (saved or {}).get("script_codes", []) if isinstance(saved, dict) else [],
                "steps": len(trace),
            })
            processed += 1
        except Exception as e:
            results.append({**item, "result": "error", "error": str(e)})

    log = _save_log(db, "patrol", "completed", processed, {"mode": "llm", "pending": len(pending), "results": results})
    return {
        **base,
        "mode": "llm",
        "processed": processed,
        "skipped": len(pending) - processed,
        "message": f"巡检完成：处理 {processed} 个商品，跳过 {len(pending) - processed} 个",
        "results": results,
        "run_id": log.id,
        "created_at": log.created_at.isoformat(),
    }


def upgrade_placeholder_contents(db: Session, limit: int | None = None) -> int:
    """把历史"占位拆解"记录用智能体重新拆解完善（保持 content_id 关联不变，脚本分组不受影响）。"""
    from ai_workflow.agents import _tool_plan_script

    rows = db.query(Content).filter(or_(
        Content.notes.like("%自动补建%"),
        Content.remix_angles == "AI自动生成二创方向",
    )).order_by(Content.id.asc()).all()
    updated = 0
    for content in rows:
        product = db.query(Product).filter(Product.id == content.product_id).first()
        if not product:
            continue
        ctx = {"product": product, "product_id": product.id, "contents": [content], "duration": 30}
        plan = _tool_plan_script({}, ctx, db)
        if plan.get("error"):
            continue
        content.hook = plan.get("hook") or content.hook
        content.scene = plan.get("scene") or content.scene
        content.target_group = plan.get("target_group") or content.target_group
        content.structure = plan.get("structure") or content.structure
        content.conversion_point = plan.get("conversion_point") or content.conversion_point
        content.remix_angles = plan.get("remix_angles") or plan.get("title") or content.remix_angles
        content.status = "已拆解"
        content.notes = "由智能体重新拆解完善（原为自动补建占位，已升级）"
        updated += 1
        if limit and updated >= limit:
            break
    db.commit()
    return updated


@router.post("/patrol/run")
def patrol_run(limit: int = None, db: Session = Depends(get_db)):
    """一键巡检：立即扫描并补齐缺拆解/缺脚本的商品。"""
    return run_patrol(db, limit=int(limit) if limit else PATROL_BATCH_LIMIT)


@router.post("/patrol/upgrade")
def patrol_upgrade(limit: int = None, db: Session = Depends(get_db)):
    """把历史占位拆解记录重新拆解完善（保持脚本关联不变）。"""
    return {"updated": upgrade_placeholder_contents(db, limit=int(limit) if limit else 20)}


@router.get("/patrol/logs")
def patrol_logs(limit: int = 10, db: Session = Depends(get_db)):
    """最近巡检记录。"""
    rows = db.query(AgentRun).order_by(AgentRun.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "run_type": r.run_type,
            "status": r.status,
            "products_processed": r.products_processed,
            "summary": json.loads(r.summary) if r.summary else {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def _patrol_loop():
    while not _scheduler_stop.wait(PATROL_INTERVAL_MINUTES * 60):
        try:
            from database import SessionLocal
            db = SessionLocal()
            try:
                with _patrol_lock:
                    run_patrol(db, PATROL_BATCH_LIMIT)
            finally:
                db.close()
        except Exception:
            # 巡检失败不影响主服务
            pass


def start_patrol_scheduler():
    """启动后台定时巡检线程（守护线程，随进程退出；间隔<=0 则不启动）。"""
    if PATROL_INTERVAL_MINUTES <= 0:
        return
    thread = threading.Thread(target=_patrol_loop, daemon=True, name="patrol-scheduler")
    thread.start()
