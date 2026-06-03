-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v4 — 클래스(반) 관리 시스템
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. classes — 선생님이 만든 클래스(반) ──────────────────────────
CREATE TABLE IF NOT EXISTS classes (
    id           BIGSERIAL PRIMARY KEY,
    teacher_id   BIGINT       NOT NULL,   -- profiles.student_id (선생님)
    class_code   VARCHAR(10)  NOT NULL UNIQUE,
    name         TEXT         NOT NULL,
    grade        TEXT         DEFAULT '',
    description  TEXT         DEFAULT '',
    is_active    BOOLEAN      DEFAULT TRUE,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_classes_teacher   ON classes (teacher_id);
CREATE INDEX IF NOT EXISTS idx_classes_code      ON classes (class_code);
CREATE INDEX IF NOT EXISTS idx_classes_active    ON classes (is_active);

-- ── 2. class_members — 클래스 학생 멤버 ───────────────────────────
CREATE TABLE IF NOT EXISTS class_members (
    id          BIGSERIAL PRIMARY KEY,
    class_id    BIGINT      NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    student_id  BIGINT      NOT NULL,
    joined_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (class_id, student_id)
);

CREATE INDEX IF NOT EXISTS idx_class_members_class   ON class_members (class_id);
CREATE INDEX IF NOT EXISTS idx_class_members_student ON class_members (student_id);

-- ── 3. class_notes — 클래스에 배포된 노트 ─────────────────────────
CREATE TABLE IF NOT EXISTS class_notes (
    id          BIGSERIAL PRIMARY KEY,
    class_id    BIGINT      NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    note_id     BIGINT      NOT NULL,
    shared_by   BIGINT      NOT NULL,   -- profiles.student_id (선생님)
    shared_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (class_id, note_id)
);

CREATE INDEX IF NOT EXISTS idx_class_notes_class ON class_notes (class_id);
CREATE INDEX IF NOT EXISTS idx_class_notes_note  ON class_notes (note_id);

-- ── 4. RLS 정책 ────────────────────────────────────────────────────

-- classes
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "classes_select_all" ON classes
    FOR SELECT USING (true);

CREATE POLICY "classes_insert_teacher" ON classes
    FOR INSERT WITH CHECK (true);

CREATE POLICY "classes_update_teacher" ON classes
    FOR UPDATE USING (true);

-- class_members
ALTER TABLE class_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "class_members_select_all" ON class_members
    FOR SELECT USING (true);

CREATE POLICY "class_members_insert_all" ON class_members
    FOR INSERT WITH CHECK (true);

CREATE POLICY "class_members_delete_all" ON class_members
    FOR DELETE USING (true);

-- class_notes
ALTER TABLE class_notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "class_notes_select_all" ON class_notes
    FOR SELECT USING (true);

CREATE POLICY "class_notes_insert_all" ON class_notes
    FOR INSERT WITH CHECK (true);

CREATE POLICY "class_notes_delete_all" ON class_notes
    FOR DELETE USING (true);

-- ── 완료 메시지 ─────────────────────────────────────────────────────
DO $$ BEGIN
  RAISE NOTICE 'Migration v4 완료: classes, class_members, class_notes 테이블 생성됨';
END $$;
