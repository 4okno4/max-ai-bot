from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.database import Base
import datetime


class SearchResult(Base):
    """
    Хранит товары, которые были показаны пользователю
    в ответ на поисковый запрос.
    """

    __tablename__ = "search_results"

    id = Column(Integer, primary_key=True, index=True)

    search_query_id = Column(
        Integer,
        ForeignKey("search_queries.id"),
        nullable=False,
        index=True
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    position = Column(Integer, nullable=False)
    score = Column(Float, default=0.0)

    reasons_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    search_query = relationship("SearchQuery", back_populates="results")
    product = relationship("Product")