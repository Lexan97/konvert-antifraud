"""Загрузка CDR и исправление ошибок формата.

Формат записи (поля через «;», без заголовка):
    тип;IMSI_A;номер_A;номер_B;yyyymmddhh24miss;длительность;номер_C

В выгрузке встречаются ошибки: лишние/недостающие поля, коды страны (+7, 7, 8),
даты в другом формате или несуществующие, нечисловая/отрицательная длительность,
обрезанные IMSI, испорченный код оператора («777» вместо 025/026/027).
Каждая правка фиксируется в отчёте о качестве данных — ничего не теряется молча.
"""
from __future__ import annotations

import glob
import os
from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .numbering import CODES

MAX_DURATION = 24 * 3600  # длительность > суток — заведомо мусор (например, 99999999)


@dataclass
class QualityReport:
    files: int = 0
    rows: int = 0
    rows_clean: int = 0
    issues: Counter = field(default_factory=Counter)
    examples: dict = field(default_factory=dict)
    touched: np.ndarray | None = None

    def add(self, issue: str, mask: pd.Series, raw: pd.Series, limit: int = 3) -> None:
        n = int(mask.sum())
        if n:
            if self.touched is None:
                self.touched = np.zeros(len(raw), dtype=bool)
            self.touched |= mask.to_numpy(dtype=bool)
            self.issues[issue] += n
            self.examples.setdefault(issue, raw[mask].head(limit).tolist())

    def as_dict(self) -> dict:
        return {
            "files": self.files,
            "rows": self.rows,
            "rows_clean": self.rows_clean,
            "rows_fixed": self.rows - self.rows_clean,
            "issues": [
                {"issue": k, "title": ISSUE_TITLES.get(k, k), "count": v, "examples": self.examples.get(k, [])}
                for k, v in self.issues.most_common()
            ],
        }


ISSUE_TITLES = {
    "fields_missing": "Не хватает поля (длительность пропущена)",
    "fields_extra": "Лишние поля в конце строки",
    "type_padded": "Тип без ведущего нуля («2» → «02»)",
    "type_inferred": "Неизвестный тип вызова — восстановлен по IMSI и номеру C",
    "number_country_code": "Номер с кодом страны (+7 / 7 / 8) — приведён к 10 цифрам",
    "number_missing": "Пустой или нечитаемый номер",
    "number_code_repaired": "Испорченный код оператора (777) — восстановлен",
    "number_code_unknown": "Неизвестный код оператора",
    "imsi_invalid": "IMSI не из 15 цифр — не используется",
    "ts_reformatted": "Дата в формате «YYYY-MM-DD hh:mm:ss» — приведена",
    "ts_imputed": "Несуществующая или неполная дата — взята по соседним записям файла",
    "dur_invalid": "Нечисловая или отрицательная длительность",
    "dur_fraction": "Дробная длительность — округлена",
    "dur_outlier": "Длительность больше суток — отброшена",
}


def _read_lines(cdr_dir: str) -> tuple[pd.DataFrame, int]:
    files = sorted(glob.glob(os.path.join(cdr_dir, "*.cdr")))
    if not files:
        raise FileNotFoundError(f"В {cdr_dir} нет файлов *.cdr")
    raw, file_idx = [], []
    for i, path in enumerate(files):
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        raw.extend(lines)
        file_idx.extend([i] * len(lines))
    frame = pd.DataFrame({"raw": raw, "file": np.asarray(file_idx, dtype=np.int32)})
    frame = frame[frame.raw.str.strip() != ""].reset_index(drop=True)
    return frame, len(files)


def _norm_number(s: pd.Series, rep: QualityReport, raw: pd.Series, required: bool) -> pd.Series:
    s = s.fillna("").str.strip()
    plus = s.str.startswith("+")
    s = s.str.lstrip("+")
    country = s.str.fullmatch(r"[78]\d{10}")
    rep.add("number_country_code", plus | country, raw)
    s = s.where(~country, s.str[1:])
    ok = s.str.fullmatch(r"\d{10}")
    if required:
        rep.add("number_missing", ~ok, raw)
    else:
        rep.add("number_missing", ~ok & (s != ""), raw)
    return s.where(ok, None)


def load_cdr(cdr_dir: str) -> tuple[pd.DataFrame, QualityReport]:
    """Читает все *.cdr из каталога и возвращает очищенный DataFrame + отчёт о качестве."""
    rep = QualityReport()
    frame, rep.files = _read_lines(cdr_dir)
    rep.rows = len(frame)
    raw = frame.raw
    parts = raw.str.split(";", expand=True)
    for k in range(parts.shape[1], 7):
        parts[k] = None
    nf = raw.str.count(";") + 1

    # --- число полей -------------------------------------------------------
    six = nf == 6
    looks_c = parts[5].fillna("").str.strip().str.fullmatch(r"\+?\d{10,11}")
    shift = six & looks_c  # «03;…;ts;C» — пропущена длительность, но номер C на месте
    parts.loc[shift, 6] = parts.loc[shift, 5]
    parts.loc[shift, 5] = ""
    parts.loc[six & ~looks_c, 6] = ""
    rep.add("fields_missing", nf < 7, raw)
    rep.add("fields_extra", nf > 7, raw)

    df = pd.DataFrame({"file": frame.file})

    # --- тип вызова --------------------------------------------------------
    t = parts[0].fillna("").str.strip()
    padded = t.isin(["1", "2", "3"])
    rep.add("type_padded", padded, raw)
    t = t.where(~padded, "0" + t)

    # --- IMSI --------------------------------------------------------------
    imsi = parts[1].fillna("").str.strip()
    bad_imsi = (imsi != "") & ~imsi.str.fullmatch(r"\d{15}")
    rep.add("imsi_invalid", bad_imsi, raw)
    df["imsi"] = imsi.where(imsi.str.fullmatch(r"\d{15}"), None)

    # --- номера ------------------------------------------------------------
    df["a"] = _norm_number(parts[2], rep, raw, required=True)
    df["b"] = _norm_number(parts[3], rep, raw, required=True)
    df["c"] = _norm_number(parts[6], rep, raw, required=False)

    unknown_t = ~t.isin(["01", "02", "03"])
    rep.add("type_inferred", unknown_t, raw)
    inferred = np.where(df.c.notna(), "03", np.where(df.imsi.notna(), "02", "01"))
    df["type"] = t.where(~unknown_t, pd.Series(inferred, index=t.index))

    # --- испорченный код оператора: 777XXXXXXX → 0??XXXXXXX ----------------
    _repair_codes(df, rep, raw)

    # --- время -------------------------------------------------------------
    ts_raw = parts[4].fillna("").str.strip()
    reformatted = ts_raw.str.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d")
    rep.add("ts_reformatted", reformatted, raw)
    digits = ts_raw.str.replace(r"\D", "", regex=True)
    ts = pd.to_datetime(digits.where(digits.str.len() == 14), format="%Y%m%d%H%M%S", errors="coerce")
    bad_ts = ts.isna()
    rep.add("ts_imputed", bad_ts, raw)
    # файлы упорядочены по времени — берём время соседней записи того же файла
    ts = ts.groupby(df.file).transform(lambda s: s.ffill().bfill())
    df["ts"] = ts
    df["ts_imputed"] = bad_ts.values

    # --- длительность ------------------------------------------------------
    dur_s = parts[5].fillna("").str.strip()
    dur = pd.to_numeric(dur_s, errors="coerce")
    invalid = dur.isna() | (dur < 0)
    rep.add("dur_invalid", invalid & (nf >= 7), raw)
    frac = dur.notna() & (dur >= 0) & (dur != dur.round())
    rep.add("dur_fraction", frac, raw)
    outlier = dur > MAX_DURATION
    rep.add("dur_outlier", outlier, raw)
    dur = dur.where(~(invalid | outlier)).round()
    df["dur"] = dur.astype("Float64").astype(float)

    df = df.dropna(subset=["a", "b"]).reset_index(drop=True)
    rep.rows_clean = rep.rows - int(rep.touched.sum() if rep.touched is not None else 0)
    df["type"] = df["type"].astype("category")
    return df[["file", "type", "imsi", "a", "b", "ts", "dur", "c", "ts_imputed"]], rep


def _repair_codes(df: pd.DataFrame, rep: QualityReport, raw: pd.Series) -> None:
    """Код «777» появляется только как порча настоящего кода. Восстанавливаем номер,
    если среди корректных номеров есть ровно один с тем же хвостом (а для номера A —
    сначала по IMSI, он однозначно указывает на абонента)."""
    cols = ["a", "b", "c"]
    known = pd.concat([df[c] for c in cols]).dropna()
    known = known[known.str[:3].isin(CODES)]
    by_tail: dict[str, set] = {}
    for num in known.unique():
        by_tail.setdefault(num[3:], set()).add(num)
    imsi_to_a = (
        df[df.a.notna() & df.a.str[:3].isin(CODES) & df.imsi.notna()]
        .drop_duplicates("imsi").set_index("imsi").a
    )
    for col in cols:
        s = df[col]
        bad = s.notna() & ~s.str[:3].isin(CODES)
        if not bad.any():
            continue
        fixed = s[bad].copy()
        for idx, num in fixed.items():
            cand = None
            if col == "a" and df.at[idx, "imsi"] in imsi_to_a.index:
                cand = imsi_to_a[df.at[idx, "imsi"]]
            if cand is None:
                options = by_tail.get(num[3:], set())
                cand = next(iter(options)) if len(options) == 1 else None
            fixed[idx] = cand
        repaired = fixed.notna()
        rep.add("number_code_repaired", bad & s.index.isin(fixed.index[repaired]), raw)
        rep.add("number_code_unknown", bad & s.index.isin(fixed.index[~repaired]), raw)
        df.loc[fixed.index[repaired], col] = fixed[repaired]


def load_cached(cdr_dir: str, cache_path: str) -> tuple[pd.DataFrame, dict]:
    """То же, что load_cdr, но с кешем на диске (pickle) — повторный запуск за секунды."""
    if os.path.exists(cache_path) and os.path.getmtime(cache_path) >= _newest_mtime(cdr_dir):
        obj = pd.read_pickle(cache_path)
        return obj["df"], obj["quality"]
    df, rep = load_cdr(cdr_dir)
    quality = rep.as_dict()
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    pd.to_pickle({"df": df, "quality": quality}, cache_path)
    return df, quality


def _newest_mtime(cdr_dir: str) -> float:
    return max(os.path.getmtime(p) for p in glob.glob(os.path.join(cdr_dir, "*.cdr")))

