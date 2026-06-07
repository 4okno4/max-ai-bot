def analyze_product(product):
    """
    Анализирует товар по названию и характеристикам.
    Возвращает базовую оценку и смысловые признаки товара.
    """
    text = product.name.lower().replace("ё", "е")

    score = 0
    tags = []

    word_groups = {
        "wood": [
            "бензопила", "электропила", "пила", "цепная",
            "шина", "цепь", "дров", "бревна", "дерево"
        ],
        "grass": [
            "триммер", "тример", "коса", "бензокоса",
            "мотокоса", "газонокосилка", "трава", "газон",
            "сорняки", "бурьян"
        ],
        "soil": [
            "мотоблок", "культиватор", "почва", "земля",
            "вспашка", "огород", "рыхление", "грядки"
        ],
        "water": [
            "насос", "полив", "вода", "дренажный",
            "скважина", "колодец"
        ],
        "garden": [
            "сад", "садовый", "дача", "растений",
            "опрыскиватель", "участок"
        ],
        "powerful": [
            "мощный", "профессиональный", "2500", "3000",
            "2.0 л.с", "2 л.с", "самоходная", "бензиновый",
            "высокой травы", "для вспашки"
        ],
        "trusted_brand": [
            "stihl", "штиль", "husqvarna", "хускварна",
            "makita", "макита", "bosch", "бош"
        ]
    }

    for tag, words in word_groups.items():
        for word in words:
            if word in text:
                tags.append(tag)
                if tag == "trusted_brand":
                    score += 4
                elif tag == "powerful":
                    score += 5
                else:
                    score += 5

    if product.power_type:
        tags.append(product.power_type)

    if product.area_max is not None:
        if product.area_max <= 6:
            tags.append("small_area")
        elif product.area_max >= 20:
            tags.append("large_area")

    return {
        "score": score,
        "tags": list(set(tags))
    }