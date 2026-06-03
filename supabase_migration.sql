-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan — Supabase 마이그레이션 v2 (2026-05-28)
-- 초대코드 + 학생-선생님 연결 + 학습 이벤트 트래킹
--
-- 실행 방법:
--   Supabase 대시보드 > SQL Editor > 이 내용 전체 붙여넣기 > Run
-- ═══════════════════════════════════════════════════════════════════


-- ──────────────────────────────────────────────────────────────────
-- 1. profiles 테이블 확장
--    (teacher_id, class_label, join_code, username, school 추가)
-- ──────────────────────────────────────────────────────────────────
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS teacher_id   UUID REFERENCES auth.users(id);
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS class_label  TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS join_code    TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS school       TEXT DEFAULT '';
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS username     TEXT UNIQUE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS role         TEXT DEFAULT 'student';


-- ──────────────────────────────────────────────────────────────────
-- 2. 초대 코드 테이블
--    선생님이 생성 → 학생이 가입 시 사용
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invite_codes (
  code          TEXT        PRIMARY KEY,
  teacher_id    UUID        REFERENCES auth.users(id) NOT NULL,
  label         TEXT        DEFAULT '',
  max_uses      INT         DEFAULT 40,
  current_uses  INT         DEFAULT 0,
  expires_at    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);


-- ──────────────────────────────────────────────────────────────────
-- 3. 학습 이벤트 테이블
--    학생 학습 행동 로그 → 선생님 대시보드 분석 기반
-- ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS learning_events (
  id          UUID        DEFAULT GEN_RANDOM_UUID() PRIMARY KEY,
  student_id  UUID        REFERENCES auth.users(id) NOT NULL,
  event_type  TEXT        NOT NULL,
  module      TEXT        NOT NULL,
  score       INT,
  correct     INT,
  total       INT,
  details     JSONB       DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- event_type 참고:
--   'vocab_quiz'        : 단어 퀴즈 완료
--   'grammar_view'      : 문법 학습 조회
--   'exam_complete'     : 내신 시험 완료
--   'wrong_note_view'   : 오답노트 조회
--   'secret_note_view'  : 비법노트 조회
--   'upload_quiz'       : 기출문제 풀기


-- ──────────────────────────────────────────────────────────────────
-- 4. 인덱스 (조회 성능 최적화)
-- ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_learning_events_student
  ON learning_events(student_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_learning_events_module
  ON learning_events(module, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_profiles_teacher
  ON profiles(teacher_id);

CREATE INDEX IF NOT EXISTS idx_profiles_username
  ON profiles(username);


-- ──────────────────────────────────────────────────────────────────
-- 5. Row Level Security (RLS) 정책
-- ──────────────────────────────────────────────────────────────────

ALTER TABLE invite_codes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_events ENABLE ROW LEVEL SECURITY;

-- invite_codes: 선생님 본인 코드 전체 관리
DROP POLICY IF EXISTS "teacher_full_access_codes"  ON invite_codes;
CREATE POLICY "teacher_full_access_codes" ON invite_codes
  FOR ALL USING (auth.uid() = teacher_id);

-- invite_codes: 가입 시 코드 검증 (anon 포함 누구나 읽기)
DROP POLICY IF EXISTS "anyone_can_read_codes" ON invite_codes;
CREATE POLICY "anyone_can_read_codes" ON invite_codes
  FOR SELECT USING (true);

-- learning_events: 학생 본인 삽입
DROP POLICY IF EXISTS "student_insert_own_events" ON learning_events;
CREATE POLICY "student_insert_own_events" ON learning_events
  FOR INSERT WITH CHECK (auth.uid() = student_id);

-- learning_events: 학생 본인 조회
DROP POLICY IF EXISTS "student_read_own_events" ON learning_events;
CREATE POLICY "student_read_own_events" ON learning_events
  FOR SELECT USING (auth.uid() = student_id);

-- learning_events: 선생님 → 자기 학생 데이터 조회
DROP POLICY IF EXISTS "teacher_read_student_events" ON learning_events;
CREATE POLICY "teacher_read_student_events" ON learning_events
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM profiles p
      WHERE p.id = learning_events.student_id
        AND p.teacher_id = auth.uid()
    )
  );


-- ──────────────────────────────────────────────────────────────────
-- 6. 헬퍼 함수: 선생님 초대코드 자동 생성
-- ──────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION generate_invite_code(
  p_teacher_id UUID,
  p_label      TEXT DEFAULT ''
)
RETURNS TEXT AS $$
DECLARE
  v_code  TEXT;
  v_chars TEXT := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  v_i     INT;
BEGIN
  LOOP
    v_code := 'BB-';
    FOR v_i IN 1..6 LOOP
      v_code := v_code || substr(v_chars,
                  floor(random() * length(v_chars) + 1)::int, 1);
    END LOOP;
    BEGIN
      INSERT INTO invite_codes(code, teacher_id, label)
      VALUES (v_code, p_teacher_id, p_label);
      RETURN v_code;
    EXCEPTION WHEN unique_violation THEN
      -- 충돌 시 재시도
    END;
  END LOOP;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ──────────────────────────────────────────────────────────────────
-- 7. 헬퍼 함수: 초대코드 사용 횟수 증가 (atomic)
-- ──────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION increment_invite_code_use(p_code TEXT)
RETURNS VOID AS $$
BEGIN
  UPDATE invite_codes
  SET    current_uses = current_uses + 1
  WHERE  code = p_code
    AND  current_uses < max_uses;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ──────────────────────────────────────────────────────────────────
-- 완료 확인
-- ──────────────────────────────────────────────────────────────────
SELECT
  'invite_codes'    AS table_name, count(*) AS rows FROM invite_codes
UNION ALL
SELECT
  'learning_events' AS table_name, count(*) AS rows FROM learning_events;
