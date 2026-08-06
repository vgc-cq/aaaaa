from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---- Product ----
class ProductBase(BaseModel):
    product_code: str
    name: str
    category: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    commission: Optional[float] = None
    sales_heat: Optional[str] = None
    reputation: Optional[str] = None
    target_users: Optional[str] = None
    selling_points: Optional[str] = None
    pain_points: Optional[str] = None
    risk_words: Optional[str] = None
    score: Optional[float] = None
    status: Optional[str] = "待评估"
    owner: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Content ----
class ContentBase(BaseModel):
    content_code: str
    reference_link: Optional[str] = None
    hook: Optional[str] = None
    scene: Optional[str] = None
    target_group: Optional[str] = None
    structure: Optional[str] = None
    conversion_point: Optional[str] = None
    remix_angles: Optional[str] = None
    risk_points: Optional[str] = None
    product_id: Optional[int] = None
    analyst: Optional[str] = None
    status: Optional[str] = "待拆解"
    priority: Optional[str] = "P1"
    notes: Optional[str] = None


class ContentCreate(ContentBase):
    pass


class ContentOut(ContentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Script ----
class ScriptBase(BaseModel):
    script_code: str
    title: Optional[str] = None
    product_id: Optional[int] = None
    content_id: Optional[int] = None
    shot_time: Optional[str] = None
    scene_desc: Optional[str] = None
    voiceover: Optional[str] = None
    subtitle: Optional[str] = None
    camera_move: Optional[str] = None
    material_req: Optional[str] = None
    ai_prompt: Optional[str] = None
    review_status: Optional[str] = "待审核"
    owner: Optional[str] = None
    priority: Optional[str] = "P1"
    notes: Optional[str] = None


class ScriptCreate(ScriptBase):
    pass


class ScriptOut(ScriptBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Video ----
class VideoBase(BaseModel):
    video_code: str
    script_id: Optional[int] = None
    script_title: Optional[str] = None
    product_id: Optional[int] = None
    product_name: Optional[str] = None
    material_status: Optional[str] = "待准备"
    generate_tool: Optional[str] = None
    editor: Optional[str] = None
    version: Optional[str] = "v1"
    quality_items: Optional[str] = None
    publish_time: Optional[datetime] = None
    publish_platform: Optional[str] = None
    publish_status: Optional[str] = "未发布"
    generate_task_id: Optional[str] = None
    generate_status: Optional[str] = None
    video_url: Optional[str] = None
    priority: Optional[str] = "P1"
    notes: Optional[str] = None


class VideoCreate(VideoBase):
    pass


class VideoOut(VideoBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- AdData ----
class AdDataBase(BaseModel):
    video_id: Optional[int] = None
    ad_date: Optional[str] = None
    content_direction: Optional[str] = None
    play_count: Optional[int] = 0
    bounce_rate_2s: Optional[float] = 0
    completion_rate_5s: Optional[float] = 0
    completion_rate: Optional[float] = 0
    plan_name: Optional[str] = None
    spend: Optional[float] = 0
    impressions: Optional[int] = 0
    clicks: Optional[int] = 0
    ctr: Optional[float] = 0
    cart_clicks: Optional[int] = 0
    revenue: Optional[float] = 0
    orders: Optional[int] = 0
    roi: Optional[float] = 0
    anomaly: Optional[str] = None
    review_suggestion: Optional[str] = None
    feedback: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = "投放中"
    priority: Optional[str] = "P1"


class AdDataCreate(AdDataBase):
    pass


class AdDataOut(AdDataBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Review ----
class ReviewBase(BaseModel):
    review_period: str
    product_id: Optional[int] = None
    video_id: Optional[int] = None
    product_performance: Optional[str] = None
    content_performance: Optional[str] = None
    video_performance: Optional[str] = None
    ad_performance: Optional[str] = None
    problem_analysis: Optional[str] = None
    next_action: Optional[str] = None
    owner: Optional[str] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = "待复盘"
    priority: Optional[str] = "P1"
    review_level: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class ReviewOut(ReviewBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Knowledge ----
class KnowledgeBase(BaseModel):
    knowledge_code: str
    category: Optional[str] = None
    source: Optional[str] = None
    applicable_scene: Optional[str] = None
    content_summary: Optional[str] = None
    prompt_version: Optional[str] = None
    usage_effect: Optional[str] = None
    updater: Optional[str] = None
    status: Optional[str] = "已生效"
    priority: Optional[str] = "P1"
    review_status: Optional[str] = "已审核"
    target_user: Optional[str] = None
    expiry_reminder: Optional[datetime] = None
    notes: Optional[str] = None


class KnowledgeCreate(KnowledgeBase):
    pass


class KnowledgeOut(KnowledgeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- AI Workflow ----
class AIWorkflowInput(BaseModel):
    product_name: str
    price_range: str
    target_users: str
    core_scenes: str
    user_pain_points: str
    selling_points: str


class ScriptGenerationInput(BaseModel):
    product_info: AIWorkflowInput
    content_angle: str
    video_duration: int = 30


class AgentInput(BaseModel):
    agent_type: str  # 投流复盘助手
    video_data: dict
    ad_data: dict
    feedback: Optional[str] = None

