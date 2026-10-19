"""스크립트 → 채널 스타일별 썸네일 문구 10개 + 제목 10개 생성 (의료 채널은 56조 필터 추가)."""
import json
from typing import Literal

from pydantic import BaseModel

from analyzer import reference_block
from claude_client import ask
from config import TOP_VIDEO_COUNT


# ---------- 1) 스타일 기반 생성 ----------

class CopyItem(BaseModel):
    text: str          # 썸네일 문구는 줄바꿈을 \n으로
    pattern_id: str    # 프로필의 패턴 ID (T1, N2 …)
    pattern_note: str  # 어떤 레퍼런스 패턴을 따랐는지 한 줄 설명


class GeneratedSet(BaseModel):
    thumbnails: list[CopyItem]
    titles: list[CopyItem]


GEN_SYSTEM = """당신은 특정 유튜브 채널의 전담 카피라이터입니다. 영상 스크립트를 받아 그 채널의 썸네일 문구와 제목을 씁니다.

최우선 원칙: 레퍼런스 채널의 스타일을 그대로 재현합니다.
- 이 채널이 훅·어그로·호기심 공백·공포·감정 자극·과장·반전을 쓴다면 같은 강도로 그대로 씁니다. 순화하거나 점잖게 바꾸지 마세요.
- 글자 수, 줄 수, 말투(어미·존댓말/반말), 문장 구조, 기호·숫자 표기, 자주 쓰는 단어는 스타일 프로필과 레퍼런스 원문 기준에 맞춥니다.
- 내용은 스크립트에 근거해야 합니다. 스크립트에 없는 사실을 지어내지 마세요. (스크립트의 어떤 포인트를 훅으로 뽑을지는 자유)
- 썸네일 문구와 제목은 이 채널이 두 요소의 역할을 나누는 방식(thumbnail_title_relation)을 따릅니다.

출력:
- 썸네일 문구 정확히 10개, 제목 정확히 10개.
- 여러 패턴을 고루 쓰되, 조회수 상위 영상에서 많이 쓰인 패턴에 더 많이 배분합니다.
- 썸네일 문구의 줄바꿈은 \\n으로 표기합니다(이 채널이 줄을 나눠 쓴다면).
- pattern_id에는 프로필의 패턴 ID(T*, N*)를 적습니다.
- pattern_note는 한 줄로: 따른 패턴 이름 + 닮은 레퍼런스 원문을 짧게 인용. 예) "T2 숫자+반전형 · 참고: '3일 만에 ⏎ 이렇게 됐다'"."""


def generate_for_channel(channel: dict, script: str) -> dict:
    profile = channel["profile"]
    profile_json = json.dumps(profile, ensure_ascii=False, indent=1)
    prompt = f"""[채널] {channel['info']['title']}

[스타일 프로필]
{profile_json}

[레퍼런스 원문 — 조회수 상위 {TOP_VIDEO_COUNT}개 (⏎ = 썸네일 줄바꿈)]
{reference_block(channel['videos'], TOP_VIDEO_COUNT)}

[영상 스크립트]
<script>
{script}
</script>

이 채널의 스타일로 썸네일 문구 10개와 제목 10개를 작성하세요."""
    out = ask(GEN_SYSTEM, prompt, GeneratedSet, effort="high")
    result = {
        "thumbnails": [i.model_dump() for i in out.thumbnails[:10]],
        "titles": [i.model_dump() for i in out.titles[:10]],
    }
    if channel.get("is_medical"):
        apply_medical_filter(result, profile)
    return result


# ---------- 2) 의료광고법 제56조 필터 (의료 채널 전용) ----------

ViolationType = Literal["치료효과 보장·확정", "타 병원 비교", "할인·무료 등 환자 유인"]


class ReviewItem(BaseModel):
    kind: Literal["thumbnail", "title"]
    index: int                         # 0부터 시작하는 번호
    violation_types: list[ViolationType]
    reason: str                        # 어느 표현이 왜 문제인지 한 줄
    revised_text: str                  # 같은 스타일을 유지한 허용 표현
    revised_note: str                  # 무엇을 어떻게 바꿨는지 한 줄


class MedicalReview(BaseModel):
    violations: list[ReviewItem]       # 위반 항목만 담는다. 없으면 빈 목록


MED_SYSTEM = """당신은 의료법 제56조(의료광고의 금지 등) 검수 담당자입니다. 의료 유튜브 채널의 썸네일 문구와 제목을 검수합니다.

아래 세 가지 유형'만' 위반으로 판정합니다. 그 외의 어그로·호기심 유발·감정 자극·공포 소구·과장된 말투는 이 검수의 대상이 아니므로 절대 건드리지 마세요.

1) 치료효과 보장·확정: 치료 결과를 보장하거나 단정하는 표현.
   예) "100% 완치", "무조건 낫는다", "확실하게 없애드립니다", "재발 없음", "부작용 0", "한 번에 끝", "평생 안 아프다"
2) 타 병원 비교: 다른 의료기관·의료인과 비교하거나 우월함을 주장하는 표현(암시 포함).
   예) "OO병원보다 낫다", "다른 병원에서 못 고친 것", "대학병원도 못하는", "국내 유일/최초/최고", "타 병원과 차원이 다른"
3) 할인·무료 등 환자 유인: 비용 할인·면제, 무료 시술·상담, 금품·이벤트로 내원을 유도하는 표현.
   예) "무료 상담", "반값", "50% 할인", "0원", "선착순 이벤트", "본인부담금 면제", "사은품 증정"

판정 기준:
- 정보 전달·경험 공유·가능성 표현("~할 수 있다", "~에 도움이 될 수 있다", "개인차가 있다")은 허용입니다.
- 질환·증상에 대한 공포나 호기심 자극("이 증상 무시하면 큰일", "의사들이 절대 안 하는 것")은 위 세 유형이 아니면 허용입니다.

수정 규칙(위반 항목만):
- 원래 문구의 패턴·훅 구조·말투·글자 수(±3자)·줄바꿈을 최대한 유지하고, 문제 되는 표현만 허용 표현으로 바꿉니다.
- 효과 확정 → 가능성·경험·변화 서술로(예: "100% 완치" → "이렇게 좋아졌습니다"), 비교 → 자기 기준 서술로, 유인 → 정보·궁금증 중심으로.
- 수정 문구도 다시 세 유형에 걸리지 않아야 합니다.
- 위반이 없는 항목은 출력하지 않습니다."""


def apply_medical_filter(result: dict, profile: dict) -> None:
    lines = []
    for kind, key in (("thumbnail", "thumbnails"), ("title", "titles")):
        for i, item in enumerate(result[key]):
            lines.append(f"{kind} #{i}: {item['text'].replace(chr(10), ' ⏎ ')}")
    prompt = f"""[채널 말투 참고] 썸네일: {profile['thumbnail']['tone']} / 제목: {profile['title']['tone']}
[썸네일 길이 기준] {profile['thumbnail']['length_guide']}
[제목 길이 기준] {profile['title']['length_guide']}

[검수 대상] (⏎ = 줄바꿈, 수정 문구에서는 \\n으로 표기)
{chr(10).join(lines)}"""
    review = ask(MED_SYSTEM, prompt, MedicalReview, effort="high")
    for v in review.violations:
        key = "thumbnails" if v.kind == "thumbnail" else "titles"
        if not 0 <= v.index < len(result[key]):
            continue
        item = result[key][v.index]
        item["filtered"] = {
            "original": item["text"],
            "violation_types": list(v.violation_types),
            "reason": v.reason,
            "revised_note": v.revised_note,
        }
        item["text"] = v.revised_text.replace(" ⏎ ", "\n")
