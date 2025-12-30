from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

class Base(DeclarativeBase):
    pass

DB_URL = settings.database_url
connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}

engine = create_engine(
    DB_URL,
    future=True,
    pool_pre_ping=True,
    echo=False,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

# ✅ FastAPI yield dependency (NOT a context manager)
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


# print("DB URL:", engine.url)