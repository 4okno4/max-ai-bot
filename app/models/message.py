from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.database import Base
import datetime

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    dialog_id = Column(Integer, ForeignKey("dialogs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" или "bot"
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # связи
    dialog = relationship("Dialog", back_populates="messages")
    user = relationship("User", back_populates="messages")
    search_query = relationship("SearchQuery", back_populates="message", uselist=False)