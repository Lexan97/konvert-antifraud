"""Полный прогон: CDR → профили → детекторы → решения → ответ и данные для интерфейса.

    python -m konvert.pipeline --cdr data/cdr_out --out outputs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from . import __version__, config as C, early
from .detectors import FRAUD_DETECTORS, Finding, recognize_legit
from .io import load_cached
from .numbering import load_whitelist, mask, operator, pretty
from .policy import decide
from .profile import activity_by_hour, build_profiles
from .schemes import FRAUD, LEGIT, ROLES


def run(cdr_dir: str, out_dir: str, log=print, with_ml: bool = True) -> dict:
    t0 = time.time()
    df, quality = load_cached(cdr_dir, os.path.join(out_dir, "cache", "cdr.pkl"))
    log(f"Загружено {len(df):,} записей за {time.time() - t0:.0f} с")
    prof = build_profiles(df)
    prof.to_pickle(os.path.join(out_dir, "cache", "profiles.pkl"))
    log(f"Профили: {len(prof):,} номеров")

    fraud: list[Finding] = []
    for det in FRAUD_DETECTORS:
        found = det(df, prof)
        log(f"  {det.__name__:<18} {len(found):>4} номеров")
        fraud.extend(found)
    legit = recognize_legit(df, prof, frozenset(f.number for f in fraud if f.scheme == "S6"))
    log(f"  {'recognize_legit':<18} {len(legit):>4} номеров")

    # номер может попасть в несколько детекторов — оставляем самую сильную находку, остальные — как доп. схемы
    best: dict[str, Finding] = {}
    extra = defaultdict(list)
    for f in sorted(fraud, key=lambda x: -x.score):
        if f.number in best:
            extra[f.number].append(f.scheme)
        else:
            best[f.number] = f
    legit_by_num = {}
    for f in legit:
        legit_by_num.setdefault(f.number, f)

    numbers, conflicts = [], []
    whitelist = load_whitelist(C.WHITELIST_FILE)
    if whitelist:
        log(f"Белый список оператора: {len(whitelist)} номеров из {C.WHITELIST_FILE}")
    for num, f in best.items():
        lm = legit_by_num.get(num)
        if lm:
            conflicts.append(num)
        numbers.append(_card(f, decide(f.scheme, f.role, f.score, len(f.factors), num,
                                       legit_match=lm.scheme if lm else None, whitelist=whitelist),
                             extra.get(num, [])))
    legit_cards = [_card(f, decide(f.scheme, f.role, f.score, len(f.factors), f.number,
                                   whitelist=whitelist))
                   for n, f in legit_by_num.items() if n not in best]

    answer = sorted((c for c in numbers if c["score"] >= C.ANSWER_MIN_SCORE), key=lambda c: (c["scheme"], c["group"] or "", c["number"]))
    _attach_activity(df, numbers + legit_cards)
    _attach_samples(df, numbers + legit_cards)
    groups = _groups(df, numbers)

    start = df.ts.min().normalize()
    slot = ((df.ts - start).dt.total_seconds() // 3600).astype(int)
    fraud_set = {c["number"] for c in answer}
    is_fraud = df.a.isin(fraud_set) | df.b.isin(fraud_set) | df.c.isin(fraud_set)
    hourly_total = slot.value_counts().sort_index()
    hourly_fraud = slot[is_fraud].value_counts().reindex(hourly_total.index).fillna(0)

    early_report = early.evaluate(df, answer, {c["number"] for c in legit_cards})
    for code, e in early_report.items():
        log(f"  раннее обнаружение {code}: {e['detected']}/{e['numbers']} номеров, медиана {e['median_minutes']} мин, "
            f"предотвращено {e['prevented_share']:.0%} вызовов, ложных тревог "
            f"{e['false_alarms_legit'] + e['false_alarms_unknown']}")

    detect_s = round(time.time() - t0, 1)
    ml_report = None
    if with_ml:
        from . import ml  # импорт здесь, чтобы расчёт без модели не требовал catboost
        ml_report = ml.second_opinion(df, prof, answer, legit_cards)
        probs = ml_report.pop("probs")
        for c in numbers + legit_cards:
            c["ml_prob"] = probs.get(c["number"])
        log(f"  модель CatBoost: совпадение с детекторами {ml_report['agree']}/{ml_report['positives']}, "
            f"только правила {ml_report['rules_only']}, только модель {ml_report['model_only']}, ROC-AUC {ml_report['roc_auc']}")

    by_scheme = {}
    for code in FRAUD:
        cs = [c for c in answer if c["scheme"] == code]
        by_scheme[code] = {
            "numbers": len(cs),
            "groups": len({c["group"] for c in cs if c["group"]}),
            "roles": dict(Counter(c["role"] for c in cs)),
            "calls": int(df.a.isin({c["number"] for c in cs}).sum() + df.b.isin({c["number"] for c in cs}).sum()),
            "autoblock": sum(c["decision"]["autoblock"] for c in cs),
        }
    legit_by_type = {code: sum(1 for c in legit_cards if c["scheme"] == code) for code in LEGIT}

    result = {
        "meta": {
            "version": __version__,
            "generated": pd.Timestamp.now().isoformat(timespec="seconds"),
            "period": [str(df.ts.min()), str(df.ts.max())],
            "records": int(len(df)),
            "numbers_seen": int(pd.concat([df.a, df.b]).nunique()),
            "runtime_s": round(time.time() - t0, 1),
            "detect_s": detect_s,
            "hour0": str(start),
        },
        "quality": quality,
        "summary": {
            "fraud_numbers": len(answer),
            "fraud_groups": len({c["group"] for c in answer if c["group"]}),
            "fraud_calls": int(is_fraud.sum()),
            "autoblock": sum(c["decision"]["autoblock"] for c in answer),
            "legit_numbers": len(legit_cards),
            "legit_conflicts": len(conflicts),
            "by_scheme": by_scheme,
            "legit_by_type": legit_by_type,
        },
        "schemes": {"fraud": FRAUD, "legit": LEGIT, "roles": ROLES},
        "thresholds": {k: getattr(C, k) for k in dir(C) if k.isupper()},
        "early": early_report,
        "ml": ml_report,
        "hourly": {"total": hourly_total.astype(int).tolist(), "fraud": hourly_fraud.astype(int).tolist()},
        "numbers": sorted(numbers, key=lambda c: (-c["score"], -c.get("seen", {}).get("records", 0))),
        "legit": legit_cards,
        "groups": groups,
    }
    _write(out_dir, result, answer)
    log(f"Готово за {time.time() - t0:.0f} с: {len(answer)} номеров в ответе, "
        f"{len(legit_cards)} легитимных источников распознано, конфликтов {len(conflicts)}")
    return result


def _card(f: Finding, decision: dict, extra_schemes: list | None = None) -> dict:
    d = f.as_dict()
    d.update({
        "masked": mask(f.number), "pretty": pretty(f.number), "operator": operator(f.number),
        "decision": decision, "extra_schemes": sorted(set(extra_schemes or []) - {f.scheme}),
    })
    return d


def _attach_activity(df: pd.DataFrame, cards: list[dict]) -> None:
    act = activity_by_hour(df, {c["number"] for c in cards})
    for c in cards:
        c["activity"] = act.get(c["number"], [])


def _attach_samples(df: pd.DataFrame, cards: list[dict], k: int = 6) -> None:
    """Несколько «конвертов» вызова на номер — для карточки вызова в интерфейсе."""
    nums = {c["number"] for c in cards}
    sub = df[df.a.isin(nums) | df.b.isin(nums) | df.c.isin(nums)].reset_index(drop=True)
    pos = defaultdict(list)
    for col in ("a", "b", "c"):
        for num, ix in sub.groupby(col).indices.items():
            if num in nums:
                pos[num].extend(ix.tolist())
    for c in cards:
        ix = sorted(set(pos.get(c["number"], [])))
        if ix:
            c["seen"] = {"records": len(ix), "first": str(sub.ts.iloc[ix[0]]), "last": str(sub.ts.iloc[ix[-1]])}
        ix = ix[:: max(1, len(ix) // k)][:k]
        c["samples"] = [
            {"type": str(r.type), "a": r.a, "b": r.b, "c": None if pd.isna(r.c) else r.c, "ts": str(r.ts),
             "dur": None if pd.isna(r.dur) else int(r.dur)}
            for r in sub.iloc[ix].itertuples()
        ]


def _groups(df: pd.DataFrame, cards: list[dict]) -> dict:
    """Связи внутри групп — для графа в интерфейсе."""
    by_group = defaultdict(list)
    for c in cards:
        if c["group"]:
            by_group[c["group"]].append(c["number"])
    carousel = {c["number"] for c in cards if c["scheme"] == "S6"}
    inner = df[df.a.isin(carousel) & df.b.isin(carousel) & (df.type != "03")][["a", "b"]]
    out = {}
    for gid, members in by_group.items():
        scheme = gid.split("-")[0]
        ms = set(members)
        edges = []
        if scheme == "S6":
            e = inner[inner.a.isin(ms) & inner.b.isin(ms)]
            lo, hi = np.minimum(e.a.values, e.b.values), np.maximum(e.a.values, e.b.values)
            cnt = pd.Series(1, index=pd.MultiIndex.from_arrays([lo, hi])).groupby(level=[0, 1]).sum()
            edges = [[a, b, int(n)] for (a, b), n in cnt.items()]
        elif scheme == "S5":
            card = next(c for c in cards if c["group"] == gid)
            path = card["stats"]["path"]
            edges = [[path[i], path[i + 1], 1] for i in range(len(path) - 1)]
        elif scheme in ("S1", "S7"):
            hub = next(c["number"] for c in cards if c["group"] == gid and c["role"] in ("initiator", "fraudster"))
            edges = [[hub, m, 1] for m in members if m != hub]
        out[gid] = {"scheme": scheme, "members": sorted(members), "edges": edges}
    return out


def _write(out_dir: str, result: dict, answer: list[dict]) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, separators=(",", ":"), default=str)
    with open(os.path.join(out_dir, "answer.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"# Конверт v{__version__}: {len(answer)} номеров, формат «номер;схема»\n")
        for code, meta in FRAUD.items():
            fh.write(f"# {code} — {meta['title']}\n")
        for c in answer:
            fh.write(f"{c['number']};{c['scheme']}\n")
    with open(os.path.join(out_dir, "answer_plain.txt"), "w", encoding="utf-8") as fh:
        for c in answer:
            fh.write(c["number"] + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Конверт: поиск мошеннических номеров в CDR")
    ap.add_argument("--cdr", default="data/cdr_out", help="каталог с файлами *.cdr")
    ap.add_argument("--out", default="outputs", help="куда положить answer.txt и results.json")
    ap.add_argument("--no-ml", action="store_true", help="не обучать модель второго контура (быстрее)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run(args.cdr, args.out, with_ml=not args.no_ml)


if __name__ == "__main__":
    main()
