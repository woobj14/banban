# 반반 BanBan — 프로젝트 스냅샷
> 마지막 업데이트: 2026-05-29  
> Claude와의 대화 컨텍스트 복구용 문서. 새 세션 시작 시 이 파일을 먼저 읽어줄 것.

---

## 1. 프로젝트 개요

**서비스명**: 반반 BanBan  
**목적**: 중학생 대상 영어 학습 플랫폼 (반반노트 생성 + 온라인 학습 + 오답노트 + AI 비법노트)  
**스택**: Python + Streamlit (멀티페이지 단일 앱) + Supabase (PostgreSQL) + OpenAI API  
**실행**: `streamlit run app.py`  
**경로**: `/Users/alexbyungjinwoo/Documents/스발노트만들기/`

---

## 2. 팀 & 보안 규칙

- 선생님 호칭: **반반쌤** (코드 내 "권나연" 전부 교체 완료)
- 팀원 이름: 프라이버시 보호 → 이니셜 사용 **(M.J., S.Y., D.Y., A.R.)**
- API 키, 관리자 계정: `.env` 파일에만 저장. **절대 UI/코드에 노출 금지**
  - `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`
  - `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- 개발 모드: `.env`에 `DEV_SKIP_AUTH=true` → 로그인 화면 스킵

---

## 3. 파일 구조 & 역할

| 파일 | 역할 | 라인 수 |
|------|------|---------|
| `app.py` | 메인 앱, 사이드바 메뉴, 페이지 라우팅 | ~2060 |
| `study_note_reader.py` | **반반 학습** 페이지 (온라인 학습 모드) | ~667 |
| `study_vocab.py` | 단어 퀴즈 + 플래시카드 (영영사전 API) | ~702 |
| `study_grammar.py` | 문법 드릴 학습 | ~1030 |
| `study_exam.py` | 내신문제 풀기 | ~485 |
| `study_wrongnote.py` | 오답노트 뷰어 | ~663 |
| `study_upload.py` | 기출문제 업로드 & 풀기 | ~578 |
| `study_secret.py` | 비법노트 (AI 생성, 5가지 스타일) | ~380 |
| `study_ai.py` | AI 비법노트 생성 로직 + 프롬프트 | ~681 |
| `study_db.py` | Supabase DB 함수 모음 | ~689 |
| `study_dashboard.py` | 학생 학습현황 대시보드 | - |
| `auth.py` | 로그인/회원가입/비밀번호재설정 | - |
| `chatbot.py` | 반쌤 채팅 (AI 튜터) | - |
| `generator.py` | 반반노트 생성 (GPT) | - |
| `library.py` | 노트 라이브러리 CRUD | - |
| `supabase_client.py` | Supabase 클라이언트 초기화 | - |
| `supabase_rls_fix.sql` | RLS 수정 SQL (Supabase 대시보드에서 실행) | - |

---

## 4. 사이드바 메뉴 구조

```
반반 BanBan (브랜드 헤더)
│
├── 반반노트 ▾  (토글 — _acc_note)
│   ├── 라이브러리
│   ├── 새 노트 만들기
│   └── 합치기 & 다운로드
│
├── 학습센터 ▾  (토글 — _acc_study)
│   ├── 반반 학습   ← (이전: "노트 학습", 2026-05-29 변경)
│   ├── 단어학습
│   ├── 문법학습
│   ├── 내신문제
│   ├── 오답노트
│   ├── 비법노트
│   ├── 기출문제
│   └── 반쌤 채팅
│
└── 대시보드 ▾  (토글 — _acc_dash, 기본 닫힘)
    ├── 내 학습현황
    └── 학생 관리
```

### 사이드바 아코디언 구현 방식 (app.py `_section_toggle()`)
- `st.markdown('<span id="accm{key}"></span>')` + CSS를 **하나의 st.markdown 호출**에 합쳐서 렌더
- CSS: `div:has(span#{uid}) + div [data-testid="stButton"] > button { all: unset !important; ... }`
- 버튼 1개만 렌더 → 헤더 텍스트 = 클릭 영역
- **주의**: 마커 span과 CSS를 별도 st.markdown으로 분리하면 `+` 인접 선택자 실패함

---

## 5. Supabase 테이블 목록

| 테이블 | 주요 컬럼 | 비고 |
|--------|-----------|------|
| `wrong_notes` | student_id, note_id, word_en, word_kr, ... | 단어 오답 |
| `word_cache` | word_en, definition, ... | 단어 캐시 |
| `quiz_sessions` | student_id(nullable), note_id, quiz_type | 퀴즈 세션 |
| `quiz_results` | session_id, word_en, is_correct, ... | **student_id 없음** |
| `exam_sets` | student_id(nullable), note_id, ... | 내신문제 세트 |
| `exam_results` | student_id(nullable), ... | 내신 결과 |
| `secret_notes` | ... | 비법노트 |
| `past_problems` | ... | 기출문제 |
| `weakness_profile` | student_id(nullable→수정됨), ... | 취약점 |
| `grammar_points` | ... | 문법 |
| `question_bank` | ... | 문제 은행 |
| `question_wrong_notes` | student_id(nullable→수정됨), ... | 문제 오답노트 |
| `online_note_sessions` | student_id(nullable→수정됨), note_id, content_type, completed | 온라인 학습 |
| `study_logs` | student_id(nullable→수정됨), note_id, activity, score, total, duration_sec, details | 학습 로그 |

> `supabase_rls_fix.sql` — Supabase 대시보드 SQL Editor에서 실행 완료 (2026-05-29)  
> **오류 수정**: `quiz_results`에 student_id 컬럼 없음 → ALTER 제외 처리

---

## 6. 이번 세션에서 완료한 작업 목록

### ✅ 완료

1. **이름 변경**
   - "권나연쌤" / "권나현 선생님" → **반반쌤** (전체 파일)
   - 팀원 실명 → 이니셜 (M.J., S.Y., D.Y., A.R.)

2. **비법노트 "만화 대화형" 스타일 추가** (`study_secret.py`, `study_ai.py`)
   - 반반쌤👩‍🏫(보라색 말풍선) × 학생🙋(앰버 말풍선) 캐릭터 대화 스타일
   - 기존 "웹툰형" → "카드형"으로 대체
   - 기본 스타일 = "만화 대화형"

3. **사이드바 아코디언 메뉴** (`app.py`)
   - 반반노트 / 학습센터 / 대시보드 접었다펼수있는 슬라이드
   - `option_menu` 유지하면서 섹션 헤더만 토글
   - CSS `all: unset` + `:has()` 마커 기법으로 네모 버튼 제거

4. **반반 학습 페이지** (`study_note_reader.py`) — 완전 재작성 v2
   - 학습 모드: `st.radio()` 방식으로 교체 (기존 카드+버튼 분리 방식 버그 수정)
   - 3가지 모드: 👁️양쪽보기 / 🇬🇧영어→한글 / 🇰🇷한글→영어
   - 블러 효과: CSS `filter:blur(6px)` + JS `classList.toggle('rev')` 클릭 reveal
   - **진도바**: 섹션별 "✅ 완료" 버튼, X/3 진도바 표시
   - **학습 로그**: 시작시 `note_read_start`, 섹션완료시 `section_complete`, 전체완료시 `note_read` → `study_logs` 저장
   - **에빙하우스 복습 알림**: 마지막 학습일 기준 urgency 뱃지 (오늘✅ / 1일파랑 / 3일노랑 / 7일주황 / 14일+빨강)
   - 완료 시 🎉 배너 + 다음 복습 권장일 표시

5. **단어 플래시카드 강화** (`study_vocab.py`)
   - 카드 뒤집으면 영영사전 API (dictionaryapi.dev) 호출
   - 영어 발음기호, 품사, 정의, 예문, 유의어 칩, 반의어 칩 표시
   - 첫 3개 단어 prefetch, `dictCache` 객체로 캐싱

6. **오답노트 자동 저장** (`study_grammar.py`, `study_exam.py`, `study_upload.py`)
   - 기존: 수동 "📌 오답노트에 추가" 버튼
   - 변경: 오답 시 자동 저장 → "📌 오답노트에 자동 저장됐어요!" 표시
   - `add_question_wrong()` 호출 (`study_db.py`)

7. **`study_wrongnote.py` 버그 수정**
   - `source_type="past_exam"` 키 누락 → `_SOURCE_LABEL`, `_SOURCE_ICON` 딕셔너리에 추가

8. **`supabase_rls_fix.sql` 수정**
   - ERROR 42703: `quiz_results`에 `student_id` 컬럼 없음 → ALTER 제외
   - 실제 `student_id` 컬럼 있는 7개 테이블만 ALTER (RLS 비활성화 + GRANT 포함)

9. **메뉴 이름 변경**: "노트 학습" → **"반반 학습"** (app.py 5곳)

10. **비법노트 자동 분석 기능 추가** (`study_ai.py`, `study_secret.py`)
    - `analyze_note_for_secrets(note, api_config)` → 노트 내용에서 문법/어휘/표현 자동 추출 + 중요도 별점
    - `generate_secret_note_from_items(items, style, api_config, note_title)` → 선택 아이템으로 비법노트 생성
    - 비법노트 탭 3개로 확장: ✨새로 만들기 / 🤖자동 비법 만들기 / 📁저장된 비법노트
    - 자동 분석 탭: 체크박스 선택 → 스타일 선택 → 생성 → 저장 흐름
    - 문법 아이템은 `grammar_points` 테이블에 함께 저장

---

## 7. 주요 함수 & 패턴 레퍼런스

### study_db.py 주요 함수
```python
# 학생 관리
get_or_create_student(name: str) -> int          # student_id 반환
list_students() -> list[dict]

# 오답노트
add_question_wrong(student_id, note_id, bank_question_id,
                   source_type, question_snapshot, user_answer)
# source_type: "grammar" | "exam" | "past_exam" | "past"

# 학습 로그
log_study_activity(student_id, note_id, activity,
                   score, total, duration_sec, details)
# activity: "note_read_start" | "note_read" | "section_complete" |
#           "word_quiz" | "exam" | "grammar_drill"

get_study_logs(student_id, days=7) -> list[dict]

# 진도 조회
get_online_note_progress(student_id, note_id) -> dict
# returns: {"단어": {"total": N, "done": M}, ...}
```

### app.py 핵심 세션 상태 키
```python
st.session_state["page"]           # 현재 반반노트 페이지
st.session_state["study_page"]     # 현재 학습센터 페이지 (기본: "반반 학습")
st.session_state["dash_page"]      # 현재 대시보드 페이지
st.session_state["study_student"]  # 선택된 학생 이름
st.session_state["study_note_id"]  # 선택된 노트 ID
st.session_state["_acc_note"]      # 반반노트 섹션 열림/닫힘 (기본 True)
st.session_state["_acc_study"]     # 학습센터 섹션 열림/닫힘 (기본 True)
st.session_state["_acc_dash"]      # 대시보드 섹션 열림/닫힘 (기본 False)
```

### study_note_reader.py 세션 상태 키 (note_id 별)
```python
f"nr_done_{note_id}"       # set() — 완료된 섹션명 ("단어", "대화문", "본문")
f"nr_started_{note_id}"    # bool — 학습 시작 여부 (로그 중복 방지)
f"nr_ts_{note_id}"         # float — 학습 시작 timestamp
f"nr_ebb_{note_id}"        # datetime | None — 마지막 학습 일시
f"nr_mode_{note_id}"       # str — 현재 학습 모드 ("both"|"en"|"kr")
```

---

## 8. 알려진 이슈 & 주의사항

### ⚠️ Streamlit 버전 호환성
```
ImportError: cannot import name 'DEFAULT_EXCLUDED_CONTENT_TYPES'
from 'starlette.middleware.gzip'
```
- `python3 -c "import streamlit"` 직접 실행 시 에러 발생 (Streamlit ↔ Starlette 버전 충돌)
- `streamlit run app.py`로 실행하면 정상 작동 (별도 환경에서 구동됨)
- **코드 자체 오류 아님**, 무시하고 진행

### ⚠️ 아코디언 CSS 주의
- 마커 span과 CSS를 **반드시 하나의 st.markdown() 호출**로 합쳐야 함
- 분리하면 DOM에서 `+ div` 인접 선택자가 CSS 요소를 먼저 잡아버려 버튼 적용 실패

### ⚠️ components.html() 모드 캐싱
- `_word_study_html(words, mode, note_id)` — `note_id` 파라미터를 HTML 주석에 삽입해 캐시 무효화
- 모드 변경 시 `st.rerun()` 이 정상 작동하면 HTML 스트링이 달라져 재렌더됨

### ⚠️ 오답노트 source_type 별칭
- `study_upload.py`는 `source_type="past_exam"` 저장
- `study_wrongnote.py` `_SOURCE_LABEL` 딕셔너리에 `"past_exam"` 키 추가됨
- 미래에 새 source_type 추가 시 양쪽 딕셔너리에 모두 추가할 것

---

## 9. 향후 구현 예정 / 아이디어

| 우선순위 | 기능 | 상태 |
|---------|------|------|
| 🔴 높음 | `study_dashboard.py` 학생별 학습현황 UI 고도화 | 미확인 |
| 🔴 높음 | 에빙하우스 복습 알림 → 대시보드에 "오늘 복습할 노트" 위젯 | 미구현 |
| 🟡 중간 | `online_note_sessions` 테이블 실제 활용 (단어별 완료 저장) | 미구현 |
| 🟡 중간 | 반반 학습 완료 후 자동 단어 퀴즈 연결 | 부분구현 (버튼만) |
| 🟢 낮음 | 학습 모드별 통계 (어느 모드에서 오답 많은지) | 미구현 |
| 🟢 낮음 | 비법노트 "만화 대화형" 스타일 출력 품질 개선 | 가능 |

---

## 10. 새 세션 시작 시 Claude에게 전달할 프롬프트

```
아래 파일을 먼저 읽어줘:
/Users/alexbyungjinwoo/Documents/스발노트만들기/PROJECT_SNAPSHOT.md

이 파일은 반반 BanBan 프로젝트의 전체 상태 스냅샷이야.
이전 대화에서 작업한 내용이 정리돼있으니 읽고 나서 이어서 도와줘.
```

---

*이 파일은 Claude와의 대화 중 중요한 결정/변경이 있을 때마다 업데이트할 것.*
