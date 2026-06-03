-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan — Supabase 마이그레이션 v3 (2026-05-29)
-- 학습 시스템 전체 테이블 (grammar_points, question_bank, wrong_notes 등)
--
-- 실행 방법:
--   Supabase 대시보드 > SQL Editor > 이 내용 전체 붙여넣기 > Run
--
-- ※ 주의: v2 migration (supabase_migration.sql) 을 먼저 실행하세요.
--   v2는 invite_codes, learning_events, profiles 확장을 포함합니다.
-- ═══════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────────────────────────
-- 1. profiles 테이블 추가 컬럼
--    (student_id 정수형, grade, is_active — study_db.py 호환)
-- ──────────────────────────────────────────────────────────────────
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS student_id  SERIAL;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS name        TEXT    DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS grade       TEXT    DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_active   BOOLEAN DEFAULT TRUE;

-- student_id 인덱스 (정수 ID로 빠른 조회)
CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_student_id
  ON profiles(student_id);


-- ──────────────────────────────────────────────────────────────────
-- 2. wrong_notes — 단어 오답노트
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wrong_notes (
  id           BIGINT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id   INT     NOT NULL,       -- profiles.student_id
  note_id      INT     NOT NULL,       -- SQLite notes.id
  word_en      TEXT    NOT NULL,
  word_kr      TEXT    DEFAULT '',
  wrong_count  INT     DEFAULT 1,
  last_wrong   TIMESTAMPTZ DEFAULT NOW(),
  ai_explain   TEXT    DEFAULT '',
  UNIQUE (student_id, note_id, word_en)
);

CREATE INDEX IF NOT EXISTS idx_wrong_notes_student
  ON wrong_notes(student_id, note_id);


-- ──────────────────────────────────────────────────────────────────
-- 3. word_cache — AI 단어 설명 캐시 (글로벌 공유)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS word_cache (
  word_en    TEXT PRIMARY KEY,
  definition TEXT DEFAULT '',
  example    TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ──────────────────────────────────────────────────────────────────
-- 4. quiz_sessions — 단어 퀴즈 세션
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_sessions (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id  INT,
  note_id     INT     NOT NULL,
  quiz_type   TEXT    DEFAULT '',
  started_at  TIMESTAMPTZ DEFAULT NOW(),
  ended_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_quiz_sessions_student
  ON quiz_sessions(student_id, note_id);


-- ──────────────────────────────────────────────────────────────────
-- 5. quiz_results — 퀴즈 개별 문항 결과
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_results (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  session_id  BIGINT  REFERENCES quiz_sessions(id) ON DELETE CASCADE,
  word_en     TEXT    NOT NULL,
  word_kr     TEXT    DEFAULT '',
  user_answer TEXT    DEFAULT '',
  is_correct  BOOLEAN DEFAULT FALSE,
  answered_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quiz_results_session
  ON quiz_results(session_id);


-- ──────────────────────────────────────────────────────────────────
-- 6. exam_sets — 내신문제 세트
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exam_sets (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id  INT,
  note_id     INT     NOT NULL,
  difficulty  TEXT    DEFAULT 'medium',
  questions   JSONB   DEFAULT '[]'::jsonb,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exam_sets_student
  ON exam_sets(student_id, note_id);


-- ──────────────────────────────────────────────────────────────────
-- 7. exam_results — 내신문제 채점 결과
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exam_results (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  exam_set_id BIGINT  REFERENCES exam_sets(id) ON DELETE CASCADE,
  student_id  INT,
  answers     JSONB   DEFAULT '{}'::jsonb,
  score       INT     DEFAULT 0,
  total       INT     DEFAULT 0,
  feedback    TEXT    DEFAULT '',
  taken_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exam_results_student
  ON exam_results(student_id);


-- ──────────────────────────────────────────────────────────────────
-- 8. secret_notes — 비법노트 (AI 인포그래픽)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS secret_notes (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id      INT     NOT NULL,
  title        TEXT    DEFAULT '',
  html_content TEXT    DEFAULT '',
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_secret_notes_note
  ON secret_notes(note_id);


-- ──────────────────────────────────────────────────────────────────
-- 9. past_problems — 기출문제
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS past_problems (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id     INT     NOT NULL,
  source_name TEXT    DEFAULT '',
  problems    JSONB   DEFAULT '[]'::jsonb,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_past_problems_note
  ON past_problems(note_id);


-- ──────────────────────────────────────────────────────────────────
-- 10. weakness_profile — 학생 취약 분석
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weakness_profile (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id  INT     NOT NULL,
  note_id     INT     NOT NULL,
  summary     TEXT    DEFAULT '',
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (student_id, note_id)
);

CREATE INDEX IF NOT EXISTS idx_weakness_student
  ON weakness_profile(student_id, note_id);


-- ──────────────────────────────────────────────────────────────────
-- 11. grammar_points — 문법 포인트 (핵심!)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grammar_points (
  id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id          INT    NOT NULL,
  point_name       TEXT   DEFAULT '',
  category         TEXT   DEFAULT '',
  explanation_kr   TEXT   DEFAULT '',
  patterns         JSONB  DEFAULT '[]'::jsonb,
  examples         JSONB  DEFAULT '[]'::jsonb,
  tip              TEXT   DEFAULT '',
  ai_generated     BOOLEAN DEFAULT TRUE,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_grammar_points_note
  ON grammar_points(note_id);


-- ──────────────────────────────────────────────────────────────────
-- 12. question_bank — 통합 문제 뱅크 (문법 드릴 + 내신 문제)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_bank (
  id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  note_id          INT    NOT NULL,
  source_type      TEXT   DEFAULT 'ai',    -- 'grammar' | 'exam' | 'ai' | 'upload'
  grammar_point_id BIGINT REFERENCES grammar_points(id) ON DELETE SET NULL,
  q_type           TEXT   DEFAULT '',      -- 빈칸완성 | 오류찾기 | 배열하기 | 우리말→영어
  difficulty       TEXT   DEFAULT 'medium',
  question         TEXT   DEFAULT '',
  passage          TEXT   DEFAULT '',
  options          JSONB  DEFAULT '[]'::jsonb,
  answer           TEXT   DEFAULT '',
  answer_kr        TEXT   DEFAULT '',
  used_count       INT    DEFAULT 0,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_question_bank_note
  ON question_bank(note_id, source_type);


-- ──────────────────────────────────────────────────────────────────
-- 13. question_wrong_notes — 문제 오답노트 (내신 + 문법 통합)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS question_wrong_notes (
  id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id        INT    NOT NULL,
  note_id           INT    NOT NULL,
  bank_question_id  BIGINT REFERENCES question_bank(id) ON DELETE SET NULL,
  source_type       TEXT   DEFAULT '',   -- 'grammar' | 'exam' | 'upload'
  question_snapshot JSONB  DEFAULT '{}'::jsonb,
  user_answer       TEXT   DEFAULT '',
  wrong_count       INT    DEFAULT 1,
  last_wrong        TIMESTAMPTZ DEFAULT NOW(),
  ai_explain        TEXT   DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_qwn_student
  ON question_wrong_notes(student_id, note_id);


-- ──────────────────────────────────────────────────────────────────
-- 14. online_note_sessions — 온라인 노트 작성 진도 저장
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS online_note_sessions (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id    INT    NOT NULL,
  note_id       INT    NOT NULL,
  content_type  TEXT   NOT NULL,   -- 'words' | 'dialogue' | 'text'
  item_index    INT    NOT NULL,
  user_input    TEXT   DEFAULT '',
  completed     BOOLEAN DEFAULT FALSE,
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (student_id, note_id, content_type, item_index)
);

CREATE INDEX IF NOT EXISTS idx_online_note_student
  ON online_note_sessions(student_id, note_id, content_type);


-- ──────────────────────────────────────────────────────────────────
-- 15. study_logs — 학습 활동 로그 (대시보드 통계 기반)
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS study_logs (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id   INT    NOT NULL,
  note_id      INT    NOT NULL,
  activity     TEXT   NOT NULL,   -- 'word_quiz' | 'grammar' | 'exam' | 'wrong_note' 등
  score        INT,
  total        INT,
  duration_sec INT    DEFAULT 0,
  details      JSONB  DEFAULT '{}'::jsonb,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_study_logs_student
  ON study_logs(student_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_study_logs_activity
  ON study_logs(student_id, activity, created_at DESC);


-- ──────────────────────────────────────────────────────────────────
-- 16. RLS 정책 — 개발 중: anon + authenticated 모두 전체 접근 허용
--     (정식 오픈 시 student_id 기반 정책으로 교체 예정)
-- ──────────────────────────────────────────────────────────────────

-- wrong_notes
ALTER TABLE wrong_notes          ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_wrong_notes"        ON wrong_notes;
CREATE POLICY "dev_open_wrong_notes"        ON wrong_notes
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- word_cache
ALTER TABLE word_cache           ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_word_cache"         ON word_cache;
CREATE POLICY "dev_open_word_cache"         ON word_cache
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- quiz_sessions
ALTER TABLE quiz_sessions        ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_quiz_sessions"      ON quiz_sessions;
CREATE POLICY "dev_open_quiz_sessions"      ON quiz_sessions
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- quiz_results
ALTER TABLE quiz_results         ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_quiz_results"       ON quiz_results;
CREATE POLICY "dev_open_quiz_results"       ON quiz_results
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- exam_sets
ALTER TABLE exam_sets            ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_exam_sets"          ON exam_sets;
CREATE POLICY "dev_open_exam_sets"          ON exam_sets
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- exam_results
ALTER TABLE exam_results         ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_exam_results"       ON exam_results;
CREATE POLICY "dev_open_exam_results"       ON exam_results
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- secret_notes
ALTER TABLE secret_notes         ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_secret_notes"       ON secret_notes;
CREATE POLICY "dev_open_secret_notes"       ON secret_notes
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- past_problems
ALTER TABLE past_problems        ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_past_problems"      ON past_problems;
CREATE POLICY "dev_open_past_problems"      ON past_problems
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- weakness_profile
ALTER TABLE weakness_profile     ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_weakness_profile"   ON weakness_profile;
CREATE POLICY "dev_open_weakness_profile"   ON weakness_profile
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- grammar_points
ALTER TABLE grammar_points       ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_grammar_points"     ON grammar_points;
CREATE POLICY "dev_open_grammar_points"     ON grammar_points
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- question_bank
ALTER TABLE question_bank        ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_question_bank"      ON question_bank;
CREATE POLICY "dev_open_question_bank"      ON question_bank
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- question_wrong_notes
ALTER TABLE question_wrong_notes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_question_wrong"     ON question_wrong_notes;
CREATE POLICY "dev_open_question_wrong"     ON question_wrong_notes
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- online_note_sessions
ALTER TABLE online_note_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_online_notes"       ON online_note_sessions;
CREATE POLICY "dev_open_online_notes"       ON online_note_sessions
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);

-- study_logs
ALTER TABLE study_logs           ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "dev_open_study_logs"         ON study_logs;
CREATE POLICY "dev_open_study_logs"         ON study_logs
  FOR ALL TO anon, authenticated USING (true) WITH CHECK (true);


-- ──────────────────────────────────────────────────────────────────
-- 17. SQL 함수 (RPC) — study_db.py에서 호출
-- ──────────────────────────────────────────────────────────────────

-- (17-1) 단어 오답 카운터 증가 (upsert 방식)
CREATE OR REPLACE FUNCTION increment_wrong_count(
  p_student_id INT,
  p_note_id    INT,
  p_word_en    TEXT,
  p_word_kr    TEXT DEFAULT ''
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO wrong_notes (student_id, note_id, word_en, word_kr, wrong_count, last_wrong)
  VALUES (p_student_id, p_note_id, p_word_en, p_word_kr, 1, NOW())
  ON CONFLICT (student_id, note_id, word_en)
  DO UPDATE SET
    wrong_count = wrong_notes.wrong_count + 1,
    last_wrong  = NOW(),
    word_kr     = COALESCE(NULLIF(p_word_kr, ''), wrong_notes.word_kr);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- (17-2) 단어 오답 카운터 감소 (0 이하 시 삭제)
CREATE OR REPLACE FUNCTION decrement_wrong_count(
  p_student_id INT,
  p_note_id    INT,
  p_word_en    TEXT
)
RETURNS VOID AS $$
BEGIN
  UPDATE wrong_notes
  SET wrong_count = wrong_count - 1
  WHERE student_id = p_student_id
    AND note_id    = p_note_id
    AND word_en    = p_word_en;

  DELETE FROM wrong_notes
  WHERE student_id  = p_student_id
    AND note_id     = p_note_id
    AND word_en     = p_word_en
    AND wrong_count <= 0;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- (17-3) 취약 분석 upsert
CREATE OR REPLACE FUNCTION upsert_weakness_profile(
  p_student_id INT,
  p_note_id    INT,
  p_summary    TEXT
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO weakness_profile (student_id, note_id, summary, updated_at)
  VALUES (p_student_id, p_note_id, p_summary, NOW())
  ON CONFLICT (student_id, note_id)
  DO UPDATE SET
    summary    = EXCLUDED.summary,
    updated_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- (17-4) 문제 오답노트 추가 (bank_question_id 포함 upsert)
CREATE OR REPLACE FUNCTION add_question_wrong_with_bank(
  p_student_id        INT,
  p_note_id           INT,
  p_bank_question_id  BIGINT,
  p_source_type       TEXT,
  p_question_snapshot JSONB,
  p_user_answer       TEXT
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO question_wrong_notes
    (student_id, note_id, bank_question_id, source_type, question_snapshot, user_answer, wrong_count, last_wrong)
  VALUES
    (p_student_id, p_note_id, p_bank_question_id, p_source_type, p_question_snapshot, p_user_answer, 1, NOW())
  ON CONFLICT DO NOTHING;

  -- 이미 존재하면 카운터 증가
  UPDATE question_wrong_notes
  SET wrong_count = wrong_count + 1,
      last_wrong  = NOW(),
      user_answer = p_user_answer
  WHERE student_id       = p_student_id
    AND bank_question_id = p_bank_question_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- (17-5) 온라인 노트 항목 upsert
CREATE OR REPLACE FUNCTION upsert_online_note_item(
  p_student_id   INT,
  p_note_id      INT,
  p_content_type TEXT,
  p_item_index   INT,
  p_user_input   TEXT,
  p_completed    BOOLEAN DEFAULT FALSE
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO online_note_sessions
    (student_id, note_id, content_type, item_index, user_input, completed, updated_at)
  VALUES
    (p_student_id, p_note_id, p_content_type, p_item_index, p_user_input, p_completed, NOW())
  ON CONFLICT (student_id, note_id, content_type, item_index)
  DO UPDATE SET
    user_input = EXCLUDED.user_input,
    completed  = EXCLUDED.completed,
    updated_at = NOW();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ──────────────────────────────────────────────────────────────────
-- 완료 확인
-- ──────────────────────────────────────────────────────────────────
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'wrong_notes', 'word_cache', 'quiz_sessions', 'quiz_results',
    'exam_sets', 'exam_results', 'secret_notes', 'past_problems',
    'weakness_profile', 'grammar_points', 'question_bank',
    'question_wrong_notes', 'online_note_sessions', 'study_logs'
  )
ORDER BY table_name;
