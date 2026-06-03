-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan — RLS 권한 수정 v2 (2026-05-29)
-- 오류 코드 42501 "new row violates row-level security policy" 해결
--
-- 실행 방법:
--   Supabase 대시보드 > SQL Editor > 이 내용 전체 붙여넣기 > Run
-- ═══════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────────────────────────
-- 1. 모든 학습 테이블에 anon + authenticated 전체 권한 부여
-- ──────────────────────────────────────────────────────────────────
GRANT ALL ON TABLE wrong_notes           TO anon, authenticated;
GRANT ALL ON TABLE word_cache            TO anon, authenticated;
GRANT ALL ON TABLE quiz_sessions         TO anon, authenticated;
GRANT ALL ON TABLE quiz_results          TO anon, authenticated;
GRANT ALL ON TABLE exam_sets             TO anon, authenticated;
GRANT ALL ON TABLE exam_results          TO anon, authenticated;
GRANT ALL ON TABLE secret_notes          TO anon, authenticated;
GRANT ALL ON TABLE past_problems         TO anon, authenticated;
GRANT ALL ON TABLE weakness_profile      TO anon, authenticated;
GRANT ALL ON TABLE grammar_points        TO anon, authenticated;
GRANT ALL ON TABLE question_bank         TO anon, authenticated;
GRANT ALL ON TABLE question_wrong_notes  TO anon, authenticated;
GRANT ALL ON TABLE online_note_sessions  TO anon, authenticated;
GRANT ALL ON TABLE study_logs            TO anon, authenticated;


-- ──────────────────────────────────────────────────────────────────
-- 2. IDENTITY 시퀀스도 사용 권한 부여 (INSERT 시 자동 증가)
-- ──────────────────────────────────────────────────────────────────
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;


-- ──────────────────────────────────────────────────────────────────
-- 3. 개발 중: RLS 비활성화 (DEV_SKIP_AUTH=true 환경)
-- ──────────────────────────────────────────────────────────────────
ALTER TABLE wrong_notes           DISABLE ROW LEVEL SECURITY;
ALTER TABLE word_cache            DISABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_sessions         DISABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_results          DISABLE ROW LEVEL SECURITY;
ALTER TABLE exam_sets             DISABLE ROW LEVEL SECURITY;
ALTER TABLE exam_results          DISABLE ROW LEVEL SECURITY;
ALTER TABLE secret_notes          DISABLE ROW LEVEL SECURITY;
ALTER TABLE past_problems         DISABLE ROW LEVEL SECURITY;
ALTER TABLE weakness_profile      DISABLE ROW LEVEL SECURITY;
ALTER TABLE grammar_points        DISABLE ROW LEVEL SECURITY;
ALTER TABLE question_bank         DISABLE ROW LEVEL SECURITY;
ALTER TABLE question_wrong_notes  DISABLE ROW LEVEL SECURITY;
ALTER TABLE online_note_sessions  DISABLE ROW LEVEL SECURITY;
ALTER TABLE study_logs            DISABLE ROW LEVEL SECURITY;


-- ──────────────────────────────────────────────────────────────────
-- 4. student_id NOT NULL 제약 제거
--    ※ 실제 스키마 기준 — student_id 컬럼이 있는 테이블만 적용
--
--    student_id 있음:
--      quiz_sessions (nullable — 이미 OK, 보험용 실행)
--      exam_sets     (nullable — 이미 OK)
--      exam_results  (nullable — 이미 OK)
--      weakness_profile      (NOT NULL → 제거)
--      question_wrong_notes  (NOT NULL → 제거)
--      online_note_sessions  (NOT NULL → 제거)
--      study_logs            (NOT NULL → 제거)
--
--    student_id 없음 (실행 제외):
--      quiz_results, word_cache, secret_notes,
--      past_problems, grammar_points, question_bank
-- ──────────────────────────────────────────────────────────────────

-- quiz_sessions: student_id 이미 nullable (오류 방지용 — 안전하게 실행 가능)
ALTER TABLE quiz_sessions        ALTER COLUMN student_id DROP NOT NULL;

-- exam_sets: student_id 이미 nullable
ALTER TABLE exam_sets            ALTER COLUMN student_id DROP NOT NULL;

-- exam_results: student_id 이미 nullable
ALTER TABLE exam_results         ALTER COLUMN student_id DROP NOT NULL;

-- weakness_profile: NOT NULL → nullable 로 변경
ALTER TABLE weakness_profile     ALTER COLUMN student_id DROP NOT NULL;

-- question_wrong_notes: NOT NULL → nullable 로 변경
ALTER TABLE question_wrong_notes ALTER COLUMN student_id DROP NOT NULL;

-- online_note_sessions: NOT NULL → nullable 로 변경
ALTER TABLE online_note_sessions ALTER COLUMN student_id DROP NOT NULL;

-- study_logs: NOT NULL → nullable 로 변경
ALTER TABLE study_logs           ALTER COLUMN student_id DROP NOT NULL;


-- ──────────────────────────────────────────────────────────────────
-- 완료 확인 — rls_enabled 가 모두 false 이면 성공
-- ──────────────────────────────────────────────────────────────────
SELECT
  tablename,
  rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'wrong_notes','word_cache','quiz_sessions','quiz_results',
    'exam_sets','exam_results','secret_notes','past_problems',
    'weakness_profile','grammar_points','question_bank',
    'question_wrong_notes','online_note_sessions','study_logs'
  )
ORDER BY tablename;
