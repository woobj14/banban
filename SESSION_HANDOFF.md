# 반반 BanBan — 세션 인계 문서 (컨텍스트 복구용)
> 최종 업데이트: 2026-06-11
> **새 채팅 시작 시 이 파일 + PROJECT_SNAPSHOT.md + DEV_ROADMAP.md를 먼저 읽을 것.**
> 이 문서는 "직전 채팅에서 무엇을 했고 다음에 뭘 할지"를 담는다.

---

## 0. 한 줄 현황
중학생 영어 학습 플랫폼. **시중화 게이트(P1) 통과**, 투자자 실사 후 **발전 전략 실행 중**.
지금 작업: **자기주도 학습 엔진 + 투자자 지적사항 해소**. 다음 할 일 = **② AI 비용 측정(유닛 이코노믹스)**.

---

## 1. 작업 환경 (중요)
- **경로**: `/Users/alexbyungjinwoo/Documents/스발노트만들기/`
- **실행**: `streamlit run app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true`
- **로컬 주소**: http://localhost:8501 · **학생용(같은 와이파이)**: http://192.168.0.228:8501
- **ngrok(빠른 외부 테스트)**: `ngrok http 8501` → 공개 URL. Render는 느려서 테스트는 ngrok 권장.
- **배포**: Render(사용중·느림) + railway.json 존재(미사용). GitHub: woobj14/banban (main 직접 푸시→자동배포)
- **DB**: Supabase (마이그레이션 v15까지 적용 완료). 새 테이블 만들 때마다 **RLS 비활성 한 줄 따로 실행 필요**:
  `ALTER TABLE <t> DISABLE ROW LEVEL SECURITY;` (CREATE와 같은 배치에선 종종 안 먹음 — 반복 패턴)
- **AI 키**: Gemini 2키 + (선택)Anthropic. 3단 폴백 체인(Gemini1→Gemini2→Claude Haiku). 모델은 전부 저가형(Flash/Haiku) 고정.
- **DEV_SKIP_AUTH=false** (로그인 게이트 ON). streamlit은 .env 변경 시 **재시작해야 반영**.
- **git push 인증**: PAT(classic, repo 권한). 만료되면 Keychain erase 후 재입력.

---

## 2. 직전 채팅에서 한 일 (최근순)
1. **세션 영속화** ✅ — refresh_token을 쿠키(30일)에 저장 → 탭 끊겨도 자동 재로그인.
   `auth.py` `_cookie_mgr/_save/_get/_clear_refresh_cookie`, `restore_session` 2단 폴백.
   (CookieManager는 위젯이라 cache_resource 금지 → session_state에 1회 생성)
2. **문법 드릴 생각 유도 채점** ✅ — 첫 오답엔 정답 비공개+'다시 생각' 1회, 둘째 오답에 확정.
   `study_grammar.py` `_handle_drill_answer` (attempts/retry 상태)
3. **자기주도 위젯** ✅ — 내 학습현황 최상단 '오늘의 학습' 다음 행동 추천(규칙기반 비용0).
   `study_dashboard.py` `_next_action / _render_next_action_widget`
4. **첫 화면 통계 접기** ✅ — 제시안(위젯) 먼저, 상세통계는 expander. `_render_stats_detail`
5. **Polar webhook HMAC 서명 검증** ✅ [P1-2] — `supabase/functions/polar-webhook/index.ts` (standardwebhooks)
6. **시험 요약노트 재설계** ✅ — 단일시트·5mm·흑백·빈칸모드·대화문요약·섹션게이트·자동저장/저장탭(migration v14)·계단식
7. **Gemini Kore TTS** ✅ — gemini-2.5-flash-preview-tts·캐싱(v15)·단어학습 고품질 발음·카드뒷면 스크롤. `tts.py`
8. **AI 비용 게이팅** ✅ — 비법/처방/요약/추천에 사용량 카운터(누수 차단). ocr Opus 잔재 제거.

---

## 3. 투자자 실사 (100억 관점) — 6대 과제 & 진행
> 전체 회의록은 이 채팅 참조. 핵심: "방향 A급, 기술기반·비즈니스증명 C급. 지금 이대로면 100억은 비싸다."

| # | 과제 | 상태 |
|---|------|------|
| ① | 세션 영속화(리텐션 기본기) | ✅ 완료 |
| ② | AI 비용 측정 → 학생당 월 비용(유닛 이코노믹스) | ✅ 완료 |
| ③ | RLS·보안 정비 (미성년자 데이터) | ✅ 완료 |
| ④ | 서술형 채점 비용 상한 | ⬜ (②데이터 쌓인 뒤 판단) |
| ⑤ | **AI 자체 콘텐츠 생성**(교육과정 기반) = 저작권+해자+무한공급 동시해결 | 🔄 **진행 중** 게임체인저 |
| ⑥ | 비즈니스 로직 UI 분리(탈Streamlit 준비) | ⬜ |

**①②③ 방어 과제 완료 — "안 죽는 회사" 기본기 갖춤.** 이제 ⑤(공격) 단계.

### ②③ 구현 메모 (중요)
- **AI 비용 측정**: 모든 AI 호출이 `_call_text`/`_call_ai` 단일 통로 → 토큰·비용 자동 로깅(`ai_usage_log`, migration v16).
  집계 `study_db.get_ai_cost_summary`, 관리자 대시보드(학생관리)에 💰카드.
- **RLS 보안**: `supabase_client.get_supabase()`가 **SERVICE_KEY 우선** 사용(서버측 신뢰→RLS 우회).
  전 테이블 RLS ENABLE + 기존 정책 DROP(migration v17) → anon 전면 차단(검증 10/10), service_role만 통과.
  **⚠️ 배포(Render) 환경변수에 SUPABASE_SERVICE_KEY 필수** (없으면 anon 폴백→RLS에 막혀 다운).

---

## 4. 다음 할 일 (바로 이어서)
**⑤ AI 자체 콘텐츠 생성 (게임체인저)** — 선생님 노동 0·저작권 0·우리만의 자산.
단계적으로:
1. **교육과정 입력(학년·단원·주제) → AI가 지문·단어 자동 생성** ← 1단계 (지금)
2. 기존 **노트 라이브러리에 저장** (모든 학습 기능 자동 연결)
3. 점진 확장 (대화문·문제·생각유도형 설계)
- 기반: 서술형 DNA 엔진(`study_ai.generate_essay_questions`)을 '노트 기반'→'교육과정 기반'으로 확장
- 담당 관점: J.H.(교육)·S.Y.(백엔드)

---

## 5. 일하는 방식 (사장님 지시 — 반드시 지킬 것)
- **작업이 한 번 끝날 때마다 전 팀원 회의**(건의/발전). 묻지 말고 보고 끝에 붙인다.
- 회의 4대 렌즈: **편의성 · 시간절약 · 자기주도 · 생각의 폭**(외우기X 생각하게).
- 회의는 **상세 대화 형식**, 어느 팀 누가 발언했는지(교육J.H./UX K.D./심리H.S./프론트D.Y./백엔드S.Y./그로스N.W./CS R.M./QA A.R.).
- 팀원 실명은 이니셜. 사장님보다 뛰어난 시각으로 비판·제안.
- 마이그레이션/시크릿 작업은 사용자가 SQL Editor/터미널에서 실행 → "완료" 받으면 검증.

---

## 6. 알려진 미해결/주의
- 미성년자 데이터인데 **RLS 전면 비활성** (보안 과제 ③)
- Streamlit 단일 인스턴스 = 대규모 동시접속 한계 (과제 ⑥)
- 기출/교과서 업로드 = 출판사 저작권 리스크 (과제 ⑤로 해소 방향)
- 기존 localStorage 자동로그인 코드도 있음(auth.py) — 새 쿠키 방식과 공존 중
