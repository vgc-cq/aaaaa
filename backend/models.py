from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Product(Base):
    """商品库"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_code = Column(String(50), unique=True, index=True, comment="商品编号")
    name = Column(String(200), comment="商品名称")
    category = Column(String(100), comment="类目")
    price_min = Column(Float, comment="最低价格")
    price_max = Column(Float, comment="最高价格")
    commission = Column(Float, comment="佣金比例")
    sales_heat = Column(String(50), comment="销量/热度")
    reputation = Column(String(50), comment="口碑")
    target_users = Column(Text, comment="目标人群")
    selling_points = Column(Text, comment="卖点")
    pain_points = Column(Text, comment="痛点")
    risk_words = Column(Text, comment="风险词")
    score = Column(Float, comment="选品评分")
    status = Column(String(50), default="待评估", comment="状态")
    owner = Column(String(100), comment="负责人")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    contents = relationship("Content", back_populates="product")
    scripts = relationship("Script", back_populates="product")


class Content(Base):
    """爆款内容拆解表"""
    __tablename__ = "contents"

    id = Column(Integer, primary_key=True, index=True)
    content_code = Column(String(50), unique=True, index=True, comment="内容编号")
    reference_link = Column(String(500), comment="对标链接")
    hook = Column(Text, comment="开头钩子")
    scene = Column(String(200), comment="场景")
    target_group = Column(String(200), comment="人群")
    structure = Column(Text, comment="内容结构")
    conversion_point = Column(Text, comment="转化点")
    remix_angles = Column(Text, comment="可二创角度")
    risk_points = Column(Text, comment="风险点")
    product_id = Column(Integer, ForeignKey("products.id"), comment="适配商品")
    analyst = Column(String(100), comment="拆解人")
    status = Column(String(50), default="待拆解", comment="状态")
    priority = Column(String(20), default="P1", comment="优先级")
    notes = Column(Text, comment="备注/问题")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    product = relationship("Product", back_populates="contents")
    scripts = relationship("Script", back_populates="content")


class Script(Base):
    """秒级脚本分镜表"""
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    script_code = Column(String(50), unique=True, index=True, comment="脚本编号")
    title = Column(String(200), comment="脚本标题/主题")
    product_id = Column(Integer, ForeignKey("products.id"), comment="关联商品")
    content_id = Column(Integer, ForeignKey("contents.id"), comment="关联内容")
    shot_time = Column(String(50), comment="镜头时间")
    scene_desc = Column(Text, comment="画面描述")
    voiceover = Column(Text, comment="旁白")
    subtitle = Column(Text, comment="字幕")
    camera_move = Column(String(100), comment="镜头运动")
    material_req = Column(Text, comment="素材要求")
    ai_prompt = Column(Text, comment="AI提示词")
    review_status = Column(String(50), default="待审核", comment="审核状态")
    owner = Column(String(100), comment="负责人")
    priority = Column(String(20), default="P1", comment="优先级")
    notes = Column(Text, comment="备注/问题")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    product = relationship("Product", back_populates="scripts")
    content = relationship("Content", back_populates="scripts")
    videos = relationship("Video", back_populates="script")


class Video(Base):
    """视频生产任务表"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    video_code = Column(String(50), unique=True, index=True, comment="视频编号")
    script_id = Column(Integer, ForeignKey("scripts.id"), comment="脚本编号")
    material_status = Column(String(50), default="待准备", comment="素材状态")
    generate_tool = Column(String(100), comment="生成工具")
    editor = Column(String(100), comment="剪辑负责人")
    version = Column(String(20), default="v1", comment="版本")
    quality_items = Column(Text, comment="质检项")
    publish_time = Column(DateTime, comment="发布时间")
    publish_platform = Column(String(100), comment="发布平台")
    publish_status = Column(String(50), default="未发布", comment="发布状态")
    priority = Column(String(20), default="P1", comment="优先级")
    notes = Column(Text, comment="备注/问题")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    script = relationship("Script", back_populates="videos")
    ad_data = relationship("AdData", back_populates="video", uselist=False)
    leads = relationship("Lead", back_populates="video")


class AdData(Base):
    """投流数据表"""
    __tablename__ = "ad_data"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), comment="视频编号")
    content_direction = Column(String(200), comment="内容方向")
    play_count = Column(Integer, default=0, comment="播放量")
    bounce_rate_2s = Column(Float, default=0, comment="2秒跳出率")
    completion_rate_5s = Column(Float, default=0, comment="5秒完播率")
    completion_rate = Column(Float, default=0, comment="完播率")
    plan_name = Column(String(200), comment="计划名称")
    spend = Column(Float, default=0, comment="消耗")
    impressions = Column(Integer, default=0, comment="展现")
    clicks = Column(Integer, default=0, comment="点击")
    ctr = Column(Float, default=0, comment="CTR")
    cart_clicks = Column(Integer, default=0, comment="购物车点击")
    revenue = Column(Float, default=0, comment="成交金额")
    orders = Column(Integer, default=0, comment="订单数")
    roi = Column(Float, default=0, comment="ROI")
    anomaly = Column(Text, comment="异常判断")
    review_suggestion = Column(Text, comment="复盘建议")
    feedback = Column(Text, comment="用户反馈")
    owner = Column(String(100), comment="负责人")
    status = Column(String(50), default="投放中", comment="状态")
    priority = Column(String(20), default="P1", comment="优先级")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    video = relationship("Video", back_populates="ad_data")


class Lead(Base):
    """客服私域线索表"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    lead_code = Column(String(50), unique=True, index=True, comment="线索编号")
    video_id = Column(Integer, ForeignKey("videos.id"), comment="来源视频")
    inquiry = Column(Text, comment="咨询内容")
    intent = Column(String(50), comment="用户意向")
    follow_status = Column(String(50), default="待跟进", comment="跟进状态")
    wechat_added = Column(String(10), default="否", comment="加微状态")
    script_template = Column(Text, comment="话术模板")
    next_follow_time = Column(DateTime, comment="下次跟进时间")
    conversion_attr = Column(String(200), comment="成交归因")
    source_platform = Column(String(100), comment="来源平台")
    owner = Column(String(100), comment="负责人")
    priority = Column(String(20), default="P1", comment="优先级")
    last_follow_time = Column(DateTime, comment="最后跟进时间")
    notes = Column(Text, comment="备注/问题")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    video = relationship("Video", back_populates="leads")


class Review(Base):
    """数据复盘表"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    review_period = Column(String(100), comment="复盘周期")
    product_id = Column(Integer, ForeignKey("products.id"), comment="关联商品")
    video_id = Column(Integer, ForeignKey("videos.id"), comment="关联视频")
    product_performance = Column(Text, comment="商品表现")
    content_performance = Column(Text, comment="内容表现")
    video_performance = Column(Text, comment="视频表现")
    ad_performance = Column(Text, comment="投流表现")
    problem_analysis = Column(Text, comment="问题归因")
    next_action = Column(Text, comment="下次优化动作")
    owner = Column(String(100), comment="负责人")
    deadline = Column(DateTime, comment="截止时间")
    status = Column(String(50), default="待复盘", comment="状态")
    priority = Column(String(20), default="P1", comment="优先级")
    review_level = Column(String(50), comment="复盘等级")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Knowledge(Base):
    """知识库/提示词库"""
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_code = Column(String(50), unique=True, index=True, comment="知识编号")
    category = Column(String(100), comment="分类")
    source = Column(String(200), comment="来源")
    applicable_scene = Column(Text, comment="适用场景")
    content_summary = Column(Text, comment="内容摘要")
    prompt_version = Column(String(50), comment="提示词版本")
    usage_effect = Column(Text, comment="使用效果")
    updater = Column(String(100), comment="更新人")
    status = Column(String(50), default="已生效", comment="状态")
    priority = Column(String(20), default="P1", comment="优先级")
    review_status = Column(String(50), default="已审核", comment="审核状态")
    target_user = Column(String(100), comment="适用对象")
    expiry_reminder = Column(DateTime, comment="失效/更新提醒")
    notes = Column(Text, comment="备注")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

