from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.product import Product
from app.schemas.message import UserMessage, BotResponse
from app.services.message_handler import handle_message, WELCOME_TEXT
from app.services.max_api_service import send_message, set_webhook
import logging
import json

router = APIRouter()
logger = logging.getLogger("uvicorn")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def extract_text_from_max_update(body: dict) -> str:
    """
    Извлекает текст сообщения из разных вариантов структуры webhook MAX.
    """
    text = body.get("text", "")

    if text:
        return text

    message_data = body.get("message", {})

    if isinstance(message_data, dict):
        text = message_data.get("text", "")
        if text:
            return text

        body_data = message_data.get("body", {})
        if isinstance(body_data, dict):
            text = body_data.get("text", "")
            if text:
                return text

        inner_message = message_data.get("message", {})
        if isinstance(inner_message, dict):
            text = inner_message.get("text", "")
            if text:
                return text

    return ""


def extract_user_id_from_max_update(body: dict):
    """
    Извлекает user_id из webhook MAX.
    """
    sender = body.get("sender", {})
    user_id = sender.get("user_id")

    if user_id:
        return user_id

    message_data = body.get("message", {})

    if isinstance(message_data, dict):
        sender = message_data.get("sender", {})
        user_id = sender.get("user_id")

        if user_id:
            return user_id

    user = body.get("user", {})
    return user.get("user_id")


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "MAX AI BOT"
    }


@router.post("/setup_webhook")
def setup_webhook(url: str = None):
    from app.core.config import WEBHOOK_URL

    target = url or WEBHOOK_URL
    result = set_webhook(target)

    return {
        "status": "ok",
        "webhook_url": target,
        "result": result
    }


@router.post("/message", response_model=BotResponse)
def receive_message(data: UserMessage, db: Session = Depends(get_db)):
    """
    Тестовый endpoint для проверки логики без MAX.
    """
    user_id = str(data.user_id) if data.user_id else "1"
    reply = handle_message(user_id, data.message, db)

    return BotResponse(reply=reply)

@router.get("/mock_1c/products")
def mock_1c_products(category: str = None, brand: str = None, db: Session = Depends(get_db)):
    try:
        query = db.query(Product)
        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))
        if brand:
            query = query.filter(Product.brand.ilike(f"%{brand}%"))
        products = query.limit(50).all()
        return [
    {
        "external_id": product.external_id,
        "article": product.article,
        "name": product.name,
        "category": product.category,
        "brand": product.brand,
        "price": product.price,
        "stock": product.stock,
        "power_type": product.power_type,
        "area_min": product.area_min,
        "area_max": product.area_max,
        "description": product.description,
        "source": "1c"
    }
    for product in products
]
    except Exception as e:
        logger.error(f"Error in /mock_1c/products: {e}")
        raise

@router.post("/webhook")
async def max_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook для получения событий от мессенджера MAX.
    """
    try:
        body_bytes = await request.body()

        if not body_bytes:
            logger.warning("Webhook received empty body")
            return {
                "status": "ignored",
                "reason": "empty body"
            }

        body = json.loads(body_bytes)

    except json.JSONDecodeError:
        logger.warning("Webhook received non-JSON body")
        return {
            "status": "ignored",
            "reason": "invalid json"
        }

    except Exception as e:
        logger.error(f"Error reading request body: {e}")
        return {
            "status": "error",
            "detail": str(e)
        }

    logger.info(f"Webhook received: {body}")

    update_type = body.get("update_type")

    if update_type == "bot_started":
        user_id = extract_user_id_from_max_update(body)

        if user_id:
            try:
                send_message(user_id, WELCOME_TEXT)
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}")
                return {
                    "status": "error",
                    "detail": str(e)
                }

        return {
            "status": "ok"
        }

    if update_type == "message_created":
        user_id = extract_user_id_from_max_update(body)
        text = extract_text_from_max_update(body)

        logger.info(f"Extracted user_id={user_id}, text='{text}'")

        if not user_id:
            logger.warning("Missing user_id")
            return {
                "status": "error",
                "detail": "Missing user_id"
            }

        if not text:
            logger.warning("Empty text")
            return {
                "status": "ignored",
                "reason": "empty text"
            }

        reply_text = handle_message(str(user_id), text, db)

        logger.info(f"Reply text: {reply_text}")

        try:
            send_message(user_id, reply_text)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return {
                "status": "error",
                "detail": str(e)
            }

        return {
            "status": "ok"
        }

    return {
        "status": "ignored",
        "reason": "unknown update_type"
    }