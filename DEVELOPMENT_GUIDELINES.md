# 반반 BanBan — 개발 지침서 (Development Guidelines)
> 버전 1.0 · 2026년 6월 기준 · 모든 팀원 필독 및 준수

---

## 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택](#2-기술-스택)
3. [아이콘 사용 규칙 ★ 핵심](#3-아이콘-사용-규칙)
4. [컬러 시스템](#4-컬러-시스템)
5. [컴포넌트 규칙](#5-컴포넌트-규칙)
6. [보안 규칙](#6-보안-규칙)
7. [심리학 설계 원칙](#7-심리학-설계-원칙)
8. [데이터베이스 규칙](#8-데이터베이스-규칙)
9. [코드 스타일](#9-코드-스타일)
10. [금지 사항](#10-금지-사항)

---

## 1. 프로젝트 개요

**반반 BanBan**은 중학생 영어 내신 특화 학습 플랫폼입니다.

| 항목 | 내용 |
|------|------|
| 대상 | 중학생 (학생) · 영어 선생님 · 학부모 |
| 핵심 가치 | 진심 · 정직 · 과장 없는 마케팅 |
| 주요 기능 | 단어/문법/내신/기출 학습 + SM-2 망각곡선 복습 + AI 오답 분석 + 학부모 리포트 |

---

## 2. 기술 스택

```
Frontend:  Streamlit (Python)
Backend:   Supabase (PostgreSQL + Auth + Realtime)
AI:        Google Gemini API (기본) / Anthropic API (보조)
Icons:     Lucide Icons (icons.py의 icon() 함수) ← 반드시 이것만
메뉴:      streamlit-option-menu (Bootstrap Icons — 예외 허용)
Email:     Gmail SMTP SSL (port 465)
```

---

## 3. 아이콘 사용 규칙

### ★ 핵심 원칙: 모든 커스텀 HTML에서 Lucide Icons만 사용

```python
# ✅ 올바른 사용 — icons.py의 icon() 함수
from icons import icon
st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;">
  {icon("users", 16, "#4338CA")} 학생 목록
</div>
""", unsafe_allow_html=True)

# ❌ 금지 — st.button()이나 st.write() 등에 icon() 직접 삽입
st.button(f"{icon('users', 16, 'white')} 클릭")  # SVG가 텍스트로 출력됨!

# ✅ Streamlit 위젯 라벨에는 이모지 사용
st.button("👥 학생 목록")
st.caption("🔑 초대 코드")
```

### icon() 함수 시그니처

```python
icon(name: str, size: int = 16, color: str = "currentColor") -> str
# 반환값: Lucide SVG 문자열 (unsafe_allow_html=True인 st.markdown에서만 사용)
```

### 자주 쓰는 Lucide 아이콘 목록

| 용도 | 아이콘 이름 | 코드 |
|------|------------|------|
| 학생 | users, user, user-plus | `icon("users", 16, "#4338CA")` |
| 선생님 | graduation-cap | `icon("graduation-cap", 16, "#7C3AED")` |
| AI / 스마트 | brain, sparkles, zap | `icon("brain", 16, "#7C3AED")` |
| 분석 | bar-chart-2, trending-up, target | `icon("bar-chart-2", 16, "#0891B2")` |
| 알림 | bell, alert-circle, alert-triangle | `icon("bell", 16, "#D97706")` |
| 완료 | check-circle, check | `icon("check-circle", 16, "#16A34A")` |
| 학습 | book-open, bookmark, layers | `icon("book-open", 16, "#4338CA")` |
| 설정 | settings, key, lock | `icon("settings", 16, "#6B7280")` |
| 시간 | clock, calendar, calendar-check | `icon("clock", 16, "#6B7280")` |
| 프리미엄 | star, award, crown | `icon("star", 16, "#D97706")` |
| 이메일 | mail, send | `icon("mail", 16, "#0891B2")` |
| 삭제/오류 | x-circle, trash-2, alert-circle | `icon("x-circle", 16, "#DC2626")` |
| 복습 | refresh-cw, rotate-ccw, repeat | `icon("refresh-cw", 16, "#7C3AED")` |

### option_menu 아이콘 예외

```python
# streamlit-option-menu는 Bootstrap Icons CSS를 사용하는 별개 라이브러리
# Lucide SVG를 직접 삽입할 수 없으므로, 아래 Bootstrap 아이콘 이름을 허용
# 단, 가능한 한 Lucide와 유사한 Bootstrap 아이콘명을 선택할 것

option_menu(
    icons=["book", "bar-chart-line", "people", "trophy"],  # Bootstrap Icons — 예외 허용
)
```

### HTML 주석 금지

```python
# ❌ Streamlit 마크다운 렌더러가 HTML 주석을 만나면 HTML 전체가 텍스트로 출력됨
st.markdown("""
<div>
  <!-- 이런 주석 절대 금지 -->
  내용
</div>
""", unsafe_allow_html=True)

# ✅ 주석이 필요하면 Python 주석 사용
# 아바타 영역
st.markdown("""<div>내용</div>""", unsafe_allow_html=True)
```

---

## 4. 컬러 시스템

### 브랜드 컬러

```css
/* Primary — 신뢰, 권위 */
--indigo-900: #1E1B4B;
--indigo-700: #3730A3;
--indigo-600: #4338CA;
--indigo-500: #4F46E5;
--indigo-400: #6366F1;
--indigo-100: #EEF2FF;

/* Premium Accent — 프리미엄, 온기 */
--amber-700:  #B45309;
--amber-500:  #D97706;
--amber-300:  #FCD34D;
--amber-100:  #FFFBEB;

/* Success */
--green-700:  #15803D;
--green-500:  #16A34A;
--green-100:  #F0FDF4;

/* Warning */
--orange-700: #C2410C;
--orange-500: #EA580C;
--orange-100: #FFF7ED;

/* Danger */
--red-700:    #B91C1C;
--red-500:    #DC2626;
--red-100:    #FEF2F2;

/* Neutral */
--gray-900:   #111827;
--gray-700:   #374151;
--gray-500:   #6B7280;
--gray-300:   #D1D5DB;
--gray-100:   #F3F4F6;
--gray-50:    #F9FAFB;
```

### 역할별 컬러

| 역할 | Primary | Accent |
|------|---------|--------|
| 선생님 | `#4338CA` (인디고) | `#D97706` (골드) |
| 학생 | `#7C3AED` (바이올렛) | `#0891B2` (스카이) |
| 학부모 | `#0F766E` (틸) | `#16A34A` (그린) |

---

## 5. 컴포넌트 규칙

### st.markdown + HTML

```python
# 항상 unsafe_allow_html=True 명시
st.markdown("...", unsafe_allow_html=True)

# 카드 기본 구조
CARD_STYLE = """
background:white;
border:1px solid #E5E7EB;
border-radius:14px;
padding:16px 18px;
box-shadow:0 1px 4px rgba(0,0,0,0.05);
"""
```

### st.button / st.form_submit_button

```python
# 라벨에 icon() 함수 절대 사용 금지 → 이모지 사용
st.button("🤖 AI 분석")          # ✅
st.button(icon("brain", 16))    # ❌ SVG 텍스트로 출력됨
```

### 선생님 전용 기능 조건 처리

```python
from auth import current_role
if current_role() in ("teacher", "admin"):
    # 선생님/관리자만 볼 수 있는 기능
    ...
```

### 학생 대시보드 메뉴 필터링

```python
# app.py 에서 역할별 _DASH_PAGES 분리 적용 중
_DASH_PAGES_TEACHER = ["내 학습현황", "학생 관리", "클래스 랭킹", "학부모 리포트", "주간 리포트 발송"]
_DASH_PAGES_STUDENT = ["내 학습현황", "클래스 랭킹"]
```

---

## 6. 보안 규칙

### API 키 관리

```bash
# ✅ .env 파일에만 저장
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...

# ❌ 절대 금지
# 소스 코드에 하드코딩
# UI에 노출
# Git 커밋에 포함 (.gitignore 필수 확인)
```

### 관리자 계정

```bash
# .env에만 저장
ADMIN_EMAIL=...
ADMIN_PASSWORD=...
# 코드에 절대 하드코딩 금지
```

### 선생님 이름

```python
# ✅ 항상 "반반쌤" 사용
teacher_display_name = "반반쌤"

# ❌ 실명 사용 금지 (코드에 하드코딩 금지)
```

### 팀원 이름

```python
# 이니셜만 사용: M.J., S.Y., D.Y., A.R.
```

### 비밀번호 정책

```python
# 선생님 + 학생 동일 적용
PW_POLICY = {
    "min_length": 8,
    "require_upper":   True,  # 대문자
    "require_lower":   True,  # 소문자
    "require_digit":   True,  # 숫자
    "require_special": True,  # 특수문자
}
```

### Supabase RLS

```sql
-- 신규 테이블 생성 시 항상 RLS 활성화 + 정책 추가
ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY "dev_open" ON new_table
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);
```

---

## 7. 심리학 설계 원칙

> 모든 원칙은 학술로 검증된 이론만 사용. 추측·허위 정보 엄금.

### 자문 페르소나

| 이름 | 전공 | 담당 |
|------|------|------|
| Dr. 이수진 | 교육심리학 · 자기결정이론(SDT) | 학습 동기 설계 |
| Dr. 박민호 | 소비자심리학 · 지각된 가치 | 가격·UX 설계 |
| Dr. 김아영 | 사회심리학 · 사회정체성이론 | 커뮤니티·소속감 |

### 적용 원칙

| 원칙 | 출처 | 적용 방법 |
|------|------|-----------|
| 자기결정이론 유능감 | Deci & Ryan (1985) | 데이터 시각화로 교사 유능감 강화 |
| 진행의 원칙 | Amabile & Kramer (2011) | 학습 진도 수치 가시화 |
| 지각된 가치 | Zeithaml (1988) | 프리미엄 UI로 가격 대비 가치 인식 상승 |
| 소유 효과 | Thaler (1980) | "선생님의 클래스", "나의 오답노트" 등 소유격 표현 |
| 사회적 정체성 | Tajfel & Turner (1979) | PREMIUM 배지·랭킹 등 긍정 집단 정체성 강화 |
| 상호성 | Cialdini (1984) | 기대 초과 서비스로 충성도 형성 |
| 인지 용이성 | Kahneman (2011) | 일관된 색상·아이콘으로 인지 부하 감소 |
| 신호등 시스템 | Norman (2013) | 녹색/노란/빨강으로 즉각적 상태 파악 |

### 금지된 심리 기법

```
❌ 다크 패턴 (무료 후 자동 결제, 숨겨진 해지 방해)
❌ 허위/과장 사회적 증거 ("1만 명 사용 중" 거짓 표시)
❌ 인위적 희소성/긴급성 ("오늘만 특가" 과장)
❌ "성적 보장", "n점 향상 보장" 등 미확인 효과 주장
```

---

## 8. 데이터베이스 규칙

### 테이블 구조

```
profiles          — 사용자 프로필 (id: UUID, student_id: SERIAL, role, teacher_id)
invite_codes      — 초대 코드 (teacher_id → auth.users.id)
study_logs        — 학습 기록 (student_id: INT = profiles.student_id)
wrong_notes       — 단어 오답 (student_id: INT)
question_wrong_notes — 문제 오답 (student_id: INT)
review_schedule   — SM-2 복습 스케줄 (student_id: INT)
parent_contacts   — 학부모 연락처
report_logs       — 리포트 발송 이력
```

### student_id 타입 주의

```python
# profiles.id = UUID (Supabase Auth 기본키)
# profiles.student_id = SERIAL 정수 (study_logs 등과 연결)
# 혼용 절대 금지!

# ✅ study_logs 조회 시
sb.table("study_logs").eq("student_id", profiles["student_id"])  # 정수

# ❌ 잘못된 예
sb.table("study_logs").eq("student_id", user.id)  # UUID — 타입 불일치!
```

### 마이그레이션 파일

```
supabase_migration.sql    — v2: invite_codes, learning_events, profiles 확장
supabase_migration_v3.sql — 학습 테이블 전체 + RLS 정책
supabase_migration_v4.sql — review_schedule (SM-2 복습)
supabase_migration_v5.sql — study_logs, online_notes 등
supabase_migration_v6.sql — parent_contacts, report_logs
```

---

## 9. 코드 스타일

### 파일 구조

```
app.py                  — 메인 앱 라우팅
auth.py                 — 인증 (로그인/가입/자동로그인)
study_db.py             — 데이터베이스 헬퍼
study_dashboard.py      — 대시보드 (학생/선생님)
study_vocab.py          — 단어 학습
study_grammar.py        — 문법 학습
study_exam.py           — 내신 문제
study_upload.py         — 기출 문제
study_review.py         — SM-2 복습
study_parent_report.py  — 학부모 리포트
study_ai.py             — AI 기능 (Gemini/Anthropic)
icons.py                — Lucide 아이콘 함수
supabase_client.py      — Supabase 클라이언트
```

### 네이밍 규칙

```python
# 함수: snake_case
def render_student_card(): ...

# 내부 전용 함수: 언더스코어 prefix
def _load_profile(): ...

# 상수: UPPER_SNAKE_CASE
_DASH_PAGES_TEACHER = [...]

# Streamlit 세션 키: "sb_" prefix (Supabase), 평문 (일반)
st.session_state["sb_user"]        # Supabase 관련
st.session_state["study_page"]     # 일반
```

### 오류 처리

```python
# DB 조회는 항상 try/except로 감싸기
try:
    result = sb.table("...").execute()
    data = result.data or []
except Exception as e:
    data = []
    # 중요한 오류만 st.error() 표시, 나머지는 조용히 무시
```

---

## 10. 금지 사항

### 코드

```
❌ .env 파일을 Git에 커밋
❌ API 키를 소스 코드에 하드코딩
❌ 실제 선생님 이름을 코드에 노출 (항상 "반반쌤")
❌ st.button() 라벨에 icon() 함수 사용 (SVG가 텍스트로 출력됨)
❌ st.markdown() HTML 내부에 <!-- HTML 주석 --> 사용
❌ st.markdown() 없이 icon() 함수 결과를 출력하는 행위
❌ profiles.id(UUID)와 profiles.student_id(INT) 혼용
```

### 마케팅/UX

```
❌ "성적 보장", "n점 향상 보장" 등 미확인 효과 표현
❌ 자동 결제 전환 트릭 (무료 후 자동 유료 전환)
❌ 해지 어렵게 만드는 UI 패턴
❌ 학생 데이터를 제3자에게 판매하거나 무단 활용
❌ 허위 사용자 수, 허위 후기
❌ 숨겨진 추가 요금
```

---

*이 지침서는 팀 전원이 숙지하고 준수해야 합니다. 위반 사항 발견 시 즉시 수정 요청.*

*최종 업데이트: 2026-06-01 · 반반 BanBan 개발팀*
