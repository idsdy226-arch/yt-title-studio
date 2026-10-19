"""웹 서버: 채널 등록·목록·학습, 스크립트 기반 생성."""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

import storage
from analyzer import build_profile, extract_thumbnail_texts
from claude_client import ClaudeError
from config import ANTHROPIC_API_KEY, BASE_DIR, CLAUDE_MODEL, PORT, YOUTUBE_API_KEY
from generator import generate_for_channel
from youtube import YouTubeError, fetch_channel_videos

app = Flask(__name__, static_folder=str(BASE_DIR / "static"))

# 채널 학습은 1~3분 걸리므로 백그라운드 작업으로 돌리고 화면에서 진행 상황을 폴링한다.
jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _summary(c: dict) -> dict:
    return {
        "id": c["info"]["id"],
        "title": c["info"]["title"],
        "handle": c["info"].get("handle", ""),
        "avatar": c["info"].get("avatar", ""),
        "subscribers": c["info"].get("subscribers", 0),
        "url": c.get("url", ""),
        "is_medical": c.get("is_medical", False),
        "video_count": len(c.get("videos", [])),
        "registered_at": c.get("registered_at", ""),
        "learned_at": c.get("learned_at", ""),
        "channel_summary": c.get("profile", {}).get("channel_summary", ""),
    }


def _set_job(job_id: str, **kw) -> None:
    with jobs_lock:
        jobs[job_id].update(kw)


def _learn(job_id: str, url: str, is_medical: bool, existing: dict | None) -> None:
    try:
        _set_job(job_id, step="YouTube에서 최근 영상 50개 수집 중…")
        info, videos = fetch_channel_videos(url)
        _set_job(job_id, step=f"썸네일 {len(videos)}장에서 문구 추출 중… (Claude 비전)")
        extract_thumbnail_texts(videos)
        _set_job(job_id, step="조회수 상위 영상 기준으로 스타일 프로필 분석 중…")
        info["is_medical"] = is_medical
        profile = build_profile(info, videos)
        info.pop("is_medical")
        channel = {
            "info": info,
            "url": url,
            "is_medical": is_medical,
            "registered_at": (existing or {}).get("registered_at") or _now(),
            "learned_at": _now(),
            "videos": videos,
            "profile": profile,
        }
        storage.save(channel)
        _set_job(job_id, status="done", step="완료", channel_id=info["id"])
    except (YouTubeError, ClaudeError) as e:
        _set_job(job_id, status="error", error=str(e))
    except Exception as e:  # 예상 못 한 오류도 화면에 보여준다
        app.logger.exception("learn failed")
        _set_job(job_id, status="error", error=f"알 수 없는 오류: {e}")


def _start_job(url: str, is_medical: bool, existing: dict | None = None) -> str:
    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = {"status": "running", "step": "시작", "error": None, "channel_id": None}
    threading.Thread(target=_learn, args=(job_id, url, is_medical, existing), daemon=True).start()
    return job_id


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/status")
def status():
    return jsonify({
        "youtube_key": bool(YOUTUBE_API_KEY),
        "anthropic_key": bool(ANTHROPIC_API_KEY),
        "model": CLAUDE_MODEL,
    })


@app.get("/api/channels")
def list_channels():
    return jsonify([_summary(c) for c in storage.list_all()])


@app.get("/api/channels/<cid>")
def get_channel(cid):
    c = storage.get(cid)
    if not c:
        return jsonify(error="채널이 없습니다."), 404
    return jsonify(c)


@app.post("/api/channels")
def add_channel():
    body = request.get_json(force=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify(error="채널 링크를 입력하세요."), 400
    return jsonify(job_id=_start_job(url, bool(body.get("is_medical"))))


@app.post("/api/channels/<cid>/relearn")
def relearn_channel(cid):
    c = storage.get(cid)
    if not c:
        return jsonify(error="채널이 없습니다."), 404
    url = c.get("url") or f"https://www.youtube.com/channel/{cid}"
    return jsonify(job_id=_start_job(url, c.get("is_medical", False), c))


@app.patch("/api/channels/<cid>")
def update_channel(cid):
    c = storage.get(cid)
    if not c:
        return jsonify(error="채널이 없습니다."), 404
    body = request.get_json(force=True) or {}
    if "is_medical" in body:
        c["is_medical"] = bool(body["is_medical"])
    storage.save(c)
    return jsonify(_summary(c))


@app.delete("/api/channels/<cid>")
def delete_channel(cid):
    storage.delete(cid)
    return jsonify(ok=True)


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        return (jsonify(job), 200) if job else (jsonify(error="작업이 없습니다."), 404)


@app.post("/api/generate")
def generate():
    body = request.get_json(force=True) or {}
    script = (body.get("script") or "").strip()
    ids = body.get("channel_ids") or [c["info"]["id"] for c in storage.list_all()]
    if not script:
        return jsonify(error="스크립트를 붙여넣으세요."), 400
    channels = [c for c in (storage.get(i) for i in ids) if c]
    if not channels:
        return jsonify(error="등록된 채널이 없습니다. 먼저 채널을 등록하세요."), 400

    def run(c):
        try:
            return {"ok": True, **generate_for_channel(c, script)}
        except ClaudeError as e:
            return {"ok": False, "error": str(e)}
        except Exception as e:
            app.logger.exception("generate failed")
            return {"ok": False, "error": f"알 수 없는 오류: {e}"}

    with ThreadPoolExecutor(max_workers=4) as ex:
        outs = list(ex.map(run, channels))
    return jsonify(results=[
        {"channel": _summary(c), **out} for c, out in zip(channels, outs)
    ])


if __name__ == "__main__":
    print(f"\n  ▶ http://localhost:{PORT} 에서 열립니다\n")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
