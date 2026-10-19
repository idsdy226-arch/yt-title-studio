"""채널의 최근 영상 50개(제목·썸네일·조회수)를 수집하고 썸네일 이미지를 저장한다.

사용법:
    python collect.py <채널링크>                 # 비의료 채널, 최근 12개월
    python collect.py <채널링크> --medical       # 의료 채널
    python collect.py <채널링크> --months 6      # 최근 6개월만
    python collect.py <채널링크> --months 0      # 기간 제한 없이 최근 영상 50개

기간 안의 영상이 50개보다 많으면 조회수 상위 50개만 남긴다.

결과:
    data/raw/<채널ID>/videos.json      채널 정보 + 영상 목록(조회수 순)
    data/raw/<채널ID>/texts.json       썸네일 문구 기록용(영상ID → 문구, 처음엔 빈 값)
    data/thumbnails/<채널ID>/NN_<영상ID>.jpg   조회수 순위가 파일명 앞에 붙은 썸네일
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

import requests

from config import BASE_DIR, DEFAULT_MONTHS, RAW_DIR, RECENT_VIDEO_COUNT, THUMB_DIR
from youtube import YouTubeError, fetch_channel_videos


def download_thumb(video: dict, path) -> bool:
    urls = [video["thumbnail"], f"https://i.ytimg.com/vi/{video['id']}/hqdefault.jpg"]
    for url in urls:
        if not url:
            continue
        try:
            r = requests.get(url, timeout=15)
        except requests.RequestException:
            continue
        if r.status_code == 200 and r.content:
            path.write_bytes(r.content)
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="유튜브 채널 최근 영상 50개 수집")
    ap.add_argument("url", help="채널 링크 (예: https://www.youtube.com/@핸들)")
    ap.add_argument("--medical", action="store_true", help="의료 채널로 기록 (의료광고법 56조 필터 대상)")
    ap.add_argument("--months", type=int, default=DEFAULT_MONTHS,
                    help=f"최근 몇 개월 영상만 볼지 (기본 {DEFAULT_MONTHS}, 0 = 제한 없이 최근 50개)")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=round(args.months * 30.44)) if args.months > 0 else None
    try:
        info, videos = fetch_channel_videos(args.url, since=since)
    except YouTubeError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    scanned = len(videos)
    videos.sort(key=lambda v: v["views"], reverse=True)
    videos = videos[:RECENT_VIDEO_COUNT]
    cid = info["id"]
    raw_dir = RAW_DIR / cid
    thumb_dir = THUMB_DIR / cid
    raw_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    for old in thumb_dir.glob("*.jpg"):
        old.unlink()

    failed = 0
    for rank, v in enumerate(videos, 1):
        v["rank"] = rank
        v["is_shorts"] = 0 < v["duration_sec"] <= 180
        path = thumb_dir / f"{rank:02d}_{v['id']}.jpg"
        if download_thumb(v, path):
            v["thumbnail_file"] = str(path.relative_to(BASE_DIR))
        else:
            v["thumbnail_file"] = ""
            failed += 1

    info["url"] = args.url
    info["is_medical"] = args.medical
    info["collected_at"] = now.isoformat(timespec="seconds")
    info["period_months"] = args.months
    info["period_since"] = since.date().isoformat() if since else ""
    info["videos_in_period"] = scanned
    (raw_dir / "videos.json").write_text(
        json.dumps({"channel": info, "videos": videos}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 재수집 시 이미 기록한 문구는 유지
    texts_path = raw_dir / "texts.json"
    old_texts = json.loads(texts_path.read_text(encoding="utf-8")) if texts_path.exists() else {}
    texts = {v["id"]: old_texts.get(v["id"], "") for v in videos}
    texts_path.write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"채널: {info['title']} ({info.get('handle', '')})  ID: {cid}")
    print(f"분야: {'의료' if args.medical else '비의료'}  구독자: {info['subscribers']:,}")
    if since:
        print(f"기간: {since.date()} 이후 (최근 {args.months}개월) · 기간 내 영상 {scanned}개"
              + (f" 중 조회수 상위 {len(videos)}개 사용" if scanned > len(videos) else ""))
    print(f"영상 {len(videos)}개 수집, 썸네일 {len(videos) - failed}개 저장 → {thumb_dir.relative_to(BASE_DIR)}/")
    print(f"데이터 → {(raw_dir / 'videos.json').relative_to(BASE_DIR)}\n")
    print("순위  조회수        형식  업로드      제목")
    for v in videos:
        kind = "쇼츠" if v["is_shorts"] else "롱폼"
        print(f"{v['rank']:>3}  {v['views']:>12,}  {kind}  {v['published_at'][:10]}  {v['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
