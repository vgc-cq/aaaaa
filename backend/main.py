from dotenv import load_dotenv
load_dotenv()

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base, ensure_sqlite_columns
from routers import products, content, scripts, videos, ads, reviews, knowledge, review_agent
from ai_workflow import vision
from services import analysis, excel_export

# 创建数据库表并补齐旧库字段
Base.metadata.create_all(bind=engine)
ensure_sqlite_columns()

app = FastAPI(
    title="短视频电商全栈系统",
    description="覆盖选品、内容、脚本、视频、投流、客服、复盘、知识库七大板块",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 本地上传素材静态访问。前端/AI 拆解上传的图片、视频、文档会保存到 backend/uploads。
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# 注册路由
app.include_router(products.router, prefix="/api/products", tags=["商品库"])
app.include_router(content.router, prefix="/api/contents", tags=["内容拆解"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["脚本分镜"])
app.include_router(videos.router, prefix="/api/videos", tags=["视频生产"])
app.include_router(ads.router, prefix="/api/ads", tags=["投流数据"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["数据复盘"])
app.include_router(review_agent.router, prefix="/api/review-agent", tags=["自主复盘智能体"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(vision.router, prefix="/api/ai", tags=["视觉内容拆解"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["数据分析"])
app.include_router(excel_export.router, prefix="/api/export", tags=["数据导出"])


@app.get("/")
def root():
    return {"message": "短视频电商全栈系统 API", "version": "1.0.0"}


@app.on_event("startup")
def startup():
    """启动时插入模拟数据"""
    from data.mock_data import init_mock_data
    from database import SessionLocal
    db = SessionLocal()
    try:
        init_mock_data(db)
    finally:
        db.close()
    # 启动投流数据复盘智能体定时任务（间隔由 REVIEW_INTERVAL_MINUTES 控制，0 表示关闭）
    from ai_workflow.agent_graph import start_review_scheduler
    start_review_scheduler()
    # 启动商品智能体定时巡检（间隔由 PRODUCT_CHECK_INTERVAL_MINUTES 控制，0 表示关闭）
    from ai_workflow.product_agent import start_product_agent_scheduler
    start_product_agent_scheduler()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)



