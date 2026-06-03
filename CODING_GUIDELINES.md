# 반반 BanBan — 코딩 & 디자인 가이드라인

> 모든 팀원(PM · 백엔드 · 프론트 · QA)이 공통으로 지켜야 할 규칙입니다.

---

## 1. 아이콘 규칙 — Lucide 아이콘만 사용

### ✅ 원칙

반반 BanBan의 모든 UI 아이콘은 **Lucide SVG 인라인 아이콘**만 사용합니다.  
이모지(📚 ✅ 🎯 등)는 **HTML/마크다운 영역에서 절대 사용 금지**입니다.

### ✅ 올바른 사용법

`icons.py`의 세 가지 함수를 사용하세요:

```python
from icons import icon, section_md, title_md
```

| 함수 | 용도 | 예시 |
|------|------|------|
| `icon(name, size, color)` | 인라인 SVG 아이콘 | `icon("book-open", 16, "#1a4fa0")` |
| `section_md(name, text)` | 섹션 헤더 | `section_md("list", "오답 목록")` |
| `title_md(name, text)` | 페이지 대제목 | `title_md("book-open", "라이브러리")` |

```python
# ✅ 올바른 예
st.markdown(section_md("pencil", "문제 풀기"), unsafe_allow_html=True)
st.markdown(f'{icon("check-circle", 15, "#16a34a")} 완료!', unsafe_allow_html=True)

# ❌ 잘못된 예 (HTML 영역에 이모지 사용)
st.markdown("### 📋 오답 목록")
st.markdown(f'<div>✅ 완료</div>', unsafe_allow_html=True)
```

### ✅ 이모지가 허용되는 곳 (예외)

다음 Streamlit 위젯은 HTML을 렌더링하지 않으므로 이모지 사용 가능:

```python
st.button("🎯 퀴즈 시작")        # ✅ 버튼 레이블
st.tabs(["📤 업로드", "📚 저장"])  # ✅ 탭 레이블
st.radio("방법", ["📸 이미지"])    # ✅ 라디오 옵션
st.success("✅ 저장되었습니다!")   # ✅ 알림 메시지
```

---

## 2. 아이콘 목록 (현재 등록된 Lucide 아이콘)

`icons.py`의 `_P` 딕셔너리에 등록된 아이콘입니다.

| 아이콘 이름 | 용도 |
|------------|------|
| `book-open` | 단어학습, 라이브러리 |
| `book` | 본문, 교재 |
| `file-text` | 내신문제, 문서 |
| `pencil` | 문제 풀기, 쓰기 |
| `check-circle` | 완료, 정답 |
| `check-square` | 문법 확인 |
| `list` | 목록 |
| `layers` | 합치기, 단원 |
| `zap` | AI 해설, 퀴즈 |
| `sparkles` | 비법노트, AI 생성 |
| `cloud-upload` | 기출 업로드 |
| `alert-circle` | 오답노트, 경고 |
| `target` | 취약 분석, 집중 연습 |
| `sliders` | 설정, 필터 |
| `eye` | 미리보기 |
| `camera` | 사진 촬영 |
| `image` | 이미지 |
| `message-circle` | 대화문 |
| `plus-circle` | 추가 |
| `wand-2` | 생성, 마법 |
| `info` | 정보 (기본값) |
| `database` | 뱅크, DB |
| `bar-chart-2` | 대시보드, 통계 |
| `user` | 학생, 사용자 |
| `award` | 성취, 점수 |
| `star` | 별점, 우수 등급 |
| `x-circle` | 오답, 취소 |
| `rotate-ccw` | 다시 풀기 |
| `flip-horizontal` | 플래시카드 뒤집기 |
| `flower` | 관리자 버튼 (로그인 페이지) |
| `lock` | 비밀번호 입력 |
| `mail` | 이메일 입력 |
| `log-in` | 로그인 |
| `log-out` | 로그아웃 |
| `shield` | 보안 / 인증 |
| `settings` | 설정, 계정 관리 |

### ✅ 새 아이콘 추가 방법

Lucide 공식 사이트(https://lucide.dev)에서 SVG 내부 path를 복사하여 `icons.py`의 `_P` 딕셔너리에 추가합니다:

```python
# icons.py — _P 딕셔너리에 추가
"아이콘-이름": '<path d="M..."/><circle cx="..." .../>',
```

> ⚠️ 반드시 **Lucide 아이콘**만 추가하세요. 다른 아이콘 라이브러리 금지.

---

## 3. HTML 렌더링 규칙

### unsafe_allow_html 사용 기준

```python
# ✅ 아이콘, 스타일 카드, 배지 등 디자인 요소
st.markdown(f'<div style="...">{icon("target",14,"#854d0e")} 텍스트</div>',
            unsafe_allow_html=True)

# ✅ 밑줄 등 서식이 필요한 문제 텍스트
st.markdown(f'<b>{p["question"]}</b>', unsafe_allow_html=True)

# ❌ 단순 텍스트에는 사용 불필요
st.markdown("단순 텍스트")   # 이게 더 간단
```

### 밑줄 처리 (기출문제)

AI가 추출한 문제 텍스트에서 밑줄은 `<u>텍스트</u>` HTML 태그로 표현됩니다.  
반드시 `unsafe_allow_html=True`로 렌더링해야 밑줄이 표시됩니다:

```python
# ✅ 밑줄 있는 문제 렌더링
st.markdown(f'<div>{p["question"]}</div>', unsafe_allow_html=True)

# ❌ 밑줄 사라짐
st.markdown(p["question"])
```

---

## 4. 색상 팔레트

| 섹션 | 주 색상 | 보조 색상 |
|------|---------|---------|
| 반반노트 (제작) | `#1a4fa0` (파랑) | `#dbeafe` |
| 단어학습 | `#1a4fa0` → `#3b82f6` | `#dbeafe` |
| 문법학습 | `#6d28d9` (보라) | `#ede9fe` |
| 내신문제 | `#166534` (녹색) | `#dcfce7` |
| 오답노트 | `#dc2626` (빨강) | `#fef2f2` |
| 비법노트 | `#7c3aed` (보라) | `#ede9fe` |
| 기출문제 | `#0f766e` (청록) | `#ccfbf1` |
| 대시보드 | `#0f766e` (청록) | `#ccfbf1` |

---

## 5. 컴포넌트 패턴

### 페이지 헤더 (그라디언트 배너)

```python
st.markdown(f"""
<div style="background:linear-gradient(135deg,#1a4fa0,#3b82f6);color:white;
     border-radius:14px;padding:18px 20px;margin-bottom:20px;">
  <div style="font-size:0.85rem;opacity:0.85;">
    {icon("book-open", 14, "rgba(255,255,255,0.85)")} 섹션명
  </div>
  <div style="font-size:1.4rem;font-weight:800;margin-top:4px;">페이지 제목</div>
</div>
""", unsafe_allow_html=True)
```

### 섹션 구분자

```python
st.markdown(section_md("list", "섹션 제목"), unsafe_allow_html=True)
```

### 정보 카드 (뱃지 포함)

```python
st.markdown(f"""
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
     padding:10px 14px;font-size:0.85rem;color:#166534;">
  {icon("check-circle", 14, "#16a34a")} 메시지 내용
</div>
""", unsafe_allow_html=True)
```

---

## 6. 아이콘 감사 결과 (2026-05-28)

> UI 팀 대상 — 페이지별 비준수 이모지 발견 및 수정 완료 현황

### ✅ 수정 완료 목록 (1차: 2026-05-28)

| 파일 | 위치 | 발견된 이모지 | 교체된 Lucide 아이콘 |
|------|------|-------------|-------------------|
| `study_vocab.py` | 퀴즈 모드 카드 (col1) | `🇬🇧` | `icon("book-open", 32, "#1a4fa0")` |
| `study_vocab.py` | 퀴즈 모드 카드 (col2) | `🇰🇷` | `icon("layers", 32, "#166534")` |
| `study_vocab.py` | 퀴즈 모드 카드 (col3) | `📖` | `icon("zap", 32, "#854d0e")` |
| `study_vocab.py` | 퀴즈 모드 카드 (col4) | `✏️` | `icon("pencil", 32, "#9d174d")` |
| `study_wrongnote.py` | 오답 없음 빈 상태 | `🎉` | `icon("check-circle", 52, "#16a34a")` |
| `study_secret.py` | 비법노트 없음 빈 상태 | `✨` | `icon("sparkles", 52, "#a78bfa")` |
| `study_grammar.py` | 문법 포인트 없음 빈 상태 | `📚` | `icon("book-open", 52, "#7c3aed")` |
| `study_upload.py` | 기출문제 없음 빈 상태 | `📥` | `icon("cloud-upload", 52, "#0d9488")` |

### ✅ 수정 완료 목록 (2차: 2026-05-28)

| 파일 | 위치 | 발견된 이모지 | 교체된 Lucide 아이콘 |
|------|------|-------------|-------------------|
| `study_exam.py` | 난이도 뱃지 (쉬움/보통/어려움) | `⭐⭐⭐` | `★★★` (타이포그래피 기호) |
| `study_exam.py` | 답변 피드백 (정답/오답) | `✅` / `❌` | `icon("check-circle", 14)` / `icon("x-circle", 14)` |
| `study_exam.py` | 시험 결과 배너 (90점↑) | `🏆` | `icon("award", 52, "#16a34a")` |
| `study_exam.py` | 시험 결과 배너 (70점↑) | `🌟` | `icon("star", 52, "#ca8a04")` |
| `study_exam.py` | 시험 결과 배너 (50점↑) | `💪` | `icon("zap", 52, "#ea580c")` |
| `study_exam.py` | 시험 결과 배너 (50점↓) | `📚` | `icon("book-open", 52, "#dc2626")` |
| `study_exam.py` | 진행률 표시기 | `📊` | `icon("bar-chart-2", 14, "#374151")` |
| `study_grammar.py` | 빈 상태 안내 텍스트 | `⚙️` | 텍스트 제거 (plain text) |
| `study_upload.py` | 채점 결과 정답 표시 | `✅` | `icon("check-circle", 13, "#16a34a")` |

### 허용 예외 (수정 불필요)

| 파일 | 이모지 | 허용 이유 |
|------|--------|---------|
| `study_wrongnote.py` | `🧠✨` | `components.html()` 내부 (별도 iframe — HTML 렌더링 격리) |
| `study_wrongnote.py` | `👆` | `components.html()` 내부 탭 힌트 |
| 모든 파일 | `st.button()`, `st.tabs()`, `st.success()` 등 위젯 레이블 | Streamlit이 HTML 렌더링 안 함 → 이모지 허용 |

### 신규 개발 시 체크리스트

1. `st.markdown(..., unsafe_allow_html=True)` 안에 이모지 사용 → **즉시 `icon()` 으로 교체**
2. `<div>` 등 HTML 태그 내부에 이모지 삽입 → **금지**
3. 빈 상태(empty state) 대형 아이콘 → `icon(name, 52, color)` 패턴 사용
4. 카드형 섹션 아이콘 → `icon(name, 32, color)` 패턴 사용
5. 인라인 텍스트 아이콘 → `icon(name, 14~16, color)` 패턴 사용

---

## 7. 금지 사항

| 금지 | 대신 사용 |
|------|---------|
| `#### 📋 섹션명` | `section_md("list", "섹션명")` |
| `### 🎯 페이지 제목` | `title_md("target", "페이지 제목")` |
| `<div>✅ 완료</div>` | `<div>{icon("check-circle",...)} 완료</div>` |
| `<div style="font-size:3rem;">🎉</div>` | `icon("check-circle", 52, "#16a34a")` |
| `<div style="font-size:1.5rem;">📖</div>` | `icon("zap", 32, "#854d0e")` |
| Bootstrap Icons in HTML | Lucide icons via `icon()` |
| 새 아이콘 라이브러리 추가 | `icons.py`에 Lucide path 추가 |

> **option_menu의 `icons=[]` 파라미터는 Bootstrap Icons를 사용합니다.**  
> 사이드바 메뉴에 한해서만 Bootstrap Icons 이름을 사용하며, 나머지 UI는 모두 Lucide입니다.

---

*최종 업데이트: 2026-05-28 (2차 아이콘 감사) | 반반 BanBan 개발팀*
