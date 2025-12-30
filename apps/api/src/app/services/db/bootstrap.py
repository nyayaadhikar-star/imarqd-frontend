# apps/api/src/app/db/bootstrap.py
from sqlalchemy import create_engine
from app.core.config import settings
from app.db.models import Base

def create_all():
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
