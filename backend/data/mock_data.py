"""模拟数据初始化"""

from sqlalchemy.orm import Session
from models import Product, Content, Script, Video, AdData, Lead, Review, Knowledge
from datetime import datetime



def enrich_existing_data(db: Session):
    """补齐测试题要求的视频表现、反馈、负责人、优先级等字段。"""
    metrics = {
        "V001": {"content_direction": "上班族40秒早餐果汁", "play_count": 12000, "bounce_rate_2s": 38, "completion_rate_5s": 22, "completion_rate": 15, "feedback": "评论集中问：清洗麻烦吗？", "owner": "投流运营", "priority": "P1", "status": "投放中"},
        "V002": {"content_direction": "健身饮品", "play_count": 8000, "bounce_rate_2s": 51, "completion_rate_5s": 16, "completion_rate": 9, "feedback": "前3秒钩子偏弱，点击偏低", "owner": "投流运营", "priority": "P0", "status": "已暂停"},
        "V003": {"content_direction": "宿舍饮品", "play_count": 20000, "bounce_rate_2s": 29, "completion_rate_5s": 31, "completion_rate": 21, "feedback": "收藏较高，评论关注价格和容量", "owner": "投流运营", "priority": "P0", "status": "放量中"},
        "V004": {"content_direction": "家庭饮品", "play_count": 5500, "bounce_rate_2s": 42, "completion_rate_5s": 19, "completion_rate": 12, "feedback": "自然流量样本较小，但转化表现可参考", "owner": "投流运营", "priority": "P2", "status": "待测试"},
        "V005": {"content_direction": "办公室下午茶替代奶茶", "play_count": 15000, "bounce_rate_2s": 34, "completion_rate_5s": 27, "completion_rate": 18, "feedback": "购物车点击不错，成交未明显放大", "owner": "投流运营", "priority": "P1", "status": "优化中"},
    }
    for video in db.query(Video).all():
        if video.video_code in metrics and video.ad_data:
            for key, value in metrics[video.video_code].items():
                setattr(video.ad_data, key, value)
        if not getattr(video, "priority", None):
            video.priority = "P1"
    for content in db.query(Content).all():
        if content.content_code in ["C001", "C002", "C003"]: content.status = "已拆解"
        elif not getattr(content, "status", None): content.status = "待拆解"
        if not getattr(content, "priority", None): content.priority = "P1"
    for script in db.query(Script).all():
        if not getattr(script, "title", None): script.title = f"{script.script_code} 分镜脚本"
        if not getattr(script, "owner", None): script.owner = "脚本编导"
        if not getattr(script, "priority", None): script.priority = "P1"
    for lead in db.query(Lead).all():
        if not getattr(lead, "owner", None): lead.owner = "客服"
        if not getattr(lead, "priority", None): lead.priority = "P1" if lead.intent != "高" else "P0"
        if not getattr(lead, "source_platform", None): lead.source_platform = "抖音"
    for review in db.query(Review).all():
        if not getattr(review, "status", None): review.status = "已完成"
        if not getattr(review, "priority", None): review.priority = "P0"
        if not getattr(review, "review_level", None): review.review_level = "周复盘"
    db.commit()

def init_mock_data(db: Session):
    """初始化模拟数据（仅在表为空时插入）"""

    if db.query(Product).first():
        enrich_existing_data(db)
        return  # 已有数据，跳过

    # ========== 商品库 ==========
    product = Product(
        product_code="P001",
        name="便携式无线榨汁杯",
        category="厨房小家电",
        price_min=79, price_max=129,
        commission=15.0,
        sales_heat="月销5000+",
        reputation="4.8分/好评率96%",
        target_users="上班族、学生、宝妈、健身人群、轻食/健康饮品需求人群",
        selling_points="便携、无线、易清洗、制作快、容量适中(300ml)、USB充电、食品级材质",
        pain_points="外卖饮品价格高含糖高；早上时间紧；传统榨汁机清洗麻烦；宿舍/办公室空间有限",
        risk_words="不得出现：治疗、减肥保证、绝对最低价、全网第一、100%纯天然",
        score=85.0,
        status="已选品",
        owner="张三"
    )
    db.add(product)
    db.flush()

    # ========== 内容拆解 ==========
    content1 = Content(
        content_code="C001",
        reference_link="https://example.com/video1",
        hook="每天早上多睡10分钟，还能喝到新鲜果汁",
        scene="厨房/早餐场景",
        target_group="上班族",
        structure="痛点引入(3s)-产品展示(5s)-使用演示(10s)-效果对比(5s)-价格引导(5s)-转化(2s)",
        conversion_point="限时特价+赠品引导",
        remix_angles="宿舍版/健身版/办公室版/宝妈版",
        risk_points="避免夸大功效，不提减肥效果",
        product_id=product.id,
        analyst="李四"
    )
    content2 = Content(
        content_code="C002",
        reference_link="https://example.com/video2",
        hook="健身后的蛋白质奶昔，30秒搞定",
        scene="健身房/运动场景",
        target_group="健身人群",
        structure="运动场景(3s)-制作过程(15s)-饮用展示(5s)-成分说明(5s)-引导购买(2s)",
        conversion_point="健身达人口碑推荐",
        remix_angles="早餐版/下午茶版/宿舍版",
        risk_points="不能宣传增肌/减脂功效",
        product_id=product.id,
        analyst="李四"
    )
    content3 = Content(
        content_code="C003",
        reference_link="https://example.com/video3",
        hook="宿舍也能实现果汁自由！不用插电",
        scene="大学宿舍",
        target_group="学生",
        structure="宿舍场景(3s)-操作演示(12s)-口味展示(8s)-价格对比(5s)-下单引导(2s)",
        conversion_point="学生优惠+宿舍必备",
        remix_angles="上班族版/宝妈版",
        risk_points="注意学生消费能力，价格要突出性价比",
        product_id=product.id,
        analyst="王五"
    )
    db.add_all([content1, content2, content3])
    db.flush()

    # ========== 脚本分镜 ==========
    script1 = Script(
        script_code="S001", product_id=product.id, content_id=content1.id,
        shot_time="0-3秒",
        scene_desc="闹钟响，女主匆忙起床，画面显示时间7:30",
        voiceover="每天早上都在多睡10分钟和吃早餐之间纠结？",
        subtitle="多睡10分钟 VS 吃早餐？",
        camera_move="固定镜头，快速剪辑",
        material_req="卧室场景、闹钟道具",
        ai_prompt="young woman waking up to alarm clock, morning bedroom, rushed expression, natural lighting",
        review_status="已通过"
    )
    script2 = Script(
        script_code="S002", product_id=product.id, content_id=content1.id,
        shot_time="3-8秒",
        scene_desc="拿出榨汁杯，放入水果，一键启动",
        voiceover="有了这个便携榨汁杯，30秒就能喝到新鲜果汁",
        subtitle="30秒鲜榨果汁",
        camera_move="特写镜头，产品展示",
        material_req="榨汁杯实物、新鲜水果",
        ai_prompt="portable blender with fresh fruits, close-up product shot, kitchen counter, bright lighting",
        review_status="已通过"
    )
    script3 = Script(
        script_code="S003", product_id=product.id, content_id=content2.id,
        shot_time="0-3秒",
        scene_desc="健身完大汗淋漓，拿出蛋白粉和水果",
        voiceover="练完来一杯蛋白质奶昔，肌肉恢复快人一步",
        subtitle="练后补充 超重要",
        camera_move="中景，健身房环境",
        material_req="健身房场景、蛋白粉",
        ai_prompt="fitness person after workout, gym environment, protein shake preparation",
        review_status="已通过"
    )
    db.add_all([script1, script2, script3])
    db.flush()

    # ========== 视频生产 ==========
    video1 = Video(
        video_code="V001", script_id=script1.id,
        material_status="已完成", generate_tool="剪映+AI",
        editor="赵六", version="v2",
        quality_items="钩子力:8分;节奏:7分;卖点:9分;合规:9分;字幕:8分;转化:7分",
        publish_time=datetime(2026, 7, 28),
        publish_platform="抖音", publish_status="已发布"
    )
    video2 = Video(
        video_code="V002", script_id=script3.id,
        material_status="已完成", generate_tool="剪映+AI",
        editor="赵六", version="v1",
        quality_items="钩子力:5分;节奏:6分;卖点:7分;合规:9分;字幕:8分;转化:6分",
        publish_time=datetime(2026, 7, 29),
        publish_platform="抖音", publish_status="已发布"
    )
    video3 = Video(
        video_code="V003", script_id=script2.id,
        material_status="已完成", generate_tool="可灵+剪映",
        editor="钱七", version="v1",
        quality_items="钩子力:9分;节奏:8分;卖点:8分;合规:9分;字幕:9分;转化:8分",
        publish_time=datetime(2026, 7, 30),
        publish_platform="抖音", publish_status="已发布"
    )
    video4 = Video(
        video_code="V004", script_id=script1.id,
        material_status="已完成", generate_tool="剪映",
        editor="钱七", version="v1",
        quality_items="钩子力:7分;节奏:7分;卖点:8分;合规:9分;字幕:8分;转化:7分",
        publish_time=datetime(2026, 7, 31),
        publish_platform="抖音", publish_status="已发布"
    )
    video5 = Video(
        video_code="V005", script_id=script2.id,
        material_status="已完成", generate_tool="剪映+AI",
        editor="赵六", version="v1",
        quality_items="钩子力:8分;节奏:7分;卖点:8分;合规:9分;字幕:8分;转化:7分",
        publish_time=datetime(2026, 8, 1),
        publish_platform="抖音", publish_status="已发布"
    )
    db.add_all([video1, video2, video3, video4, video5])
    db.flush()

    # ========== 投流数据 ==========
    ad1 = AdData(
        video_id=video1.id, plan_name="上班族早餐-放量计划",
        spend=300, impressions=15000, clicks=450, ctr=3.0,
        cart_clicks=90, revenue=712, orders=8,
        roi=round(712/300, 2),
        anomaly=None,
        review_suggestion="评论集中问清洗问题，建议在脚本中增加清洗演示环节"
    )
    ad2 = AdData(
        video_id=video2.id, plan_name="健身饮品-测试计划",
        spend=200, impressions=10000, clicks=200, ctr=2.0,
        cart_clicks=35, revenue=178, orders=2,
        roi=round(178/200, 2),
        anomaly="前3秒钩子偏弱，2秒跳出率51%偏高",
        review_suggestion="停投重做脚本，优化前3秒钩子，增加运动场景吸引力"
    )
    ad3 = AdData(
        video_id=video3.id, plan_name="宿舍饮品-放量计划",
        spend=250, impressions=25000, clicks=750, ctr=3.0,
        cart_clicks=220, revenue=1602, orders=18,
        roi=round(1602/250, 2),
        anomaly=None,
        review_suggestion="表现优秀，建议加大预算放量，同时准备宿舍场景2.0版本"
    )
    ad4 = AdData(
        video_id=video4.id, plan_name="家庭饮品-自然流量观察",
        spend=0, impressions=7000, clicks=140, ctr=2.0,
        cart_clicks=48, revenue=356, orders=4,
        roi=0,
        anomaly="自然流量样本较小",
        review_suggestion="先小预算测试，验证转化后考虑放量"
    )
    ad5 = AdData(
        video_id=video5.id, plan_name="办公室下午茶-放量计划",
        spend=400, impressions=20000, clicks=600, ctr=3.0,
        cart_clicks=160, revenue=980, orders=11,
        roi=round(980/400, 2),
        anomaly="购物车点击不错但成交未明显放大",
        review_suggestion="优化购物车落地页，检查价格竞争力，考虑增加限时优惠"
    )
    db.add_all([ad1, ad2, ad3, ad4, ad5])
    db.flush()

    # ========== 私域线索 ==========
    lead1 = Lead(
        lead_code="L001", video_id=video1.id,
        inquiry="这个榨汁杯清洗方便吗？", intent="中",
        follow_status="待跟进", wechat_added="否",
        script_template="亲，这款榨汁杯支持一键清洗功能，加水后双击启动就能自动清洗，非常方便哦~"
    )
    lead2 = Lead(
        lead_code="L002", video_id=video3.id,
        inquiry="价格能不能便宜点？学生党预算有限", intent="高",
        follow_status="待跟进", wechat_added="否",
        script_template="同学你好！现在下单享受学生专属优惠，还送便携袋哦~"
    )
    lead3 = Lead(
        lead_code="L003", video_id=video5.id,
        inquiry="容量够几个人喝？办公室能用吗？", intent="中",
        follow_status="已加微", wechat_added="是",
        script_template="300ml容量刚好一人份，USB充电，在办公室用电脑就能充，特别方便！"
    )
    db.add_all([lead1, lead2, lead3])
    db.flush()

    # ========== 复盘表 ==========
    review = Review(
        review_period="2026年7月第5周",
        product_performance="便携榨汁杯整体表现良好，选品评分85分，月销5000+验证了市场需求",
        content_performance="宿舍饮品方向完播率最高(21%)，健身方向最差(9%)；前3秒钩子质量直接影响完播",
        video_performance="V003宿舍版表现最优，V002健身版需重做脚本；AI辅助制作效率提升约40%",
        ad_performance="整体ROI:宿舍6.41>下午茶2.45>早餐2.37>健身0.89；健身方向需停投",
        problem_analysis="1.前3秒钩子质量是关键变量;2.价格敏感人群转化率更高;3.清洗问题是用户核心顾虑",
        next_action="1.健身版停投重做脚本;2.宿舍版加大预算;3.在脚本中增加清洗演示;4.优化购物车落地页",
        owner="运营负责人",
        deadline=datetime(2026, 8, 10)
    )
    db.add(review)
    db.flush()

    # ========== 知识库 ==========
    knowledge_items = [
        Knowledge(
            knowledge_code="K001", category="商品卖点库",
            source="选品调研", applicable_scene="所有内容创作",
            content_summary="便携榨汁杯核心卖点：便携(500g)、无线(USB充电)、易清洗(一键清洗)、制作快(30秒)、容量适中(300ml)、食品级材质",
            prompt_version="v1.0", usage_effect="已验证有效",
            updater="张三"
        ),
        Knowledge(
            knowledge_code="K002", category="提示词库",
            source="AI工作流", applicable_scene="文生图/文生视频",
            content_summary="产品展示提示词模板：portable blender product shot, clean white background, fresh fruits around, professional lighting, commercial photography style",
            prompt_version="v1.0", usage_effect="生成效果良好",
            updater="赵六"
        ),
        Knowledge(
            knowledge_code="K003", category="投流复盘库",
            source="投流数据", applicable_scene="投流决策",
            content_summary="ROI判断标准：>3优秀继续放量;1.5-3正常优化;1-1.5观察调整;<1考虑停投。2秒跳出率>50%需重做钩子",
            prompt_version="v1.0", usage_effect="判断准确率约85%",
            updater="运营负责人"
        ),
        Knowledge(
            knowledge_code="K004", category="客服话术库",
            source="客服实践", applicable_scene="私域转化",
            content_summary="高频问题话术：清洗问题→一键清洗演示;价格问题→性价比对比+优惠;容量问题→一人份刚好+场景说明",
            prompt_version="v1.0", usage_effect="转化率提升约20%",
            updater="客服主管"
        ),
        Knowledge(
            knowledge_code="K005", category="员工SOP",
            source="团队经验", applicable_scene="新人培训",
            content_summary="视频制作SOP：1.选品评分→2.内容拆解→3.AI生成脚本→4.人工审核→5.素材制作→6.剪辑精修→7.质检→8.发布→9.投流→10.复盘",
            prompt_version="v1.0", usage_effect="新人上手时间缩短50%",
            updater="运营负责人"
        ),
        Knowledge(
            knowledge_code="K006", category="爆款内容库",
            source="竞品分析", applicable_scene="内容策划",
            content_summary="高完播率内容特征：前3秒强钩子(疑问/反常识/利益点)、生活化场景、真实使用体验、节奏紧凑(信息密度高)、结尾有行动指令",
            prompt_version="v1.0", usage_effect="参考后完播率平均提升15%",
            updater="李四"
        ),
    ]
    db.add_all(knowledge_items)

    db.commit()
    enrich_existing_data(db)
    print("模拟数据初始化完成")


