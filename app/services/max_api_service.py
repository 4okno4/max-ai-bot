import requests
import logging
from app.core.config import MAX_BOT_TOKEN

logger = logging.getLogger("uvicorn")
MAX_API_BASE = "https://platform-api.max.ru"


def send_message(user_id: int, text: str) -> dict:
    url = f"{MAX_API_BASE}/messages"

    headers = {
        "Authorization": MAX_BOT_TOKEN,
        "Content-Type": "application/json"
    }

    params = {
        "user_id": int(user_id)
    }

    payload = {
        "text": text
    }

    logger.info(f"Sending message to user_id={user_id} with text={text}")

    response = requests.post(
        url,
        params=params,
        json=payload,
        headers=headers
    )

    if not response.ok:
        logger.error(f"Max API error: {response.status_code} - {response.text}")

    response.raise_for_status()
    return response.json()


def set_webhook(url: str) -> dict:
    """
    Регистрирует URL для получения вебхуков.
    """
    endpoint = f"{MAX_API_BASE}/subscriptions"

    headers = {
        "Authorization": MAX_BOT_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "url": url,
        "update_types": ["message_created", "bot_started"],
        "version": "0.0.1"
    }

    logger.info(f"Setting webhook to {url}")

    response = requests.post(endpoint, json=payload, headers=headers)

    if not response.ok:
        logger.error(f"Failed to set webhook: {response.status_code} - {response.text}")

    response.raise_for_status()
    return response.json()