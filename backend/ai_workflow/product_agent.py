"""商品智能体（LangGraph）：导入商品后自动完成 选品评分 → 内容拆解 → 脚本分镜。

图结构（5 个节点）：
  START → load_products → score → decide → process → record → END
  1. load_products  扫描需要处理的商品（未评分/缺拆解/缺脚本），已淘汰跳过，按业务价值排序
  2. score          规则评分（复用 services.scoring），自动定级 已选品/待评估/已淘汰
  3. decide         自主决策：仅已选品拆解分镜；高热优质商品优先且更详细，其余已选品标准拆解排后，待评估/已淘汰跳过
  4. process        每个商品一条"拆解→分镜"流水线，最多 3 路并发；拆完立即分镜，不等其他商品；
                    拆解/分镜都带自检（<60 重新生成，最多 3 次），写回内容+脚本（状态待审核）
  5. record         写入 agent_runs 运行日志

支持：
  - 商品导入后自动触发（products 路由调用 trigger_product_agent_background）
  - 后台每 PRODUCT_CHECK_INTERVAL_MINUTES 分钟巡检一次，防止漏处理
  - 记忆：脚本分镜审核通过后会沉淀到知识库（分类"拆解分镜"），生成时作为经验参考
"""

import json
import operator
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from models import AgentRun, Content, Knowledge, Product, Script
from services.scoring import score_product, status_for_score

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "deepseek-chat")

PRODUCT_BATCH_LIMIT = int(os.getenv("PRODUCT_BATCH_LIMIT", "3"))
PRODUCT_CHECK_INTERVAL_MINUTES = int(os.getenv("PRODUCT_CHECK_INTERVAL_MINUTES", "10"))
PASS_SCORE = 60
MAX_ATTEMPTS = 3

_product_lock = threading.Lock()
_product_stop = threading.Event()
_code_lock = threading.Lock()  # 多线程写库时保护编号分配，避免并发冲突


class ProductAgentState(TypedDict, total=False):
    product_records: list
    trace: Annotated[list, operator.add]
    message: str
    run_log_id: int | None
    saved: list


def _has_key() -> bool:
    return bool(OPENAI_API_KEY) and OPENAI_API_KEY != "sk-placeholder" and "在这里" not in OPENAI_API_KEY


def _trace_step(state: ProductAgentState, tool: str, args: dict, result: dict, index: int = 1) -> dict:
    return {
        "round": len(state.get("trace") or []) + index,
        "tool": tool,
        "args": args,
        "result": result,
        "status": "success" if "error" not in result else "error",
    }


def _next_code(db: Session, model, field_name: str, prefix: str) -> str:
    field = getattr(model, field_name)
    rows = db.query(field).filter(field.like(f"{prefix}%")).all()
    max_num = 0
    for (code,) in rows:
        s = str(code or "")
        m = re.fullmatch(rf"{prefix}(\d+)", s)
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"{prefix}{max_num + 1:03d}"


def scan_products_needing_work(db: Session, limit: int | None = None) -> list[dict]:
    """扫描需要处理的商品（未评分/缺拆解/缺脚本），已淘汰跳过，按业务价值排序。"""
    products = db.query(Product).order_by(Product.id.asc()).all()
    pending = []
    for p in products:
        needs_score = (p.score is None) or (float(p.score or 0) == 0)
        # 缺关键字段（人群/痛点/风险词）的商品需要先补全再评分，已淘汰的商品若字段不完整也重新评分
        needs_enrich = any(not str(getattr(p, f) or "").strip() for f in ("target_users", "pain_points", "risk_words"))
        if p.status == "已淘汰" and not needs_enrich and not needs_score:
            continue
        # 只有已选品才需要拆解+分镜；待评估/已淘汰只参与评分（不拆解分镜）
        is_selected = p.status == "已选品"
        has_content = db.query(Content.id).filter(Content.product_id == p.id).first() is not None
        has_script = db.query(Script.id).filter(Script.product_id == p.id).first() is not None
        need_breakdown = is_selected and (not has_content or not has_script)
        if not (needs_score or needs_enrich or need_breakdown):
            continue
        missing = []
        if needs_score:
            missing.append("选品评分")
        if needs_enrich:
            missing.append("字段补全")
        if need_breakdown:
            if not has_content:
                missing.append("内容拆解")
            if not has_script:
                missing.append("脚本分镜")
        pending.append({
            "product": p,
            "missing": missing,
            "needs_score": needs_score or needs_enrich,
            "needs_enrich": needs_enrich,
            "has_content": has_content,
            "has_script": has_script,
        })

    def _key(item: dict):
        p = item["product"]
        # 未评分的最优先，且最老的排前面（防止低 ID 商品一直被新商品挤掉）
        if item["needs_score"] or item["needs_enrich"]:
            return (0, p.id)
        # 已评分：只有已选品在拆解队列，按月销热度从高到低（高热优质商品优先拆解分镜）
        return (1, 0 - _sales_heat_value(p), 0 - float(p.score or 0), p.id)

    pending.sort(key=_key)
    return pending[:limit] if limit else pending


def _sales_heat_value(product: Product) -> float:
    """解析月销热度数字（如"月销12000+" → 12000），无数据返回 0。"""
    m = re.search(r"(\d+(?:\.\d+)?)", str(product.sales_heat or ""))
    return float(m.group(1)) if m else 0.0


def _enrich_product_fields(product: Product) -> bool:
    """用大模型补全缺失字段（人群/痛点/风险词），让评分更公平；无 Key 时规则兜底。"""
    missing = [f for f in ("target_users", "pain_points", "risk_words") if not str(getattr(product, f) or "").strip()]
    if not missing:
        return False
    if not _has_key():
        if "target_users" in missing:
            product.target_users = "年轻上班族、学生、家庭用户"
        if "pain_points" in missing:
            product.pain_points = f"{product.name or '商品'}使用不便、费时费力、体验不佳"
        if "risk_words" in missing:
            product.risk_words = "不得使用：治疗、减肥保证、绝对最低价、全网第一、100%纯天然"
        return True
    prompt = f"""你是短视频电商选品专家。请根据商品信息补全缺失字段，只输出 JSON，不要 Markdown。

商品：{product.name}（编号 {product.product_code}）
类目：{product.category or '未知'}
价格：{product.price_min}-{product.price_max}
卖点：{product.selling_points or ''}

只补全以下缺失字段：
{"、".join(missing)}

输出 JSON：
{{"target_users": "目标人群（2-3类，用顿号分隔）", "pain_points": "用户痛点（2-3个，用分号分隔）", "risk_words": "合规风险词约束（如：不得使用治疗、减肥保证等）"}}"""
    data = _call_llm(prompt)
    if data.get("target_users") and "target_users" in missing:
        t = data["target_users"]
        product.target_users = "、".join(str(x) for x in t) if isinstance(t, list) else str(t)
    if data.get("pain_points") and "pain_points" in missing:
        pp = data["pain_points"]
        product.pain_points = "；".join(str(x) for x in pp) if isinstance(pp, list) else str(pp)
    if data.get("risk_words") and "risk_words" in missing:
        rw = data["risk_words"]
        product.risk_words = "、".join(str(x) for x in rw) if isinstance(rw, list) else str(rw)
    return True


def _memory_context(db: Session) -> str:
    """读取知识库中审核通过沉淀的脚本经验（分类"拆解分镜"），作为生成参考。"""
    rows = db.query(Knowledge).filter(Knowledge.category == "拆解分镜").order_by(Knowledge.id.desc()).limit(3).all()
    if not rows:
        return ""
    lines = []
    for k in rows:
        lines.append(f"[已审核通过经验] {k.content_summary or ''}")
    return "\n".join(lines)


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


def _call_llm(prompt: str) -> dict:
    if not _has_key():
        return {}
    try:
        llm = ChatOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL, model=OPENAI_MODEL, temperature=0.3, max_tokens=3000)
        response = llm.invoke(prompt)
        return _parse_json_text(response.content or "")
    except Exception:
        return {}


# ---------- 内容拆解（带自检重试） ----------

def _fallback_breakdown(product: Product, detail_level: str) -> dict:
    name = product.name or "商品"
    breakdown = {
        "hook": f"{name}：直击日常使用痛点" if detail_level == "detailed" else f"{name}：简要场景切入",
        "scene": (product.category or "日常使用场景") if detail_level == "detailed" else "通用生活场景",
        "target_group": product.target_users or "年轻上班族/学生/家庭用户",
        "structure": "痛点开场-产品演示-效果对比-转化引导",
        "conversion_point": "引导收藏并点击购物车",
        "remix_angles": f"围绕{name}的差异化卖点做2-3个二创角度" if detail_level == "detailed" else "1个常规二创角度",
    }
    score = 100
    if not breakdown.get("hook"):
        score -= 20
    if not breakdown.get("target_group"):
        score -= 15
    breakdown["self_score"] = max(60, score)
    breakdown["self_reason"] = "规则兜底生成，字段完整"
    return breakdown


def _generate_breakdown_with_self_check(product: Product, detail_level: str, db: Session) -> dict:
    feedback = ""
    result = None
    for attempt in range(MAX_ATTEMPTS):
        candidate = _call_llm(_breakdown_prompt(product, detail_level, db, feedback))
        if not candidate:
            candidate = _fallback_breakdown(product, detail_level)
        score = candidate.get("self_score")
        if isinstance(score, (int, float)) and score < PASS_SCORE and attempt < MAX_ATTEMPTS - 1:
            feedback = f"上次自检 {score} 分：{candidate.get('self_reason', '')}，请针对性改进后再输出"
            continue
        result = candidate
        break
    return result or _fallback_breakdown(product, detail_level)


def _breakdown_prompt(product: Product, detail_level: str, db: Session, feedback: str) -> str:
    if detail_level == "detailed":
        mode_desc = "请做**详细**内容拆解：场景要具体（如通勤地铁、宿舍书桌），人群要具体，二创角度给2-3个。"
    elif detail_level == "standard":
        mode_desc = "请做**标准**内容拆解：场景、人群给出具体方向，二创角度给1-2个。"
    else:
        mode_desc = "请做**简要**内容拆解：给出核心钩子、场景、人群、结构和1个二创角度即可，内容从简。"
    memory = _memory_context(db)
    memory_text = f"\n\n历史已审核通过的脚本经验参考：\n{memory}" if memory else ""
    prompt = f"""你是短视频电商内容拆解专家。请为以下商品做内容拆解，只输出 JSON，不要 Markdown。

商品：{product.name}（编号 {product.product_code}）
类目：{product.category or '未知'}
价格：{product.price_min}-{product.price_max}
目标人群：{product.target_users or '未提供（请合理推断）'}
核心卖点：{product.selling_points or '未提供'}
用户痛点：{product.pain_points or '未提供'}
风险词约束：{product.risk_words or '无'}

{mode_desc}
{memory_text}

输出前自检（0-100分）：钩子有吸引力（30分）、场景/人群具体（25分）、结构与转化点清晰（25分）、合规无违规词（20分），低于60分必须改进。

输出 JSON：
{{"hook": "开头钩子", "scene": "具体场景", "target_group": "目标人群", "structure": "内容结构", "conversion_point": "转化引导", "remix_angles": "二创角度", "self_score": 0-100, "self_reason": "自检理由"}}
"""
    if feedback:
        prompt += f"\n\n上次自检未通过，请改进后重新输出：{feedback}"
    return prompt


# ---------- 脚本分镜（带自检重试） ----------

def _fallback_script(product: Product, content, detail_level: str) -> dict:
    name = product.name or "商品"
    hook = (content.get("hook") if content and isinstance(content, dict) else None) or f"{name}：从场景痛点开场"
    scene = (content.get("scene") if content and isinstance(content, dict) else None) or "日常使用场景"
    sp = [x.strip() for x in (product.selling_points or "便携、易清洗、制作快").replace("、", ",").split(",") if x.strip()][:2] or ["便携", "易清洗"]
    scenes = [
        {"time_range": "0-3秒", "scene_desc": f"{scene}场景开场，抛出痛点", "voiceover": hook, "subtitle": "多睡10分钟，也能喝上", "camera_move": "快速切入", "material_req": "场景道具", "ai_prompt": "scene opening, close-up, natural light"},
        {"time_range": "3-10秒", "scene_desc": f"展示核心功能：{'、'.join(sp)}", "voiceover": "30秒搞定，省时省心", "subtitle": "一键操作", "camera_move": "产品特写", "material_req": "商品实物", "ai_prompt": "product demo, clean background"},
        {"time_range": "10-18秒", "scene_desc": "使用/清洗便利演示", "voiceover": "用完之后，清洗也很简单", "subtitle": "易清洗更省事", "camera_move": "近景演示", "material_req": "使用过程", "ai_prompt": "easy clean close-up"},
        {"time_range": "18-25秒", "scene_desc": "对比同类/替代方案", "voiceover": "一杯奶茶钱，健康又划算", "subtitle": "性价比对比", "camera_move": "横移对比", "material_req": "价格字幕", "ai_prompt": "comparison shot"},
        {"time_range": "25-30秒", "scene_desc": "结尾引导转化", "voiceover": "喜欢的话先收藏，点下方购物车", "subtitle": "收藏+购物车", "camera_move": "定格收尾", "material_req": "商品主图", "ai_prompt": "hero shot, bright commercial style"},
    ]
    script = {
        "script_title": f"{name}｜30秒种草脚本",
        "total_duration": 30,
        "scenes": scenes[:5] if detail_level == "detailed" else (scenes[:4] if detail_level == "standard" else scenes[:3]),
        "publish_title": f"{name}，早八人也能轻松拥有",
        "tags": [product.category or "好物"],
        "quality_checklist": ["前3秒是否有痛点钩子", "是否展示核心卖点", "是否有转化引导", "是否避免绝对化宣传"],
    }
    script["self_score"] = 82
    script["self_reason"] = "规则兜底生成，分镜结构完整"
    return script


def _generate_script_with_self_check(product: Product, content, detail_level: str, db: Session) -> dict:
    feedback = ""
    result = None
    for attempt in range(MAX_ATTEMPTS):
        candidate = _call_llm(_script_prompt(product, content, detail_level, db, feedback))
        if not candidate:
            candidate = _fallback_script(product, content, detail_level)
        if isinstance(candidate.get("script"), dict):
            candidate = candidate["script"]
        scenes = candidate.get("scenes") or []
        score = candidate.get("self_score")
        if (not isinstance(scenes, list) or not scenes) and attempt < MAX_ATTEMPTS - 1:
            feedback = "上次输出缺少 scenes 分镜数组，请补全后重新输出"
            continue
        if isinstance(score, (int, float)) and score < PASS_SCORE and attempt < MAX_ATTEMPTS - 1:
            feedback = f"上次自检 {score} 分：{candidate.get('self_reason', '')}，请针对性改进后再输出"
            continue
        result = candidate
        break
    return result or _fallback_script(product, content, detail_level)


def _script_prompt(product: Product, content, detail_level: str, db: Session, feedback: str) -> str:
    memory = _memory_context(db)
    memory_text = f"\n\n历史已审核通过的脚本经验参考：\n{memory}" if memory else ""
    content_text = ""
    if content and isinstance(content, dict):
        content_text = (
            f"- 钩子：{content.get('hook', '')}\n"
            f"- 场景：{content.get('scene', '')}\n"
            f"- 结构：{content.get('structure', '')}\n"
            f"- 转化点：{content.get('conversion_point', '')}"
        )
    if detail_level == "detailed":
        scene_req = "生成5-6个镜头的完整分镜"
    elif detail_level == "standard":
        scene_req = "生成4-5个镜头的分镜"
    else:
        scene_req = "生成3-4个镜头的简要分镜"
    prompt = f"""你是短视频脚本创作专家。请为以下商品生成{scene_req}，只输出 JSON，不要 Markdown。

商品：{product.name}（编号 {product.product_code}）
卖点：{product.selling_points or '未提供'}
痛点：{product.pain_points or '未提供'}
目标人群：{product.target_users or '未提供'}
风险词约束：{product.risk_words or '无'}

内容拆解参考：
{content_text or '无'}
{memory_text}

要求：
1. 前3秒必须有强钩子，结尾必须有转化引导；
2. 每镜包含 time_range、scene_desc、voiceover、subtitle、camera_move、material_req、ai_prompt(英文)；
3. 不得出现风险词约束中的违规表达。

输出前自检（0-100分）：钩子力（25）、节奏/分镜完整（25）、卖点传达（20）、合规（15）、转化引导（15），低于60分必须改进。

输出 JSON：
{{"script_title": "...", "total_duration": 30, "scenes": [...], "publish_title": "...", "tags": ["..."], "quality_checklist": ["..."], "self_score": 0-100, "self_reason": "自检理由"}}
"""
    if feedback:
        prompt += f"\n\n上次自检未通过，请改进后重新输出：{feedback}"
    return prompt


# ---------- LangGraph 图 ----------

def _save_product_result(db: Session, product: Product, detail_level: str, breakdown: dict | None, script: dict | None, existing_content_id: int | None = None) -> tuple:
    """保存拆解+脚本（线程内独立 session；加锁串行写库，避免编号冲突与 SQLite 写锁）。"""
    with _code_lock:
        content_id = existing_content_id
        if breakdown:
            content = Content(
                content_code=_next_code(db, Content, "content_code", "C"),
                hook=breakdown.get("hook"),
                scene=breakdown.get("scene"),
                target_group=breakdown.get("target_group"),
                structure=breakdown.get("structure"),
                conversion_point=breakdown.get("conversion_point"),
                remix_angles=breakdown.get("remix_angles"),
                risk_points=product.risk_words,
                product_id=product.id,
                analyst="商品智能体",
                status="已拆解",
                priority="P1",
                notes=f"由商品智能体自动拆解（{'详细' if detail_level == 'detailed' else '标准'}），需人工复核",
            )
            db.add(content)
            db.flush()
            content_id = content.id
        script_codes = []
        if script:
            scenes = script.get("scenes") or []
            for sc in scenes:
                if not isinstance(sc, dict):
                    continue
                item = Script(
                    script_code=_next_code(db, Script, "script_code", "S"),
                    title=script.get("script_title") or f"{product.name} AI脚本",
                    product_id=product.id,
                    content_id=content_id,
                    shot_time=sc.get("time_range") or "待拆分",
                    scene_desc=sc.get("scene_desc") or "",
                    voiceover=sc.get("voiceover") or "",
                    subtitle=sc.get("subtitle") or "",
                    camera_move=sc.get("camera_move") or "",
                    material_req=sc.get("material_req") or "",
                    ai_prompt=sc.get("ai_prompt") or "",
                    review_status="待审核",
                    owner="脚本编导",
                    priority="P1",
                    notes="由商品智能体生成，需人工审核",
                )
                db.add(item)
                db.flush()
                script_codes.append(item.script_code)
        db.commit()
        return content_id, script_codes


def build_graph(db: Session, limit: int | None = None):
    def load_products_node(state):
        pending = scan_products_needing_work(db, limit)
        message = f"扫描到 {len(pending)} 个需要处理的商品" if pending else "商品库无需处理（均已评分并有拆解和脚本）"
        return {
            "product_records": pending,
            "message": message,
            "trace": [_trace_step(state, "load_products", {"limit": limit}, {"count": len(pending), "products": [p["product"].product_code for p in pending]})],
        }

    def score_node(state):
        records = []
        steps = []
        for i, rec in enumerate(state["product_records"], 1):
            p = rec["product"]
            if rec["needs_score"] or rec["needs_enrich"]:
                enriched = _enrich_product_fields(p)
                result = score_product(p)
                p.score = result["total"]
                p.status = status_for_score(result["total"])
                rec["needs_score"] = False
                rec["needs_enrich"] = False
                steps.append(_trace_step(state, "score_product", {"product_id": p.id}, {
                    "product_code": p.product_code, "score": p.score, "status": p.status,
                    "enriched": enriched, "dimensions": result["dimensions"],
                }, index=i))
            records.append(rec)
        db.commit()
        return {"product_records": records, "trace": steps}

    def decide_node(state):
        records = []
        steps = []
        for i, rec in enumerate(state["product_records"], 1):
            p = rec["product"]
            if p.status == "已选品":
                heat = _sales_heat_value(p)
                rec["heat_value"] = heat
                rec["detail_level"] = "detailed" if (heat >= 10000 or (p.score or 0) >= 90) else "standard"
            else:
                rec["detail_level"] = "skip"
                rec["skip_reason"] = "已淘汰，不拆解" if p.status == "已淘汰" else "待评估，暂不拆解分镜（评分≥80后自动升级）"
            records.append(rec)
            steps.append(_trace_step(state, "decide_detail", {"product_id": p.id}, {
                "status": p.status, "score": p.score, "detail_level": rec["detail_level"],
                "heat_value": rec.get("heat_value"), "skip_reason": rec.get("skip_reason"),
            }, index=i))
        return {"product_records": records, "trace": steps}

    def process_node(state):
        """方案二：每个商品一条"拆解→分镜"流水线，最多 3 路并发；拆完立即分镜，不等其他商品。"""
        targets = [rec for rec in state["product_records"] if rec.get("detail_level") != "skip"]
        results = []
        trace_entries = []

        def _process_one(idx: int, rec: dict) -> tuple:
            from database import SessionLocal
            sdb = SessionLocal()
            try:
                p = rec["product"]
                breakdown = None
                content_id = None
                if rec["has_content"]:
                    c = sdb.query(Content).filter(Content.product_id == p.id).order_by(Content.id.asc()).first()
                    if c:
                        content_id = c.id
                else:
                    breakdown = _generate_breakdown_with_self_check(p, rec["detail_level"], sdb)

                script = None
                if not rec["has_script"]:
                    content = breakdown
                    if not content and content_id:
                        c = sdb.query(Content).filter(Content.id == content_id).first()
                        content = {"hook": c.hook, "scene": c.scene, "structure": c.structure, "conversion_point": c.conversion_point} if c else None
                    script = _generate_script_with_self_check(p, content, rec["detail_level"], sdb)

                content_id, script_codes = _save_product_result(sdb, p, rec["detail_level"], breakdown, script, content_id)
                return (idx, {
                    "product_code": p.product_code,
                    "name": p.name,
                    "status": p.status,
                    "detail_level": rec["detail_level"],
                    "breakdown_score": breakdown.get("self_score") if breakdown else None,
                    "script_score": script.get("self_score") if script else None,
                    "script_codes": script_codes,
                    "content_id": content_id,
                })
            except Exception as e:
                return (idx, {"product_code": rec["product"].product_code, "name": rec["product"].name, "error": str(e)})
            finally:
                sdb.close()

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(_process_one, i, rec) for i, rec in enumerate(targets)]
            for fut in as_completed(futures):
                idx, res = fut.result()
                results.append(res)
                rec = targets[idx]
                round_no = len(state.get("trace") or []) + len(trace_entries) + 1
                if res.get("error"):
                    trace_entries.append({
                        "round": round_no, "tool": "pipeline", "status": "error",
                        "args": {"product_id": rec["product"].id, "level": rec["detail_level"]},
                        "result": {"error": res["error"]},
                    })
                else:
                    trace_entries.append({
                        "round": round_no, "tool": "pipeline", "status": "success",
                        "args": {"product_id": rec["product"].id, "level": rec["detail_level"]},
                        "result": {
                            "breakdown_score": res.get("breakdown_score"),
                            "script_score": res.get("script_score"),
                            "scripts": res.get("script_codes"),
                        },
                    })
        return {"saved": results, "trace": trace_entries}

    def record_node(state):
        saved = state.get("saved") or []
        log = AgentRun(
            run_type="product_agent",
            status="completed",
            products_processed=len(saved),
            summary=json.dumps({"message": state.get("message", ""), "saved": saved}, ensure_ascii=False, default=str),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return {
            "run_log_id": log.id,
            "trace": [_trace_step(state, "record_log", {}, {"run_id": log.id, "processed": len(saved)})],
        }

    def route_after_load(state):
        return "score" if state.get("product_records") else "end"

    graph = StateGraph(ProductAgentState)
    graph.add_node("load_products", load_products_node)
    graph.add_node("score", score_node)
    graph.add_node("decide", decide_node)
    graph.add_node("process", process_node)
    graph.add_node("record", record_node)
    graph.add_edge(START, "load_products")
    graph.add_conditional_edges("load_products", route_after_load, {"score": "score", "end": END})
    graph.add_edge("score", "decide")
    graph.add_edge("decide", "process")
    graph.add_edge("process", "record")
    graph.add_edge("record", END)
    return graph.compile()


def run_product_agent(db: Session, limit: int | None = None) -> dict:
    app = build_graph(db, limit)
    result = app.invoke({"product_records": [], "trace": [], "message": "", "run_log_id": None, "saved": []})
    return {
        "status": "completed",
        "message": result.get("message", ""),
        "processed": len(result.get("saved") or []),
        "saved": result.get("saved") or [],
        "run_id": result.get("run_log_id"),
        "trace": result.get("trace") or [],
    }


def _safe_run(limit: int | None):
    """后台执行一轮商品智能体；失败时写入 agent_runs 错误日志，避免静默丢失。"""
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            with _product_lock:
                run_product_agent(db, limit)
        finally:
            db.close()
    except Exception as e:
        try:
            from database import SessionLocal as SL
            db = SL()
            try:
                db.add(AgentRun(
                    run_type="product_agent",
                    status="error",
                    products_processed=0,
                    summary=json.dumps({"error": str(e)}, ensure_ascii=False),
                ))
                db.commit()
            finally:
                db.close()
        except Exception:
            pass


def trigger_product_agent_background(limit: int | None = None):
    """商品导入后异步触发一轮智能体处理（不阻塞导入请求）；limit=None 表示处理全部待处理商品。"""
    threading.Thread(target=_safe_run, args=(limit,), daemon=True, name="product-agent-trigger").start()


def _scheduler_loop():
    while not _product_stop.wait(PRODUCT_CHECK_INTERVAL_MINUTES * 60):
        _safe_run(PRODUCT_BATCH_LIMIT)


def start_product_agent_scheduler():
    """启动后台每10分钟巡检（间隔<=0 则不启动），防止商品漏掉拆解分镜。"""
    if PRODUCT_CHECK_INTERVAL_MINUTES <= 0:
        return
    threading.Thread(target=_scheduler_loop, daemon=True, name="product-agent-scheduler").start()
