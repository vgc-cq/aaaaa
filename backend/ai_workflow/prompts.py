"""AI 工作流提示词模板"""

SELLING_POINTS_PROMPT = """你是一位资深短视频电商选品专家。请根据以下商品信息，分析并输出结构化的卖点分析。

商品信息：
- 商品名称：{product_name}
- 价格区间：{price_range}
- 目标用户：{target_users}
- 核心场景：{core_scenes}
- 用户痛点：{user_pain_points}
- 可表达卖点：{selling_points}

请输出以下JSON格式：
{{
    "core_selling_points": ["卖点1", "卖点2", "卖点3"],
    "target_user_tags": ["人群标签1", "人群标签2"],
    "pain_point_mapping": {{"痛点": "对应卖点解决方案"}},
    "risk_warnings": ["风险提示1", "风险提示2"],
    "differentiation": "差异化优势描述"
}}"""


CONTENT_ANGLES_PROMPT = """你是一位短视频内容策划专家。请根据商品卖点分析，生成3个不同的内容创作角度。

商品信息：
- 商品名称：{product_name}
- 核心卖点：{selling_points}
- 目标人群：{target_user_tags}
- 用户痛点：{pain_points}

请为每个角度输出：
{{
    "angles": [
        {{
            "angle_id": 1,
            "title": "角度标题",
            "hook": "开头钩子（前3秒吸引用户的话术）",
            "target_emotion": "目标情绪",
            "scene": "场景描述",
            "structure": "内容结构（开头-中间-结尾）",
            "conversion_point": "转化引导点"
        }},
        ...
    ]
}}"""


SCRIPT_GENERATION_PROMPT = """你是一位短视频脚本创作专家。请根据以下信息生成一个{duration}秒的短视频脚本。

商品信息：
- 商品名称：{product_name}
- 核心卖点：{selling_points}
- 目标人群：{target_users}

内容角度：
- 标题：{angle_title}
- 开头钩子：{hook}
- 场景：{scene}
- 内容结构：{structure}

请输出完整的秒级分镜脚本：
{{
    "script_title": "脚本标题",
    "total_duration": {duration},
    "scenes": [
        {{
            "time_range": "0-3秒",
            "scene_desc": "画面描述",
            "voiceover": "旁白文案",
            "subtitle": "字幕文字",
            "camera_move": "镜头运动（推/拉/摇/移/固定）",
            "material_req": "素材要求",
            "ai_prompt": "用于AI生成画面的英文提示词"
        }},
        ...
    ],
    "publish_title": "发布标题",
    "tags": ["标签1", "标签2"],
    "quality_checklist": ["质检项1", "质检项2"]
}}"""


VIDEO_QUALITY_CHECK_PROMPT = """你是一位短视频质检专家。请根据以下脚本信息进行质量检查。

脚本内容：
{script_content}

质检维度：
1. 钩子力：前3秒是否能吸引用户停留
2. 节奏感：信息密度是否合理，是否有拖沓
3. 卖点传达：核心卖点是否清晰传达
4. 合规性：是否有违规词、夸大宣传
5. 字幕规范：字幕是否简洁易读
6. 转化引导：是否有明确的转化引导

请输出质检报告：
{{
    "overall_score": 85,
    "dimensions": {{
        "hook_power": {{"score": 90, "comment": "评价"}},
        "rhythm": {{"score": 80, "comment": "评价"}},
        "selling_point": {{"score": 85, "comment": "评价"}},
        "compliance": {{"score": 90, "comment": "评价"}},
        "subtitle": {{"score": 80, "comment": "评价"}},
        "conversion": {{"score": 85, "comment": "评价"}}
    }},
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"],
    "pass": true
}}"""


AD_REVIEW_PROMPT = """你是一位千川投流数据分析专家。请根据以下视频和投流数据进行复盘分析。

视频信息：
- 视频编号：{video_code}
- 内容方向：{content_direction}
- 播放量：{play_count}
- 2秒跳出率：{bounce_rate_2s}
- 5秒完播率：{completion_rate_5s}
- 完播率：{completion_rate}

投流数据：
- 购物车点击：{cart_clicks}
- 投流消耗：{spend}
- 成交金额：{revenue}
- 订单数：{orders}

用户反馈：{feedback}

请输出复盘分析：
{{
    "performance_rating": "优秀/良好/一般/较差",
    "key_metrics": {{
        "ctr": "购物车点击率",
        "cvr": "成交转化率",
        "roi": "ROI",
        "cpa": "单笔成交成本"
    }},
    "problems": [
        {{"issue": "问题描述", "cause": "原因分析", "severity": "高/中/低"}}
    ],
    "optimization_actions": [
        {{"action": "优化动作", "priority": "高/中/低", "expected_effect": "预期效果"}}
    ],
    "decision": "继续放量/小幅测试/停投重做",
    "next_step": "下一步具体操作建议"
}}"""


DAILY_REPORT_PROMPT = """你是一位短视频电商数据分析师。请根据以下数据生成{period}复盘报告。

数据汇总：
{data_summary}

请输出复盘报告：
{{
    "period": "{period}",
    "highlights": ["亮点1", "亮点2"],
    "problems": ["问题1", "问题2"],
    "top_performing_videos": ["表现最好的视频及原因"],
    "underperforming_videos": ["表现最差的视频及原因"],
    "optimization_priorities": ["优先优化方向1", "方向2"],
    "action_items": [
        {{"action": "具体动作", "owner": "负责人", "deadline": "截止时间"}}
    ]
}}"""
