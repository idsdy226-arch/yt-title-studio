"""YouTube Data API v3로 채널의 최근 영상(제목·썸네일·조회수)을 수집한다."""
import re
from urllib.parse import unquote, urlparse

import requests

from config import RECENT_VIDEO_COUNT, YOUTUBE_API_KEY

API = "https://www.googleapis.com/youtube/v3"


class YouTubeError(Exception):
    pass


def _get(endpoint: str, **params) -> dict:
    if not YOUTUBE_API_KEY:
        raise YouTubeError(".env에 YOUTUBE_API_KEY가 설정되어 있지 않습니다.")
    params["key"] = YOUTUBE_API_KEY
    r = requests.get(f"{API}/{endpoint}", params=params, timeout=20)
    if r.status_code != 200:
        try:
            msg = r.json()["error"]["message"]
        except Exception:
            msg = r.text[:300]
        raise YouTubeError(f"YouTube API 오류 ({r.status_code}): {msg}")
    return r.json()


def _channel_by(**query) -> dict | None:
    data = _get("channels", part="snippet,contentDetails,statistics", **query)
    items = data.get("items") or []
    return items[0] if items else None


def resolve_channel(url: str) -> dict:
    """채널 링크(@핸들, /channel/UC..., /user/, /c/, 영상 링크)를 채널 리소스로 변환."""
    url = url.strip()
    if not url:
        raise YouTubeError("채널 링크를 입력하세요.")
    if url.startswith("@"):
        url = "https://www.youtube.com/" + url
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    path = unquote(parsed.path).rstrip("/")
    parts = [p for p in path.split("/") if p]

    channel = None
    if parts and parts[0].startswith("@"):
        channel = _channel_by(forHandle=parts[0])
    elif len(parts) >= 2 and parts[0] == "channel":
        channel = _channel_by(id=parts[1])
    elif len(parts) >= 2 and parts[0] == "user":
        channel = _channel_by(forUsername=parts[1])
    elif (len(parts) >= 1 and parts[0] in ("watch", "shorts")) or parsed.netloc.endswith("youtu.be"):
        # 영상 링크가 들어오면 그 영상의 채널로
        vid = None
        if parsed.netloc.endswith("youtu.be") and parts:
            vid = parts[0]
        elif parts[0] == "shorts" and len(parts) >= 2:
            vid = parts[1]
        else:
            m = re.search(r"[?&]v=([\w-]{11})", url)
            vid = m.group(1) if m else None
        if vid:
            v = _get("videos", part="snippet", id=vid).get("items") or []
            if v:
                channel = _channel_by(id=v[0]["snippet"]["channelId"])
    elif len(parts) >= 1:
        # /c/커스텀이름 또는 /커스텀이름 → 핸들로 먼저 시도, 실패 시 검색
        name = parts[1] if parts[0] == "c" and len(parts) >= 2 else parts[0]
        channel = _channel_by(forHandle="@" + name)
        if not channel:
            s = _get("search", part="snippet", q=name, type="channel", maxResults=1).get("items") or []
            if s:
                channel = _channel_by(id=s[0]["snippet"]["channelId"])

    if not channel:
        raise YouTubeError("채널을 찾을 수 없습니다. 링크를 확인하세요. (예: https://www.youtube.com/@채널핸들)")
    return channel


def _best_thumb(thumbs: dict) -> str:
    for key in ("maxres", "standard", "high", "medium", "default"):
        if key in thumbs:
            return thumbs[key]["url"]
    return ""


def _parse_duration(iso: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def fetch_channel_videos(url: str) -> tuple[dict, list[dict]]:
    channel = resolve_channel(url)
    uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids: list[str] = []
    page_token = None
    while len(video_ids) < RECENT_VIDEO_COUNT:
        params = dict(part="contentDetails", playlistId=uploads, maxResults=50)
        if page_token:
            params["pageToken"] = page_token
        data = _get("playlistItems", **params)
        video_ids += [it["contentDetails"]["videoId"] for it in data.get("items", [])]
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    video_ids = video_ids[:RECENT_VIDEO_COUNT]
    if not video_ids:
        raise YouTubeError("이 채널에 공개된 영상이 없습니다.")

    videos = []
    for i in range(0, len(video_ids), 50):
        data = _get("videos", part="snippet,statistics,contentDetails", id=",".join(video_ids[i:i + 50]))
        for it in data.get("items", []):
            sn, st = it["snippet"], it.get("statistics", {})
            videos.append({
                "id": it["id"],
                "title": sn["title"],
                "published_at": sn["publishedAt"],
                "thumbnail": _best_thumb(sn.get("thumbnails", {})),
                "views": int(st.get("viewCount", 0)),
                "duration_sec": _parse_duration(it.get("contentDetails", {}).get("duration", "")),
            })

    sn = channel["snippet"]
    info = {
        "id": channel["id"],
        "title": sn["title"],
        "handle": sn.get("customUrl", ""),
        "description": sn.get("description", "")[:500],
        "avatar": _best_thumb(sn.get("thumbnails", {})),
        "subscribers": int(channel.get("statistics", {}).get("subscriberCount", 0) or 0),
    }
    return info, videos
