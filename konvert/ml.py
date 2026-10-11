"""Второй контур: модель CatBoost как независимая перепроверка детекторов.

Разметки в данных нет, поэтому модель учится на находках детекторов («учитель»),
но видит только общий поведенческий профиль номера — без графа и без правил схем.
Обучение идёт с перекрёстной проверкой по группам: все номера одной связки или
карусели попадают либо в обучение, либо в проверку, так что модель оценивает
каждый номер, не видев его «соседей по схеме».

Что это даёт:
  * совпадение двух независимых контуров — довод в пользу находки;
  * расхождения — очередь аналитику: правила нашли, а модель не узнаёт (слабая находка),
    либо модель видит сходство с фродом там, где правила молчат (кандидат в новую схему);
  * вклад признаков (SHAP) объясняет мнение модели тем же языком факторов;
  * «экзамен на новую схему» показывает, какие схемы модель узнала бы без подсказки,
    а для каких нужны специальные детекторы по графу связей.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold

from . import config as C

FEATURES = {
    "n_out": "Исходящих вызовов",
    "rate_per_h": "Вызовов в час",
    "uniq_share": "Доля уникальных собеседников",
    "zero_share": "Доля вызовов без ответа",
    "short_share": "Доля сбросов на 0–2 с",
    "median_dur": "Медиана длительности",
    "night_share": "Доля ночных вызовов",
    "weekend_share": "Доля вызовов в выходные",
    "active_hours": "Разных часов суток с активностью",
    "active_days": "Дней с активностью",
    "span_h": "Часов между первым и последним вызовом",
    "in_ratio": "Входящих на один исходящий",
    "fwd_share": "Доля переадресаций",
    "n_imsi": "Разных SIM (IMSI)",
    "is_city": "Городской номер",
    "b_step_log": "Шаг между набранными номерами (log10)",
    "contacts_closed": "Доля вызовов «своим» (взаимным) контактам",
}

# схемы, которые видны в профиле исходящих вызовов номера; цепочки, платные и спуф-номера
# почти не звонят сами — их находит только граф, и модель по профилю к ним не применяется
PROFILE_ROLES = {("S1", "initiator"), ("S2", "initiator"), ("S3", "sim"), ("S4", "clone"),
                 ("S6", "member"), ("S7", "fraudster")}


def build_features(df: pd.DataFrame, prof: pd.DataFrame, min_calls: int) -> pd.DataFrame:
    p = prof[prof.n_out >= min_calls]
    x = p[["n_out", "rate_per_h", "uniq_share", "zero_share", "short_share", "median_dur", "night_share",
           "weekend_share", "active_hours", "active_days", "span_h", "fwd_share", "n_imsi"]].copy()
    x["in_ratio"] = p.n_in / p.n_out
    x["is_city"] = p.is_city.astype(int)

    rows = df[df.a.isin(p.index)]
    bn = pd.to_numeric(rows.b, errors="coerce")
    step = {}
    for num, b in bn.groupby(rows.a):
        u = np.sort(b.dropna().unique())
        step[num] = np.median(np.diff(u)) if len(u) > 2 else np.nan
    x["b_step_log"] = np.log10(pd.Series(step).reindex(x.index).clip(lower=1))

    # взаимность: какая доля исходящих идёт тем, кто сам звонит этому номеру
    direct = df[df.type != "03"][["a", "b"]]
    back = set(zip(direct.b.to_numpy(), direct.a.to_numpy()))
    out = direct[direct.a.isin(p.index)]
    mutual = pd.Series([(a, b) in back for a, b in zip(out.a.to_numpy(), out.b.to_numpy())], index=out.index)
    x["contacts_closed"] = mutual.groupby(out.a).mean().reindex(x.index).fillna(0)
    return x[list(FEATURES)]


def second_opinion(df: pd.DataFrame, prof: pd.DataFrame, cards: list[dict], legit: list[dict]) -> dict:
    x = build_features(df, prof, C.ML_MIN_CALLS)
    by_num = {c["number"]: c for c in cards}
    y = pd.Series([int(n in by_num and (by_num[n]["scheme"], by_num[n]["role"]) in PROFILE_ROLES) for n in x.index],
                  index=x.index)
    # группа для перекрёстной проверки: связка/карусель целиком, у одиночных номеров — сам номер
    groups = pd.Series([(by_num[n]["group"] or n) if n in by_num else n for n in x.index], index=x.index)

    oof = pd.Series(0.0, index=x.index)
    shap = pd.DataFrame(0.0, index=x.index, columns=list(FEATURES))
    params = dict(iterations=300, depth=5, learning_rate=0.08, auto_class_weights="Balanced",
                  random_seed=42, verbose=False, thread_count=4, allow_writing_files=False)
    folds = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    for tr, te in folds.split(x, y, groups):
        model = CatBoostClassifier(**params).fit(x.iloc[tr], y.iloc[tr])
        oof.iloc[te] = model.predict_proba(x.iloc[te])[:, 1]
        shap.iloc[te] = model.get_feature_importance(Pool(x.iloc[te]), type="ShapValues")[:, :-1]
    final = CatBoostClassifier(**params).fit(x, y)

    # «Экзамен на новую схему»: убираем одну схему из обучения целиком и смотрим, узнает ли её модель
    scheme = pd.Series([by_num[n]["scheme"] if y[n] else "" for n in x.index], index=x.index)
    unseen = []
    for code in sorted(set(scheme) - {""}):
        held = scheme == code
        m = CatBoostClassifier(**params).fit(x[~held], y[~held])
        prob = m.predict_proba(x[held])[:, 1]
        unseen.append({"scheme": code, "numbers": int(held.sum()), "caught": int((prob >= C.ML_THRESHOLD).sum()),
                       "median_prob": round(float(np.median(prob)), 3)})
    importance = dict(zip(FEATURES, (final.get_feature_importance() / 100).round(4).tolist()))

    thr = C.ML_THRESHOLD
    pred = oof >= thr
    legit_set = {c["number"] for c in legit}
    tp, fn, fp = int((pred & (y == 1)).sum()), int((~pred & (y == 1)).sum()), int((pred & (y == 0)).sum())

    def explain(num: str) -> list[dict]:
        s = shap.loc[num].sort_values(key=abs, ascending=False).head(4)
        return [{"feature": FEATURES[k], "value": _fmt(k, x.at[num, k]), "impact": round(float(v), 2)} for k, v in s.items()]

    missed = [{"number": n, "prob": round(float(oof[n]), 3), "scheme": by_num[n]["scheme"], "why": explain(n)}
              for n in oof[(y == 1) & ~pred].sort_values().index]
    extra = [{"number": n, "prob": round(float(oof[n]), 3), "legit": n in legit_set,
              "other_scheme": by_num[n]["scheme"] if n in by_num else None, "why": explain(n)}
             for n in oof[(y == 0) & pred].sort_values(ascending=False).index]
    probs = {n: round(float(oof[n]), 3) for n in x.index if n in by_num or n in legit_set}
    return {
        "model": "CatBoostClassifier, 300 деревьев глубины 5; перекрёстная проверка 5 блоков по группам",
        "evaluated": int(len(x)), "min_calls": C.ML_MIN_CALLS, "threshold": thr,
        "positives": int(y.sum()),
        "roc_auc": round(float(roc_auc_score(y, oof)), 4),
        "pr_auc": round(float(average_precision_score(y, oof)), 4),
        "agree": tp, "rules_only": fn, "model_only": fp,
        "recall": round(tp / max(1, tp + fn), 4), "precision": round(tp / max(1, tp + fp), 4),
        "legit_flagged": sum(e["legit"] for e in extra),
        "importance": [{"feature": FEATURES[k], "share": v} for k, v in sorted(importance.items(), key=lambda kv: -kv[1])],
        "unseen": unseen,
        "rules_only_list": missed, "model_only_list": extra[:30],
        "probs": probs,
    }


def _fmt(key: str, v: float) -> str:
    if pd.isna(v):
        return "—"
    if key.endswith("_share") or key == "contacts_closed":
        return f"{100 * v:.0f}%"
    if key == "b_step_log":
        return f"{10 ** v:,.0f}".replace(",", " ")
    if key in ("is_city",):
        return "да" if v else "нет"
    if key in ("in_ratio", "rate_per_h", "span_h", "median_dur"):
        return f"{v:.1f}".replace(".", ",")
    return f"{v:.0f}"
