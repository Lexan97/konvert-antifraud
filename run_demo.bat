@echo off
rem Запуск интерфейса и API на http://127.0.0.1:8000
if not exist outputs\results.json .venv\Scripts\python.exe -m konvert.pipeline --cdr data\cdr_out --out outputs
start "" http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn konvert.api:app --port 8000
