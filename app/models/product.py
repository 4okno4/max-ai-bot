from sqlalchemy import Column, Integer, String, Float, DateTime
from app.models.database import Base
import datetime


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, nullable=False, unique=True)
    article = Column(String, nullable=True)
    name = Column(String, nullable=False)
    category = Column(String)
    brand = Column(String)
    price = Column(Float)
    stock = Column(Integer)
    power_type = Column(String, nullable=True)
    area_min = Column(Float, nullable=True)
    area_max = Column(Float, nullable=True)
    description = Column(String, nullable=True)
    source = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)