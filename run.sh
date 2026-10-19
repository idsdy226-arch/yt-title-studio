#!/usr/bin/env bash
# macOS / Linux 실행 스크립트
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install -q -r requirements.txt
if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env 파일을 만들었습니다. API 키를 입력한 뒤 다시 실행하세요."
  exit 1
fi
./.venv/bin/python app.py
