"""План нумерации: коды операторов из ТЗ и экстренные номера."""

OPERATORS = {
    "842": "Городской", "499": "Городской", "892": "Городской",
    "025": "Альфа", "026": "Альфа", "027": "Альфа",
    "899": "Барбетта", "810": "Барбетта", "834": "Барбетта",
    "210": "Bell-ka", "214": "Bell-ka", "200": "Bell-ka",
}
CODES = frozenset(OPERATORS)
CITY_CODES = frozenset(c for c, op in OPERATORS.items() if op == "Городской")

# Экстренные и социально значимые номера: никогда не блокируются автоматически,
# даже если скоринг высокий (см. konvert.policy).
EMERGENCY = {
    "112": "Единая служба спасения",
    "101": "Пожарная охрана / МЧС",
    "102": "Полиция",
    "103": "Скорая помощь",
    "104": "Газовая служба",
}


def operator(number: str | None) -> str:
    if not number:
        return "—"
    if number in EMERGENCY:
        return "Экстренная служба"
    return OPERATORS.get(number[:3], "Неизвестный")


def is_city(number: str | None) -> bool:
    return bool(number) and number[:3] in CITY_CODES


def is_emergency(number: str | None) -> bool:
    return bool(number) and number.lstrip("+") in EMERGENCY


def load_whitelist(path: str | None) -> frozenset:
    """Белый список оператора: один номер на строку, # — комментарий.

    Файла может не быть — тогда список пуст, и это нормальное состояние.
    """
    import os

    if not path or not os.path.exists(path):
        return frozenset()
    with open(path, encoding="utf-8") as fh:
        nums = [line.strip().lstrip("+") for line in fh]
    return frozenset(n for n in nums if n and not n.startswith("#"))


def mask(number: str | None) -> str:
    """+7 499 ***-**-12 — маскирование для интерфейса и отчётов."""
    if not number or len(number) != 10:
        return number or "—"
    return f"+7 {number[:3]} ***-**-{number[-2:]}"


def pretty(number: str | None) -> str:
    if not number or len(number) != 10:
        return number or "—"
    return f"+7 {number[:3]} {number[3:6]}-{number[6:8]}-{number[8:]}"
