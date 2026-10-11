"""Политика реагирования: что делать с номером и когда допустима автоблокировка.

Принцип: балл — это уверенность, а не приговор. Автоблокировка — отдельное решение
с отдельной ценой ошибки, поэтому она включается только когда одновременно:
  1) схема такова, что у номера нет легитимного использования (SIM-box, Wangiri, робот, клон);
  2) балл ≥ AUTOBLOCK_MIN_SCORE и сработали минимум 3 независимых фактора;
  3) номер не экстренный, не в белом списке и не похож ни на один легитимный профиль.
Экстренные службы (112, 101–104 …) не блокируются никогда — ни по баллу, ни вручную из интерфейса.
"""
from __future__ import annotations

from . import config as C
from .numbering import is_emergency
from .schemes import FRAUD

ACTIONS = {
    "block": "Заблокировать",
    "flag": "Пометить абоненту",
    "review": "На проверку аналитику",
    "watch": "Наблюдать",
    "allow": "Пропускать",
    "never_block": "Никогда не блокировать",
}

RECOMMENDATION = {
    ("S1", "initiator"): "Заблокировать исходящие; предупредить абонентов, которым звонил номер",
    ("S1", "premium"): "Запретить переадресацию на этот номер; передать в службу безопасности",
    ("S2", "initiator"): "Пометить абонентам «Робот / спам»; ограничить частоту вызовов",
    ("S3", "sim"): "Заблокировать SIM; передать в службу безопасности весь шлюз",
    ("S4", "clone"): "Заблокировать посторонние IMSI; связаться с владельцем номера и перевыпустить SIM",
    ("S5", "node"): "Отключить переадресацию; проверить владельцев номеров цепочки",
    ("S6", "member"): "Исключить трафик группы из взаиморасчётов; проверить договоры",
    ("S7", "fraudster"): "Пометить абоненту «Возможно мошенник»; передать в службу безопасности",
    ("S7", "spoof"): "Пометить абоненту «Подмена номера»; не перезванивать",
}


def decide(scheme: str, role: str, score: int, n_factors: int, number: str,
           legit_match: str | None = None, whitelist: frozenset = frozenset()) -> dict:
    if is_emergency(number) or number in whitelist:
        return {"action": "never_block", "label": ACTIONS["never_block"], "autoblock": False,
                "reason": "Экстренный или социально значимый номер в белом списке"}
    if scheme.startswith("D"):
        return {"action": "allow", "label": ACTIONS["allow"], "autoblock": False,
                "reason": "Распознан легитимный массовый источник"}
    allowed = FRAUD[scheme]["autoblock"] and role != "premium"
    strong = score >= C.AUTOBLOCK_MIN_SCORE and n_factors >= 3
    if legit_match:
        return {"action": "review", "label": ACTIONS["review"], "autoblock": False,
                "reason": f"Похож и на фрод, и на легитимный профиль {legit_match} — нужен человек",
                "recommendation": RECOMMENDATION.get((scheme, role))}
    if allowed and strong:
        action, auto, reason = "block", True, "Схема без легитимного применения, уверенность высокая"
    elif score >= 75:
        action, auto = "flag", False
        reason = ("Автоблокировка для этой схемы отключена: цена ошибки выше, решение за человеком"
                  if not allowed else "Уверенность недостаточна для автоблокировки")
    elif score >= C.ANSWER_MIN_SCORE:
        action, auto, reason = "review", False, "Средняя уверенность"
    else:
        action, auto, reason = "watch", False, "Слабые признаки"
    return {"action": action, "label": ACTIONS[action], "autoblock": auto, "reason": reason,
            "recommendation": RECOMMENDATION.get((scheme, role))}
