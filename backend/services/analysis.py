"""数据分析与复盘服务"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Video, AdData, Product

router = APIRouter()


def calculate_metrics(ad: AdData) -> dict:
    """计算关键指标"""
    metrics = {}
    # 购物车点击率：优先按播放量计算，更贴合测试题口径；无播放量时回退到展现量
    base_traffic = ad.play_count or ad.impressions
    if base_traffic and base_traffic > 0:
        metrics["cart_click_rate"] = round(ad.cart_clicks / base_traffic * 100, 2)
    metrics["play_count"] = ad.play_count or 0
    metrics["bounce_rate_2s"] = ad.bounce_rate_2s or 0
    metrics["completion_rate_5s"] = ad.completion_rate_5s or 0
    metrics["completion_rate"] = ad.completion_rate or 0
    # 成交转化率
    if ad.cart_clicks and ad.cart_clicks > 0:
        metrics["conversion_rate"] = round(ad.orders / ad.cart_clicks * 100, 2)
    # ROI
    if ad.spend and ad.spend > 0:
        metrics["roi"] = round(ad.revenue / ad.spend, 2)
    # CPA（单笔成交成本）
    if ad.orders and ad.orders > 0:
        metrics["cpa"] = round(ad.spend / ad.orders, 2)
    # CTR
    if ad.impressions and ad.impressions > 0:
        metrics["ctr"] = round(ad.clicks / ad.impressions * 100, 2)
    return metrics


def judge_anomaly(ad: AdData, video: Video) -> list:
    """异常判断规则"""
    issues = []
    metrics = calculate_metrics(ad)

    # ROI 判断
    roi = metrics.get("roi", 0)
    if ad.spend > 0:
        if roi < 1:
            issues.append({"type": "ROI过低", "severity": "高", "detail": f"ROI={roi}，低于盈亏平衡点"})
        elif roi < 1.5:
            issues.append({"type": "ROI偏低", "severity": "中", "detail": f"ROI={roi}，接近盈亏线"})

    # 内容表现异常
    if ad.bounce_rate_2s and ad.bounce_rate_2s > 50:
        issues.append({"type": "2秒跳出率过高", "severity": "高", "detail": f"2秒跳出率={ad.bounce_rate_2s}%，前3秒钩子需重做"})
    if ad.completion_rate and ad.completion_rate < 10:
        issues.append({"type": "完播率过低", "severity": "高", "detail": f"完播率={ad.completion_rate}%，内容节奏或选题需调整"})
    if ad.ctr and ad.ctr < 2.0:
        issues.append({"type": "点击率偏低", "severity": "中", "detail": f"CTR={ad.ctr}%，内容吸引力不足"})

    # 购物车点击 vs 成交
    if ad.cart_clicks > 0 and ad.orders > 0:
        cvr = ad.orders / ad.cart_clicks * 100
        if cvr < 5:
            issues.append({"type": "转化率偏低", "severity": "中", "detail": f"购物车到成交转化率={cvr:.1f}%，落地页可能有问题"})

    # 消耗高但成交低
    if ad.spend > 300 and ad.revenue < ad.spend:
        issues.append({"type": "消耗未回本", "severity": "高", "detail": f"消耗{ad.spend}元，成交{ad.revenue}元"})

    return issues


def generate_decision(ad: AdData, issues: list) -> str:
    """生成投放决策"""
    if not ad.spend or ad.spend == 0:
        return "小预算测试"

    roi = ad.revenue / ad.spend if ad.spend > 0 else 0
    high_issues = [i for i in issues if i["severity"] == "高"]

    if high_issues:
        return "停投重做"
    elif roi >= 3:
        return "继续放量"
    elif roi >= 1.5:
        return "小幅优化"
    elif roi >= 1:
        return "观察调整"
    else:
        return "考虑停投"


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """仪表盘数据"""
    products = db.query(Product).all()
    videos = db.query(Video).all()
    ads = db.query(AdData).all()

    total_spend = sum(a.spend or 0 for a in ads)
    total_revenue = sum(a.revenue or 0 for a in ads)
    total_orders = sum(a.orders or 0 for a in ads)
    overall_roi = round(total_revenue / total_spend, 2) if total_spend > 0 else 0

    # 各视频表现排名
    video_performance = []
    for ad in ads:
        video = db.query(Video).filter(Video.id == ad.video_id).first()
        if video:
            video_performance.append({
                "video_code": video.video_code,
                "spend": ad.spend,
                "revenue": ad.revenue,
                "orders": ad.orders,
                "roi": round(ad.revenue / ad.spend, 2) if ad.spend and ad.spend > 0 else 0,
                "cart_clicks": ad.cart_clicks,
                "content_direction": ad.content_direction,
                "play_count": ad.play_count,
            })
    video_performance.sort(key=lambda x: x["roi"], reverse=True)

    return {
        "summary": {
            "total_products": len(products),
            "total_videos": len(videos),
            "total_spend": total_spend,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "overall_roi": overall_roi,
        },
        "video_ranking": video_performance,
    }


@router.get("/analysis/all_videos")
def analyze_all_videos(db: Session = Depends(get_db)):
    """所有视频的复盘分析"""
    ads = db.query(AdData).all()
    results = []

    for ad in ads:
        video = db.query(Video).filter(Video.id == ad.video_id).first()
        if not video:
            continue

        metrics = calculate_metrics(ad)
        issues = judge_anomaly(ad, video)
        decision = generate_decision(ad, issues)

        results.append({
            "video_code": video.video_code,
            "metrics": metrics,
            "issues": issues,
            "decision": decision,
            "anomaly": ad.anomaly,
            "suggestion": ad.review_suggestion,
            "content_direction": ad.content_direction,
            "feedback": ad.feedback,
            "priority": ad.priority,
        })

    return results


@router.get("/analysis/video/{video_id}")
def analyze_single_video(video_id: int, db: Session = Depends(get_db)):
    """单个视频的详细分析"""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        return {"error": "视频不存在"}

    ad = db.query(AdData).filter(AdData.video_id == video_id).first()
    if not ad:
        return {"error": "无投流数据"}

    metrics = calculate_metrics(ad)
    issues = judge_anomaly(ad, video)
    decision = generate_decision(ad, issues)

    return {
        "video_code": video.video_code,
        "video_info": {
            "editor": video.editor,
            "platform": video.publish_platform,
            "status": video.publish_status,
            "quality_items": video.quality_items,
        },
        "ad_info": {
            "plan_name": ad.plan_name,
            "spend": ad.spend,
            "impressions": ad.impressions,
            "clicks": ad.clicks,
            "cart_clicks": ad.cart_clicks,
            "revenue": ad.revenue,
            "orders": ad.orders,
        },
        "metrics": metrics,
        "issues": issues,
        "decision": decision,
        "anomaly": ad.anomaly,
        "suggestion": ad.review_suggestion,
    }



@router.get("/today_tasks")
def today_tasks(db: Session = Depends(get_db)):
    """统一今日待处理视图。"""
    from models import Content, Script, Review, Knowledge
    tasks = []
    for p in db.query(Product).filter(Product.status.in_(["待评估", "待选品"])).all():
        tasks.append({"module": "商品库", "code": p.product_code, "title": p.name, "owner": p.owner, "status": p.status, "priority": "P1"})
    for c in db.query(Content).filter(Content.status.in_(["待拆解", "待二创"])).all():
        tasks.append({"module": "内容拆解", "code": c.content_code, "title": c.hook, "owner": c.analyst, "status": c.status, "priority": c.priority})
    for sc in db.query(Script).filter(Script.review_status.in_(["待审核", "已驳回"])).all():
        tasks.append({"module": "脚本分镜", "code": sc.script_code, "title": sc.title or sc.scene_desc, "owner": sc.owner, "status": sc.review_status, "priority": sc.priority})
    for r in db.query(Review).filter(Review.status.in_(["待复盘", "分析中"])).all():
        tasks.append({"module": "数据复盘", "code": f"R{r.id:03d}", "title": r.review_period, "owner": r.owner, "status": r.status, "priority": r.priority})
    order = {"P0": 0, "P1": 1, "P2": 2}
    tasks.sort(key=lambda x: order.get(x.get("priority"), 9))
    return tasks


@router.get("/owner_kanban")
def owner_kanban(db: Session = Depends(get_db)):
    """按负责人看板。"""
    from models import Content, Script, Video, Review
    board = {}
    def add(owner, module, code, status, priority="P1"):
        owner = owner or "未分配"
        board.setdefault(owner, []).append({"module": module, "code": code, "status": status, "priority": priority})
    for p in db.query(Product).all(): add(p.owner, "商品库", p.product_code, p.status)
    for c in db.query(Content).all(): add(c.analyst, "内容拆解", c.content_code, c.status, c.priority)
    for sc in db.query(Script).all(): add(sc.owner, "脚本分镜", sc.script_code, sc.review_status, sc.priority)
    for v in db.query(Video).all(): add(v.editor, "视频任务", v.video_code, v.publish_status, v.priority)
    for r in db.query(Review).all(): add(r.owner, "数据复盘", f"R{r.id:03d}", r.status, r.priority)
    return board


@router.get("/status_kanban")
def status_kanban(db: Session = Depends(get_db)):
    """按状态看板。"""
    from models import Content, Script, Video, Review
    board = {}
    def add(status, module, code, owner=None, priority="P1"):
        status = status or "未设置"
        board.setdefault(status, []).append({"module": module, "code": code, "owner": owner, "priority": priority})
    for p in db.query(Product).all(): add(p.status, "商品库", p.product_code, p.owner)
    for c in db.query(Content).all(): add(c.status, "内容拆解", c.content_code, c.analyst, c.priority)
    for sc in db.query(Script).all(): add(sc.review_status, "脚本分镜", sc.script_code, sc.owner, sc.priority)
    for v in db.query(Video).all(): add(v.publish_status, "视频任务", v.video_code, v.editor, v.priority)
    for r in db.query(Review).all(): add(r.status, "数据复盘", f"R{r.id:03d}", r.owner, r.priority)
    return board


@router.get("/high_priority")
def high_priority(db: Session = Depends(get_db)):
    """复盘结果/高优先级问题视图。"""
    ads = db.query(AdData).all()
    rows = []
    for ad in ads:
        video = db.query(Video).filter(Video.id == ad.video_id).first()
        issues = judge_anomaly(ad, video) if video else []
        if ad.priority == "P0" or issues or (ad.roi is not None and ad.roi < 1):
            rows.append({
                "video_code": video.video_code if video else ad.video_id,
                "content_direction": ad.content_direction,
                "roi": ad.roi,
                "priority": ad.priority,
                "status": ad.status,
                "issues": issues,
                "suggestion": ad.review_suggestion,
                "owner": ad.owner,
            })
    return rows
