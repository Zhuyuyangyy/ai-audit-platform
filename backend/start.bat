@echo off
title AI Audit Platform Backend
cd /d "%~dp0"
echo Starting AI Compliance Audit Platform...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8014 --reload
pause