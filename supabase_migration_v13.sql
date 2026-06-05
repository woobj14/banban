-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v13 — 기출문제 출처 구조화 (연도·출판사·학기·시험)
--   자유 입력 출처 → 구조화 메타로 통일성·탐색 확보
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE past_problems
    ADD COLUMN IF NOT EXISTS exam_year text DEFAULT '',   -- 연도 (예: '2024')
    ADD COLUMN IF NOT EXISTS publisher text DEFAULT '',   -- 출판사 (예: 'YBM')
    ADD COLUMN IF NOT EXISTS semester  text DEFAULT '',   -- 학기 (예: '1학기')
    ADD COLUMN IF NOT EXISTS exam_type text DEFAULT '';   -- 시험 (예: '중간고사')

-- 탐색(필터) 가속
CREATE INDEX IF NOT EXISTS idx_pp_year      ON past_problems (exam_year);
CREATE INDEX IF NOT EXISTS idx_pp_semester  ON past_problems (semester);
CREATE INDEX IF NOT EXISTS idx_pp_exam_type ON past_problems (exam_type);

-- 비고: source_name(조합 문자열)은 그대로 유지(표시·하위호환).
--       기존 행의 메타는 빈 값 → 저장된 기출 '수정' 기능으로 정리 가능.
