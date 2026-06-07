import os
from dotenv import load_dotenv

load_dotenv()

def get_env(key, default=None):
    return os.getenv(key, default)

DATABASE_URL = get_env("DATABASE_URL")
MAX_BOT_TOKEN = get_env("MAX_BOT_TOKEN")
WEBHOOK_URL = get_env("WEBHOOK_URL")
ONEC_API_URL = get_env("ONEC_API_URL")
ONEC_API_TOKEN = get_env("ONEC_API_TOKEN")