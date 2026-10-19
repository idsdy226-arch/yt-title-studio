"""채널 프로필을 data/channels/<채널ID>.json 으로 저장·재사용한다."""
import json
import re

from config import DATA_DIR


def _path(channel_id: str):
    if not re.fullmatch(r"[\w-]+", channel_id):
        raise ValueError("잘못된 채널 ID")
    return DATA_DIR / f"{channel_id}.json"


def save(channel: dict) -> None:
    p = _path(channel["info"]["id"])
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(channel, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def get(channel_id: str) -> dict | None:
    p = _path(channel_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def delete(channel_id: str) -> bool:
    p = _path(channel_id)
    if p.exists():
        p.unlink()
        return True
    return False


def list_all() -> list[dict]:
    out = []
    for p in sorted(DATA_DIR.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(out, key=lambda c: c.get("registered_at", ""))
