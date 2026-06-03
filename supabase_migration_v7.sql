-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v7 — 문법 포인트 학습 활성/비활성 토글
-- Supabase SQL Editor에서 실행하세요.
-- (실행 전에도 앱은 동작하지만, 비활성 토글 기능은 이 컬럼이 있어야 작동)
-- ═══════════════════════════════════════════════════════════════════

-- 문법 포인트에 '학습 포함 여부' 컬럼 추가
ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- 기존 행은 모두 활성으로 간주 (DEFAULT TRUE)
UPDATE grammar_points SET is_active = TRUE WHERE is_active IS NULL;
