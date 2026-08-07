from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Script
from schemas import ScriptCreate, ScriptOut

router = APIRouter()


@router.get("/", response_model=List[ScriptOut])
def list_scripts(skip: int = 0, limit: int = 500, product_id: int = None, content_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Script)
    if product_id:
        query = query.filter(Script.product_id == product_id)
    if content_id:
        query = query.filter(Script.content_id == content_id)
    return query.order_by(Script.id.asc()).offset(skip).limit(limit).all()


@router.get("/{script_id}", response_model=ScriptOut)
def get_script(script_id: int, db: Session = Depends(get_db)):
    item = db.query(Script).filter(Script.id == script_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="脚本不存在")
    return item


@router.post("/", response_model=ScriptOut)
def create_script(item: ScriptCreate, db: Session = Depends(get_db)):
    db_item = Script(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.put("/{script_id}", response_model=ScriptOut)
def update_script(script_id: int, item: ScriptCreate, db: Session = Depends(get_db)):
    db_item = db.query(Script).filter(Script.id == script_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="脚本不存在")
    for key, value in item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Script).filter(Script.id == script_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="脚本不存在")
    db.delete(db_item)
    db.commit()
    return {"message": "删除成功"}


from pydantic import BaseModel


class BatchDeleteIn(BaseModel):
    ids: list[int] = []


@router.post("/batch_delete")
def batch_delete_scripts(data: BatchDeleteIn, db: Session = Depends(get_db)):
    ids = data.ids
    if not ids:
        raise HTTPException(status_code=400, detail="请先勾选要删除的脚本")
    items = db.query(Script).filter(Script.id.in_(ids)).all()
    if not items:
        raise HTTPException(status_code=400, detail="没有可删除的脚本")
    db.query(Script).filter(Script.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"已删除 {len(items)} 条脚本记录"}


class BatchReviewIn(BaseModel):
    ids: list[int]
    review_status: str


@router.post("/batch_review")
def batch_review_scripts(data: BatchReviewIn, db: Session = Depends(get_db)):
    """批量审核：大标题选择审核状态后，组内所有分镜脚本同步更新。"""
    ids = data.ids
    if not ids:
        raise HTTPException(status_code=400, detail="请先选择要审核的脚本")
    if data.review_status not in ("待审核", "已通过", "已驳回"):
        raise HTTPException(status_code=400, detail="无效的审核状态")
    db.query(Script).filter(Script.id.in_(ids)).update(
        {Script.review_status: data.review_status}, synchronize_session=False
    )
    db.commit()
    return {"message": f"已更新 {len(ids)} 条分镜脚本的审核状态为「{data.review_status}」"}


class ScriptGenerateIn(BaseModel):
    content_id: int
    product_id: int | None = None
    duration: int = 30


@router.post("/generate")
def generate_script(data: ScriptGenerateIn, db: Session = Depends(get_db)):
    """基于内容拆解要点，调用 DeepSeek 生成秒级分镜脚本并写回脚本分镜表"""
    import os

    from ai_workflow.workflow import call_ai, parse_ai_response
    from models import Content, Product

    content = db.query(Content).filter(Content.id == data.content_id).first()
    if not content:
        raise HTTPException(status_code=404, detail="内容拆解记录不存在")

    product = None
    if data.product_id:
        product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product and content.product_id:
        product = db.query(Product).filter(Product.id == content.product_id).first()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "sk-placeholder" or "在这里" in api_key:
        raise HTTPException(status_code=400, detail="未配置 DeepSeek API Key，请先在 backend/.env 配置 OPENAI_API_KEY 后使用")

    product_name = product.name if product else "未指定商品"
    product_code = product.product_code if product else "-"
    prompt = f"""你是短视频电商脚本编导。请根据以下内容拆解结果，为指定商品生成一条完整的短视频脚本（总时长控制在 20 秒以内），只输出 JSON，不要 Markdown。

商品：{product_name}（编号 {product_code}）

内容拆解要点：
- 开头钩子：{content.hook or '无'}
- 场景：{content.scene or '无'}
- 目标人群：{content.target_group or '无'}
- 内容结构：{content.structure or '无'}
- 转化点：{content.conversion_point or '无'}
- 可二创角度：{content.remix_angles or '无'}
- 风险点/合规约束：{content.risk_points or '无'}

要求：
1. 严格按“内容结构”拆成秒级分镜，每镜 3-6 秒，总时长控制在 20 秒以内；
2. 前 3 秒必须用“开头钩子”，结尾必须用“转化点”；
3. 每镜包含：time_range(如"0-3秒")、scene_desc(画面描述)、voiceover(旁白)、subtitle(字幕)、camera_move(镜头运动)、material_req(素材要求)、ai_prompt(英文，用于文生图/文生视频)；
4. 文案不得出现“风险点/合规约束”中的违规表达；
5. 输出 JSON：{{"script_title": "脚本标题", "scenes": [...], "publish_title": "发布标题", "tags": ["标签"], "quality_checklist": ["质检项"]}}"""

    result = parse_ai_response(call_ai(prompt))
    if result.get("error") or result.get("parse_error") or result.get("local_demo"):
        raise HTTPException(status_code=500, detail="AI 生成失败：" + str(result.get("error") or result.get("raw_text") or "未知错误"))

    script = result.get("script") if isinstance(result.get("script"), dict) else result
    scenes = script.get("scenes") or script.get("shots") or []
    if not isinstance(scenes, list) or not scenes:
        raise HTTPException(status_code=500, detail="AI 未返回有效的分镜数据")

    def next_code(model, field_name: str, prefix: str) -> str:
        field = getattr(model, field_name)
        rows = db.query(field).filter(field.like(f"{prefix}%")).all()
        max_num = 0
        for (code,) in rows:
            if not code:
                continue
            digits = "".join(ch for ch in str(code) if ch.isdigit())
            if digits:
                max_num = max(max_num, int(digits))
        return f"{prefix}{max_num + 1:03d}"

    title = script.get("script_title") or script.get("title") or f"{product_name} 拆解脚本"
    created = []
    for sc in scenes:
        if not isinstance(sc, dict):
            continue
        item = Script(
            script_code=next_code(Script, "script_code", "S"),
            title=title,
            product_id=product.id if product else content.product_id,
            content_id=content.id,
            shot_time=sc.get("time_range") or sc.get("shot_time") or "待拆分",
            scene_desc=sc.get("scene_desc") or sc.get("visual") or sc.get("description") or "",
            voiceover=sc.get("voiceover") or sc.get("narration") or "",
            subtitle=sc.get("subtitle") or sc.get("caption") or "",
            camera_move=sc.get("camera_move") or sc.get("camera") or "",
            material_req=sc.get("material_req") or sc.get("materials") or "",
            ai_prompt=sc.get("ai_prompt") or sc.get("prompt") or "",
            review_status="待审核",
            owner="脚本编导",
            priority="P1",
            notes=f"由内容拆解({content.content_code})生成，需人工审核",
        )
        db.add(item)
        db.flush()
        created.append({
            "script_code": item.script_code,
            "shot_time": item.shot_time,
            "scene_desc": (item.scene_desc or "")[:50],
        })
    db.commit()
    return {
        "message": f"已生成 {len(created)} 条分镜脚本",
        "script_title": title,
        "content_id": content.id,
        "scripts": created,
    }

