"""AI 工作流引擎 - 商品信息到短视频脚本的完整流程"""

import json
import os
from fastapi import APIRouter, HTTPException, Depends
from openai import OpenAI
import httpx
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database import get_db
from models import Product, Content, Script, Knowledge
from schemas import AIWorkflowInput, ScriptGenerationInput
from ai_workflow.prompts import (
    SELLING_POINTS_PROMPT,
    CONTENT_ANGLES_PROMPT,
    SCRIPT_GENERATION_PROMPT,
    VIDEO_QUALITY_CHECK_PROMPT,
)

router = APIRouter()

# 支持多种 API 配置
API_KEY = os.getenv("OPENAI_API_KEY", "sk-placeholder")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client():
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, http_client=httpx.Client())


def call_ai(prompt: str) -> str:
    """调用 AI API；未配置 Key 时返回本地演示标记。"""
    if not API_KEY or API_KEY == "sk-placeholder":
        return json.dumps({"local_demo": True, "message": "未配置大模型，使用本地模拟流程"}, ensure_ascii=False)
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是一位专业的短视频电商运营专家，请始终以JSON格式输出结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": str(e), "fallback": True}, ensure_ascii=False)


def parse_ai_response(text: str) -> dict:
    """解析 AI 返回的 JSON"""
    try:
        # 尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 块
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        # 尝试找 { } 包裹的内容
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_text": text, "parse_error": True}




def local_workflow_result(input_data: AIWorkflowInput) -> dict:
    """不接入大模型时的本地模拟工作流，保证演示链路可跑通。"""
    selling_points = [x.strip() for x in input_data.selling_points.replace('、', ',').replace('，', ',').split(',') if x.strip()]
    if not selling_points:
        selling_points = ["便携", "易清洗", "制作快"]
    users = [x.strip() for x in input_data.target_users.replace('、', ',').replace('，', ',').split(',') if x.strip()]
    scenes = [x.strip() for x in input_data.core_scenes.replace('、', ',').replace('，', ',').split(',') if x.strip()]
    pain_points = [x.strip() for x in input_data.user_pain_points.replace('；', ';').split(';') if x.strip()]
    angles = [
        {"angle_id": 1, "title": "上班族早餐效率场景", "hook": "每天早上多睡10分钟，还能喝到新鲜果汁", "target_emotion": "省时、省钱、健康替代", "scene": scenes[0] if scenes else "早餐", "structure": "痛点开场-产品演示-清洗证明-下单引导", "conversion_point": "突出30秒制作和一键清洗"},
        {"angle_id": 2, "title": "宿舍饮品性价比场景", "hook": "宿舍也能实现果汁自由，不用插电", "target_emotion": "便宜、方便、小空间可用", "scene": "宿舍", "structure": "场景代入-价格对比-容量说明-收藏下单", "conversion_point": "突出一人份和价格区间"},
        {"angle_id": 3, "title": "办公室下午茶替代奶茶", "hook": "一杯奶茶钱，办公室喝三天水果饮", "target_emotion": "控糖、精致、低负担", "scene": "办公室", "structure": "奶茶痛点-水果制作-同事反馈-转化", "conversion_point": "突出便携和易清洗"},
    ]
    script = {
        "script_title": f"{input_data.product_name}｜上班族早餐30秒果汁",
        "total_duration": 30,
        "scenes": [
            {"time_range": "0-3秒", "scene_desc": "闹钟响起，上班族匆忙看时间", "voiceover": "早上又来不及吃早餐？", "subtitle": "多睡10分钟，也能喝果汁", "camera_move": "快速切入", "material_req": "卧室/通勤道具", "ai_prompt": "morning rush, young office worker, alarm clock, natural light"},
            {"time_range": "3-10秒", "scene_desc": "水果切块放入便携榨汁杯，一键启动", "voiceover": "水果加水，30秒打一杯", "subtitle": "30秒鲜榨", "camera_move": "产品特写", "material_req": "水果、榨汁杯、桌面", "ai_prompt": "portable blender close-up, fresh fruits, clean kitchen counter"},
            {"time_range": "10-18秒", "scene_desc": "办公室饮用，对比外卖饮品价格和糖分", "voiceover": "少点一杯奶茶，自己做更安心", "subtitle": "办公室下午茶替代", "camera_move": "横移对比", "material_req": "办公室、杯子、价格字幕", "ai_prompt": "office desk, homemade fruit drink, lifestyle commercial video"},
            {"time_range": "18-25秒", "scene_desc": "加水双击清洗，倒出后杯体干净", "voiceover": "大家最关心的清洗，也很简单", "subtitle": "一键清洗更省事", "camera_move": "近景演示", "material_req": "清水、杯体清洗过程", "ai_prompt": "portable blender self cleaning, water swirl, product demo"},
            {"time_range": "25-30秒", "scene_desc": "成品果汁和商品展示，出现价格区间提示", "voiceover": "想省时又想喝点新鲜的，可以先收藏", "subtitle": "79-129元区间｜按实物参数为准", "camera_move": "定格收尾", "material_req": "商品主图、合规价格字幕", "ai_prompt": "product hero shot, fresh juice, clean bright commercial style"},
        ],
        "publish_title": "早八人也能喝到的新鲜果汁，清洗这点我替你们试了",
        "tags": ["便携榨汁杯", "早餐效率", "办公室好物"],
        "quality_checklist": ["前3秒是否有痛点钩子", "是否展示清洗", "是否避免绝对化宣传", "是否有价格和容量说明", "字幕是否清晰"]
    }
    quality = {"overall_score": 86, "dimensions": {"钩子力": {"score": 86, "comment": "痛点明确"}, "节奏": {"score": 84, "comment": "分镜完整"}, "卖点": {"score": 88, "comment": "便携、快、易清洗均覆盖"}, "合规": {"score": 90, "comment": "未使用绝对化表述"}}, "issues": ["需按真实商品参数确认容量和材质"], "suggestions": ["成片中增加真实清洗特写", "评论区置顶清洗说明"], "pass": True}
    return {"status": "completed", "mode": "local_demo", "input": input_data.model_dump(), "steps": {"step1_selling_points": {"core_selling_points": selling_points, "target_user_tags": users, "pain_point_mapping": {p: "用便携、快速、易清洗场景回应" for p in pain_points}, "risk_warnings": ["避免治疗、减肥保证、全网第一等表达"]}, "step2_content_angles": {"angles": angles}, "step3_script": script, "step4_quality_check": quality}, "summary": {"selling_points": selling_points, "content_angles_count": len(angles), "script_title": script["script_title"], "quality_score": quality["overall_score"]}}

@router.post("/workflow/step1_selling_points")
def step1_selling_points(input_data: AIWorkflowInput):
    """步骤1：分析商品卖点"""
    prompt = SELLING_POINTS_PROMPT.format(
        product_name=input_data.product_name,
        price_range=input_data.price_range,
        target_users=input_data.target_users,
        core_scenes=input_data.core_scenes,
        user_pain_points=input_data.user_pain_points,
        selling_points=input_data.selling_points,
    )
    result = call_ai(prompt)
    return {"step": 1, "name": "卖点分析", "result": parse_ai_response(result)}


@router.post("/workflow/step2_content_angles")
def step2_content_angles(input_data: AIWorkflowInput, selling_points: str = ""):
    """步骤2：生成内容角度"""
    prompt = CONTENT_ANGLES_PROMPT.format(
        product_name=input_data.product_name,
        selling_points=selling_points or input_data.selling_points,
        target_user_tags=input_data.target_users,
        pain_points=input_data.user_pain_points,
    )
    result = call_ai(prompt)
    return {"step": 2, "name": "内容角度", "result": parse_ai_response(result)}


@router.post("/workflow/step3_script_generation")
def step3_script(input_data: ScriptGenerationInput):
    """步骤3：生成短视频脚本"""
    prompt = SCRIPT_GENERATION_PROMPT.format(
        duration=input_data.video_duration,
        product_name=input_data.product_info.product_name,
        selling_points=input_data.product_info.selling_points,
        target_users=input_data.product_info.target_users,
        angle_title=input_data.content_angle,
        hook="吸引用户注意力的开头",
        scene=input_data.product_info.core_scenes,
        structure="问题引入-产品展示-使用演示-效果对比-引导转化",
    )
    result = call_ai(prompt)
    return {"step": 3, "name": "脚本生成", "result": parse_ai_response(result)}


@router.post("/workflow/step4_quality_check")
def step4_quality_check(script_content: str):
    """步骤4：视频质检"""
    prompt = VIDEO_QUALITY_CHECK_PROMPT.format(script_content=script_content)
    result = call_ai(prompt)
    return {"step": 4, "name": "质检报告", "result": parse_ai_response(result)}


@router.post("/workflow/full")
def full_workflow(input_data: AIWorkflowInput):
    """完整工作流：商品信息 → 卖点 → 内容角度 → 脚本 → 质检"""
    if not API_KEY or API_KEY == "sk-placeholder":
        return local_workflow_result(input_data)
    steps = {}

    # Step 1: 卖点分析
    prompt1 = SELLING_POINTS_PROMPT.format(
        product_name=input_data.product_name,
        price_range=input_data.price_range,
        target_users=input_data.target_users,
        core_scenes=input_data.core_scenes,
        user_pain_points=input_data.user_pain_points,
        selling_points=input_data.selling_points,
    )
    result1 = call_ai(prompt1)
    selling_points_result = parse_ai_response(result1)
    steps["step1_selling_points"] = selling_points_result

    # Step 2: 内容角度
    sp_text = ", ".join(selling_points_result.get("core_selling_points", [input_data.selling_points]))
    prompt2 = CONTENT_ANGLES_PROMPT.format(
        product_name=input_data.product_name,
        selling_points=sp_text,
        target_user_tags=input_data.target_users,
        pain_points=input_data.user_pain_points,
    )
    result2 = call_ai(prompt2)
    angles_result = parse_ai_response(result2)
    steps["step2_content_angles"] = angles_result

    # Step 3: 脚本生成（选第一个角度）
    angles = angles_result.get("angles", [{}])
    first_angle = angles[0] if angles else {}
    prompt3 = SCRIPT_GENERATION_PROMPT.format(
        duration=30,
        product_name=input_data.product_name,
        selling_points=sp_text,
        target_users=input_data.target_users,
        angle_title=first_angle.get("title", "默认角度"),
        hook=first_angle.get("hook", "吸引用户"),
        scene=first_angle.get("scene", input_data.core_scenes),
        structure=first_angle.get("structure", "开头-中间-结尾"),
    )
    result3 = call_ai(prompt3)
    script_result = parse_ai_response(result3)
    steps["step3_script"] = script_result

    # Step 4: 质检
    script_text = json.dumps(script_result, ensure_ascii=False)
    prompt4 = VIDEO_QUALITY_CHECK_PROMPT.format(script_content=script_text)
    result4 = call_ai(prompt4)
    steps["step4_quality_check"] = parse_ai_response(result4)

    return {
        "status": "completed",
        "input": input_data.model_dump(),
        "steps": steps,
        "summary": {
            "selling_points": selling_points_result.get("core_selling_points", []),
            "content_angles_count": len(angles),
            "script_title": script_result.get("script_title", ""),
            "quality_score": steps["step4_quality_check"].get("overall_score", 0),
        }
    }



@router.post("/workflow/save_result")
def save_workflow_result(payload: dict, db: Session = Depends(get_db)):
    """把工作流结果写回业务表：内容拆解、脚本分镜、知识库。"""
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

    def as_dict(value):
        return value if isinstance(value, dict) else {}

    def first_text(*values, default=""):
        for value in values:
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                value = "、".join(str(x) for x in value)
            value = str(value).strip()
            if value:
                return value
        return default

    try:
        input_data = as_dict(payload.get("input"))
        steps = as_dict(payload.get("steps"))
        product_name = first_text(input_data.get("product_name"), default="未命名商品")

        product = db.query(Product).filter(Product.name == product_name).first()
        if not product:
            product = Product(
                product_code=next_code(Product, "product_code", "P"),
                name=product_name,
                target_users=input_data.get("target_users"),
                selling_points=input_data.get("selling_points"),
                pain_points=input_data.get("user_pain_points"),
                status="待评估",
                owner="选品运营",
            )
            db.add(product)
            db.flush()

        angles_block = as_dict(steps.get("step2_content_angles"))
        angles = angles_block.get("angles") or angles_block.get("content_angles") or []
        if not isinstance(angles, list):
            angles = []
        angle = as_dict(angles[0]) if angles else {}

        content = Content(
            content_code=next_code(Content, "content_code", "C"),
            hook=first_text(angle.get("hook"), angle.get("opening_hook"), default="由AI工作流生成的内容方向"),
            scene=first_text(angle.get("scene"), angle.get("scenario"), input_data.get("core_scenes")),
            target_group=input_data.get("target_users"),
            structure=first_text(angle.get("structure"), angle.get("content_structure"), default="AI生成内容结构，需人工复核"),
            conversion_point=first_text(angle.get("conversion_point"), angle.get("cta"), default="引导收藏/咨询/下单"),
            remix_angles=first_text(angle.get("title"), angle.get("angle_title"), default="AI二创方向"),
            product_id=product.id,
            analyst="AI工作流",
            status="待二创",
            priority="P1",
            notes="由AI工作流写回，需人工审核",
        )
        db.add(content)
        db.flush()

        script = as_dict(steps.get("step3_script"))
        if "script" in script and isinstance(script.get("script"), dict):
            script = script["script"]
        scenes = script.get("scenes") or script.get("shots") or script.get("storyboard") or []
        if not isinstance(scenes, list):
            scenes = []
        if not scenes:
            scenes = [{
                "time_range": "0-30秒",
                "scene_desc": first_text(script.get("content"), script.get("script_content"), default="AI生成完整脚本文本，需人工拆分分镜"),
                "voiceover": first_text(script.get("voiceover"), script.get("narration")),
                "subtitle": first_text(script.get("subtitle")),
                "ai_prompt": first_text(script.get("ai_prompt"), default="按商品场景生成短视频画面"),
            }]

        created_scripts = []
        for scene in scenes:
            scene = as_dict(scene)
            item = Script(
                script_code=next_code(Script, "script_code", "S"),
                title=first_text(script.get("script_title"), script.get("title"), default=f"{product_name} AI脚本"),
                product_id=product.id,
                content_id=content.id,
                shot_time=first_text(scene.get("time_range"), scene.get("time"), scene.get("shot_time"), default="待拆分"),
                scene_desc=first_text(scene.get("scene_desc"), scene.get("visual"), scene.get("picture"), scene.get("description")),
                voiceover=first_text(scene.get("voiceover"), scene.get("narration"), scene.get("旁白")),
                subtitle=first_text(scene.get("subtitle"), scene.get("caption"), scene.get("字幕")),
                camera_move=first_text(scene.get("camera_move"), scene.get("camera")),
                material_req=first_text(scene.get("material_req"), scene.get("materials")),
                ai_prompt=first_text(scene.get("ai_prompt"), scene.get("prompt"), default="可用于视频/图片生成的提示词"),
                review_status="待审核",
                owner="脚本编导",
                priority="P1",
                notes="工作流自动生成，发布前必须人工审核",
            )
            db.add(item)
            db.flush()
            created_scripts.append(item)

        knowledge = Knowledge(
            knowledge_code=next_code(Knowledge, "knowledge_code", "K"),
            category="提示词库",
            source="AI工作流写回",
            applicable_scene="短视频脚本/分镜/视频生成提示词",
            content_summary=f"{product_name} 工作流生成脚本：{first_text(script.get('script_title'), script.get('title'), default='AI脚本')}；已生成{len(created_scripts)}条分镜。",
            prompt_version="deepseek-v1",
            usage_effect="待验证",
            updater="AI工作流",
            status="待验证",
            priority="P1",
            review_status="待审核",
            notes="由工作流保存生成",
        )
        db.add(knowledge)
        db.commit()
        return {
            "message": "写回成功",
            "product_id": product.id,
            "content_id": content.id,
            "content_code": content.content_code,
            "script_count": len(created_scripts),
            "script_codes": [x.script_code for x in created_scripts],
            "knowledge_code": knowledge.knowledge_code,
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库写入失败：{str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"写回失败：{str(e)}")
