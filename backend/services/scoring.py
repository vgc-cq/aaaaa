"""商品选品评分规则（确定性、可解释），供 AI 选品功能使用。

维度与权重：
  热度 25% + 口碑 20% + 佣金 15% + 内容完整度 20% + 合规意识 20%
状态阈值：
  >=80 已选品；60-79 待评估；<60 已淘汰
"""

import re


def _num(value) -> float | None:
    if value is None:
        return None
    m = re.search(r"\d+(?:\.\d+)?", str(value))
    return float(m.group(0)) if m else None


def heat_score(sales_heat) -> int:
    """热度分：从 月销/销量 数字分档"""
    n = _num(sales_heat)
    if n is None:
        return 30
    if n >= 100000:
        return 100
    if n >= 50000:
        return 90
    if n >= 20000:
        return 80
    if n >= 10000:
        return 70
    if n >= 5000:
        return 60
    if n >= 1000:
        return 50
    if n > 0:
        return 40
    return 30


def reputation_score(reputation) -> int:
    """口碑分：评分(4.x) 为主，好评率微调"""
    text = str(reputation or "")
    r = _num(text)
    score = 40
    if r is not None:
        if r >= 4.8:
            score = 100
        elif r >= 4.6:
            score = 85
        elif r >= 4.4:
            score = 70
        elif r >= 4.0:
            score = 55
        else:
            score = 40
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if m:
        rate = float(m.group(1))
        if rate >= 97:
            score = min(100, score + 5)
        elif rate >= 95:
            score = min(100, score + 3)
    return score


def commission_score(commission) -> int:
    """佣金分：比例越高越有利润空间"""
    c = _num(commission)
    if c is None:
        return 30
    if c >= 25:
        return 100
    if c >= 20:
        return 90
    if c >= 15:
        return 75
    if c >= 10:
        return 60
    if c >= 5:
        return 45
    return 30


def content_score(product) -> int:
    """内容完整度分：人群30 + 卖点30 + 痛点20 + 类目20"""
    parts = [
        (bool(product.target_users), 30),
        (bool(product.selling_points), 30),
        (bool(product.pain_points), 20),
        (bool(product.category), 20),
    ]
    return sum(w for filled, w in parts if filled)


def compliance_score(risk_words) -> int:
    """合规意识分：填写了风险词约束视为有合规意识"""
    return 100 if str(risk_words or "").strip() else 70


def score_product(product) -> dict:
    """返回各维度分和总分（0-100）"""
    dims = {
        "heat": heat_score(product.sales_heat),
        "reputation": reputation_score(product.reputation),
        "commission": commission_score(product.commission),
        "content": content_score(product),
        "compliance": compliance_score(product.risk_words),
    }
    weights = {"heat": 0.25, "reputation": 0.20, "commission": 0.15, "content": 0.20, "compliance": 0.20}
    total = round(sum(dims[k] * weights[k] for k in dims))
    return {"dimensions": dims, "total": total}


def status_for_score(score: int) -> str:
    if score >= 80:
        return "已选品"
    if score >= 60:
        return "待评估"
    return "已淘汰"
