@echo off
chcp 65001 >nul
REM Windows 실행 스크립트
cd /d "%~dp0"
if not exist .venv python -m venv .venv
.venv\Scripts\pip install -q -r requirements.txt
if not exist .env (
  copy .env.example .env
  echo .env 파일을 만들었습니다. API 키를 입력한 뒤 다시 실행하세요.
  pause
  exit /b 1
)
.venv\Scripts\python app.py
pause
