"""Поведенческий профиль номера за всё окно наблюдения — «по номеру за окно времени» из ТЗ."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .numbering import CITY_CODES

NIGHT_FROM, NIGHT_TO = 22, 6  # ночь: 22:00–05:59


def build_profiles(df: pd.DataFrame) -> pd.DataFrame:
    """Одна строка на номер, который хоть раз был звонящим (A)."""
    hour = df.ts.dt.hour
    t = pd.DataFrame({
        "a": df.a.values,
        "b": df.b.values,
        "ts": df.ts.values,
        "dur": df.dur.values,
        "zero": (df.dur == 0).values,
        "short": (df.dur <= 2).values,
        "night": ((hour >= NIGHT_FROM) | (hour < NIGHT_TO)).values,
        "hour": hour.values,
        "day": df.ts.dt.day.values,
        "weekend": (df.ts.dt.dayofweek >= 5).values,
        "bn": pd.to_numeric(df.b, errors="coerce").values,
        "imsi": df.imsi.values,
        "fwd": (df.type == "03").values,
    })
    g = t.groupby("a", sort=False)
    p = pd.DataFrame({
        "n_out": g.size(),
        "uniq_b": g.b.nunique(),
        "zero_share": g.zero.mean(),
        "short_share": g.short.mean(),
        "median_dur": g.dur.median(),
        "night_share": g.night.mean(),
        "weekend_share": g.weekend.mean(),
        "active_hours": g.hour.nunique(),
        "hour_min": g.hour.min(),
        "hour_max": g.hour.max(),
        "active_days": g.day.nunique(),
        "t0": g.ts.min(),
        "t1": g.ts.max(),
        "bmin": g.bn.min(),
        "bmax": g.bn.max(),
        "n_imsi": g.imsi.nunique(),
        "fwd_share": g.fwd.mean(),
    })
    p["span_h"] = (p.t1 - p.t0).dt.total_seconds() / 3600
    p["rate_per_h"] = p.n_out / p.span_h.clip(lower=0.25)
    p["b_density"] = p.uniq_b / (p.bmax - p.bmin + 1)
    p["uniq_share"] = p.uniq_b / p.n_out

    direct = df[df.type != "03"]
    p["n_in"] = direct.groupby("b").size().reindex(p.index).fillna(0).astype(int)
    p["uniq_in"] = direct.groupby("b").a.nunique().reindex(p.index).fillna(0).astype(int)
    p["n_fwd_target"] = df.groupby("c").size().reindex(p.index).fillna(0).astype(int)
    p["is_city"] = p.index.str[:3].isin(CITY_CODES)
    return p


def activity_by_hour(df: pd.DataFrame, numbers: set[str]) -> dict[str, list[int]]:
    """Почасовая активность (исходящие) за 5 дней — для графика в карточке номера."""
    d = df[df.a.isin(numbers)]
    start = df.ts.min().normalize()
    slot = ((d.ts - start).dt.total_seconds() // 3600).astype(int)
    n_slots = int(((df.ts.max() - start).total_seconds() // 3600) + 1)
    out = {}
    for num, s in slot.groupby(d.a):
        out[num] = np.bincount(s.values, minlength=n_slots).tolist()
    return out
