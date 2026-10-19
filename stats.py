"""data/raw/<채널ID>/texts.json 에 썸네일 문구를 채운 뒤, 글자 수·줄 수 통계를 계산한다.

사용법:
    python stats.py <채널ID>

글자 수는 공백 포함·줄바꿈 제외 기준. 썸네일 문구의 줄바꿈은 texts.json 에 \\n 으로 기록한다.
"""
import json
import statistics
import sys

from config import RAW_DIR, TOP_VIDEO_COUNT


def describe(label: str, texts: list[str]) -> str:
    texts = [t for t in texts if t]
    if not texts:
        return f"{label}: 데이터 없음"
    lens = [len(t.replace("\n", "")) for t in texts]
    lines = [t.count("\n") + 1 for t in texts]
    return (f"{label}: {len(texts)}개 · 글자 수 평균 {statistics.mean(lens):.1f} / 중앙값 {statistics.median(lens):.0f}"
            f" / 최소 {min(lens)} / 최대 {max(lens)} · 줄 수 평균 {statistics.mean(lines):.1f} / 최대 {max(lines)}")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    raw = RAW_DIR / sys.argv[1]
    if not (raw / "videos.json").exists():
        print(f"오류: {raw}/videos.json 이 없습니다. 먼저 collect.py 를 실행하세요.", file=sys.stderr)
        return 1
    videos = json.loads((raw / "videos.json").read_text(encoding="utf-8"))["videos"]
    texts = json.loads((raw / "texts.json").read_text(encoding="utf-8"))
    top = videos[:TOP_VIDEO_COUNT]

    filled = sum(1 for v in videos if texts.get(v["id"]))
    print(f"썸네일 문구 기록: {filled}/{len(videos)}개 영상")
    print(describe(f"썸네일 문구(상위 {len(top)})", [texts.get(v["id"], "") for v in top]))
    print(describe("썸네일 문구(전체)", [texts.get(v["id"], "") for v in videos]))
    print(describe(f"제목(상위 {len(top)})", [v["title"] for v in top]))
    print(describe("제목(전체)", [v["title"] for v in videos]))
    for kind, flag in (("롱폼", False), ("쇼츠", True)):
        group = [v for v in top if v.get("is_shorts") == flag]
        if group:
            print(describe(f"  └ {kind} 썸네일(상위 중 {len(group)})", [texts.get(v["id"], "") for v in group]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
