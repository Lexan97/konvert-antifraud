@echo off
rem Запуск интерфейса и API на http://127.0.0.1:8000
rem Если результата нет — сначала считает по выгрузке CDR.
setlocal
set PY=.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

if exist outputs\results.json goto serve

set CDR=
for %%D in ("data\cdr_out" "..\cdr_out\cdr_out" "cdr_out") do if exist %%D set CDR=%%~D
if not defined CDR goto nocdr

echo Результата нет — считаю по выгрузке из %CDR% (1–3 минуты)...
"%PY%" -m konvert.pipeline --cdr "%CDR%" --out outputs
if errorlevel 1 goto pipelinefail

:serve
start "" http://127.0.0.1:8000
"%PY%" -m uvicorn konvert.api:app --port 8000
goto end

:nocdr
echo Не найден каталог с выгрузкой. Положите файлы CDR_*.cdr в data\cdr_out\
echo (или рядом с репозиторием: ..\cdr_out\cdr_out) и запустите снова.
echo Либо скопируйте готовый outputs\results.json из репозитория.
exit /b 1

:pipelinefail
echo Расчёт не завершился. См. вывод выше.
exit /b 1

:end
