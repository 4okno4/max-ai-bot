from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database import Base


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(Integer, primary_key=True, index=True)

    dialog_id = Column(
        Integer,
        ForeignKey("dialogs.id"),
        nullable=False,
        index=True
    )

    message_id = Column(
        Integer,
        ForeignKey("messages.id"),
        nullable=False,
        unique=True,
        index=True
    )

    original_text = Column(String, nullable=False)
    normalized_text = Column(String)

    category = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    purpose = Column(String, nullable=True)
    price_segment = Column(String, nullable=True)

    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)

    power_type = Column(String, nullable=True)
    area_sotka = Column(Float, nullable=True)

    excluded_brand = Column(String, nullable=True)
    excluded_power_type = Column(String, nullable=True)

    confidence_category = Column(Float, default=0.0)
    confidence_purpose = Column(Float, default=0.0)
    confidence_brand = Column(Float, default=0.0)
    confidence_price = Column(Float, default=0.0)

    dialog = relationship("Dialog", back_populates="search_queries")
    message = relationship("Message", back_populates="search_query")

    results = relationship(
        "SearchResult",
        back_populates="search_query",
        cascade="all, delete-orphan"
    )