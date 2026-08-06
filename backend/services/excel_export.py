"""Excel 导出服务"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Product, Content, Script, Video, AdData, Review, Knowledge
import io

router = APIRouter()


def create_excel(sheets: dict) -> bytes:
    """创建多 Sheet 的 Excel 文件"""
    from openpyxl import Workbook
    wb = Workbook()

    for sheet_name, (headers, rows) in sheets.items():
        ws = wb.active if sheet_name == list(sheets.keys())[0] else wb.create_sheet()
        ws.title = sheet_name
        ws.append(headers)
        for row in rows:
            ws.append(row)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


@router.get("/all")
def export_all(db: Session = Depends(get_db)):
    """导出所有数据为 Excel"""
    sheets = {}

    # 商品库
    products = db.query(Product).all()
    sheets["商品库"] = (
        ["编号", "商品编号", "名称", "类目", "价格区间", "佣金", "热度", "口碑", "评分", "状态", "负责人"],
        [[p.id, p.product_code, p.name, p.category, f"{p.price_min}-{p.price_max}",
          p.commission, p.sales_heat, p.reputation, p.score, p.status, p.owner] for p in products]
    )

    # 内容拆解
    contents = db.query(Content).all()
    sheets["内容拆解"] = (
        ["编号", "内容编号", "钩子", "场景", "人群", "结构", "转化点", "拆解人"],
        [[c.id, c.content_code, c.hook, c.scene, c.target_group, c.structure, c.conversion_point, c.analyst] for c in contents]
    )

    # 脚本分镜
    scripts = db.query(Script).all()
    sheets["脚本分镜"] = (
        ["编号", "脚本编号", "镜头时间", "画面描述", "旁白", "字幕", "AI提示词", "审核状态"],
        [[s.id, s.script_code, s.shot_time, s.scene_desc, s.voiceover, s.subtitle, s.ai_prompt, s.review_status] for s in scripts]
    )

    # 视频生产
    videos = db.query(Video).all()
    sheets["视频生产"] = (
        ["编号", "视频编号", "素材状态", "工具", "负责人", "版本", "平台", "发布状态"],
        [[v.id, v.video_code, v.material_status, v.generate_tool, v.editor, v.version, v.publish_platform, v.publish_status] for v in videos]
    )

    # 投流数据
    ads = db.query(AdData).all()
    sheets["投流数据"] = (
        ["编号", "计划名称", "消耗", "展现", "点击", "CTR", "购物车点击", "成交金额", "订单数", "ROI", "异常", "建议"],
        [[a.id, a.plan_name, a.spend, a.impressions, a.clicks, a.ctr, a.cart_clicks, a.revenue, a.orders, a.roi, a.anomaly, a.review_suggestion] for a in ads]
    )

    # 复盘表
    reviews = db.query(Review).all()
    sheets["复盘表"] = (
        ["编号", "周期", "商品表现", "内容表现", "投流表现", "问题归因", "优化动作", "负责人"],
        [[r.id, r.review_period, r.product_performance, r.content_performance, r.ad_performance, r.problem_analysis, r.next_action, r.owner] for r in reviews]
    )

    # 知识库
    knowledge = db.query(Knowledge).all()
    sheets["知识库"] = (
        ["编号", "知识编号", "分类", "来源", "适用场景", "内容摘要", "版本", "更新人"],
        [[k.id, k.knowledge_code, k.category, k.source, k.applicable_scene, k.content_summary, k.prompt_version, k.updater] for k in knowledge]
    )

    excel_bytes = create_excel(sheets)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ecommerce_data.xlsx"}
    )

