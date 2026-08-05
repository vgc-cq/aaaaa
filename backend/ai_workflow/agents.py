"""智能体/数字员工雏形 - 投流复盘助手"""

import json
import os
from fastapi import APIRouter
from openai import OpenAI
import httpx
from schemas import AgentInput
from ai_workflow.prompts import AD_REVIEW_PROMPT, DAILY_REPORT_PROMPT

router = APIRouter()

API_KEY = os.getenv("OPENAI_API_KEY", "sk-placeholder")
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client():
    return OpenAI(api_key=API_KEY, base_url=BASE_URL, http_client=httpx.Client())


def call_ai(system_prompt: str, user_prompt: str) -> str:
    if not API_KEY or API_KEY == "sk-placeholder":
        return json.dumps({"local_demo": True, "summary": "未配置大模型，已使用本地规则生成演示结果", "next_step": "如需真实生成，请配置 OPENAI_API_KEY；当前测试可先展示流程闭环。"}, ensure_ascii=False)
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def parse_response(text: str) -> dict:
    import re
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        brace_match = re.search(r'\{[\s\S]*\}', text)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except:
                pass
        return {"raw_text": text}


AGENT_CONFIGS = {
    "投流复盘助手": {
        "name": "投流复盘助手",
        "description": "输入视频表现数据和投流数据，输出问题分析、优化建议和投放决策",
        "input_fields": ["video_code", "content_direction", "play_count", "bounce_rate_2s",
                         "completion_rate_5s", "completion_rate", "cart_clicks", "spend",
                         "revenue", "orders", "feedback"],
        "output_fields": ["performance_rating", "key_metrics", "problems",
                          "optimization_actions", "decision", "next_step"],
        "system_prompt": "你是一位资深千川投流数据分析专家，擅长从数据中发现问题并给出可执行的优化建议。"
    },
    "选品分析助手": {
        "name": "选品分析助手",
        "description": "输入商品基础数据，输出选品评分、适合人群、风险点和是否建议测试",
        "input_fields": ["product_name", "price", "sales", "reviews", "category"],
        "output_fields": ["score", "target_users", "risk_points", "content_angles", "recommendation"],
        "system_prompt": "你是一位资深选品专家，擅长从市场数据中筛选有潜力的商品。"
    },
    "脚本生成助手": {
        "name": "脚本生成助手",
        "description": "输入商品和场景信息，输出15-30秒短视频脚本和秒级分镜",
        "input_fields": ["product_name", "target_users", "scene", "duration"],
        "output_fields": ["script", "scenes", "subtitles", "prompts"],
        "system_prompt": "你是一位短视频脚本创作专家，擅长创作高转化的短视频内容。"
    },
    "视频质检助手": {
        "name": "视频质检助手",
        "description": "输入脚本或成片信息，按多维度输出质检结论",
        "input_fields": ["script_content"],
        "output_fields": ["overall_score", "dimensions", "issues", "suggestions"],
        "system_prompt": "你是一位短视频质检专家，擅长从多个维度评估视频质量。"
    },
    "客服话术助手": {
        "name": "客服话术助手",
        "description": "输入用户咨询内容和商品卖点，输出合规话术和跟进动作",
        "input_fields": ["inquiry", "product_info"],
        "output_fields": ["response", "follow_up", "intent_analysis"],
        "system_prompt": "你是一位专业的电商客服专家，擅长用合规且有说服力的话术回复用户。"
    },
}


@router.get("/agents")
def list_agents():
    """列出所有可用智能体"""
    return [
        {
            "name": config["name"],
            "description": config["description"],
            "input_fields": config["input_fields"],
            "output_fields": config["output_fields"],
        }
        for config in AGENT_CONFIGS.values()
    ]


@router.post("/agents/投流复盘助手")
def ad_review_agent(data: dict):
    """投流复盘助手 - 核心智能体"""
    video = data.get("video_data", {})
    ad = data.get("ad_data", {})
    feedback = data.get("feedback", "")

    prompt = AD_REVIEW_PROMPT.format(
        video_code=video.get("video_code", "未知"),
        content_direction=video.get("content_direction", "未知"),
        play_count=video.get("play_count", 0),
        bounce_rate_2s=video.get("bounce_rate_2s", "未知"),
        completion_rate_5s=video.get("completion_rate_5s", "未知"),
        completion_rate=video.get("completion_rate", "未知"),
        cart_clicks=ad.get("cart_clicks", 0),
        spend=ad.get("spend", 0),
        revenue=ad.get("revenue", 0),
        orders=ad.get("orders", 0),
        feedback=feedback,
    )

    system = AGENT_CONFIGS["投流复盘助手"]["system_prompt"]
    spend = float(ad.get("spend") or 0)
    revenue = float(ad.get("revenue") or 0)
    orders = int(ad.get("orders") or 0)
    cart_clicks = int(ad.get("cart_clicks") or 0)
    roi = round(revenue / spend, 2) if spend > 0 else 0
    cvr = round(orders / cart_clicks * 100, 2) if cart_clicks else 0
    bounce = str(video.get("bounce_rate_2s", "0")).replace("%", "")
    try:
        bounce_value = float(bounce)
    except Exception:
        bounce_value = 0
    problems = []
    if roi < 1 and spend > 0:
        problems.append({"problem": "ROI亏损", "severity": "高", "reason": f"ROI={roi}<1"})
    if bounce_value > 50:
        problems.append({"problem": "前3秒钩子弱", "severity": "高", "reason": f"2秒跳出率={bounce_value}%"})
    if cvr and cvr < 5:
        problems.append({"problem": "成交转化偏低", "severity": "中", "reason": f"购物车到成交转化率={cvr}%"})
    decision = "继续放量" if roi >= 3 else "小幅优化" if roi >= 1.5 else "观察调整" if roi >= 1 else "停投重做"
    local_output = {
        "performance_rating": "优秀" if roi >= 3 else "良好" if roi >= 1.5 else "一般" if roi >= 1 else "较差",
        "key_metrics": {"roi": roi, "cart_to_order_cvr": cvr, "cpa": round(spend / orders, 2) if orders else None},
        "problems": problems or [{"problem": "暂无高风险异常", "severity": "低", "reason": "核心指标在可接受范围"}],
        "optimization_actions": ["优先处理评论高频问题并补进脚本", "根据ROI决定放量/停投", "把复盘结论归档到知识库"],
        "decision": decision,
        "next_step": "清洗/价格/容量等高频问题同步给脚本和客服话术",
        "feedback_used": feedback,
        "local_demo": True
    }
    if not API_KEY or API_KEY == "sk-placeholder":
        return {"agent": "投流复盘助手", "input": data, "output": local_output}
    result = call_ai(system, prompt)

    return {
        "agent": "投流复盘助手",
        "input": data,
        "output": parse_response(result),
    }


@router.post("/agents/选品分析助手")
def product_analysis_agent(data: dict):
    """选品分析助手"""
    system = AGENT_CONFIGS["选品分析助手"]["system_prompt"]
    prompt = f"""请分析以下商品的选品价值：

商品名称：{data.get('product_name', '')}
价格：{data.get('price', '')}
销量/热度：{data.get('sales', '')}
口碑评价：{data.get('reviews', '')}
类目：{data.get('category', '')}

请输出JSON格式的选品分析报告，包含：score(0-100评分)、target_users(适合人群)、risk_points(风险点)、content_angles(内容角度建议)、recommendation(是否建议测试及理由)"""

    result = call_ai(system, prompt)
    return {"agent": "选品分析助手", "input": data, "output": parse_response(result)}


@router.post("/agents/脚本生成助手")
def script_gen_agent(data: dict):
    """脚本生成助手"""
    system = AGENT_CONFIGS["脚本生成助手"]["system_prompt"]
    prompt = f"""请为以下商品生成一个{data.get('duration', 30)}秒的短视频脚本：

商品名称：{data.get('product_name', '')}
目标人群：{data.get('target_users', '')}
场景：{data.get('scene', '')}

请输出JSON格式，包含：script(脚本标题)、scenes(秒级分镜数组，每项含time_range/scene_desc/voiceover/subtitle/camera_move/ai_prompt)、publish_title(发布标题)、tags(标签数组)"""

    result = call_ai(system, prompt)
    return {"agent": "脚本生成助手", "input": data, "output": parse_response(result)}


@router.post("/agents/视频质检助手")
def video_qa_agent(data: dict):
    """视频质检助手"""
    from ai_workflow.prompts import VIDEO_QUALITY_CHECK_PROMPT
    system = AGENT_CONFIGS["视频质检助手"]["system_prompt"]
    prompt = VIDEO_QUALITY_CHECK_PROMPT.format(script_content=data.get("script_content", ""))

    result = call_ai(system, prompt)
    return {"agent": "视频质检助手", "input": data, "output": parse_response(result)}


@router.post("/agents/客服话术助手")
def customer_service_agent(data: dict):
    """客服话术助手"""
    system = AGENT_CONFIGS["客服话术助手"]["system_prompt"]
    prompt = f"""用户咨询内容：{data.get('inquiry', '')}
商品信息：{data.get('product_info', '')}

请输出JSON格式的客服回复方案，包含：response(回复话术)、follow_up(跟进动作)、intent_analysis(用户意向分析：高/中/低)、wechat_script(加微话术)"""

    result = call_ai(system, prompt)
    return {"agent": "客服话术助手", "input": data, "output": parse_response(result)}


@router.post("/agents/auto_review")
def auto_review(data: dict):
    """自动生成复盘报告"""
    system = "你是一位短视频电商数据分析师，擅长从数据中发现规律并给出可执行建议。"
    prompt = DAILY_REPORT_PROMPT.format(
        period=data.get("period", "本周"),
        data_summary=json.dumps(data.get("data", {}), ensure_ascii=False),
    )

    result = call_ai(system, prompt)
    return {"agent": "自动复盘", "input": data, "output": parse_response(result)}


