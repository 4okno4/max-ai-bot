from sqlalchemy import Column, Integer, String
from app.models.database import Base

class Synonym(Base):
    __tablename__ = "synonyms"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, nullable=False, index=True)
    normalized = Column(String, nullable=False)
    category = Column(String, nullable=True)  # к какой группе синонимов относится