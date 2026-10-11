"""HTTP-сервис: интерфейс оператора и API для интеграции.

    uvicorn konvert.api:app --port 8000

    GET  /                    интерфейс
    GET  /api/health          состояние сервиса
    GET  /api/results         полный результат последнего расчёта
    GET  /api/numbers         номера в ответе (фильтры: scheme, min_score)
    GET  /api/number/{msisdn} карточка номера: балл, факторы, решение
    POST /api/score-call      скоринг одного вызова по его «конверту»
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import __version__
from .numbering import operator
from .scoring import NumberIndex, normalize, score_call
from .webbuild import render

OUT_DIR = os.environ.get("KONVERT_OUT", "outputs")

app = FastAPI(
    title="Конверт — антифрод по метаданным вызова",
    version=__version__,
    description="Скоринг номеров и вызовов по CDR без доступа к содержимому разговора. "
                "Каждый ответ содержит факторы с вкладом в баллах.",
)


class Call(BaseModel):
    """«Конверт» вызова — те же поля, что в записи CDR."""
    type: str = Field("02", description="01 — входящий, 02 — исходящий, 03 — переадресация", pattern="^0[123]$")
    a: str = Field(..., description="Номер A (кто звонит), 10 цифр; код страны допускается", examples=["8991234567"])
    b: str = Field(..., description="Номер B (кому звонят)", examples=["0261234567"])
    c: str | None = Field(None, description="Номер C — куда переадресован вызов (для типа 03)")
    dur: int | None = Field(None, ge=0, description="Длительность, с")


@lru_cache(maxsize=1)
def _load(mtime: float) -> tuple[dict, NumberIndex]:
    with open(os.path.join(OUT_DIR, "results.json"), encoding="utf-8") as fh:
        results = json.load(fh)
    return results, NumberIndex(results)


def state() -> tuple[dict, NumberIndex]:
    path = os.path.join(OUT_DIR, "results.json")
    if not os.path.exists(path):
        raise HTTPException(503, "Расчёт ещё не выполнен: запустите `python -m konvert.pipeline`")
    return _load(os.path.getmtime(path))  # файл обновился — кеш сбросится сам


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> str:
    return render(data_url="/api/results")


@app.get("/api/health")
def health() -> dict:
    results, _ = state()
    return {"status": "ok", "version": __version__, "generated": results["meta"]["generated"],
            "records": results["meta"]["records"], "fraud_numbers": results["summary"]["fraud_numbers"]}


@app.get("/api/results")
def results() -> dict:
    return state()[0]


@app.get("/api/numbers")
def numbers(scheme: str | None = Query(None, description="S1…S7"), min_score: int = Query(60, ge=0, le=100)) -> list[dict]:
    cards = state()[0]["numbers"]
    return [
        {k: c[k] for k in ("number", "operator", "scheme", "role", "score", "decision", "group")}
        for c in cards if c["score"] >= min_score and (scheme is None or c["scheme"] == scheme.upper())
    ]


@app.get("/api/number/{msisdn}")
def number(msisdn: str) -> dict:
    num = normalize(msisdn)
    card = state()[1].get(num)
    if card:
        return card
    return {"number": num, "operator": operator(num), "scheme": None, "score": 0, "factors": [],
            "decision": {"action": "allow", "label": "Пропускать", "autoblock": False,
                         "reason": "Номер не входит в найденные схемы и не является массовым источником"}}


@app.post("/api/score-call")
def score(call: Call) -> dict:
    return score_call(call.model_dump(), state()[1])
