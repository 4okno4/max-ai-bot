from pydantic import BaseModel
from typing import Optional

class UserMessage(BaseModel):
    message: str
    user_id: Optional[int] = None

class BotResponse(BaseModel):
    reply: str