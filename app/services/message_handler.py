import re
from sqlalchemy.orm import Session

from app.services import dialog_service, flow_service, search_service, nlp_service
from app.services.session_service import reset_session
from app.services.search_service import POWER_TYPE_LABELS


WELCOME_TEXT = (
    "Здравствуйте! Я помогу подобрать товары по данным 1С.\n\n"
    "Можно написать запрос в свободной форме, например:\n"
    "• нужна бензопила для дров до 15000\n"
    "• нужен мощный триммер для участка 10 соток\n"
    "• подберите аккумуляторный опрыскиватель для сада\n"
    "• есть ли насос Зубр для полива\n"
    "• покажи все товары бренда Stihl\n"
    "• какие бренды есть\n"
    "• сравни Stihl и Champion\n"
    "• что лучше взять для дачи до 15000\n\n"
    "После выдачи товаров можно написать:\n"
    "• покажи второй\n"
    "• характеристики первого\n"
    "• почему подходит первый\n"
    "• сравни первый и второй\n"
    "• что лучше из этих\n"
    "• покажи дешевле"
)


HELP_TEXT = (
    "Я умею подбирать товары не по кнопкам, а по обычному тексту.\n\n"
    "Понимаю:\n"
    "• товар: бензопила, триммер, коса, насос, мотоблок;\n"
    "• задачу: для дров, травы, сада, полива, земли;\n"
    "• бюджет: до 15000, от 10000 до 20000;\n"
    "• площадь: участок 10 соток;\n"
    "• тип питания: бензиновый, электрический, аккумуляторный;\n"
    "• бренд: Stihl, Champion, Bosch, Huter, Patriot;\n"
    "• отрицания: не электрический, не Stihl;\n"
    "• наличие, сравнение и рекомендации.\n\n"
    "Примеры:\n"
    "• нужен не электрический триммер для травы до 15000\n"
    "• покажи второй\n"
    "• характеристики первого\n"
    "• сравни первый и второй\n"
    "• почему подходит третий\n"
    "• покажи дешевле"
)


POSITION_WORDS = {
    "первый": 1,
    "первого": 1,
    "первую": 1,
    "первым": 1,
    "1": 1,
    "1-й": 1,
    "1ый": 1,

    "второй": 2,
    "второго": 2,
    "вторую": 2,
    "вторым": 2,
    "2": 2,
    "2-й": 2,
    "2ой": 2,

    "третий": 3,
    "третьего": 3,
    "третью": 3,
    "третьим": 3,
    "3": 3,
    "3-й": 3,
    "3ий": 3,

    "четвертый": 4,
    "четвертого": 4,
    "четвертую": 4,
    "четвертым": 4,
    "4": 4,
    "4-й": 4,

    "пятый": 5,
    "пятого": 5,
    "пятую": 5,
    "пятым": 5,
    "5": 5,
    "5-й": 5,
}


def normalize_message_text(text: str) -> str:
    """
    Нормализует текст для определения постпоисковых команд.
    """
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_show_all_products_phrase(text: str) -> bool:
    """
    Определяет, что пользователь просит показать все товары
    в рамках уже сохранённого контекста.

    Примеры:
    - все товары
    - покажи все
    - показать все
    - давай все
    - все варианты
    """
    normalized = normalize_message_text(text)

    phrases = [
        "все товары",
        "покажи все",
        "показать все",
        "давай все",
        "все варианты",
        "весь список",
        "покажи товары",
        "показать товары",
    ]

    return normalized in phrases or any(phrase in normalized for phrase in phrases)

def is_show_more_products_phrase(text: str) -> bool:
        """
        Определяет, что пользователь просит показать больше товаров
        по последнему сохранённому контексту.

        Примеры:
        - ещё
        - еще
        - покажи еще
        - покажи ещё
        - давай еще
        - остальные
        """
        normalized = normalize_message_text(text)

        phrases = [
            "еще",
            "ещё",
            "покажи еще",
            "покажи ещё",
            "давай еще",
            "давай ещё",
            "остальные",
            "покажи остальные",
            "еще товары",
            "ещё товары",
            "еще варианты",
            "ещё варианты",
        ]

        return normalized in phrases or any(phrase in normalized for phrase in phrases)
def build_all_context_products_reply(db, session_state: dict):
    """
    Показывает все товары по текущему контексту:
    категория, бренд, бюджет, тип питания, площадь и ограничения.
    """
    products = search_service.search_products(
        db=db,
        category=session_state.get("category"),
        brand=session_state.get("brand"),
        price_category=session_state.get("price_segment"),
        purpose=session_state.get("purpose"),
        min_price=session_state.get("min_price"),
        max_price=session_state.get("max_price"),
        power_type=session_state.get("power_type"),
        area_sotka=session_state.get("area_sotka"),
        excluded_brand=session_state.get("excluded_brand"),
        excluded_power_type=session_state.get("excluded_power_type"),
        limit=None
    )

    if not products:
        return (
            "По текущим условиям больше товаров не найдено.\n\n"
            "Можно сбросить диалог или изменить параметры: бренд, бюджет, тип питания или категорию."
        )

    session_state["show_all_requested"] = True

    return build_reply(products, session_state=session_state)

def build_context_brand_products_reply(db, brand: str):
    """
    Показывает все товары бренда из сохранённого контекста.
    Используется, когда пользователь сначала написал бренд,
    а потом ответил: 'все товары'.
    """
    products = search_service.get_products_by_brand(db, brand, limit=20)

    if not products:
        brands = search_service.get_all_brands(db)
        return (
            f"Товаров бренда {brand} сейчас не нашёл.\n\n"
            f"Доступные бренды: {', '.join(brands)}."
        )

    lines = [
        f"Показал все товары бренда {brand}:",
        ""
    ]

    for index, product in enumerate(products, start=1):
        lines.append(f"{index}. {product.name}")
        lines.append(f"Цена: {int(product.price)} ₽")
        lines.append(f"Остаток: {product.stock} шт.")
        lines.append(f"Тип питания: {POWER_TYPE_LABELS.get(product.power_type, 'не указан')}")

        if product.area_min is not None and product.area_max is not None:
            lines.append(
                f"Рекомендуемая площадь: от {int(product.area_min)} до {int(product.area_max)} соток"
            )

        lines.append("")

    lines.append(
        "Можно уточнить категорию, например: "
        f"«бензопилы {brand}», «триммеры {brand}» или «что лучше из этих»."
    )

    return "\n".join(lines)

def extract_positions(text: str) -> list[int]:
    """
    Извлекает номера товаров из фразы:
    - покажи второй
    - характеристики первого
    - сравни первый и третий
    - сравни 1 и 2
    """
    normalized = normalize_message_text(text)
    positions = []

    for word, number in POSITION_WORDS.items():
        pattern = rf"(^|\s){re.escape(word)}($|\s)"
        if re.search(pattern, normalized):
            if number not in positions:
                positions.append(number)

    numeric_matches = re.findall(r"\b([1-5])\b", normalized)
    for item in numeric_matches:
        number = int(item)
        if number not in positions:
            positions.append(number)

    return positions


def detect_post_search_command(text: str) -> dict:
    """
    Определяет команды, которые относятся к последней выдаче товаров.
    """
    normalized = normalize_message_text(text)
    positions = extract_positions(normalized)

    if any(phrase in normalized for phrase in [
        "что лучше из этих",
        "какой лучше",
        "какая лучше",
        "какое лучше",
        "лучший из этих",
        "лучше из этих",
        "что выбрать из этих",
        "какой выбрать"
    ]):
        return {
            "type": "best_from_last",
            "positions": positions
        }

    if any(phrase in normalized for phrase in [
        "сравни",
        "сравнить",
        "сравнение",
        "чем отличается",
        "отличия"
    ]) and positions:
        return {
            "type": "compare_positions",
            "positions": positions
        }

    if any(phrase in normalized for phrase in [
        "характеристики",
        "характеристика",
        "подробнее",
        "подробно",
        "описание",
        "расскажи про",
        "информация о"
    ]) and positions:
        return {
            "type": "product_details",
            "positions": positions
        }

    if any(phrase in normalized for phrase in [
        "почему подходит",
        "почему этот",
        "почему эта",
        "почему оно",
        "почему он",
        "почему она",
        "почему выбрал",
        "почему рекоменд"
    ]):
        return {
            "type": "explain_product",
            "positions": positions or [1]
        }

    if any(phrase in normalized for phrase in [
        "покажи дешевле",
        "есть дешевле",
        "подешевле",
        "дешевле"
    ]):
        return {
            "type": "show_cheaper",
            "positions": positions
        }

    if any(phrase in normalized for phrase in [
        "покажи дороже",
        "есть дороже",
        "подороже",
        "дороже"
    ]):
        return {
            "type": "show_more_expensive",
            "positions": positions
        }

    if any(phrase in normalized for phrase in [
        "покажи",
        "открой",
        "выведи",
        "дай"
    ]) and positions:
        return {
            "type": "show_product",
            "positions": positions
        }

    if positions and len(normalized.split()) <= 3:
        return {
            "type": "show_product",
            "positions": positions
        }

    return {
        "type": None,
        "positions": []
    }


def save_user_and_bot_messages(db, user_db_id, user_text, bot_text):
    dialog = dialog_service.get_active_dialog(db, user_db_id)

    dialog_service.save_message(
        db=db,
        dialog_id=dialog.id,
        user_id=user_db_id,
        role="user",
        text=user_text
    )

    dialog_service.save_message(
        db=db,
        dialog_id=dialog.id,
        user_id=user_db_id,
        role="bot",
        text=bot_text
    )


def format_product_short(product):
    power = POWER_TYPE_LABELS.get(product.power_type, "не указан")

    area = ""
    if product.area_min is not None and product.area_max is not None:
        area = f"\nРекомендуемая площадь: от {int(product.area_min)} до {int(product.area_max)} соток"

    return (
        f"• {product.name}\n"
        f"Цена: {int(product.price)} ₽\n"
        f"Остаток: {product.stock} шт.\n"
        f"Тип питания: {power}"
        f"{area}"
    )


def format_product_card(product, position=None, score=None, reasons=None):
    """
    Формирует подробную карточку товара.
    """
    reasons = reasons or []
    power = POWER_TYPE_LABELS.get(product.power_type, "не указан")

    title = f"{position}. {product.name}" if position else product.name

    lines = [
        title,
        f"Категория: {product.category or 'не указана'}",
        f"Бренд: {product.brand or 'не указан'}",
        f"Цена: {int(product.price)} ₽" if product.price is not None else "Цена: не указана",
        f"Остаток на складе: {product.stock} шт." if product.stock is not None else "Остаток на складе: не указан",
        f"Тип питания: {power}",
    ]

    if product.area_min is not None and product.area_max is not None:
        lines.append(
            f"Рекомендуемая площадь: от {int(product.area_min)} до {int(product.area_max)} соток"
        )

    if score is not None:
        lines.append(f"Оценка соответствия запросу: {int(score)}")

    useful_reasons = [
        reason for reason in reasons
        if not str(reason).startswith("исключ")
    ]

    if useful_reasons:
        lines.append("")
        lines.append("Почему подходит:")
        for reason in useful_reasons[:5]:
            lines.append(f"• {reason}")

    return "\n".join(lines)


def build_reply(products, session_state=None, fallback=False):
    session_state = session_state or {}

    lines = []

    if fallback:
        lines.append("Точного совпадения не нашёл, но могу предложить похожие варианты:")
    else:
        lines.append("Подобрал подходящие товары:")

    if session_state.get("max_price"):
        lines.append(f"Бюджет: до {int(session_state['max_price'])} ₽")

    if session_state.get("min_price"):
        lines.append(f"Минимальная цена: от {int(session_state['min_price'])} ₽")

    if session_state.get("area_sotka"):
        lines.append(f"Площадь участка: около {int(session_state['area_sotka'])} соток")

    if session_state.get("power_type"):
        lines.append(
            f"Тип питания: {POWER_TYPE_LABELS.get(session_state['power_type'], session_state['power_type'])}"
        )

    if session_state.get("excluded_brand"):
        lines.append(f"Исключён бренд: {session_state['excluded_brand']}")

    if session_state.get("excluded_power_type"):
        lines.append(
            f"Исключён тип питания: {POWER_TYPE_LABELS.get(session_state['excluded_power_type'])}"
        )

    lines.append("")

    for index, item in enumerate(products, start=1):
        product, score, reasons = item
        power = POWER_TYPE_LABELS.get(product.power_type, "не указан")

        lines.append(f"{index}. {product.name}")
        lines.append(f"Цена: {int(product.price)} ₽")
        lines.append(f"Остаток на складе: {product.stock} шт.")
        lines.append(f"Тип питания: {power}")

        if product.area_min is not None and product.area_max is not None:
            lines.append(
                f"Рекомендуемая площадь: от {int(product.area_min)} до {int(product.area_max)} соток"
            )

        lines.append(f"Оценка соответствия запросу: {int(score)}")

        good_reasons = [r for r in reasons if not str(r).startswith("исключ")]
        if good_reasons:
            lines.append("Почему подходит: " + "; ".join(good_reasons[:4]) + ".")

        lines.append("")

    if session_state.get("show_all_requested"):
        if session_state.get("category"):
            lines.append(
                f"Это все найденные товары категории «{session_state.get('category')}» по текущим условиям."
            )
        elif session_state.get("brand"):
            lines.append(
                f"Это все найденные товары бренда «{session_state.get('brand')}» по текущим условиям."
            )
        else:
            lines.append("Это все найденные товары по текущему запросу.")
    else:
        lines.append(
            "Можно уточнить запрос: указать бюджет, бренд, тип питания, площадь участка "
            "или написать «покажи второй», «характеристики первого», «сравни первый и второй». "
            "Чтобы увидеть больше вариантов, напишите «покажи все»."
        )

    return "\n".join(lines)


def build_brands_reply(db):
    brands = search_service.get_all_brands(db)

    if not brands:
        return "В базе пока нет брендов."

    return (
        "Сейчас в базе есть такие бренды:\n\n"
        + ", ".join(brands)
        + ".\n\n"
        "Можно написать, например: «покажи товары бренда Stihl» или «сравни Stihl и Champion»."
    )


def build_categories_reply(db):
    categories = search_service.get_all_categories(db)

    if not categories:
        return "В базе пока нет товарных категорий."

    return (
        "Сейчас можно подобрать товары из таких категорий:\n\n"
        + "\n".join(f"• {category}" for category in categories)
        + "\n\nМожно написать задачу обычными словами: "
          "«нужно косить траву», «нужно пилить дрова», «нужен полив участка»."
    )


def build_out_of_stock_reply(db):
    products = search_service.get_out_of_stock_products(db)

    if not products:
        return "Сейчас все товары из базы есть в наличии. Позиции с нулевым остатком не найдены."

    lines = ["Сейчас нет в наличии:"]

    for product in products:
        lines.append("")
        lines.append(f"• {product.name}")
        lines.append(f"Цена: {int(product.price)} ₽")

    return "\n".join(lines)


def build_availability_reply(db, query_data):
    products = search_service.get_available_products(
        db=db,
        category=query_data.get("category"),
        brand=query_data.get("brand"),
        product_hint=query_data.get("product_hint"),
        limit=5
    )

    if products:
        lines = ["Проверил наличие. Есть такие варианты:", ""]

        for product in products:
            lines.append(format_product_short(product))
            lines.append("")

        return "\n".join(lines)

    similar = search_service.find_similar_products(
        db=db,
        product_hint=query_data.get("product_hint"),
        category=query_data.get("category"),
        brand=query_data.get("brand"),
        limit=5
    )

    if similar:
        return build_reply(similar, fallback=True)

    return (
        "Точного товара в наличии не нашёл. "
        "Попробуйте написать категорию проще, например: бензопила, триммер, насос, мотоблок."
    )


def build_brand_products_reply(db, brand):
    products = search_service.get_products_by_brand(db, brand)

    if not products:
        brands = search_service.get_all_brands(db)
        return (
            f"Товаров бренда {brand} сейчас не нашёл.\n\n"
            f"Доступные бренды: {', '.join(brands)}."
        )

    lines = [f"Товары бренда {brand}:", ""]

    for product in products:
        lines.append(format_product_short(product))
        lines.append("")

    return "\n".join(lines)


def build_compare_reply(db, query_data):
    brands = query_data.get("brands") or []

    if len(brands) < 2:
        return (
            "Для сравнения напишите два бренда или два товара. "
            "Например: «сравни Stihl и Champion»."
        )

    compared = search_service.compare_brands(
        db=db,
        brands=brands[:2],
        category=query_data.get("category")
    )

    lines = ["Сравнил подходящие варианты:", ""]

    best_product = None
    best_score = -999

    for brand, item in compared.items():
        lines.append(f"{brand}:")

        if not item:
            lines.append("• подходящих товаров не найдено")
            lines.append("")
            continue

        product, score, reasons = item

        lines.append(f"• {product.name}")
        lines.append(f"Цена: {int(product.price)} ₽")
        lines.append(f"Остаток: {product.stock} шт.")
        lines.append(f"Оценка: {int(score)}")

        if reasons:
            lines.append("Плюсы: " + "; ".join(reasons[:4]) + ".")

        lines.append("")

        if score > best_score:
            best_score = score
            best_product = product

    if best_product:
        lines.append(
            f"Рекомендация: я бы выбрал {best_product.name}, "
            f"потому что он лучше подходит по совокупности параметров."
        )

    return "\n".join(lines)


def build_no_last_results_reply():
    return (
        "Пока нет последней выдачи товаров для такой команды.\n"
        "Сначала выполните поиск, например: «нужен триммер до 15000», "
        "а потом можно написать «покажи второй» или «сравни первый и второй»."
    )


def build_show_product_reply(db, dialog_id: int, position: int):
    item = dialog_service.get_result_by_position(db, dialog_id, position)

    if not item:
        return (
            f"В последней выдаче нет товара под номером {position}. "
            "Попробуйте выбрать номер из показанного списка."
        )

    product = item["product"]
    return format_product_card(
        product=product,
        position=item["position"],
        score=item["score"],
        reasons=item["reasons"]
    )


def build_product_details_reply(db, dialog_id: int, position: int):
    item = dialog_service.get_result_by_position(db, dialog_id, position)

    if not item:
        return (
            f"Не нашёл товар под номером {position} в последней выдаче. "
            "Сначала выполните поиск или выберите другой номер."
        )

    product = item["product"]
    power = POWER_TYPE_LABELS.get(product.power_type, "не указан")

    lines = [
        f"Характеристики товара №{position}:",
        "",
        f"Наименование: {product.name}",
        f"Категория: {product.category or 'не указана'}",
        f"Бренд: {product.brand or 'не указан'}",
        f"Цена: {int(product.price)} ₽" if product.price is not None else "Цена: не указана",
        f"Остаток: {product.stock} шт." if product.stock is not None else "Остаток: не указан",
        f"Тип питания: {power}",
    ]

    if product.area_min is not None and product.area_max is not None:
        lines.append(
            f"Рекомендуемая площадь применения: от {int(product.area_min)} до {int(product.area_max)} соток"
        )

    lines.append("")
    lines.append(f"Оценка соответствия последнему запросу: {int(item['score'])}")

    if item["reasons"]:
        lines.append("")
        lines.append("Причины подбора:")
        for reason in item["reasons"][:6]:
            lines.append(f"• {reason}")

    return "\n".join(lines)


def build_explain_product_reply(db, dialog_id: int, position: int):
    item = dialog_service.get_result_by_position(db, dialog_id, position)

    if not item:
        return (
            f"Не могу объяснить товар №{position}, потому что его нет в последней выдаче. "
            "Сначала выполните поиск."
        )

    product = item["product"]
    reasons = item["reasons"]

    lines = [
        f"Товар №{position} — {product.name}.",
        f"Оценка соответствия последнему запросу: {int(item['score'])}.",
        "",
    ]

    if reasons:
        lines.append("Я выбрал его по следующим причинам:")
        for reason in reasons[:6]:
            lines.append(f"• {reason}")
    else:
        lines.append(
            "У товара хорошее совпадение с последним запросом по категории, названию или характеристикам."
        )

    return "\n".join(lines)


def build_compare_positions_reply(db, dialog_id: int, positions: list[int]):
    if len(positions) < 2:
        return "Для сравнения выберите два товара, например: «сравни первый и второй»."

    first = dialog_service.get_result_by_position(db, dialog_id, positions[0])
    second = dialog_service.get_result_by_position(db, dialog_id, positions[1])

    if not first or not second:
        return (
            "Не нашёл один из выбранных товаров в последней выдаче. "
            "Попробуйте написать, например: «сравни первый и второй»."
        )

    p1 = first["product"]
    p2 = second["product"]

    lines = [
        f"Сравнение товара №{positions[0]} и товара №{positions[1]}:",
        "",
        f"1) {p1.name}",
        f"Цена: {int(p1.price)} ₽",
        f"Остаток: {p1.stock} шт.",
        f"Тип питания: {POWER_TYPE_LABELS.get(p1.power_type, 'не указан')}",
        f"Оценка: {int(first['score'])}",
        "",
        f"2) {p2.name}",
        f"Цена: {int(p2.price)} ₽",
        f"Остаток: {p2.stock} шт.",
        f"Тип питания: {POWER_TYPE_LABELS.get(p2.power_type, 'не указан')}",
        f"Оценка: {int(second['score'])}",
        "",
    ]

    if first["score"] > second["score"]:
        winner = p1
        winner_position = positions[0]
    elif second["score"] > first["score"]:
        winner = p2
        winner_position = positions[1]
    else:
        winner = None
        winner_position = None

    if winner:
        lines.append(
            f"Рекомендация: лучше выбрать товар №{winner_position} — {winner.name}, "
            "потому что он выше оценён по соответствию последнему запросу."
        )
    else:
        cheaper = p1 if p1.price <= p2.price else p2
        lines.append(
            f"По оценке товары примерно равны. Если важна цена, выгоднее {cheaper.name}."
        )

    return "\n".join(lines)


def build_best_from_last_reply(db, dialog_id: int):
    results = dialog_service.get_last_search_results(db, dialog_id)

    if not results:
        return build_no_last_results_reply()

    best = max(results, key=lambda item: item["score"])
    product = best["product"]

    lines = [
        f"Из этих вариантов я бы выбрал №{best['position']} — {product.name}.",
        "",
        f"Цена: {int(product.price)} ₽",
        f"Остаток: {product.stock} шт.",
        f"Тип питания: {POWER_TYPE_LABELS.get(product.power_type, 'не указан')}",
        f"Оценка соответствия: {int(best['score'])}",
    ]

    if best["reasons"]:
        lines.append("")
        lines.append("Почему именно он:")
        for reason in best["reasons"][:5]:
            lines.append(f"• {reason}")

    return "\n".join(lines)


def build_sorted_last_results_reply(db, dialog_id: int, mode: str):
    results = dialog_service.get_last_search_results(db, dialog_id)

    if not results:
        return build_no_last_results_reply()

    if mode == "cheaper":
        sorted_results = sorted(results, key=lambda item: item["product"].price or 0)
        title = "Показал варианты из последней выдачи от более дешёвых к более дорогим:"
    else:
        sorted_results = sorted(results, key=lambda item: item["product"].price or 0, reverse=True)
        title = "Показал варианты из последней выдачи от более дорогих к более дешёвым:"

    lines = [title, ""]

    for item in sorted_results:
        product = item["product"]
        lines.append(f"{item['position']}. {product.name}")
        lines.append(f"Цена: {int(product.price)} ₽")
        lines.append(f"Остаток: {product.stock} шт.")
        lines.append(f"Оценка соответствия: {int(item['score'])}")
        lines.append("")

    lines.append(
        "Можно написать «характеристики первого», «покажи второй» или «сравни первый и второй»."
    )

    return "\n".join(lines)


def handle_post_search_command(db, dialog_id: int, command: dict):
    command_type = command.get("type")
    positions = command.get("positions") or []

    if not command_type:
        return None

    if command_type == "show_product":
        return build_show_product_reply(db, dialog_id, positions[0])

    if command_type == "product_details":
        return build_product_details_reply(db, dialog_id, positions[0])

    if command_type == "explain_product":
        return build_explain_product_reply(db, dialog_id, positions[0])

    if command_type == "compare_positions":
        return build_compare_positions_reply(db, dialog_id, positions)

    if command_type == "best_from_last":
        return build_best_from_last_reply(db, dialog_id)

    if command_type == "show_cheaper":
        return build_sorted_last_results_reply(db, dialog_id, mode="cheaper")

    if command_type == "show_more_expensive":
        return build_sorted_last_results_reply(db, dialog_id, mode="expensive")

    return None


def merge_session(session_state, query_data):
    """
    Объединяет сохранённый контекст диалога с новым запросом пользователя.
    Если пользователь сменил категорию, часть старого контекста сбрасывается.
    """
    if query_data.get("category") and query_data.get("category") != session_state.get("category"):
        session_state["purpose"] = None
        session_state["price_segment"] = None
        session_state["min_price"] = None
        session_state["max_price"] = None
        session_state["power_type"] = None
        session_state["area_sotka"] = None
        session_state["excluded_brand"] = None
        session_state["excluded_power_type"] = None
        session_state["purpose_conf"] = 0.0

    fields = [
        "category",
        "brand",
        "purpose",
        "price_segment",
        "min_price",
        "max_price",
        "power_type",
        "area_sotka",
        "excluded_brand",
        "excluded_power_type",
    ]

    for field in fields:
        if query_data.get(field) is not None:
            session_state[field] = query_data.get(field)

    if query_data.get("purpose"):
        session_state["purpose_conf"] = query_data["confidence"]["purpose"]

    return session_state


def make_query_data_for_save(query_data, session_state):
    return {
        "original_query": query_data.get("original_query"),
        "normalized_query": query_data.get("normalized_query"),

        "category": session_state.get("category"),
        "brand": session_state.get("brand"),
        "purpose": session_state.get("purpose"),
        "price_segment": session_state.get("price_segment"),

        "min_price": session_state.get("min_price"),
        "max_price": session_state.get("max_price"),

        "power_type": session_state.get("power_type"),
        "area_sotka": session_state.get("area_sotka"),

        "excluded_brand": session_state.get("excluded_brand"),
        "excluded_power_type": session_state.get("excluded_power_type"),

        "confidence": {
            "category": 1.0 if session_state.get("category") else 0.0,
            "purpose": session_state.get("purpose_conf", 0.0),
            "brand": 1.0 if session_state.get("brand") else 0.0,
            "price_segment": 1.0 if (
                session_state.get("price_segment")
                or session_state.get("min_price")
                or session_state.get("max_price")
            ) else 0.0,
        }
    }


def handle_message(user_id_from_max: str, message_text: str, db: Session) -> str:
    user = dialog_service.get_or_create_user(db, str(user_id_from_max))
    user_db_id = user.id

    query_data = nlp_service.process_user_query(message_text)
    intent = query_data.get("intent")

    if intent == "greeting":
        reset_session(db, user_db_id)
        save_user_and_bot_messages(db, user_db_id, message_text, WELCOME_TEXT)
        return WELCOME_TEXT

    if intent == "help":
        save_user_and_bot_messages(db, user_db_id, message_text, HELP_TEXT)
        return HELP_TEXT

    if intent == "reset":
        reset_session(db, user_db_id)
        reply = (
            "Диалог сброшен. Напишите, что нужно подобрать. "
            "Например: «бензопила до 15000», «триммер для травы», «насос для полива»."
        )
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    dialog = dialog_service.get_active_dialog(db, user_db_id)

    session_state, _ = dialog_service.load_session_from_db(db, user_db_id)

    show_all_phrase = is_show_all_products_phrase(message_text)
    show_more_phrase = is_show_more_products_phrase(message_text)

    if show_all_phrase or show_more_phrase:
        if session_state.get("category") or session_state.get("brand"):
            reply = build_all_context_products_reply(db, session_state)
            save_user_and_bot_messages(db, user_db_id, message_text, reply)
            return reply

        if show_all_phrase:
            categories = search_service.get_all_categories(db)
            reply = (
               "Могу показать все товары, но лучше выбрать категорию, чтобы список был понятнее.\n\n"
               "Сейчас доступны категории:\n"
               + "\n".join(f"• {category}" for category in categories)
               + "\n\nНапример: «покажи все триммеры», «все бензопилы» или «все насосы»."
            )
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    post_command = detect_post_search_command(message_text)

    if post_command.get("type"):
        reply = handle_post_search_command(db, dialog.id, post_command)

        if reply:
            save_user_and_bot_messages(db, user_db_id, message_text, reply)
            return reply

    if intent == "list_brands":
        reply = build_brands_reply(db)
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    if intent == "list_categories":
        reply = build_categories_reply(db)
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    if intent == "out_of_stock":
        reply = build_out_of_stock_reply(db)
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    if intent == "availability":
        reply = build_availability_reply(db, query_data)
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    if intent == "compare" and len(query_data.get("brands") or []) >= 2:
        reply = build_compare_reply(db, query_data)
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    if intent == "list_products" and query_data.get("brand"):
        reply = build_brand_products_reply(db, query_data["brand"])
        save_user_and_bot_messages(db, user_db_id, message_text, reply)
        return reply

    msg_id = dialog_service.save_message(
        db=db,
        dialog_id=dialog.id,
        user_id=user_db_id,
        role="user",
        text=message_text
    )


    if intent == "no_preference":
        if not session_state.get("category"):
            reply = (
                "Хорошо, тогда могу предложить самые универсальные товары. "
                "Но сначала напишите хотя бы категорию: триммер, бензопила, насос, мотоблок или культиватор."
            )
            dialog_service.save_message(db, dialog.id, user_db_id, "bot", reply)
            return reply

    session_state = merge_session(session_state, query_data)

    if is_show_all_products_phrase(message_text) or intent == "no_preference":
        session_state["skip_clarification"] = True

    merged_query_data = make_query_data_for_save(query_data, session_state)

    search_query_id = dialog_service.save_search_query(
        db=db,
        dialog_id=dialog.id,
        message_id=msg_id,
        query_data=merged_query_data
    )

    step = flow_service.next_dialog_step(session_state)

    if step.get("action") == "ask":
        reply = step.get("message")
        dialog_service.save_message(db, dialog.id, user_db_id, "bot", reply)
        return reply
    
    
    show_all_requested = is_show_all_products_phrase(message_text) or is_show_more_products_phrase(message_text)
    result_limit = None if show_all_requested else 5


    products = search_service.search_products(
        db=db,
        category=session_state.get("category"),
        brand=session_state.get("brand"),
        price_category=session_state.get("price_segment"),
        purpose=session_state.get("purpose"),
        min_price=session_state.get("min_price"),
        max_price=session_state.get("max_price"),
        power_type=session_state.get("power_type"),
        area_sotka=session_state.get("area_sotka"),
        excluded_brand=session_state.get("excluded_brand"),
        excluded_power_type=session_state.get("excluded_power_type"),
        limit=result_limit
    )

    if products:
        dialog_service.save_search_results(
            db=db,
            search_query_id=search_query_id,
            products_with_scores=products
        )

        session_state["show_all_requested"] = show_all_requested

        reply = build_reply(products, session_state=session_state)
        dialog_service.save_message(db, dialog.id, user_db_id, "bot", reply)
        return reply

    reply = (
        "По заданным параметрам товары не найдены.\n\n"
        "Можно попробовать:\n"
        "• убрать ограничение по бренду;\n"
        "• увеличить бюджет;\n"
        "• выбрать другой тип питания;\n"
        "• написать задачу проще, например «нужно косить траву» или «нужно пилить дрова»."
    )

    dialog_service.save_message(db, dialog.id, user_db_id, "bot", reply)
    return reply