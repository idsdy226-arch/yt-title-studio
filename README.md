# 썸네일·제목 스튜디오

레퍼런스 유튜브 채널의 스타일을 학습해서, 영상 스크립트로 **채널별 썸네일 문구 10개 + 제목 10개**를 만드는 로컬 웹 프로그램입니다.

## 동작 방식

| 단계 | 하는 일 |
|---|---|
| 1. 채널 학습 | 채널 링크 → YouTube Data API로 최근 영상 50개의 제목·썸네일·조회수 수집 → Claude 비전으로 썸네일에 적힌 문구 추출 → 조회수 상위 20개 위주로 스타일 프로필(문구 패턴, 글자 수, 말투, 문장 구조, 훅 방식, 제목 구조) 분석 → `data/channels/<채널ID>.json` 저장 |
| 2. 생성 | 스크립트 + 각 채널 프로필 + 상위 영상 원문 → 채널별 썸네일 문구 10개 + 제목 10개. 항목마다 따른 패턴을 한 줄로 표시 |
| 3. 의료 필터 | **의료 채널만** 생성 결과를 한 번 더 검수해서 의료법 제56조 위반 표현 3가지(치료 효과 보장·확정, 타 병원 비교, 할인·무료 등 환자 유인)만 골라 같은 스타일의 허용 표현으로 바꿉니다. 바꾼 항목은 원문·사유와 함께 표시됩니다. 비의료 채널은 이 단계를 건너뜁니다. |

등록한 채널은 파일로 남아서 다음 실행 때도 그대로 쓰입니다. 채널 목록에서 의료/비의료 변경, 재학습, 삭제를 할 수 있습니다.

---

## 1단계. API 키 발급

### YouTube Data API 키

1. https://console.cloud.google.com 에 구글 계정으로 로그인합니다.
2. 위쪽 프로젝트 선택 메뉴 → **새 프로젝트** → 이름(예: `yt-title-studio`) 입력 → **만들기**.
3. 왼쪽 메뉴 **API 및 서비스 → 라이브러리**에서 `YouTube Data API v3`를 검색 → **사용**을 누릅니다.
4. **API 및 서비스 → 사용자 인증 정보** → **+ 사용자 인증 정보 만들기 → API 키**.
5. 생성된 키를 복사합니다. (권장) **키 수정 → API 제한사항 → 키 제한 → YouTube Data API v3**만 선택 후 저장.

> 무료 할당량은 하루 10,000 유닛입니다. 채널 1개 학습에 약 3~5 유닛을 쓰므로 충분합니다. (`/c/이름` 형태 링크가 핸들로 안 찾아지면 검색 API를 써서 100 유닛이 추가로 들 수 있습니다.)

### Anthropic API 키

1. https://console.anthropic.com 에 가입/로그인합니다.
2. **Settings → Billing**에서 결제 수단을 등록하고 크레딧을 충전합니다. (API는 사용량만큼 과금)
3. **Settings → API Keys → Create Key** → 이름 입력 → 생성된 `sk-ant-...` 키를 복사합니다. (창을 닫으면 다시 볼 수 없으니 바로 저장하세요.)

> 기본 모델은 `claude-opus-5-5`입니다. 채널 학습 1회는 썸네일 문구 추출 5번 + 프로필 분석 1번, 생성은 채널당 1번(의료 채널은 검수 포함 2번) 호출합니다. 비용을 줄이려면 `.env`에 `CLAUDE_MODEL=claude-sonnet-5-5`를 넣으면 됩니다.

---

## 2단계. 설치 및 실행

필요한 것: **Python 3.10 이상** (https://www.python.org/downloads/ — Windows는 설치 화면에서 "Add Python to PATH" 체크)

### 간단 실행 (스크립트)

- **macOS / Linux**: 터미널에서 이 폴더로 이동 후 `./run.sh`
- **Windows**: 폴더에서 `run.bat` 더블클릭

처음 실행하면 `.env` 파일이 만들어지고 멈춥니다. `.env`를 메모장 등으로 열어 키를 넣고 다시 실행하세요.

```
YOUTUBE_API_KEY=AIza...
ANTHROPIC_API_KEY=sk-ant-...
```

### 수동 실행

```bash
cd yt-title-studio
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
# .env 열어서 두 키 입력
python app.py
```

브라우저에서 **http://localhost:5000** 을 엽니다. (포트를 바꾸려면 `.env`에 `PORT=8000`)

---

## 3단계. 사용법

1. **채널 등록**: 왼쪽에 채널 링크 입력 → 의료/비의료 선택 → **채널 학습 시작**. 1~3분 걸리고 진행 상황이 표시됩니다.
   - 지원 링크: `youtube.com/@핸들`, `youtube.com/channel/UC...`, `youtube.com/user/이름`, `youtube.com/c/이름`, 해당 채널의 영상 링크
2. **프로필 보기**로 학습된 패턴과 조회수 상위 레퍼런스(추출된 썸네일 문구 포함)를 확인할 수 있습니다.
3. 오른쪽에 **스크립트 붙여넣기** → 결과에 쓸 채널을 체크 → **생성하기**.
4. 결과는 **채널별 탭**으로 나옵니다.
   - 문구를 클릭하거나 **복사** 버튼 → 한 개 복사 (썸네일 줄바꿈 유지)
   - **문구만 전체 복사** / **패턴 포함 복사** → 10개 한 번에 복사
   - 의료 채널 탭의 `수정 N` 배지 = 56조 필터로 바뀐 항목 수

---

## 파일 구성

```
app.py            웹 서버 (Flask) · API 라우트
youtube.py        채널 링크 해석, 최근 영상 50개 수집
analyzer.py       썸네일 문구 추출(비전), 스타일 프로필 분석
generator.py      채널별 생성, 의료법 56조 필터
claude_client.py  Claude API 공통 호출(구조화 출력)
storage.py        data/channels/*.json 저장·조회
static/index.html 웹 화면
.env.example      API 키 템플릿
```

## 참고

- 56조 필터는 AI 검수이므로 법률 자문을 대신하지 않습니다. 실제 게시 전 최종 확인은 직접 해주세요.
- 문구가 없는 썸네일(사진만 있는 썸네일)은 "문구 없음"으로 기록되고, 그 비율도 스타일의 일부로 분석됩니다.
- 거절이 드물게 발생하면 Anthropic 서버가 권장 모델로 자동 재시도하도록 설정되어 있습니다(`fallbacks: "default"`).
