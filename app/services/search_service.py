from difflib import SequenceMatcher

from app.models.product import Product
from app.services.product_analyzer import analyze_product


POWER_TYPE_LABELS = {
    "gasoline": "бензиновый",
    "electric": "электрический",
    "battery": "аккумуляторный",
    "manual": "ручной",
    "none": "не указан",
    None: "не указан",
}

PURPOSE_LABELS = {
    "wood": "подходит для дров, веток и дерева",
    "grass": "подходит для травы, газона и участка",
    "soil": "подходит для обработки земли и огорода",
    "water": "подходит для воды и полива",
    "garden": "подходит для сада и дачи",
    "farm": "подходит для хозяйства",
}


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def get_all_categories(db):
    rows = db.query(Product.category).filter(Product.category.isnot(None)).distinct().all()
    return sorted([row[0] for row in rows if row[0]])


def get_all_brands(db):
    rows = db.query(Product.brand).filter(Product.brand.isnot(None)).distinct().all()
    return sorted([row[0] for row in rows if row[0]])


def get_products_by_brand(db, brand: str, limit: int | None = 10):
    query = (
        db.query(Product)
        .filter(Product.brand.ilike(f"%{brand}%"))
        .order_by(Product.stock.desc(), Product.price.asc())
    )

    if limit is None:
        return query.all()

    return query.limit(limit).all()


def get_out_of_stock_products(db):
    return (
        db.query(Product)
        .filter((Product.stock == 0) | (Product.stock.is_(None)))
        .order_by(Product.name.asc())
        .all()
    )


def get_available_products(db, category=None, brand=None, product_hint=None, limit: int = 10):
    query = db.query(Product).filter(Product.stock > 0)

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    products = query.all()

    if product_hint:
        products = sorted(
            products,
            key=lambda p: _text_similarity(product_hint, p.name),
            reverse=True
        )

    return products[:limit]


def find_similar_products(db, product_hint=None, category=None, brand=None, limit: int = 5):
    query = db.query(Product).filter(Product.stock > 0)

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    products = query.all()

    scored = []

    for product in products:
        score = 0
        reasons = ["похожая категория или близкое назначение"]

        if product_hint:
            score += int(_text_similarity(product_hint, product.name) * 30)

        if category and product.category and category.lower() in product.category.lower():
            score += 15

        if brand and product.brand and brand.lower() == product.brand.lower():
            score += 15
            reasons.append(f"совпадает с брендом {product.brand}")

        analysis = analyze_product(product)
        score += analysis["score"]

        scored.append((product, score, reasons))

    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[:limit]


def calculate_score(
    product,
    price_category=None,
    purpose=None,
    brand=None,
    min_price=None,
    max_price=None,
    power_type=None,
    area_sotka=None,
    excluded_brand=None,
    excluded_power_type=None
):
    score = 0
    reasons = []

    analysis = analyze_product(product)
    tags = analysis["tags"]

    score += analysis["score"]

    if not product.stock or product.stock <= 0:
        score -= 100
        reasons.append("нет в наличии")
    else:
        score += 8
        reasons.append("есть в наличии")

    if excluded_brand and product.brand and product.brand.lower() == excluded_brand.lower():
        score -= 80
        reasons.append(f"исключён бренд {excluded_brand}")

    if excluded_power_type and product.power_type == excluded_power_type:
        score -= 80
        reasons.append(f"исключён тип питания {POWER_TYPE_LABELS.get(excluded_power_type)}")

    if brand:
        if product.brand and product.brand.lower() == brand.lower():
            score += 20
            reasons.append(f"совпадает с брендом {product.brand}")
        else:
            score -= 8

    if purpose:
        if purpose in tags:
            score += 18
            reasons.append(PURPOSE_LABELS.get(purpose, "соответствует назначению"))
        else:
            score -= 4

    if power_type:
        if product.power_type == power_type:
            score += 18
            reasons.append(f"{POWER_TYPE_LABELS.get(power_type)} тип питания")
        else:
            score -= 30
            reasons.append(f"не совпадает тип питания")

    if area_sotka is not None:
        if product.area_min is not None and product.area_max is not None:
            if product.area_min <= area_sotka <= product.area_max:
                score += 18
                reasons.append(f"подходит для участка около {int(area_sotka)} соток")
            elif area_sotka < product.area_min:
                score -= 2
                reasons.append("модель рассчитана на участок больше указанного")
            else:
                score -= 8
                reasons.append("для такой площади может быть слабоват")

    if min_price is not None:
        if product.price >= min_price:
            score += 4
            reasons.append(f"дороже нижней границы {int(min_price)} ₽")
        else:
            score -= 3

    if max_price is not None:
        if product.price <= max_price:
            score += 12
            reasons.append(f"укладывается в бюджет до {int(max_price)} ₽")
        else:
            score -= 25
            reasons.append(f"выше бюджета до {int(max_price)} ₽")

    if price_category == "cheap":
        if product.price <= 7000:
            score += 10
            reasons.append("самый бюджетный сегмент")
        elif product.price <= 15000:
            score += 8
            reasons.append("недорогой вариант")
        elif product.price <= 30000:
            score += 2
        else:
            score -= 8

    if price_category == "premium":
        if "powerful" in tags:
            score += 12
            reasons.append("есть признаки мощной модели")

        if product.price >= 30000:
            score += 8
        elif product.price >= 15000:
            score += 5
        else:
            score -= 2

    if "trusted_brand" in tags:
        reasons.append("бренд относится к проверенным производителям")

    unique_reasons = []
    for reason in reasons:
        if reason not in unique_reasons:
            unique_reasons.append(reason)

    return score, unique_reasons


def search_products(
    db,
    category=None,
    brand=None,
    price_category=None,
    purpose=None,
    min_price=None,
    max_price=None,
    power_type=None,
    area_sotka=None,
    excluded_brand=None,
    excluded_power_type=None,
    limit: int = 5
):
    """
    Основной поиск товаров.

    Важная логика:
    - категория, бренд, тип питания, исключённый бренд и исключённый тип питания
      работают как строгие фильтры;
    - max_price и min_price тоже работают как строгие фильтры;
    - если строгий поиск ничего не нашёл, функция возвращает пустой список,
      чтобы message_handler мог корректно объяснить ситуацию пользователю.
    """
    query = db.query(Product).filter(Product.stock > 0)

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    if excluded_brand:
        query = query.filter(Product.brand.notilike(f"%{excluded_brand}%"))

    if power_type:
        query = query.filter(Product.power_type == power_type)

    if excluded_power_type:
        query = query.filter(Product.power_type != excluded_power_type)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    products = query.all()

    scored_products = []

    for product in products:
        score, reasons = calculate_score(
            product,
            price_category=price_category,
            purpose=purpose,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            power_type=power_type,
            area_sotka=area_sotka,
            excluded_brand=excluded_brand,
            excluded_power_type=excluded_power_type
        )

        scored_products.append((product, score, reasons))

    scored_products.sort(key=lambda x: x[1], reverse=True)

    if limit is None:
        return scored_products

    return scored_products[:limit]


def search_nearest_more_expensive(
    db,
    category=None,
    brand=None,
    min_price=None,
    max_price=None,
    power_type=None,
    excluded_brand=None,
    excluded_power_type=None,
    limit: int | None = 5
):
    """
    Ищет ближайшие товары дороже указанного бюджета.
    Используется для сценария:
    - мотоблок до 5000
    - покажи ближайшие дороже
    """
    query = db.query(Product).filter(Product.stock > 0)

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    if excluded_brand:
        query = query.filter(Product.brand.notilike(f"%{excluded_brand}%"))

    if power_type:
        query = query.filter(Product.power_type == power_type)

    if excluded_power_type:
        query = query.filter(Product.power_type != excluded_power_type)

    if max_price is not None:
        query = query.filter(Product.price > max_price)

    if min_price is not None:
        query = query.filter(Product.price >= min_price)

    products = query.order_by(Product.price.asc()).limit(limit).all()

    result = []

    for product in products:
        score, reasons = calculate_score(
            product,
            brand=brand,
            min_price=min_price,
            max_price=None,
            power_type=power_type,
            excluded_brand=excluded_brand,
            excluded_power_type=excluded_power_type
        )

        if max_price is not None:
            reasons.append(f"ближайший вариант дороже бюджета {int(max_price)} ₽")

        result.append((product, score, reasons))

    return result


def compare_brands(db, brands: list[str], category=None):
    result = {}

    for brand in brands:
        products = search_products(
            db=db,
            category=category,
            brand=brand,
            limit=1
        )

        if products:
            result[brand] = products[0]
        else:
            result[brand] = None

    return result