from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.models.database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    max_user_id = Column(String, unique=True, nullable=False)  # ID из мессенджера Max
    username = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # связи
    dialogs = relationship("Dialog", back_populates="user")
    messages = relationship("Message", back_populates="user")