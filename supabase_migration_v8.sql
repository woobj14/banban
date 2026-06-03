-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v8 — 요금제(Plan) + AI 사용량 추적
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. profiles에 plan 필드 추가 ────────────────────────────────
-- plan: 'free' | 'student' | 'pro'
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS plan              TEXT    NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS plan_expires_at   TIMESTAMPTZ,          -- null = 무기한
    ADD COLUMN IF NOT EXISTS polar_customer_id TEXT    DEFAULT '',    -- Polar 고객 ID
    ADD COLUMN IF NOT EXISTS polar_sub_id      TEXT    DEFAULT '';    -- Polar 구독 ID

-- ── 2. AI 사용량 추적 테이블 ─────────────────────────────────────
-- 월별 AI 호출 횟수 카운팅 (FREE: 10회/월 한도)
CREATE TABLE IF NOT EXISTS ai_usage (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    year_month   CHAR(7)     NOT NULL,  -- 'YYYY-MM'
    count        INT         NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_ai_usage_user ON ai_usage (user_id, year_month);

-- ── 3. 출력 횟수 추적 테이블 ─────────────────────────────────────
-- 월별 반반노트 출력 횟수 (FREE: 3회, STUDENT: 10회, PRO: 무제한)
CREATE TABLE IF NOT EXISTS print_usage (
    id           BIGSERIAL PRIMARY KEY,
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    year_month   CHAR(7)     NOT NULL,
    count        INT         NOT NULL DEFAULT 0,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, year_month)
);

CREATE INDEX IF NOT EXISTS idx_print_usage_user ON print_usage (user_id, year_month);

-- ── 4. RLS ──────────────────────────────────────────────────────
ALTER TABLE ai_usage    ENABLE ROW LEVEL SECURITY;
ALTER TABLE print_usage ENABLE ROW LEVEL SECURITY;

-- CREATE POLICY 는 IF NOT EXISTS 미지원 → DROP 후 CREATE
DROP POLICY IF EXISTS "ai_usage_self"    ON ai_usage;
DROP POLICY IF EXISTS "print_usage_self" ON print_usage;

CREATE POLICY "ai_usage_self" ON ai_usage
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "print_usage_self" ON print_usage
    FOR ALL USING (auth.uid() = user_id);

-- ── 5. 기존 사용자 plan = 'free' 기본값 보장 ────────────────────
UPDATE profiles SET plan = 'free' WHERE plan IS NULL OR plan = '';

-- ── 6. admin 계정 plan = 'pro' 자동 설정 ────────────────────────
UPDATE profiles SET plan = 'pro' WHERE role = 'admin';
