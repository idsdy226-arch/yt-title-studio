"""채널 학습: 썸네일 문구 추출(비전) → 조회수 상위 영상 기반 스타일 프로필 분석."""
import base64
import statistics
from concurrent.futures import ThreadPoolExecutor

import requests
from pydantic import BaseModel

from claude_client import ask
from config import OCR_BATCH_SIZE, TOP_VIDEO_COUNT


# ---------- 1) 썸네일 문구 추출 ----------

class ThumbText(BaseModel):
    image_number: int
    text: str            # 이미지에 적힌 문구 그대로. 줄바꿈은 \n. 문구가 없으면 빈 문자열
    emphasis: str        # 강조 방식(색·크기·박스 등)과 강조된 단어. 없으면 빈 문자열


class ThumbTextBatch(BaseModel):
    results: list[ThumbText]


OCR_SYSTEM = """당신은 유튜브 썸네일 이미지에서 '디자인으로 얹은 문구'만 정확히 옮겨 적는 전사 담당자입니다.
- 썸네일에 편집으로 넣은 텍스트(자막·타이틀 문구)만 적습니다. 채널 로고, 워터마크, 배경 속 간판·화면 글자, 영상 재생시간 표시는 제외합니다.
- 맞춤법을 고치거나 요약하지 말고 보이는 그대로 적습니다. 줄이 나뉘어 있으면 \\n으로 줄을 나눕니다.
- 읽는 순서는 디자인상 시선이 가는 순서(보통 위→아래, 큰 글자→작은 글자)를 따릅니다.
- 문구가 전혀 없으면 text는 빈 문자열입니다.
- emphasis에는 특정 단어를 색·크기·박스·외곽선 등으로 강조했다면 '빨간색 큰 글씨: 단어'처럼 짧게 적습니다."""


def _download_thumb(video: dict) -> tuple[str, str] | None:
    urls = [video["thumbnail"], f"https://i.ytimg.com/vi/{video['id']}/hqdefault.jpg"]
    for url in urls:
        if not url:
            continue
        try:
            r = requests.get(url, timeout=15)
        except requests.RequestException:
            continue
        if r.status_code == 200 and r.content:
            media = r.headers.get("content-type", "image/jpeg").split(";")[0]
            if media not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
                media = "image/jpeg"
            return media, base64.standard_b64encode(r.content).decode()
    return None


def _ocr_batch(videos: list[dict]) -> dict[str, dict]:
    content: list = []
    numbered: dict[int, dict] = {}
    for v in videos:
        img = _download_thumb(v)
        if not img:
            continue
        n = len(numbered) + 1
        numbered[n] = v
        content.append({"type": "text", "text": f"[이미지 {n}]"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": img[0], "data": img[1]}})
    if not numbered:
        return {}
    content.append({"type": "text", "text": f"위 {len(numbered)}개 썸네일 각각의 문구를 image_number와 함께 추출하세요."})
    out = ask(OCR_SYSTEM, content, ThumbTextBatch, effort="low")
    result = {}
    for r in out.results:
        if r.image_number in numbered:
            result[numbered[r.image_number]["id"]] = {"text": r.text.strip(), "emphasis": r.emphasis.strip()}
    return result


def extract_thumbnail_texts(videos: list[dict]) -> None:
    """videos 각 항목에 thumb_text, thumb_emphasis를 채운다(제자리 수정)."""
    batches = [videos[i:i + OCR_BATCH_SIZE] for i in range(0, len(videos), OCR_BATCH_SIZE)]
    with ThreadPoolExecutor(max_workers=5) as ex:
        merged: dict[str, dict] = {}
        for part in ex.map(_ocr_batch, batches):
            merged.update(part)
    for v in videos:
        found = merged.get(v["id"], {})
        v["thumb_text"] = found.get("text", "")
        v["thumb_emphasis"] = found.get("emphasis", "")


# ---------- 2) 스타일 프로필 분석 ----------

class Pattern(BaseModel):
    id: str              # 썸네일 패턴은 T1, T2… / 제목 패턴은 N1, N2…
    name: str            # 패턴 이름 (예: "숫자+충격 결과형")
    template: str        # 빈칸 템플릿 (예: "[기간] 만에 [결과]…[반전]")
    description: str     # 언제·왜 쓰는지, 어떤 심리를 건드리는지
    examples: list[str]  # 실제 레퍼런스 원문 2~3개


class StyleSection(BaseModel):
    length_guide: str              # 글자 수·줄 수 기준 (실측 통계 반영)
    tone: str                      # 말투 (반말/존댓말, 구어체, 감탄, 단정 등)
    sentence_structures: list[str] # 자주 쓰는 문장 구조
    hook_methods: list[str]        # 훅 방식 (호기심 공백, 어그로, 공포, 숫자, 반전 등)
    signature_words: list[str]     # 자주 쓰는 단어·표현·기호
    patterns: list[Pattern]
    rules: list[str]               # 생성 시 반드시 지킬 규칙


class StyleProfile(BaseModel):
    channel_summary: str
    target_audience: str
    thumbnail: StyleSection
    title: StyleSection
    thumbnail_title_relation: str  # 썸네일 문구와 제목이 역할을 어떻게 나누는지


PROFILE_SYSTEM = """당신은 유튜브 클릭률(CTR) 카피 분석 전문가입니다.
한 채널의 영상 데이터(조회수, 제목, 썸네일 문구)를 보고, 이 채널이 '실제로 쓰는' 썸네일 문구와 제목 스타일을
다른 작가가 그대로 재현할 수 있을 만큼 구체적인 스타일 프로필로 정리합니다.

원칙:
- 조회수 상위 영상에 가중치를 크게 두세요. 상위 영상에서 반복되는 방식이 이 채널의 '이기는 공식'입니다.
- 일반론("호기심을 자극한다") 대신 이 채널 고유의 장치를 적으세요: 어떤 단어·어미·기호·숫자 표기·줄바꿈·강조색을 쓰는지.
- 어그로·공포·과장·반전 등 자극적인 방식도 이 채널이 쓴다면 그대로 기록합니다. 도덕적 평가는 하지 마세요.
- 글자 수는 제공된 실측 통계를 근거로 적으세요.
- patterns는 썸네일·제목 각각 4~7개. 각 패턴의 examples는 반드시 제공된 데이터의 원문을 그대로 인용하세요.
- 썸네일 문구가 없는 영상이 많다면 그것도 스타일로 기록하세요."""


def _length_stats(texts: list[str]) -> str:
    texts = [t for t in texts if t]
    if not texts:
        return "데이터 없음"
    lens = [len(t.replace("\n", "")) for t in texts]
    lines = [t.count("\n") + 1 for t in texts]
    return (f"글자 수(공백 포함, 줄바꿈 제외) 평균 {statistics.mean(lens):.1f}, 중앙값 {statistics.median(lens):.0f}, "
            f"최소 {min(lens)}, 최대 {max(lens)} / 줄 수 평균 {statistics.mean(lines):.1f}, 최대 {max(lines)}")


def _video_line(rank: int, v: dict) -> str:
    kind = "쇼츠" if 0 < v.get("duration_sec", 0) <= 180 else "롱폼"
    thumb = v.get("thumb_text") or "(문구 없음)"
    emph = f" / 강조: {v['thumb_emphasis']}" if v.get("thumb_emphasis") else ""
    return (f"{rank}. 조회수 {v['views']:,} | {kind}\n"
            f"   제목: {v['title']}\n"
            f"   썸네일: {thumb.replace(chr(10), ' ⏎ ')}{emph}")


def reference_block(videos: list[dict], limit: int) -> str:
    ranked = sorted(videos, key=lambda v: v["views"], reverse=True)[:limit]
    return "\n".join(_video_line(i + 1, v) for i, v in enumerate(ranked))


def build_profile(channel: dict, videos: list[dict]) -> dict:
    ranked = sorted(videos, key=lambda v: v["views"], reverse=True)
    top = ranked[:TOP_VIDEO_COUNT]
    rest = ranked[TOP_VIDEO_COUNT:]
    stats = {
        "thumbnail_length": _length_stats([v.get("thumb_text", "") for v in top]),
        "title_length": _length_stats([v["title"] for v in top]),
        "thumbnail_text_ratio": f"{sum(1 for v in videos if v.get('thumb_text'))}/{len(videos)}개 영상에 썸네일 문구 있음",
    }
    prompt = f"""채널: {channel['title']} ({channel.get('handle', '')})
채널 소개: {channel.get('description', '') or '(없음)'}
분야: {'의료' if channel.get('is_medical') else '비의료'}

[실측 통계 - 조회수 상위 {len(top)}개 기준]
- 썸네일 문구: {stats['thumbnail_length']}
- 제목: {stats['title_length']}
- {stats['thumbnail_text_ratio']}

[조회수 상위 {len(top)}개 영상 — 분석의 중심]
{reference_block(top, len(top))}

[나머지 영상 — 비교용(상위 영상과 무엇이 다른지 참고)]
{reference_block(rest, len(rest)) if rest else '(없음)'}

위 데이터로 이 채널의 스타일 프로필을 작성하세요."""
    profile = ask(PROFILE_SYSTEM, prompt, StyleProfile, effort="high")
    data = profile.model_dump()
    data["measured_stats"] = stats
    return data
