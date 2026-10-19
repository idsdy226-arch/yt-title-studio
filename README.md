# 썸네일·제목 스튜디오 (Claude Code 버전)

레퍼런스 유튜브 채널의 스타일을 학습해서, 영상 스크립트로 **채널별 썸네일 문구 10개 + 제목 10개**를 만듭니다.

Anthropic API 키는 필요 없습니다. 이 폴더에서 **Claude Code**를 열고 말로 요청하면, Claude Code가 `CLAUDE.md`의 작업 방법대로 처리합니다.

| 누가 | 무엇을 |
|---|---|
| `collect.py` (YouTube Data API) | 채널의 **최근 12개월** 영상(많으면 조회수 상위 50개) 제목·조회수 수집, 썸네일 이미지를 `data/thumbnails/<채널ID>/`에 저장 |
| Claude Code | 썸네일 이미지를 직접 보고 문구 추출 → 스타일 프로필 분석·저장 → 스크립트로 카피 생성 → 의료 채널은 56조 필터 |

---

## 1단계. YouTube Data API 키 발급

1. https://console.cloud.google.com 에 구글 계정으로 로그인합니다.
2. 위쪽 프로젝트 선택 메뉴 → **새 프로젝트** → 이름(예: `yt-title-studio`) 입력 → **만들기**.
3. 왼쪽 메뉴 **API 및 서비스 → 라이브러리**에서 `YouTube Data API v3`를 검색 → **사용**.
4. **API 및 서비스 → 사용자 인증 정보** → **+ 사용자 인증 정보 만들기 → API 키**.
5. 키를 복사합니다. (권장) **키 수정 → API 제한사항 → 키 제한 → YouTube Data API v3**만 선택 후 저장.

> 무료 할당량은 하루 10,000 유닛이고, 채널 1개 수집에 약 3~5 유닛을 씁니다.

## 2단계. 설치

필요한 것: **Python 3.10 이상**, **Claude Code** (https://claude.com/claude-code)

```bash
git clone https://github.com/idsdy226-arch/yt-title-studio.git
cd yt-title-studio
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```

`.env`를 열어 키를 넣습니다.

```
YOUTUBE_API_KEY=AIza...
```

## 3단계. 사용법

이 폴더에서 Claude Code를 실행하고(`claude`) 아래처럼 말하면 됩니다.

### 채널 학습

> 이 채널 학습해줘 https://www.youtube.com/@채널핸들
>
> 이 채널 학습해줘 https://www.youtube.com/@병원채널 (의료 채널)

Claude Code가 `collect.py`로 수집하고, 썸네일을 한 장씩 열어 문구를 읽고, 조회수 상위 영상 중심으로 스타일 프로필을 만들어 `data/channels/<채널이름>.md`에 저장합니다. 의료/비의료 여부도 프로필에 기록됩니다(말하지 않으면 물어봅니다).

기간을 바꾸고 싶으면 "최근 6개월만 보고 학습해줘"처럼 말하면 됩니다.

### 생성

> A·B·C 스타일로 뽑아줘
> (스크립트 붙여넣기)

지정한 채널마다 썸네일 문구 10개 + 제목 10개가 나오고, 각 항목 아래에 어떤 레퍼런스 패턴을 따랐는지 한 줄로 표시됩니다. 같은 내용이 `output/<날짜>_<영상주제>.md`에도 저장됩니다.

- 레퍼런스 채널의 훅·어그로·감정 자극 방식을 그대로 따릅니다.
- **의료 채널**만 의료법 제56조 위반 표현(치료 효과 보장·확정, 타 병원 비교, 할인·무료 등 환자 유인)을 걸러, 같은 스타일의 허용 표현으로 바꾸고 원문·사유를 함께 표시합니다.

### 채널 관리

> 등록된 채널 보여줘
>
> ○○ 채널 재학습해줘
>
> ○○ 채널 의료로 바꿔줘
>
> ○○ 채널 삭제해줘

### 수집만 직접 할 때

```bash
python collect.py https://www.youtube.com/@채널핸들             # 비의료
python collect.py https://www.youtube.com/@병원채널 --medical   # 의료
python collect.py <링크> --months 6                              # 최근 6개월만 (기본 12개월)
python collect.py <링크> --months 0                              # 기간 제한 없이 최근 50개
python stats.py <채널ID>                                       # 썸네일 문구 기록 후 글자 수 통계
```

지원 링크: `youtube.com/@핸들`, `youtube.com/channel/UC...`, `youtube.com/user/이름`, `youtube.com/c/이름`, 해당 채널의 영상 링크

---

## 파일 구성

```
CLAUDE.md          Claude Code 작업 지침 (학습·생성·56조 필터·채널 관리)
collect.py         채널 수집 + 썸네일 저장
stats.py           썸네일 문구·제목 글자 수 통계
youtube.py         YouTube Data API 호출
config.py          경로·설정
data/channels/     스타일 프로필 (.md, git에 포함)
data/raw/          수집 원본 JSON (git 제외)
data/thumbnails/   썸네일 이미지 (git 제외)
output/            생성 결과 (.md, git에 포함)
```

## 참고

- 56조 필터는 AI 검수이므로 법률 자문을 대신하지 않습니다. 게시 전 최종 확인은 직접 해주세요.
- 썸네일 문구 추출과 분석은 Claude Code 사용량으로 처리됩니다(채널 1개 학습에 이미지 약 50장을 봅니다).
