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

# 분석에 쓰는 영상 수(기간 안에서 조회수 상위), 스타일 분석의 중심이 되는 상위 영상 수
RECENT_VIDEO_COUNT = 50
# 기본 수집 기간(개월). 0이면 기간 제한 없이 최근 영상 50개
DEFAULT_MONTHS = 12
# 기간 안의 영상을 훑을 최대 개수 (업로드가 많은 채널 대비)
MAX_SCAN_VIDEOS = 500
TOP_VIDEO_COUNT = 20
