import json

from app.models.dialog import Dialog
from app.models.search_query import SearchQuery
from app.models.search_result import SearchResult
from app.models.user import User
from app.models.message import Message
from app.models.product import Product


def get_or_create_user(db, max_user_id: str, username: str = None):
    """
    Получает пользователя по max_user_id или создаёт нового.
    max_user_id — идентификатор пользователя в мессенджере MAX.
    """
    user = db.query(User).filter(User.max_user_id == str(max_user_id)).first()

    if not user:
        user = User(
            max_user_id=str(max_user_id),
            username=username
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_active_dialog(db, user_id: int):
    """
    Возвращает активный диалог пользователя.
    Если активного диалога нет, создаёт новый.
    """
    dialog = (
        db.query(Dialog)
        .filter(
            Dialog.user_id == user_id,
            Dialog.status == "active"
        )
        .order_by(Dialog.updated_at.desc())
        .first()
    )

    if not dialog:
        dialog = Dialog(
            user_id=user_id,
            status="active"
        )
        db.add(dialog)
        db.commit()
        db.refresh(dialog)

    return dialog


def complete_active_dialogs(db, user_id: int):
    """
    Завершает все активные диалоги пользователя.
    Используется при сбросе диалога.
    """
    active_dialogs = (
        db.query(Dialog)
        .filter(
            Dialog.user_id == user_id,
            Dialog.status == "active"
        )
        .all()
    )

    for dialog in active_dialogs:
        dialog.status = "completed"

    db.commit()


def load_session_from_db(db, user_id: int):
    """
    Загружает параметры последнего поискового запроса из активного диалога.
    Возвращает состояние диалога и id активного диалога.
    """
    dialog = get_active_dialog(db, user_id)

    last_sq = (
        db.query(SearchQuery)
        .filter(SearchQuery.dialog_id == dialog.id)
        .order_by(SearchQuery.id.desc())
        .first()
    )

    session = {
        "category": last_sq.category if last_sq else None,
        "brand": last_sq.brand if last_sq else None,
        "purpose": last_sq.purpose if last_sq else None,
        "price_segment": last_sq.price_segment if last_sq else None,
        "min_price": last_sq.min_price if last_sq else None,
        "max_price": last_sq.max_price if last_sq else None,
        "power_type": last_sq.power_type if last_sq else None,
        "area_sotka": last_sq.area_sotka if last_sq else None,
        "excluded_brand": last_sq.excluded_brand if last_sq else None,
        "excluded_power_type": last_sq.excluded_power_type if last_sq else None,
        "purpose_conf": last_sq.confidence_purpose if last_sq else 0.0,
    }

    return session, dialog.id


def save_search_query(db, dialog_id: int, message_id: int, query_data: dict):
    """
    Сохраняет результат NLP-обработки пользовательского запроса.
    """
    sq = SearchQuery(
        dialog_id=dialog_id,
        message_id=message_id,

        original_text=query_data.get("original_query") or "",
        normalized_text=query_data.get("normalized_query"),

        category=query_data.get("category"),
        brand=query_data.get("brand"),
        purpose=query_data.get("purpose"),
        price_segment=query_data.get("price_segment"),

        min_price=query_data.get("min_price"),
        max_price=query_data.get("max_price"),

        power_type=query_data.get("power_type"),
        area_sotka=query_data.get("area_sotka"),

        excluded_brand=query_data.get("excluded_brand"),
        excluded_power_type=query_data.get("excluded_power_type"),

        confidence_category=query_data.get("confidence", {}).get("category", 0.0),
        confidence_purpose=query_data.get("confidence", {}).get("purpose", 0.0),
        confidence_brand=query_data.get("confidence", {}).get("brand", 0.0),
        confidence_price=query_data.get("confidence", {}).get("price_segment", 0.0),
    )

    db.add(sq)
    db.commit()
    db.refresh(sq)

    return sq.id


def save_message(db, dialog_id: int, user_id: int, role: str, text: str):
    """
    Сохраняет сообщение пользователя или бота.
    role: user / bot
    """
    msg = Message(
        dialog_id=dialog_id,
        user_id=user_id,
        role=role,
        text=text
    )

    db.add(msg)
    db.commit()
    db.refresh(msg)

    return msg.id


def save_search_results(db, search_query_id: int, products_with_scores: list):
    """
    Сохраняет последнюю выдачу товаров.

    products_with_scores должен иметь формат:
    [
        (product, score, reasons),
        ...
    ]
    """
    old_results = (
        db.query(SearchResult)
        .filter(SearchResult.search_query_id == search_query_id)
        .all()
    )

    for result in old_results:
        db.delete(result)

    for index, item in enumerate(products_with_scores, start=1):
        product, score, reasons = item

        result = SearchResult(
            search_query_id=search_query_id,
            product_id=product.id,
            position=index,
            score=float(score),
            reasons_json=json.dumps(reasons, ensure_ascii=False)
        )

        db.add(result)

    db.commit()


def get_last_search_query(db, dialog_id: int):
    """
    Возвращает последний поисковый запрос активного диалога.
    """
    return (
        db.query(SearchQuery)
        .filter(SearchQuery.dialog_id == dialog_id)
        .order_by(SearchQuery.id.desc())
        .first()
    )


def get_last_search_results(db, dialog_id: int):
    """
    Возвращает последние товары, которые бот показывал пользователю.
    Используется для команд:
    - покажи первый;
    - покажи второй;
    - сравни первый и второй;
    - какие характеристики у первого;
    - что лучше из этих.
    """
    last_query = get_last_search_query(db, dialog_id)

    if not last_query:
        return []

    rows = (
        db.query(SearchResult)
        .filter(SearchResult.search_query_id == last_query.id)
        .order_by(SearchResult.position.asc())
        .all()
    )

    result = []

    for row in rows:
        product = db.query(Product).filter(Product.id == row.product_id).first()

        if not product:
            continue

        try:
            reasons = json.loads(row.reasons_json) if row.reasons_json else []
        except json.JSONDecodeError:
            reasons = []

        result.append(
            {
                "position": row.position,
                "product": product,
                "score": row.score,
                "reasons": reasons,
            }
        )

    return result


def get_result_by_position(db, dialog_id: int, position: int):
    """
    Возвращает товар из последней выдачи по номеру.
    Например: пользователь пишет 'покажи второй'.
    """
    results = get_last_search_results(db, dialog_id)

    for item in results:
        if item["position"] == position:
            return item

    return None