"""Скоринг одного вызова — то, что оператор видит в момент соединения.

На вход — «конверт» вызова (тип, A, B, C, длительность), на выход — балл, факторы
с вкладом, рекомендация и отдельное решение об автоблокировке. Балл берётся из
карточки самого опасного участника вызова; экстренные номера пропускаются до скоринга.
"""
from __future__ import annotations

from .numbering import EMERGENCY, is_emergency, operator
from .schemes import FRAUD, LEGIT, ROLES


class NumberIndex:
    """Быстрый доступ к карточкам номеров из results.json."""

    def __init__(self, results: dict):
        self.cards = {c["number"]: c for c in results["legit"]}
        self.cards.update({c["number"]: c for c in results["numbers"]})

    def get(self, number: str | None) -> dict | None:
        return self.cards.get(number) if number else None


def normalize(number: str | None) -> str:
    digits = "".join(ch for ch in (number or "") if ch.isdigit())
    return digits[1:] if len(digits) == 11 and digits[0] in "78" else digits


def _is_fraud(card: dict | None) -> bool:
    return bool(card) and card["scheme"] in FRAUD


def _title(card: dict) -> str:
    return (FRAUD.get(card["scheme"]) or LEGIT[card["scheme"]])["title"]


def score_call(call: dict, index: NumberIndex) -> dict:
    a, b, c = normalize(call.get("a")), normalize(call.get("b")), normalize(call.get("c"))
    ca, cb, cc = index.get(a), index.get(b), index.get(c)
    out = {
        "call": {"type": call.get("type", "02"), "a": a, "b": b, "c": c or None, "dur": call.get("dur")},
        "parties": {k: {"number": n, "operator": operator(n), "scheme": card["scheme"] if card else None,
                        "role": ROLES[card["role"]] if card else None}
                    for k, n, card in (("a", a, ca), ("b", b, cb), ("c", c, cc)) if n},
        "score": 0, "factors": [], "notes": [],
    }

    if is_emergency(b) or is_emergency(a):
        num = b if is_emergency(b) else a
        out["score"] = ca["score"] if _is_fraud(ca) else 0
        out["factors"] = ca["factors"] if _is_fraud(ca) else []
        out["notes"].append(f"Вызов с участием экстренного номера {num} ({EMERGENCY[num]}) пропускается до любого скоринга.")
        if _is_fraud(ca):
            out["notes"].append("Звонящий под подозрением, но балл показан только для сведения: "
                                "человек с заблокированного номера тоже может вызывать помощь.")
        out["decision"] = {"action": "never_block", "label": "Никогда не блокировать", "autoblock": False,
                           "recommendation": "Пропустить без условий",
                           "reason": "Экстренные и социально значимые номера в белом списке"}
        return out

    main, why = None, ""
    for card, label in ((ca, "звонящий номер"), (cb, "номер, на который звонят"), (cc, "номер переадресации")):
        if _is_fraud(card) and (main is None or card["score"] > main["score"]):
            main, why = card, label
    if main:
        out["score"], out["factors"] = main["score"], main["factors"]
        out["notes"].append(f"Балл определяет {why}: {_title(main)}, роль — {ROLES[main['role']].lower()}.")
        if main is ca:
            out["decision"] = main["decision"]
        else:
            out["notes"].append("Абонент сам звонит на номер схемы — скорее всего, перезванивает после сброса.")
            out["decision"] = {"action": "flag", "label": "Предупредить абонента", "autoblock": False,
                               "recommendation": "Предупредить звонящего до соединения: «Номер связан с мошенничеством»",
                               "reason": "Звонящий — вероятная жертва, блокировать его нельзя; опасен номер назначения"}
        return out

    known = ca or cb
    if known:
        out["score"], out["factors"] = known["score"], known["factors"]
        side = "Звонящий" if known is ca else "Вызываемый"
        out["notes"].append(f"{side} номер распознан как легитимный массовый источник: {_title(known).lower()}.")
        out["decision"] = known["decision"]
        return out

    out["notes"].append("Ни один из номеров не входит в найденные схемы и не является массовым источником.")
    out["decision"] = {"action": "allow", "label": "Пропускать", "autoblock": False,
                       "recommendation": "Пропустить", "reason": "Признаков мошенничества нет"}
    return out
