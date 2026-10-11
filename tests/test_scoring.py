"""Скоринг вызова и политика: экстренные номера не блокируются ни при каких условиях."""
import pytest

from konvert.policy import decide
from konvert.scoring import NumberIndex, normalize, score_call

SIM = {"number": "8990000001", "scheme": "S3", "role": "sim", "score": 100,
       "factors": [{"label": "Только исходящие", "points": 30}],
       "decision": decide("S3", "sim", 100, 5, "8990000001")}
PREMIUM = {"number": "4990000002", "scheme": "S1", "role": "premium", "score": 90,
           "factors": [{"label": "Принимает перезвоны жертв", "points": 50}],
           "decision": decide("S1", "premium", 90, 4, "4990000002")}
BANK = {"number": "2100000003", "scheme": "D2", "role": "legit", "score": 10,
        "factors": [{"label": "Волны в одни и те же часы", "points": -20}],
        "decision": decide("D2", "legit", 10, 4, "2100000003")}


@pytest.fixture
def index():
    return NumberIndex({"numbers": [SIM, PREMIUM], "legit": [BANK]})


def test_normalize_strips_country_code_only():
    assert normalize("+7 899 000-00-01") == "8990000001"
    assert normalize("88990000001") == "8990000001"
    assert normalize("0261234567") == "0261234567"
    assert normalize("103") == "103"


@pytest.mark.parametrize("emergency", ["112", "101", "102", "103", "104"])
def test_call_to_emergency_is_never_blocked_even_from_a_blocked_number(index, emergency):
    res = score_call({"type": "02", "a": SIM["number"], "b": emergency, "dur": 40}, index)
    assert SIM["decision"]["autoblock"] is True            # сам номер подлежит автоблокировке…
    assert res["decision"]["action"] == "never_block"      # …но вызов в скорую проходит
    assert res["decision"]["autoblock"] is False


def test_emergency_and_whitelist_numbers_are_never_autoblocked_by_policy():
    assert decide("S3", "sim", 100, 5, "103")["action"] == "never_block"
    wl = decide("S3", "sim", 100, 5, "4950000000", whitelist=frozenset({"4950000000"}))
    assert wl["action"] == "never_block" and wl["autoblock"] is False


def test_fraud_caller_keeps_its_own_decision(index):
    res = score_call({"type": "02", "a": SIM["number"], "b": "0261234567", "dur": 80}, index)
    assert res["score"] == 100 and res["decision"]["autoblock"] is True
    assert res["factors"] == SIM["factors"]


def test_victim_calling_back_is_warned_not_blocked(index):
    res = score_call({"type": "03", "a": "0261234567", "b": "8101111111", "c": PREMIUM["number"], "dur": 120}, index)
    assert res["score"] == 90
    assert res["decision"]["action"] == "flag" and res["decision"]["autoblock"] is False


def test_legit_source_passes(index):
    res = score_call({"type": "02", "a": BANK["number"], "b": "0261234567", "dur": 12}, index)
    assert res["decision"]["action"] == "allow" and res["decision"]["autoblock"] is False


def test_unknown_numbers_pass_with_zero_score(index):
    res = score_call({"type": "02", "a": "8991234567", "b": "0261234567", "dur": 54}, index)
    assert res["score"] == 0 and res["decision"]["action"] == "allow"


def test_autoblock_needs_scheme_score_and_factors():
    assert decide("S1", "initiator", 95, 4, "8101111111")["autoblock"] is True
    assert decide("S1", "initiator", 95, 2, "8101111111")["autoblock"] is False   # мало независимых факторов
    assert decide("S1", "initiator", 80, 4, "8101111111")["autoblock"] is False   # балл ниже порога
    assert decide("S7", "fraudster", 100, 4, "0251111111")["autoblock"] is False  # для вишинга решает человек
    assert decide("S1", "initiator", 100, 4, "8101111111", legit_match="D1")["action"] == "review"
