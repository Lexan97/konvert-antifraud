"""Детекторы проверяются на маленькой искусственной сети, собранной прямо в тесте:
фон из обычных абонентов, две схемы и два легальных источника, похожих на фрод."""
import numpy as np
import pandas as pd
import pytest

from konvert import early
from konvert.detectors import detect_robots, detect_wangiri, recognize_legit
from konvert.profile import build_profiles

T0 = pd.Timestamp("2026-10-01 00:00:00")
WANGIRI, PREMIUM = "8105550001", "4995550002"
ROBOTS = ["0255550003", "8995550004"]
CALL_CENTRE, BANK = "4995550005", "2105550006"


def _rows(a, b, ts, dur, typ="02", c=None):
    return {"type": typ, "imsi": "250020000000000" if typ != "01" else None, "a": a, "b": b, "ts": ts, "dur": dur, "c": c}


@pytest.fixture(scope="module")
def net():
    rng = np.random.default_rng(7)
    subs = [f"899{rng.integers(1_000_000, 9_999_999)}" for _ in range(400)]
    rows = []
    # фон: обычные абоненты звонят друг другу все пять дней
    for _ in range(6000):
        a, b = rng.choice(subs, 2, replace=False)
        rows.append(_rows(a, b, T0 + pd.Timedelta(seconds=int(rng.integers(0, 5 * 86400))), int(rng.integers(5, 300))))
    # Wangiri: 300 сбросов за час, 15 жертв перезванивают — вызов уходит на платный номер
    victims = [f"026{n}" for n in rng.choice(np.arange(1_000_000, 9_999_999), 300, replace=False)]
    for i, v in enumerate(victims):
        rows.append(_rows(WANGIRI, v, T0 + pd.Timedelta(hours=30, seconds=12 * i), int(rng.integers(0, 3))))
    for v in victims[:15]:
        rows.append(_rows(v, WANGIRI, T0 + pd.Timedelta(hours=32), 120, typ="03", c=PREMIUM))
    # робот: два номера по очереди перебирают диапазон подряд
    for i in range(400):
        rows.append(_rows(ROBOTS[i % 2], f"834{3_000_000 + i}", T0 + pd.Timedelta(hours=50, seconds=6 * i),
                          0 if i % 4 == 0 else int(rng.integers(4, 26))))
    # колл-центр: городской номер, рабочие часы трёх будних дней, треть без ответа, клиенты перезванивают
    for day in (0, 1, 4):
        for i in range(150):
            ts = T0 + pd.Timedelta(days=day, hours=9, seconds=int(rng.integers(0, 10 * 3600)))
            rows.append(_rows(CALL_CENTRE, rng.choice(subs), ts, 0 if i % 3 == 0 else int(rng.integers(20, 200)), typ="01"))
            if i % 5 == 0:
                rows.append(_rows(rng.choice(subs), CALL_CENTRE, ts + pd.Timedelta(minutes=30), 90))
    # банк: три волны в день в одни и те же часы, короткие вызовы клиентам из базы
    for day in range(5):
        for hour in (9, 15, 18):
            for i in range(40):
                ts = T0 + pd.Timedelta(days=day, hours=hour, seconds=int(rng.integers(0, 3000)))
                rows.append(_rows(BANK, f"027{rng.integers(1_000_000, 9_999_999)}", ts, int(rng.integers(6, 21))))
    df = pd.DataFrame(rows).sort_values("ts").reset_index(drop=True)
    df["dur"] = df.dur.astype(float)
    df["file"], df["ts_imputed"] = 0, False
    return df, build_profiles(df)


def test_wangiri_and_its_premium_number_are_found(net):
    df, prof = net
    found = {f.number: f for f in detect_wangiri(df, prof)}
    assert set(found) == {WANGIRI, PREMIUM}
    assert found[WANGIRI].role == "initiator" and found[PREMIUM].role == "premium"
    assert found[WANGIRI].score >= 90
    assert found[WANGIRI].related == [PREMIUM]


def test_score_is_the_sum_of_its_factors(net):
    df, prof = net
    for f in detect_wangiri(df, prof) + detect_robots(df, prof):
        assert f.score == min(100, max(0, sum(x.points for x in f.factors)))
        assert all(x.label for x in f.factors)


def test_robot_pair_is_one_group(net):
    df, prof = net
    found = detect_robots(df, prof)
    assert {f.number for f in found} == set(ROBOTS)
    assert len({f.group for f in found}) == 1          # два номера делят один диапазон


def test_legit_sources_are_recognised_and_never_flagged(net):
    df, prof = net
    fraud = {f.number for f in detect_wangiri(df, prof) + detect_robots(df, prof)}
    legit = {f.number: f.scheme for f in recognize_legit(df, prof)}
    assert legit.get(CALL_CENTRE) == "D1"
    assert legit.get(BANK) == "D2"
    assert not fraud & set(legit)


def test_legit_card_explains_both_sides(net):
    df, prof = net
    bank = next(f for f in recognize_legit(df, prof) if f.number == BANK)
    assert any(x.points > 0 for x in bank.factors) and any(x.points < 0 for x in bank.factors)
    assert bank.score < 30


def test_stream_rules_fire_early_and_only_on_the_schemes(net):
    df, _ = net
    d = early._prepare(df)
    w = early.wangiri_alarms(d, 20, 0.9)
    r = early.robot_alarms(d, 10, 100)
    assert list(w.index) == [WANGIRI] and int(w.alarm_call.iloc[0]) == 20
    assert set(r.index) == set(ROBOTS) and (r.alarm_call == 10).all()
