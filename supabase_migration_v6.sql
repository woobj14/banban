-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v6 — 학부모 주간 리포트 시스템
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. parent_contacts — 학부모 연락처 ───────────────────────────
CREATE TABLE IF NOT EXISTS parent_contacts (
    id            BIGSERIAL PRIMARY KEY,
    student_id    BIGINT       NOT NULL,          -- profiles.student_id
    parent_name   TEXT         NOT NULL DEFAULT '',
    parent_email  TEXT         NOT NULL,
    relation      VARCHAR(20)  DEFAULT '부모',    -- '부모' | '아버지' | '어머니' | '기타'
    is_active     BOOLEAN      DEFAULT TRUE,
    created_at    TIMESTAMPTZ  DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (student_id, parent_email)
);

CREATE INDEX IF NOT EXISTS idx_parent_student ON parent_contacts (student_id);
CREATE INDEX IF NOT EXISTS idx_parent_email   ON parent_contacts (parent_email);
CREATE INDEX IF NOT EXISTS idx_parent_active  ON parent_contacts (is_active);

-- ── 2. report_logs — 발송 이력 ────────────────────────────────────
CREATE TABLE IF NOT EXISTS report_logs (
    id            BIGSERIAL PRIMARY KEY,
    student_id    BIGINT       NOT NULL,
    parent_email  TEXT         NOT NULL,
    report_week   DATE         NOT NULL,          -- 해당 주 월요일
    sent_at       TIMESTAMPTZ  DEFAULT NOW(),
    status        VARCHAR(20)  DEFAULT 'sent',    -- 'sent' | 'failed'
    error_msg     TEXT         DEFAULT '',
    UNIQUE (student_id, parent_email, report_week)
);

CREATE INDEX IF NOT EXISTS idx_report_student ON report_logs (student_id);
CREATE INDEX IF NOT EXISTS idx_report_week    ON report_logs (report_week);

-- ── 3. RLS ────────────────────────────────────────────────────────
ALTER TABLE parent_contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "parent_select_all" ON parent_contacts FOR SELECT USING (true);
CREATE POLICY "parent_insert_all" ON parent_contacts FOR INSERT WITH CHECK (true);
CREATE POLICY "parent_update_all" ON parent_contacts FOR UPDATE USING (true);
CREATE POLICY "parent_delete_all" ON parent_contacts FOR DELETE USING (true);

ALTER TABLE report_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "report_log_select" ON report_logs FOR SELECT USING (true);
CREATE POLICY "report_log_insert" ON report_logs FOR INSERT WITH CHECK (true);

-- ── 완료 ─────────────────────────────────────────────────────────
DO $$ BEGIN
  RAISE NOTICE 'Migration v6 완료: parent_contacts, report_logs 테이블 생성됨';
END $$;
