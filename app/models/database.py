from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# Импорт всех моделей, чтобы Base.metadata.create_all видел таблицы
from app.models.user import User
from app.models.dialog import Dialog
from app.models.message import Message
from app.models.search_query import SearchQuery
from app.models.synonym import Synonym
from app.models.search_cache import SearchCache
from app.models.product import Product
from app.models.search_result import SearchResult