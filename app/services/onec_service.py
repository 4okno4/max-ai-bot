import logging
import requests
from sqlalchemy.orm import Session
from app.core.config import ONEC_API_URL, ONEC_API_TOKEN
from app.models.product import Product
from app.models.database import SessionLocal
import datetime

logger = logging.getLogger("uvicorn")


def get_products_from_1c(category: str = None, brand: str = None, db: Session = None):
    """
    Интеграционный слой для получения товаров из 1С.
    При отсутствии ONEC_API_URL возвращает данные из локальной базы PostgreSQL.
    """

    # Если база не передана, создаем сессию
    own_db = False
    if db is None:
        db = SessionLocal()
        own_db = True

    try:
        # Если ONEC_API_URL задан, пытаемся получить данные через HTTP
        if ONEC_API_URL:
            headers = {"Content-Type": "application/json"}
            if ONEC_API_TOKEN:
                headers["Authorization"] = f"Bearer {ONEC_API_TOKEN}"

            params = {}
            if category:
                params["category"] = category
            if brand:
                params["brand"] = brand

            try:
                response = requests.get(
                    ONEC_API_URL,
                    headers=headers,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                products_data = response.json()
                # Сохраняем локально
                sync_products_from_1c(db, products_data)
                return products_data
            except requests.RequestException as e:
                logger.error(f"1C API request failed: {e}")

        # Fallback: берем данные из PostgreSQL
        query = db.query(Product)
        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))
        if brand:
            query = query.filter(Product.brand.ilike(f"%{brand}%"))

        products = query.limit(50).all()
        return [
            {
                "external_id": p.external_id,
                "article": p.article,
                "name": p.name,
                "category": p.category,
                "brand": p.brand,
                "price": p.price,
                "stock": p.stock,
                "power_type": p.power_type,
                "area_min": p.area_min,
                "area_max": p.area_max,
                "description": p.description,
                "source": p.source or "local"
            } for p in products
        ]

    finally:
        if own_db:
            db.close()


def sync_products_from_1c(db: Session, products_data: list):
    """
    Синхронизирует данные товаров из 1С с локальной PostgreSQL базой.
    """
    for item in products_data:
        product = db.query(Product).filter(
            (Product.external_id == item.get("external_id")) |
            (Product.article == item.get("article"))
        ).first()

        if product:
            # Обновляем поля
            product.name = item.get("name")
            product.category = item.get("category")
            product.brand = item.get("brand")
            product.price = item.get("price")
            product.stock = item.get("stock")
            product.power_type = item.get("power_type")
            product.area_min = item.get("area_min")
            product.area_max = item.get("area_max")
            product.description = item.get("description")
            product.source = "1c"
            product.updated_at = datetime.datetime.utcnow()
        else:
            # Создаем новую запись
            product = Product(
                external_id=item.get("external_id") or f"local-{datetime.datetime.utcnow().timestamp()}",
                article=item.get("article"),
                name=item.get("name"),
                category=item.get("category"),
                brand=item.get("brand"),
                price=item.get("price"),
                stock=item.get("stock"),
                power_type=item.get("power_type"),
                area_min=item.get("area_min"),
                area_max=item.get("area_max"),
                description=item.get("description"),
                source="1c",
                updated_at=datetime.datetime.utcnow()
            )
            db.add(product)
    db.commit()