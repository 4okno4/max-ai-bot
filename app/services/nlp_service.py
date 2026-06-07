import re
from difflib import get_close_matches


def normalize_text(text: str) -> str:
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


BRAND_ALIASES = {
    "stihl": ["stihl", "штиль", "стихл", "стил", "стihl"],
    "husqvarna": ["husqvarna", "хускварна", "хусварна", "хускварна"],
    "makita": ["makita", "макита"],
    "bosch": ["bosch", "бош", "босх"],
    "patriot": ["patriot", "патриот"],
    "champion": ["champion", "чемпион", "чемпионн"],
    "huter": ["huter", "хутер"],
    "carver": ["carver", "карвер"],
    "зубр": ["зубр", "zubr"],
    "жук": ["жук"],
    "нева": ["нева"],
    "ока": ["ока"],
}

CATEGORY_ALIASES = {
    "бензопила": [
        "бензопила", "бензопилу", "бензо пила", "безнопила", "бензапила",
        "бензопилы", "пила", "пилу", "пилы", "цепная пила", "цепную пилу",
        "электропила", "электро пила"
    ],
    "триммер": [
        "триммер", "тример", "триммеры", "тримеры", "коса", "косу", "косы",
        "бензокоса", "мотокоса", "электрокоса", "травокосилка"
    ],
    "газонокосилка": [
        "газонокосилка", "газонокосилку", "газонокосилки", "косилка", "косилку",
        "косилки для газона"
    ],
    "мотоблок": [
        "мотоблок", "мотоблоки", "мотоблоком", "пахарь"
    ],
    "культиватор": [
        "культиватор", "культиваторы", "рыхлитель"
    ],
    "опрыскиватель": [
        "опрыскиватель", "опрыскиватель садовый", "прыскалка", "распылитель",
        "обрызгиватель"
    ],
    "насос": [
        "насос", "насосы", "помпа", "водяной насос", "дренажник", "дренажный насос"
    ],
}

PURPOSE_ALIASES = {
    "wood": [
        "дров", "дрова", "для дров", "бревна", "бревен", "ветки", "дерево",
        "деревья", "лес", "пилить", "распил", "заготовка", "заготовки дров"
    ],
    "grass": [
        "трава", "травы", "для травы", "газон", "газона", "покос", "косить",
        "сорняки", "бурьян", "высокая трава", "высокой травы"
    ],
    "soil": [
        "земля", "земли", "почва", "почвы", "огород", "огорода", "грядки",
        "рыхлить", "вспашка", "пахать", "обработка земли", "обработки земли",
        "участок", "участка", "учаастка"
    ],
    "water": [
        "полив", "полива", "для полива", "вода", "воды", "колодец", "колодца",
        "скважина", "скважины", "откачка", "откачать", "перекачать"
    ],
    "garden": [
        "сад", "сада", "для сада", "дача", "дачи", "для дачи", "теплица",
        "теплицы", "растения", "растений", "кусты", "деревья", "садовый участок"
    ],
}

POWER_TYPE_ALIASES = {
    "gasoline": [
        "бензиновый", "бензиновая", "бензиновое", "бензин", "на бензине",
        "бензо"
    ],
    "electric": [
        "электрический", "электрическая", "электро", "от сети", "сетевой",
        "сетевая", "220", "220в"
    ],
    "battery": [
        "аккумуляторный", "аккумуляторная", "аккумулятор", "акб", "на аккумуляторе",
        "беспроводной", "беспроводная"
    ],
    "manual": [
        "ручной", "ручная", "механический", "механическая"
    ],
}

PRICE_SEGMENTS = {
    "cheap": [
        "дешевый", "дешевая", "дешевле", "недорогой", "недорогая", "бюджетный",
        "бюджетная", "подешевле", "не дорогой", "не дорого", "доступный"
    ],
    "premium": [
        "дорогой", "дорогая", "премиум", "профессиональный", "профессиональная",
        "мощный", "мощная", "сильный", "надежный", "топовый", "лучший"
    ],
}

NO_PREFERENCE_WORDS = [
    "без разницы",
    "любой",
    "любая",
    "любое",
    "любые",
    "что угодно",
    "не важно",
    "неважно",
    "все равно",
    "всё равно",
    "на ваше усмотрение",
    "любой вариант",
    "любые варианты",
    "давай любые",
    "покажи любые",
]

NEGATION_WORDS = ["не", "без", "кроме", "только не", "не хочу", "не надо"]


def _contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _extract_by_aliases(text: str, aliases: dict) -> str | None:
    for value, words in aliases.items():
        for word in words:
            if word in text:
                return value
    return None


def _extract_brand(text: str) -> str | None:
    for brand, aliases in BRAND_ALIASES.items():
        for alias in aliases:
            if alias in text:
                return brand
    return None


def _extract_all_brands(text: str) -> list[str]:
    found = []
    for brand, aliases in BRAND_ALIASES.items():
        for alias in aliases:
            if alias in text and brand not in found:
                found.append(brand)
    return found


def _extract_category(text: str) -> str | None:
    category = _extract_by_aliases(text, CATEGORY_ALIASES)
    if category:
        return category

    words = text.split()
    all_aliases = []
    alias_to_category = {}

    for category_name, aliases in CATEGORY_ALIASES.items():
        for alias in aliases:
            all_aliases.append(alias)
            alias_to_category[alias] = category_name

    for word in words:
        match = get_close_matches(word, all_aliases, n=1, cutoff=0.78)
        if match:
            return alias_to_category[match[0]]

    return None


def _extract_purpose(text: str) -> str | None:
    return _extract_by_aliases(text, PURPOSE_ALIASES)


def _extract_power_type(text: str) -> str | None:
    return _extract_by_aliases(text, POWER_TYPE_ALIASES)


def _extract_price_segment(text: str) -> str | None:
    return _extract_by_aliases(text, PRICE_SEGMENTS)


def _extract_area_sotka(text: str) -> float | None:
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*(?:соток|сотки|сотка|сот)",
        r"участок\s*(\d+(?:[.,]\d+)?)",
        r"на\s*(\d+(?:[.,]\d+)?)\s*(?:соток|сотки|сотка|сот)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1).replace(",", "."))

    return None


def _extract_budget(text: str):
    max_price = None
    min_price = None

    text_clean = text.replace(" ", "")

    patterns_max = [
        r"до(\d+)(?:руб|р|₽)?",
        r"небольше(\d+)",
        r"максимум(\d+)",
        r"до(\d+)к",
    ]

    patterns_min = [
        r"от(\d+)(?:руб|р|₽)?",
        r"минимум(\d+)",
        r"дороже(\d+)",
    ]

    patterns_range = [
        r"от(\d+)до(\d+)",
        r"(\d+)-(\d+)",
    ]

    for pattern in patterns_range:
        match = re.search(pattern, text_clean)
        if match:
            a = float(match.group(1))
            b = float(match.group(2))
            if a < 1000 and "к" in text_clean:
                a *= 1000
            if b < 1000 and "к" in text_clean:
                b *= 1000
            return a, b

    for pattern in patterns_max:
        match = re.search(pattern, text_clean)
        if match:
            value = float(match.group(1))
            if value < 1000:
                value *= 1000
            max_price = value

    for pattern in patterns_min:
        match = re.search(pattern, text_clean)
        if match:
            value = float(match.group(1))
            if value < 1000:
                value *= 1000
            min_price = value

    return min_price, max_price


def _extract_exclusions(text: str):
    excluded_brand = None
    excluded_power_type = None

    for brand, aliases in BRAND_ALIASES.items():
        for alias in aliases:
            if f"не {alias}" in text or f"кроме {alias}" in text or f"без {alias}" in text:
                excluded_brand = brand

    for power_type, aliases in POWER_TYPE_ALIASES.items():
        for alias in aliases:
            if f"не {alias}" in text or f"кроме {alias}" in text or f"без {alias}" in text:
                excluded_power_type = power_type

    return excluded_brand, excluded_power_type


def _detect_intent(text: str) -> str:
    if text in ["привет",
        "приветик",
        "приветики",
        "здравствуйте",
        "здравствуй",
        "добрый день",
        "добрый вечер",
        "доброе утро",
        "/start",
        "старт",
        "начать"]:
        return "greeting"

    if text in ["помощь", "help", "что ты умеешь", "как пользоваться", "команды"]:
        return "help"

    if text in ["сброс", "reset", "заново", "новый поиск", "начать заново"]:
        return "reset"

    if _contains_any(text, ["какие бренды", "бренды есть", "список брендов", "производители", "какие фирмы", "фирмы есть"]):
        return "list_brands"

    if _contains_any(text, ["какие товары", "что есть", "ассортимент", "каталог", "категории", "что продаете", "что продаёте"]):
        return "list_categories"

    if _contains_any(text, ["чего нет", "что отсутствует", "нет в наличии", "нету в наличии", "закончилось"]):
        return "out_of_stock"

    if _contains_any(text, ["есть ли", "в наличии", "наличие", "осталось", "сколько есть"]):
        return "availability"

    if _contains_any(text, ["сравни", "сравнить", "что лучше из", "чем отличается"]):
        return "compare"

    if _contains_any(text, ["что лучше", "лучше взять", "посоветуй", "порекомендуй", "рекоменд", "лучший вариант"]):
        return "recommend"

    if _contains_any(text, ["покажи все", "все товары", "весь бренд", "товары бренда", "фирма "]):
        return "list_products"

    if _contains_any(text, NO_PREFERENCE_WORDS):
        return "no_preference"

    return "search"


def extract_product_hint(text: str) -> str | None:
    cleaned = text

    stop_words = [
        "а у вас есть", "есть ли", "есть", "в наличии", "наличие", "покажи",
        "подбери", "подберите", "нужен", "нужна", "нужно", "хочу", "мне",
        "товар", "товары", "бренда", "фирма", "до", "от", "рублей", "руб", "р"
    ]

    for stop in stop_words:
        cleaned = cleaned.replace(stop, " ")

    cleaned = re.sub(r"\d+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) >= 3:
        return cleaned

    return None


def process_user_query(text: str) -> dict:
    normalized = normalize_text(text)

    category = _extract_category(normalized)
    purpose = _extract_purpose(normalized)
    brand = _extract_brand(normalized)
    brands = _extract_all_brands(normalized)
    power_type = _extract_power_type(normalized)
    price_segment = _extract_price_segment(normalized)
    area_sotka = _extract_area_sotka(normalized)
    min_price, max_price = _extract_budget(normalized)
    excluded_brand, excluded_power_type = _extract_exclusions(normalized)
    intent = _detect_intent(normalized)
    product_hint = extract_product_hint(normalized)

    ambiguous_category = False

    if normalized in ["коса", "косу", "косы"]:
        category = "триммер"
        ambiguous_category = False

    return {
        "original_query": text,
        "normalized_query": normalized,
        "intent": intent,

        "category": category,
        "brand": brand,
        "brands": brands,
        "purpose": purpose,
        "price_segment": price_segment,

        "min_price": min_price,
        "max_price": max_price,

        "power_type": power_type,
        "area_sotka": area_sotka,

        "excluded_brand": excluded_brand,
        "excluded_power_type": excluded_power_type,

        "product_hint": product_hint,
        "ambiguous_category": ambiguous_category,

        "confidence": {
            "category": 1.0 if category else 0.0,
            "purpose": 1.0 if purpose else 0.0,
            "brand": 1.0 if brand else 0.0,
            "price_segment": 1.0 if price_segment or min_price or max_price else 0.0,
            "power_type": 1.0 if power_type else 0.0,
            "area": 1.0 if area_sotka else 0.0,
        }
    }