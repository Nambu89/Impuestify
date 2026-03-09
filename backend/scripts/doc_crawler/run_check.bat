@echo off
REM TaxIA Document Crawler — Weekly scheduled check
REM This .bat is invoked by Windows Task Scheduler every Monday at 09:00

cd /d "%~dp0..\..\..\"
set PYTHONUTF8=1
"venv\Scripts\python.exe" -m backend.scripts.doc_crawler.scheduled_check
