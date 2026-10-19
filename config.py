import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5").strip()
PORT = int(os.getenv("PORT", "5000"))

DATA_DIR = BASE_DIR / "data" / "channels"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 수집할 최근 영상 수, 스타일 분석에 쓰는 조회수 상위 영상 수
RECENT_VIDEO_COUNT = 50
TOP_VIDEO_COUNT = 20
# 썸네일 문구 추출 시 한 번의 API 호출에 넣는 이미지 수
OCR_BATCH_SIZE = 10
