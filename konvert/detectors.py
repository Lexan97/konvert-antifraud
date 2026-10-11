"""Детекторы схем мошенничества и распознаватели легитимных массовых источников.

Каждый детектор возвращает список Finding: номер, схема, роль номера в схеме и
список факторов с вкладом в баллах. Итоговый балл = сумма вкладов (0–100), поэтому
решение всегда раскладывается на понятные человеку причины — как требует ТЗ.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import pandas as pd

from . import config as C
from .numbering import CITY_CODES, mask, operator


# --------------------------------------------------------------------------- модель
@dataclass
class Factor:
    label: str
    points: int

    def as_dict(self) -> dict:
        return {"label": self.label, "points": self.points}


@dataclass
class Finding:
    number: str
    scheme: str
    role: str
    factors: list[Factor]
    group: str | None = None
    related: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def score(self) -> int:
        return int(max(0, min(100, sum(f.points for f in self.factors))))

    def as_dict(self) -> dict:
        return {
            "number": self.number, "scheme": self.scheme, "role": self.role, "score": self.score,
            "factors": [f.as_dict() for f in self.factors], "group": self.group,
            "related": self.related, "stats": self.stats,
        }


def pts(weight: float, strength: float) -> int:
    return int(round(weight * float(np.clip(strength, 0.0, 1.0))))


# --------------------------------------------------------------------------- формат
def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        w = one
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        w = few
    else:
        w = many
    return f"{n:,}".replace(",", " ") + " " + w


def calls(n: int) -> str:
    return plural(n, "вызов", "вызова", "вызовов")


def span(hours: float) -> str:
    if hours < 1:
        return plural(max(1, round(hours * 60)), "минуту", "минуты", "минут")
    if hours < 48:
        return f"{hours:.1f} ч".replace(".0 ", " ").replace(".", ",")
    return f"{hours / 24:.1f} сут".replace(".", ",")


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def tail(num: str, k: int = 4) -> str:
    return "…" + num[-k:]


def _stats(p: pd.Series) -> dict:
    keys = ["n_out", "uniq_b", "n_in", "zero_share", "short_share", "median_dur", "night_share", "span_h", "n_imsi"]
    out = {}
    for k in keys:
        v = p.get(k)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        out[k] = round(float(v), 3) if isinstance(v, (float, np.floating)) else int(v)
    return out


# --------------------------------------------------------------------------- S2 роботы
def detect_robots(df: pd.DataFrame, prof: pd.DataFrame) -> list[Finding]:
    c = prof[(prof.n_out >= C.ROBOT_MIN_CALLS) & (prof.span_h <= C.ROBOT_MAX_SPAN_H)]
    rows_all = df[df.a.isin(c.index)]
    bn_all = pd.to_numeric(rows_all.b, errors="coerce")
    # шаг между соседними набранными номерами: у робота он равен числу номеров в связке (1–3),
    # у любого обычного источника — миллионы. Медиана устойчива к единичным посторонним вызовам.
    cand = {}
    for num, b in bn_all.groupby(rows_all.a):
        u = np.sort(b.dropna().unique())
        if len(u) < C.ROBOT_MIN_CALLS:
            continue
        step = float(np.median(np.diff(u)))
        if step <= C.ROBOT_MAX_STEP:
            lo, hi = np.quantile(u, [0.02, 0.98])
            cand[num] = (lo, hi)
    # номера, которые делят один диапазон B, объединяем в группу
    groups, cur, cur_max = [], [], -1.0
    for num, (lo, hi) in sorted(cand.items(), key=lambda kv: kv[1][0]):
        if cur and lo <= cur_max:
            cur.append(num)
            cur_max = max(cur_max, hi)
        else:
            if cur:
                groups.append(cur)
            cur, cur_max = [num], hi
    if cur:
        groups.append(cur)

    out = []
    for gi, grp in enumerate(groups, 1):
        sel = rows_all.a.isin(grp)
        u = np.sort(bn_all[sel].dropna().unique())
        lo, hi = np.quantile(u, [0.01, 0.99])
        core = u[(u >= lo) & (u <= hi)]
        density = len(core) / (core[-1] - core[0] + 1)
        if density < C.ROBOT_GROUP_DENSITY:
            continue
        lo_s, hi_s = f"{int(core[0]):010d}", f"{int(core[-1]):010d}"
        for num in grp:
            p = prof.loc[num]
            f = [
                Factor(f"Обзванивает номера подряд: {tail(lo_s, 7)} → {tail(hi_s, 7)} "
                       f"({plural(len(u), 'номер', 'номера', 'номеров')}, пропусков {pct(1 - density)})", pts(40, density)),
                Factor(f"{calls(p.n_out)} за {span(p.span_h)}", pts(25, p.rate_per_h / 200)),
                Factor(f"Короткие вызовы: медиана {p.median_dur:.0f} с, без ответа {pct(p.zero_share)}",
                       pts(20, 1.0 if p.median_dur <= 25 else 0.4)),
            ]
            if len(grp) > 1:
                f.append(Factor(f"Работает в связке из {len(grp)} номеров — делят один диапазон", 15))
            else:
                f.append(Factor("Ни одного входящего вызова" if p.n_in == 0 else f"Входящих всего {p.n_in}",
                                pts(15, 1 - p.n_in / 5)))
            out.append(Finding(num, "S2", "initiator", f, group=f"S2-{gi}", related=[x for x in grp if x != num],
                               stats=_stats(p) | {"range": [lo_s, hi_s], "group_size": len(grp)}))
    return out


# --------------------------------------------------------------------------- S1 wangiri
def detect_wangiri(df: pd.DataFrame, prof: pd.DataFrame) -> list[Finding]:
    c = prof[(prof.n_out >= C.WANGIRI_MIN_CALLS) & (prof.short_share >= C.WANGIRI_MIN_SHORT)
             & (prof.span_h <= C.WANGIRI_MAX_SPAN_H)]
    cb = df[(df.type == "03") & df.b.isin(c.index)]
    by_bait = cb.groupby("b")
    prem_all = set(cb.c.dropna())
    direct_in = df[(df.type != "03") & df.b.isin(prem_all)].b.value_counts()
    out = []
    for gi, (num, p) in enumerate(c.iterrows(), 1):
        victims = by_bait.get_group(num) if num in by_bait.groups else cb.iloc[:0]
        k = victims.a.nunique()
        premium = victims.c.value_counts()
        prem = premium.index[0] if len(premium) else None
        f = [
            Factor(f"{calls(p.n_out)} за {span(p.span_h)}", pts(25, p.rate_per_h / 150)),
            Factor(f"{pct(p.short_share)} вызовов — сброс на 0–2 секунде", pts(35, p.short_share)),
            Factor(f"{plural(k, 'жертва перезвонила', 'жертвы перезвонили', 'жертв перезвонили')} — "
                   f"вызов ушёл на номер {mask(prem)}" if prem else "Перезвонов жертв не зафиксировано",
                   pts(25, k / 10)),
            Factor(f"Номер «жил» всего {span(p.span_h)}", pts(15, 1.0 if p.span_h <= 6 else 0.5)),
        ]
        grp = f"S1-{gi}"
        out.append(Finding(num, "S1", "initiator", f, group=grp, related=[prem] if prem else [],
                           stats=_stats(p) | {"callbacks": int(k)}))
        if prem:
            n_prem = int((victims.c == prem).sum())
            own = int(prof.n_out.get(prem, 0) + direct_in.get(prem, 0))
            fp = [
                Factor(f"Принимает перезвоны {plural(n_prem, 'жертвы', 'жертв', 'жертв')} "
                       f"Wangiri-номера {mask(num)}", pts(50, n_prem / 5)),
                Factor("Все переадресации — от одного номера-приманки", pts(20, premium.iloc[0] / premium.sum())),
                Factor("Сам не звонит и обычных вызовов не принимает" if own == 0
                       else f"Своих вызовов: {own}", pts(20, own == 0)),
                Factor(f"Оператор «{operator(prem)}» — чужой для приманки «{operator(num)}»"
                       if operator(prem) != operator(num) else "Тот же оператор, что у приманки",
                       pts(10, operator(prem) != operator(num))),
            ]
            out.append(Finding(prem, "S1", "premium", fp, group=grp, related=[num],
                               stats={"callbacks": n_prem}))
    return out


# --------------------------------------------------------------------------- S3 sim-box
def detect_simbox(df: pd.DataFrame, prof: pd.DataFrame) -> list[Finding]:
    fwd_src = df[df.type == "03"].groupby("b").size()
    c = prof[(prof.n_out >= C.SIMBOX_MIN_CALLS) & (prof.n_in <= C.SIMBOX_MAX_IN_SHARE * prof.n_out) & (prof.n_fwd_target == 0)
             & (prof.uniq_share >= C.SIMBOX_MIN_UNIQUE) & (prof.zero_share <= C.SIMBOX_MAX_ZERO)
             & (prof.median_dur < C.SIMBOX_MAX_MEDIAN_DUR) & (prof.span_h >= C.SIMBOX_MIN_SPAN_H)
             & (prof.n_imsi <= 1)]
    c = c[~c.index.isin(fwd_src.index)]
    rows = df[df.a.isin(c.index)].sort_values(["a", "ts"])
    end = rows.ts + pd.to_timedelta(rows.dur.fillna(0), unit="s")
    gap = (rows.ts - end.groupby(rows.a).shift()).dt.total_seconds()
    no_overlap = (gap >= 0).groupby(rows.a).mean()
    med_gap = gap.groupby(rows.a).median()

    out = []
    for num, p in c.iterrows():
        if no_overlap.get(num, 0) < C.SIMBOX_MIN_NO_OVERLAP:
            continue
        f = [
            Factor(f"Только исходящие: {calls(p.n_out)}, входящих {p.n_in}", 30 if p.n_in == 0 else 25),
            Factor(f"Каждый раз новый абонент: {p.uniq_b} из {p.n_out}", pts(20, (p.uniq_share - 0.9) / 0.1)),
            Factor(f"Работает без перерыва {span(p.span_h)}, в том числе ночью ({pct(p.night_share)})",
                   pts(20, min(1, p.span_h / 12) * (p.night_share > 0))),
            Factor(f"Вызовы строго один за другим, без наложений (пауза ~{med_gap.get(num, 0) / 60:.0f} мин)",
                   pts(20, no_overlap.get(num, 0))),
            Factor("Все вызовы состоялись — нет сбросов, как у транзитного шлюза", pts(10, 1 - p.zero_share * 10)),
        ]
        # В CDR нет IMEI и соты, поэтому SIM не раскладываются по конкретным шлюзам — каждая оценивается сама.
        out.append(Finding(num, "S3", "sim", f, stats=_stats(p) | {"median_gap_s": float(med_gap.get(num, 0))}))
    return out


# --------------------------------------------------------------------------- S4 клоны SIM
def detect_clones(df: pd.DataFrame, prof: pd.DataFrame) -> list[Finding]:
    c = prof[prof.n_imsi >= C.CLONE_MIN_IMSI]
    rows = df[df.a.isin(c.index) & df.imsi.notna()].sort_values(["a", "ts"])
    end = rows.ts + pd.to_timedelta(rows.dur.fillna(0), unit="s")
    prev_end = end.groupby(rows.a).shift()
    prev_imsi = rows.imsi.groupby(rows.a).shift()
    simult = ((rows.ts < prev_end) & (rows.imsi != prev_imsi)).groupby(rows.a).sum()
    switches = ((rows.imsi != prev_imsi) & prev_imsi.notna()).groupby(rows.a).sum()
    out = []
    for num, p in c.iterrows():
        m, s = int(simult.get(num, 0)), int(switches.get(num, 0))
        f = [
            Factor(f"Один номер — {p.n_imsi} разных SIM-карт (IMSI)", pts(50, (p.n_imsi - 1) / 3)),
            Factor(f"{plural(m, 'вызов идёт', 'вызова идут', 'вызовов идут')} одновременно с разных SIM"
                   if m else "Одновременных вызовов нет", pts(30, m / 3)),
            Factor(f"SIM сменилась {plural(s, 'раз', 'раза', 'раз')} за {span(p.span_h)}", pts(20, s / 5)),
        ]
        imsis = sorted(rows[rows.a == num].imsi.unique())
        out.append(Finding(num, "S4", "clone", f, group=f"S4-{num}", stats=_stats(p) | {"imsi": imsis}))
    return out


# --------------------------------------------------------------------------- S5 цепочки
def find_chains(df: pd.DataFrame) -> pd.DataFrame:
    """Один вызов → серия записей 03 от одного звонящего с шагом ≤ 2 с, где C предыдущей = B следующей."""
    f = df[df.type == "03"].sort_values(["a", "ts"]).reset_index(drop=True)
    linked = ((f.a == f.a.shift()) & (f.ts - f.ts.shift()).dt.total_seconds().between(0, C.CHAIN_STEP_S)
              & (f.b == f.c.shift()))
    f["cid"] = (~linked).cumsum()
    ch = f.groupby("cid").agg(caller=("a", "first"), ts=("ts", "first"), links=("b", "size"),
                              nodes=("b", list), last=("c", "last"), dur=("dur", "first"))
    ch = ch[ch.links >= C.CHAIN_MIN_LINKS].copy()
    ch["path"] = [tuple(n) + (l,) for n, l in zip(ch.nodes, ch["last"])]
    ch["ring"] = [l in n for n, l in zip(ch.nodes, ch["last"])]
    return ch


def detect_chains(df: pd.DataFrame, prof: pd.DataFrame) -> list[Finding]:
    ch = find_chains(df)
    # маршрут = набор узлов; одинаковые маршруты используются многими звонящими
    route_id = {}
    for path in ch.path:
        key = frozenset(path)
        route_id.setdefault(key, len(route_id) + 1)
    node_routes = defaultdict(set)
    for path in ch.path:
        for n in path:
            node_routes[n].add(route_id[frozenset(path)])
    out = []
    for num, routes in node_routes.items():
        sub = ch[[num in p for p in ch.path]]
        path = max(sub.path, key=len)
        uniq = list(dict.fromkeys(path))
        ring = bool(sub.ring.any())
        ops = len({operator(x) for x in uniq})
        callers = sub.caller.nunique()
        own_calls = int(prof.n_out.get(num, 0)) if num in prof.index else 0
        f = [
            Factor(f"Узел цепочки переадресаций из {len(uniq)} номеров: "
                   + " → ".join(tail(x) for x in path), pts(35, (len(uniq) - 1) / 3)),
            Factor(f"Через цепочку прошло {calls(len(sub))} от "
                   f"{plural(callers, 'абонента', 'разных абонентов', 'разных абонентов')}", pts(25, callers / 10)),
            Factor("Цепочка замкнута в кольцо — вызов «гуляет» с нулевой длительностью" if ring
                   else f"Переадресация через {plural(ops, 'оператора', 'операторов', 'операторов')}",
                   20 if ring else pts(20, (ops - 1) / 2)),
            Factor("Сам почти не звонит — только пересылает" if own_calls <= 3 else f"Своих вызовов: {own_calls}",
                   pts(20, own_calls <= 3)),
        ]
        rid = min(routes)
        out.append(Finding(num, "S5", "node", f, group=f"S5-{rid}", related=[x for x in uniq if x != num],
                           stats={"chains": int(len(sub)), "callers": int(callers), "ring": ring, "path": list(path)}))
    return out


# --------------------------------------------------------------------------- S6 карусель
def detect_carousels(df: pd.DataFrame, prof: pd.DataFrame) -> list[Finding]:
    e = df[df.type != "03"][["a", "b", "dur", "ts"]]
    pairs = pd.concat([e[["a", "b"]].set_axis(["x", "y"], axis=1), e[["b", "a"]].set_axis(["x", "y"], axis=1)])
    pairs = pairs.drop_duplicates()
    deg = pairs.groupby("x").y.nunique()
    vol = pd.concat([e.a, e.b]).value_counts()
    cand = set(deg[deg <= C.CAROUSEL_MAX_DEGREE].index) & set(vol[vol >= C.CAROUSEL_MIN_CALLS].index)
    g = nx.Graph()
    g.add_edges_from(pairs[pairs.x.isin(cand) & pairs.y.isin(cand)].itertuples(index=False, name=None))
    out = []
    for gi, comp in enumerate(sorted(nx.connected_components(g), key=min), 1):
        if not C.CAROUSEL_MIN_SIZE <= len(comp) <= C.CAROUSEL_MAX_SIZE:
            continue
        sub = e[e.a.isin(comp) | e.b.isin(comp)]
        inside = sub.a.isin(comp) & sub.b.isin(comp)
        closed = inside.mean()
        d = sub.dur[inside]
        in_band = d.between(8, 45).mean()
        if closed < C.CAROUSEL_MIN_CLOSED or in_band < 0.9:
            continue
        hrs = (sub.ts.max() - sub.ts.min()).total_seconds() / 3600
        night = ((sub.ts.dt.hour >= 22) | (sub.ts.dt.hour < 6)).mean()
        members = sorted(comp)
        for num in members:
            k = int(deg.get(num, 0))
            f = [
                Factor(f"Закрытая группа из {len(comp)} номеров: {pct(closed)} вызовов — внутри группы",
                       pts(40, (closed - 0.8) / 0.2)),
                Factor(f"{calls(int(inside.sum()))} между участниками за {span(hrs)}, ночью — {pct(night)}",
                       pts(25, min(1, inside.sum() / 200) * (night > 0.1))),
                Factor(f"Длительность всегда {d.min():.0f}–{d.max():.0f} с (медиана {d.median():.0f} с)",
                       pts(20, in_band)),
                Factor(f"У номера {plural(k, 'собеседник', 'собеседника', 'собеседников')} — и все из группы",
                       pts(15, k <= len(comp) - 1)),
            ]
            out.append(Finding(num, "S6", "member", f, group=f"S6-{gi}", related=[x for x in members if x != num],
                               stats=_stats(prof.loc[num]) if num in prof.index else {}))
    return out


# --------------------------------------------------------------------------- S7 вишинг
def detect_vishing(df: pd.DataFrame, prof: pd.DataFrame) -> list[Finding]:
    long_share = df.dur.between(C.VISH_LONG_MIN_S, C.VISH_LONG_MAX_S).groupby(df.a).mean()
    c = prof[(prof.n_out >= C.VISH_MIN_CALLS) & (prof.n_in <= 1)
             & (long_share.reindex(prof.index).fillna(0) >= C.VISH_MIN_LONG_SHARE)]
    hits = df[df.a.isin(c.index)][["a", "b", "ts", "dur"]].rename(columns={"a": "fraud", "b": "victim", "ts": "tf"})
    pre = df[(df.type == "01") & df.a.str[:3].isin(CITY_CODES) & (df.dur <= C.VISH_SPOOF_MAX_DUR)]
    pre = pre.merge(hits[["fraud", "victim", "tf"]], left_on="b", right_on="victim")
    pre = pre[(pre.ts < pre.tf) & (pre.ts >= pre.tf - pd.Timedelta(hours=C.VISH_WINDOW_H))]
    pair_hits = pre.groupby(["fraud", "a"]).victim.nunique()
    spoof_pairs = pair_hits[pair_hits >= C.VISH_SPOOF_MIN_VICTIMS].reset_index()
    spoof_short = (df.dur <= C.VISH_SPOOF_MAX_DUR).groupby(df.a).mean()
    spoof_pairs = spoof_pairs[spoof_pairs.a.map(spoof_short).fillna(0) >= 0.9]
    spoof_of = spoof_pairs.groupby("fraud").a.apply(list).to_dict()
    to_spoof = df[df.b.isin(set(spoof_pairs.a))][["a", "b"]]

    out = []
    for gi, (num, p) in enumerate(c.iterrows(), 1):
        mine = hits[hits.fraud == num]
        pool = spoof_of.get(num, [])
        prepped = pre[(pre.fraud == num) & pre.a.isin(pool)].groupby(["victim", "tf"]).size()
        share = len(prepped) / max(1, len(mine))
        f = [
            Factor(f"{plural(p.n_out, 'длинный разговор', 'длинных разговора', 'длинных разговоров')} "
                   f"(медиана {p.median_dur / 60:.0f} мин) — всё с разными людьми", pts(35, p.uniq_share)),
            Factor(f"Перед звонком {pct(share)} жертв получили серию сбросов с «городских» номеров",
                   pts(35, share / 0.8)),
            Factor(f"Работает с пулом из {plural(len(pool), 'спуф-номера', 'спуф-номеров', 'спуф-номеров')}",
                   pts(15, len(pool) / 4)),
            Factor("Нет входящих — номер только звонит" if p.n_in == 0 else f"Входящих всего {p.n_in}", 15 if p.n_in == 0 else 10),
        ]
        grp = f"S7-{gi}"
        out.append(Finding(num, "S7", "fraudster", f, group=grp, related=pool, stats=_stats(p) | {"victims": int(mine.victim.nunique())}))
        victims = set(mine.victim)
        for s in pool:
            k = int(pair_hits.get((num, s), 0))
            cb = int(((to_spoof.b == s) & to_spoof.a.isin(victims)).sum())
            fs = [
                Factor(f"Звонил {plural(k, 'жертве', 'жертвам', 'жертвам')} мошенника {mask(num)} "
                       f"за несколько часов до его звонка", pts(45, k / 4)),
                Factor(f"Все звонки короткие или сбросы (≤ {C.VISH_SPOOF_MAX_DUR} с)", pts(25, spoof_short.get(s, 0))),
                Factor(f"{plural(cb, 'жертва перезвонила', 'жертвы перезвонили', 'жертв перезвонили')} на этот номер"
                       if cb else "Жертвы не перезванивали", pts(15, cb / 3)),
                Factor("«Городской» номер — звонок выглядит как из банка или госоргана", 15),
            ]
            out.append(Finding(s, "S7", "spoof", fs, group=grp, related=[num],
                               stats=_stats(prof.loc[s]) if s in prof.index else {}))
    return out


# --------------------------------------------------------------------------- легитимные
def recognize_legit(df: pd.DataFrame, prof: pd.DataFrame, closed_groups: frozenset = frozenset()) -> list[Finding]:
    """closed_groups — номера из замкнутых групп (карусели): у них тоже «постоянный круг контактов»,
    но он замкнут сам на себя, поэтому под профиль диспетчерской они не подходят."""
    out = []
    big = prof[prof.n_out >= C.LEGIT_MIN_CALLS]

    # D1 колл-центр
    d1 = big[big.is_city & big.zero_share.between(0.2, 0.5) & (big.night_share == 0)
             & (big.hour_min >= 8) & (big.hour_max <= 20)]
    for num, p in d1.iterrows():
        f = [
            Factor(f"Городской номер: {calls(p.n_out)} исходящих", 30),
            Factor(f"{pct(p.zero_share)} вызовов без ответа", 25),
            Factor(f"Работает только в рабочее время: {p.hour_min:.0f}:00–{p.hour_max + 1:.0f}:00"
                   + (", по будням" if p.weekend_share == 0 else ""), -20),
            Factor(f"Клиенты перезванивают: {calls(p.n_in)} входящих" if p.n_in else "Входящих нет", -15 if p.n_in else 0),
            Factor(f"Нормальные разговоры: медиана {p.median_dur:.0f} с", -10),
        ]
        out.append(Finding(num, "D1", "legit", f, stats=_stats(p)))

    # D2 банковские оповещения
    hours = df[df.a.isin(big.index)].groupby("a").ts.apply(lambda s: sorted(set(s.dt.hour)))
    d2 = big[(big.active_days >= 3) & (big.active_hours <= 4) & big.median_dur.between(6, 20)
             & (big.b_density < 0.01)]
    for num, p in d2.iterrows():
        hh = ", ".join(f"{h}:00" for h in hours[num])
        f = [
            Factor(f"Много коротких вызовов: {calls(p.n_out)}, медиана {p.median_dur:.0f} с", 30),
            Factor("Нет входящих", 10),
            Factor(f"Волны в одни и те же часы ({hh}) — {plural(p.active_days, 'день', 'дня', 'дней')} подряд", -20),
            Factor("Номера абонентов — из клиентской базы, не перебор подряд", -10),
        ]
        out.append(Finding(num, "D2", "legit", f, stats=_stats(p) | {"wave_hours": hours[num]}))

    # D3 ночная диспетчерская / охрана
    d3 = prof[(prof.n_out >= 50) & (prof.night_share >= 0.4) & (prof.uniq_share <= 0.35)
              & (prof.uniq_b >= 8) & (prof.n_in >= 0.3 * prof.n_out)]
    d3 = d3[~d3.index.isin(closed_groups)]
    for num, p in d3.iterrows():
        f = [
            Factor(f"{pct(p.night_share)} вызовов — ночью", 30),
            Factor(f"Постоянный круг: {plural(p.uniq_b, 'контакт', 'контакта', 'контактов')} на {calls(p.n_out)}", -10),
            Factor(f"Много входящих: {p.n_in}", -5),
            Factor(f"Нормальная длительность: медиана {p.median_dur:.0f} с", -5),
        ]
        out.append(Finding(num, "D3", "legit", f, stats=_stats(p)))

    # D4 горячая линия: много переадресаций на один номер от 10–30 номеров компании
    fw = df[df.type == "03"]
    hc = fw.groupby("c").agg(n=("b", "size"), k=("b", "nunique"), md=("dur", "median"))
    hot = hc[(hc.n >= C.HOTLINE_MIN_FWD) & hc.k.between(8, 40) & (hc.md >= 30)]
    for num, h in hot.iterrows():
        company = sorted(fw[fw.c == num].b.unique())
        f = [
            Factor(f"{plural(h.n, 'переадресация', 'переадресации', 'переадресаций')} на один номер", 30),
            Factor(f"Переадресуют {plural(h.k, 'номер', 'номера', 'номеров')} одной компании", -15),
            Factor(f"Нормальные разговоры: медиана {h.md:.0f} с", -5),
        ]
        out.append(Finding(num, "D4", "legit", f, group=f"D4-{num}", related=company, stats={"forwards": int(h.n)}))
        for b in company:
            n_b = int(((fw.b == b) & (fw.c == num)).sum())
            fb = [
                Factor(f"Переадресует вызовы: {n_b}", 20),
                Factor(f"Все переадресации — на горячую линию {mask(num)}", -10),
            ]
            out.append(Finding(b, "D4", "legit", fb, group=f"D4-{num}", related=[num], stats={"forwards": n_b}))

    # D5 оповещение ЖКХ / МЧС
    d5 = big[big.is_city & (big.span_h <= 3) & (big.n_in == 0) & (big.b_density < 0.01) & (big.median_dur >= 15)]
    for num, p in d5.iterrows():
        f = [
            Factor(f"{calls(p.n_out)} за {span(p.span_h)}", 35),
            Factor("Нет входящих", 10),
            Factor("Номера абонентов случайные — не перебор подряд", -20),
            Factor(f"С абонентами говорят: медиана {p.median_dur:.0f} с, сбросов {pct(p.zero_share)}", -15),
        ]
        out.append(Finding(num, "D5", "legit", f, stats=_stats(p)))
    return out


FRAUD_DETECTORS = [detect_wangiri, detect_robots, detect_simbox, detect_clones,
                   detect_chains, detect_carousels, detect_vishing]
