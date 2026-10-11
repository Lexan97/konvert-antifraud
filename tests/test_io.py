"""Загрузчик обязан чинить ошибки формата и отчитываться о каждой правке."""
import pandas as pd
import pytest

from konvert.io import load_cdr

LINES = [
    "02;250011111111111;8991234567;0261234567;20261001080000;54;",          # 0 эталон
    "2;250011111111111;8991234567;0261234567;20261001080001;10;",           # 1 тип без нуля
    "02;250011111111111;+78991234567;80261234567;20261001080002;10;",       # 2 коды страны
    "01;;4991234567;8991234567;2026-10-01 08:00:03;5;",                     # 3 другой формат даты
    "01;;4991234567;8991234567;20261301080004;5;",                          # 4 13-й месяц
    "02;250011111111111;8991234567;0261234567;20261001080005;abc;",         # 5 длительность не число
    "02;250011111111111;8991234567;0261234567;20261001080006;99999999;",    # 6 длительность-выброс
    "03;250011111111111;8991234567;0261234567;20261001080007;8101234567",   # 7 нет длительности, C на месте
    "02;250011111111111;8991234567;0261234567;20261001080008;7;;;",         # 8 лишние поля
    "02;25001;8991234567;0261234567;20261001080009;7;",                     # 9 обрезанный IMSI
    "AA;250011111111111;8991234567;0261234567;20261001080010;7;",           # 10 неизвестный тип
    "02;250011111111111;8991234567;;20261001080011;7;",                     # 11 нет номера B — строка отбрасывается
    "02;250011111111111;7771234567;0261234567;20261001080012;7;",           # 12 испорченный код оператора
    "01;;4991234567;8991234567;20261001080013;12.5;",                       # 13 дробная длительность
]


@pytest.fixture(scope="module")
def loaded(tmp_path_factory):
    d = tmp_path_factory.mktemp("cdr")
    (d / "CDR_000001_20261001080000.cdr").write_text("\n".join(LINES) + "\n", encoding="utf-8")
    return load_cdr(str(d))


def test_row_without_b_is_dropped_and_reported(loaded):
    df, rep = loaded
    assert len(df) == len(LINES) - 1
    assert rep.issues["number_missing"] == 1


def test_type_is_normalised_and_inferred(loaded):
    df, rep = loaded
    assert set(df.type.astype(str)) <= {"01", "02", "03"}
    assert df.type.astype(str).iloc[1] == "02"       # «2» → «02»
    assert df.type.astype(str).iloc[10] == "02"      # «AA» при наличии IMSI → исходящий
    assert rep.issues["type_padded"] == 1 and rep.issues["type_inferred"] == 1


def test_country_code_is_stripped_and_leading_zero_kept(loaded):
    df, _ = loaded
    assert df.a.iloc[2] == "8991234567"
    assert df.b.iloc[2] == "0261234567"              # ведущий ноль кода Альфы не теряется
    assert (df.a.str.len() == 10).all() and (df.b.str.len() == 10).all()


def test_bad_timestamps_are_fixed_from_neighbours(loaded):
    df, rep = loaded
    assert df.ts.iloc[3] == pd.Timestamp("2026-10-01 08:00:03")
    assert df.ts.iloc[4] == pd.Timestamp("2026-10-01 08:00:03")   # 13-й месяц → время предыдущей записи файла
    assert bool(df.ts_imputed.iloc[4]) and not bool(df.ts_imputed.iloc[3])
    assert df.ts.notna().all()
    assert rep.issues["ts_reformatted"] == 1 and rep.issues["ts_imputed"] == 1


def test_bad_durations_become_missing_not_zero(loaded):
    df, _ = loaded
    assert pd.isna(df.dur.iloc[5]) and pd.isna(df.dur.iloc[6]) and pd.isna(df.dur.iloc[7])
    assert df.dur.iloc[12] == 12 or df.dur.iloc[12] == 13         # 12.5 округлено, а не отброшено
    assert df.dur.max() <= 86400


def test_forward_target_survives_missing_duration(loaded):
    df, _ = loaded
    assert df.c.iloc[7] == "8101234567" and df.type.astype(str).iloc[7] == "03"


def test_truncated_imsi_is_not_used(loaded):
    df, rep = loaded
    assert pd.isna(df.imsi.iloc[9])
    assert rep.issues["imsi_invalid"] == 1


def test_broken_operator_code_is_repaired_by_imsi(loaded):
    df, rep = loaded
    assert df.a.iloc[11] == "8991234567"             # строка 12 исходного файла (строка 11 отброшена)
    assert rep.issues["number_code_repaired"] == 1


def test_report_counts_touched_rows_once(loaded):
    _, rep = loaded
    q = rep.as_dict()
    assert q["rows"] == len(LINES)
    assert q["rows_fixed"] == len(LINES) - 1         # все строки, кроме эталонной
