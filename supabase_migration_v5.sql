-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v5 — 망각 곡선 복습 스케줄러
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- ── review_schedule — SM-2 기반 복습 예약 테이블 ──────────────────
CREATE TABLE IF NOT EXISTS review_schedule (
    id             BIGSERIAL PRIMARY KEY,
    student_id     BIGINT       NOT NULL,
    note_id        BIGINT,                     -- NULL 허용 (문법 포인트 등)
    item_type      VARCHAR(20)  NOT NULL,       -- 'word' | 'grammar' | 'sentence'
    item_key       TEXT         NOT NULL,       -- word_en / grammar_point_id / 문장idx
    item_data      JSONB        DEFAULT '{}',   -- 복습에 필요한 스냅샷 데이터
    -- SM-2 알고리즘 필드
    next_review    DATE         NOT NULL,       -- 다음 복습 날짜
    interval_days  INT          DEFAULT 1,      -- 현재 간격(일)
    repetitions    INT          DEFAULT 0,      -- 성공 반복 횟수
    ease_factor    FLOAT        DEFAULT 2.5,    -- 난이도 계수 (최소 1.3)
    -- 상태
    last_reviewed  DATE,
    is_mastered    BOOLEAN      DEFAULT FALSE,  -- 마스터 여부
    created_at     TIMESTAMPTZ  DEFAULT NOW(),
    updated_at     TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (student_id, item_type, item_key)    -- 중복 스케줄 방지
);

CREATE INDEX IF NOT EXISTS idx_review_student      ON review_schedule (student_id);
CREATE INDEX IF NOT EXISTS idx_review_next         ON review_schedule (next_review);
CREATE INDEX IF NOT EXISTS idx_review_student_due  ON review_schedule (student_id, next_review, is_mastered);

-- ── RLS ───────────────────────────────────────────────────────────
ALTER TABLE review_schedule ENABLE ROW LEVEL SECURITY;

CREATE POLICY "review_select_all" ON review_schedule FOR SELECT USING (true);
CREATE POLICY "review_insert_all" ON review_schedule FOR INSERT WITH CHECK (true);
CREATE POLICY "review_update_all" ON review_schedule FOR UPDATE USING (true);
CREATE POLICY "review_delete_all" ON review_schedule FOR DELETE USING (true);

-- ── 완료 ─────────────────────────────────────────────────────────
DO $$ BEGIN
  RAISE NOTICE 'Migration v5 완료: review_schedule 테이블 생성됨';
END $$;
