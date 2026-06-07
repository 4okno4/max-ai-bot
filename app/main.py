from fastapi import FastAPI

from app.api.routes import router
from app.models.database import Base, engine

app = FastAPI(title="MAX AI BOT")

Base.metadata.create_all(bind=engine)
app.include_router(router)


@app.get("/")
def home():
    return {
        "status": "ok",
        "message": "Bot is working"
    }