"""채널의 최근 영상 50개(제목·썸네일·조회수)를 수집하고 썸네일 이미지를 저장한다.

사용법:
    python collect.py <채널링크>              # 비의료 채널
    python collect.py <채널링크> --medical    # 의료 채널

결과:
    data/raw/<채널ID>/videos.json      채널 정보 + 영상 목록(조회수 순)
    data/raw/<채널ID>/texts.json       썸네일 문구 기록용(영상ID → 문구, 처음엔 빈 값)
    data/thumbnails/<채널ID>/NN_<영상ID>.jpg   조회수 순위가 파일명 앞에 붙은 썸네일
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import requests

from config import BASE_DIR, RAW_DIR, THUMB_DIR
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
    args = ap.parse_args()

    try:
        info, videos = fetch_channel_videos(args.url)
    except YouTubeError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    videos.sort(key=lambda v: v["views"], reverse=True)
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
    info["collected_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (raw_dir / "videos.json").write_text(
        json.dumps({"channel": info, "videos": videos}, ensure_ascii=False, indent=2), encoding="utf-8")

    # 재수집 시 이미 기록한 문구는 유지
    texts_path = raw_dir / "texts.json"
    old_texts = json.loads(texts_path.read_text(encoding="utf-8")) if texts_path.exists() else {}
    texts = {v["id"]: old_texts.get(v["id"], "") for v in videos}
    texts_path.write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"채널: {info['title']} ({info.get('handle', '')})  ID: {cid}")
    print(f"분야: {'의료' if args.medical else '비의료'}  구독자: {info['subscribers']:,}")
    print(f"영상 {len(videos)}개 수집, 썸네일 {len(videos) - failed}개 저장 → {thumb_dir.relative_to(BASE_DIR)}/")
    print(f"데이터 → {(raw_dir / 'videos.json').relative_to(BASE_DIR)}\n")
    print("순위  조회수        형식  제목")
    for v in videos:
        kind = "쇼츠" if v["is_shorts"] else "롱폼"
        print(f"{v['rank']:>3}  {v['views']:>12,}  {kind}  {v['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
