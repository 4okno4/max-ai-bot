from sqlalchemy import Column, Integer, String, DateTime, Text
from app.models.database import Base
import datetime

class SearchCache(Base):
    __tablename__ = "search_cache"

    id = Column(Integer, primary_key=True, index=True)
    query_hash = Column(String, unique=True, nullable=False, index=True)
    result_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)