"""Claude API 호출 공통 래퍼: 구조화 출력(Pydantic) + 거절 시 서버측 폴백."""
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None


class ClaudeError(Exception):
    pass


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise ClaudeError(".env에 ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, max_retries=3, timeout=600)
    return _client


def ask(system: str, content: list | str, schema: type[T], effort: str = "high",
        max_tokens: int = 16000) -> T:
    try:
        resp = client().beta.messages.parse(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=schema,
            output_config={"effort": effort},
            # 안전 분류기가 거절하면 서버에서 권장 모델로 자동 재시도
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise ClaudeError("Anthropic API 키가 올바르지 않습니다.") from e
    except anthropic.RateLimitError as e:
        raise ClaudeError("Anthropic API 사용량 한도에 걸렸습니다. 잠시 후 다시 시도하세요.") from e
    except anthropic.APIStatusError as e:
        raise ClaudeError(f"Anthropic API 오류 ({e.status_code}): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ClaudeError("Anthropic API에 연결할 수 없습니다.") from e

    if resp.stop_reason == "refusal":
        raise ClaudeError("Claude가 이 요청을 거절했습니다. 입력 내용을 확인하세요.")
    if resp.stop_reason == "max_tokens":
        raise ClaudeError("응답이 너무 길어 잘렸습니다. 다시 시도하세요.")
    if resp.parsed_output is None:
        raise ClaudeError("Claude 응답을 해석하지 못했습니다. 다시 시도하세요.")
    return resp.parsed_output
