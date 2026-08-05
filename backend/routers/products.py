import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Product
from schemas import ProductCreate, ProductOut
from ai_workflow.workflow import call_ai, parse_ai_response

router = APIRouter()


PRODUCT_FIELDS = [
    "product_code", "name", "category", "price_min", "price_max", "commission",
    "sales_heat", "reputation", "target_users", "selling_points", "pain_points",
    "risk_words", "score", "owner", "status",
]


def _first_text(text: str, names: list[str]) -> str:
    for name in names:
        m = re.search(rf"{name}\s*[：:]\s*([^；;\n\r]+)", text, re.I)
        if m:
            return m.group(1).strip()
    return ""


def _num(value) -> float | None:
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group(0)) if m else None


def _parse_price(text: str) -> tuple[float | None, float | None]:
    m = re.search(r"(?:价格|售价|价格区间)\s*[：:]?\s*¥?\s*(\d+(?:\.\d+)?)\s*[-~—至到]\s*¥?\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(?:价格|售价)\s*[：:]?\s*¥?\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        v = float(m.group(1))
        return v, v
    return None, None


def _next_product_code(db: Session) -> str:
    rows = db.query(Product.product_code).filter(Product.product_code.like("P%")).all()
    max_num = 0
    for (code,) in rows:
        digits = "".join(ch for ch in str(code or "") if ch.isdigit())
        if digits:
            max_num = max(max_num, int(digits))
    return f"P{max_num + 1:03d}"


def _heuristic_parse_product(text: str, db: Session) -> dict:
    price_min, price_max = _parse_price(text)
    return {
        "product_code": _first_text(text, ["商品编号", "编号"]) or _next_product_code(db),
        "name": _first_text(text, ["商品名称", "商品名", "产品名称", "名称"]),
        "category": _first_text(text, ["类目", "分类", "品类"]),
        "price_min": price_min,
        "price_max": price_max,
        "commission": _num(_first_text(text, ["佣金", "佣金比例"])),
        "sales_heat": _first_text(text, ["热度", "销量", "销量/热度"]),
        "reputation": _first_text(text, ["口碑", "评价", "好评率"]),
        "target_users": _first_text(text, ["目标人群", "目标用户", "人群"]),
        "selling_points": _first_text(text, ["卖点", "核心卖点", "可表达卖点"]),
        "pain_points": _first_text(text, ["痛点", "用户痛点"]),
        "risk_words": _first_text(text, ["风险词", "合规风险", "禁用词"]),
        "score": _num(_first_text(text, ["评分", "选品评分"])),
        "owner": _first_text(text, ["负责人", "维护人"]) or "选品运营",
        "status": _first_text(text, ["状态"]) or "待评估",
    }


def _normalize_product(data: dict, text: str, db: Session) -> dict:
    fallback = _heuristic_parse_product(text, db)
    result = {}
    for key in PRODUCT_FIELDS:
        value = data.get(key, None) if isinstance(data, dict) else None
        result[key] = value if value not in (None, "") else fallback.get(key)
    for key in ["price_min", "price_max", "commission", "score"]:
        result[key] = _num(result.get(key))
    result["product_code"] = result.get("product_code") or _next_product_code(db)
    result["status"] = result.get("status") or "待评估"
    return result


def _ai_parse_product(text: str, db: Session) -> dict:
    prompt = f"""
你是短视频电商选品运营助手。请从下面文档文本中识别商品信息，只输出 JSON，不要 Markdown。
字段：
product_code,name,category,price_min,price_max,commission,sales_heat,reputation,target_users,selling_points,pain_points,risk_words,score,owner,status
数值字段用数字；缺失填 null。

文档内容：
{text[:12000]}
"""
    parsed = parse_ai_response(call_ai(prompt))
    if parsed.get("local_demo") or parsed.get("error") or parsed.get("parse_error"):
        parsed = {}
    return _normalize_product(parsed, text, db)


def _read_txt(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", errors="ignore")


def _read_docx(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for p in root.findall(".//w:p", ns):
            texts = [t.text or "" for t in p.findall(".//w:t", ns)]
            if texts:
                paragraphs.append("".join(texts))
        return "\n".join(paragraphs)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"docx 解析失败：{str(e)}")


def _read_xlsx(raw: bytes) -> str:
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(raw), data_only=True)
        lines = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                vals = [str(v) for v in row if v is not None]
                if vals:
                    lines.append("；".join(vals))
        return "\n".join(lines)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"xlsx 解析失败：{str(e)}")


def _read_csv(raw: bytes) -> str:
    text = _read_txt(raw)
    rows = csv.reader(io.StringIO(text))
    return "\n".join("；".join(cell for cell in row if cell) for row in rows)


def _extract_document_text(filename: str, raw: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt":
        return _read_txt(raw)
    if ext == ".docx":
        return _read_docx(raw)
    if ext == ".xlsx":
        return _read_xlsx(raw)
    if ext == ".csv":
        return _read_csv(raw)
    raise HTTPException(status_code=400, detail="仅支持 txt/docx/xlsx/csv 文档")


@router.get("/", response_model=List[ProductOut])
def list_products(skip: int = 0, limit: int = 500, status: str = None, db: Session = Depends(get_db)):
    query = db.query(Product)
    if status:
        query = query.filter(Product.status == status)
    return query.order_by(Product.id.desc()).offset(skip).limit(limit).all()


@router.post("/import_document")
async def import_product_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传 txt/docx/xlsx/csv，解析商品字段，返回给前端填入新增商品表单。"""
    filename = file.filename or ""
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空")
    text = _extract_document_text(filename, raw)
    if not text.strip():
        raise HTTPException(status_code=400, detail="未能从文档中读取到文本")
    return {
        "filename": filename,
        "text_preview": text[:1000],
        "parsed": _ai_parse_product(text, db),
    }


@router.get("/{product_id:int}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.post("/", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.put("/{product_id:int}", response_model=ProductOut)
def update_product(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    for key, value in product.model_dump(exclude_unset=True).items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.delete("/{product_id:int}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="商品不存在")
    db.delete(db_product)
    db.commit()
    return {"message": "删除成功"}


@router.get("/view/today")
def today_tasks(db: Session = Depends(get_db)):
    """今日待处理视图"""
    return db.query(Product).filter(Product.status.in_(["待评估", "待选品"])).all()


@router.get("/view/kanban")
def kanban_view(db: Session = Depends(get_db)):
    """按状态看板视图"""
    products = db.query(Product).all()
    kanban = {}
    for p in products:
        kanban.setdefault(p.status, []).append({
            "id": p.id, "name": p.name, "score": p.score, "owner": p.owner
        })
    return kanban

