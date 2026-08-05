from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./ecommerce.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_columns():
    """为已有 SQLite 数据库补齐新增原型字段，避免手动删库。"""
    columns = {
        "contents": {"status": "VARCHAR(50) DEFAULT '待拆解'", "priority": "VARCHAR(20) DEFAULT 'P1'", "notes": "TEXT"},
        "scripts": {"title": "VARCHAR(200)", "owner": "VARCHAR(100)", "priority": "VARCHAR(20) DEFAULT 'P1'", "notes": "TEXT"},
        "videos": {"priority": "VARCHAR(20) DEFAULT 'P1'", "notes": "TEXT"},
        "ad_data": {"content_direction": "VARCHAR(200)", "play_count": "INTEGER DEFAULT 0", "bounce_rate_2s": "FLOAT DEFAULT 0", "completion_rate_5s": "FLOAT DEFAULT 0", "completion_rate": "FLOAT DEFAULT 0", "feedback": "TEXT", "owner": "VARCHAR(100)", "status": "VARCHAR(50) DEFAULT '投放中'", "priority": "VARCHAR(20) DEFAULT 'P1'"},
        "leads": {"source_platform": "VARCHAR(100)", "owner": "VARCHAR(100)", "priority": "VARCHAR(20) DEFAULT 'P1'", "last_follow_time": "DATETIME", "notes": "TEXT"},
        "reviews": {"product_id": "INTEGER", "video_id": "INTEGER", "status": "VARCHAR(50) DEFAULT '待复盘'", "priority": "VARCHAR(20) DEFAULT 'P1'", "review_level": "VARCHAR(50)"},
        "knowledge": {"status": "VARCHAR(50) DEFAULT '已生效'", "priority": "VARCHAR(20) DEFAULT 'P1'", "review_status": "VARCHAR(50) DEFAULT '已审核'", "target_user": "VARCHAR(100)", "expiry_reminder": "DATETIME", "notes": "TEXT"},
    }
    with engine.begin() as conn:
        for table, defs in columns.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
            for name, ddl in defs.items():
                if name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
