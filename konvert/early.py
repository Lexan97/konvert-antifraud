"""Раннее обнаружение: через сколько вызовов схему можно поймать «на лету».

Детекторы в detectors.py смотрят на всё окно наблюдения — это точно, но поздно.
Здесь те же признаки считаются скользящим окном из последних W вызовов номера,
как это делал бы потоковый обработчик на коммутаторе:

  * Wangiri — в окне из W вызовов не меньше доли SHARE сброшены на 0–2 секунде;
  * робот   — W набранных подряд разных номеров укладываются в узкий диапазон нумерации.

Для каждого окна считаем, на каком по счёту вызове сработала бы тревога, сколько
вызовов схемы это предотвращает и сколько посторонних номеров задело бы правило.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from . import config as C


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    d = df[["a", "b", "ts", "dur"]].sort_values(["a", "ts"], kind="stable").reset_index(drop=True)
    d["code"] = d.a.astype("category").cat.codes.to_numpy()
    d["pos"] = d.groupby("code").cumcount().to_numpy() + 1  # порядковый номер вызова у этого номера
    return d


def _first_alarm(d: pd.DataFrame, hit: np.ndarray, window: int) -> pd.DataFrame:
    """hit[i] — тревога в окне, которое заканчивается на строке i + window - 1."""
    code = d.code.to_numpy()
    same = code[window - 1:] == code[: len(code) - window + 1]  # окно целиком внутри одного номера
    idx = np.flatnonzero(hit & same) + window - 1
    rows = d.iloc[idx].drop_duplicates("a", keep="first")
    start = d.drop_duplicates("a", keep="first").set_index("a").ts
    out = rows.set_index("a")[["pos", "ts"]].rename(columns={"pos": "alarm_call", "ts": "alarm_ts"})
    out["minutes"] = (out.alarm_ts - start.reindex(out.index)).dt.total_seconds() / 60
    return out


def wangiri_alarms(d: pd.DataFrame, window: int, share: float) -> pd.DataFrame:
    short = (d.dur <= 2).to_numpy(dtype=np.int32)
    cs = np.concatenate([[0], np.cumsum(short)])
    in_window = cs[window:] - cs[:-window]
    return _first_alarm(d, in_window >= share * window, window)


def robot_alarms(d: pd.DataFrame, window: int, max_range: int) -> pd.DataFrame:
    bn = pd.to_numeric(d.b, errors="coerce").to_numpy(dtype=np.float64)
    win = sliding_window_view(bn, window)
    spread = win.max(axis=1) - win.min(axis=1)  # NaN в окне даёт NaN — такое окно тревогу не поднимает
    # нижняя граница отсекает повторные звонки одному и тому же абоненту: W разных номеров занимают минимум W-1
    return _first_alarm(d, (spread <= max_range) & (spread >= window - 1), window)


def evaluate(df: pd.DataFrame, cards: list[dict], legit_numbers: set[str]) -> dict:
    """Проверяет потоковые правила на всей выгрузке: скорость обнаружения и ложные тревоги."""
    d = _prepare(df)
    n_out = d.groupby("a").size()
    by_scheme = {}
    for c in cards:
        by_scheme.setdefault((c["scheme"], c["role"]), set()).add(c["number"])
    all_fraud = {c["number"] for c in cards}

    def report(alarms: pd.DataFrame, target: set[str], window: int, rule: str) -> dict:
        hit = alarms[alarms.index.isin(target)]
        extra = alarms[~alarms.index.isin(target)]
        total = int(n_out.reindex(list(target)).fillna(0).sum())
        before = int(hit.alarm_call.sum() + n_out.reindex(list(target - set(hit.index))).fillna(0).sum())
        return {
            "rule": rule,
            "window": window,
            "numbers": len(target),
            "detected": int(len(hit)),
            "median_minutes": round(float(hit.minutes.median()), 1) if len(hit) else None,
            "max_minutes": round(float(hit.minutes.max()), 1) if len(hit) else None,
            "calls_total": total,
            "calls_prevented": total - before,
            "prevented_share": round((total - before) / total, 4) if total else 0.0,
            "false_alarms_legit": int(extra.index.isin(legit_numbers).sum()),
            "false_alarms_other_fraud": int(extra.index.isin(all_fraud).sum()),
            "false_alarms_unknown": int((~extra.index.isin(legit_numbers | all_fraud)).sum()),
        }

    w1, w2 = C.EARLY_WANGIRI_WINDOW, C.EARLY_ROBOT_WINDOW
    return {
        "S1": report(wangiri_alarms(d, w1, C.EARLY_WANGIRI_SHARE), by_scheme.get(("S1", "initiator"), set()), w1,
                     f"из последних {w1} вызовов не меньше {C.EARLY_WANGIRI_SHARE:.0%} сброшены на 0–2 секунде"),
        "S2": report(robot_alarms(d, w2, C.EARLY_ROBOT_RANGE), by_scheme.get(("S2", "initiator"), set()), w2,
                     f"{w2} набранных подряд разных номеров умещаются в диапазон из {C.EARLY_ROBOT_RANGE} номеров"),
    }
