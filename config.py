import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"                # 수집 원본: raw/<채널ID>/videos.json, texts.json
THUMB_DIR = DATA_DIR / "thumbnails"       # 썸네일 이미지: thumbnails/<채널ID>/
CHANNELS_DIR = DATA_DIR / "channels"      # 스타일 프로필: channels/<채널이름>.md
OUTPUT_DIR = BASE_DIR / "output"          # 생성 결과: output/<날짜>_<영상주제>.md

# 수집할 최근 영상 수, 스타일 분석에 쓰는 조회수 상위 영상 수
RECENT_VIDEO_COUNT = 50
TOP_VIDEO_COUNT = 20
