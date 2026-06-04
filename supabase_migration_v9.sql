-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v9 — 방문자 세그먼트 집계 (랜딩 → 진입 팝업)
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- 방문자가 진입 시 선택한 세그먼트(학생/선생님 + 학년) 익명 집계
CREATE TABLE IF NOT EXISTS visitor_segments (
    id          BIGSERIAL PRIMARY KEY,
    role        TEXT        NOT NULL DEFAULT '',   -- 'student' | 'teacher'
    level       TEXT        NOT NULL DEFAULT '',   -- '중1'~'고3' | '기타' | 자유입력
    user_id     UUID,                              -- 로그인 사용자면 연결 (없으면 null)
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visitor_seg_role  ON visitor_segments (role);
CREATE INDEX IF NOT EXISTS idx_visitor_seg_date  ON visitor_segments (created_at);

-- 익명 방문자도 INSERT 가능하도록 RLS 설정
ALTER TABLE visitor_segments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "visitor_seg_insert" ON visitor_segments;
DROP POLICY IF EXISTS "visitor_seg_select" ON visitor_segments;

-- 누구나(익명 포함) 삽입 가능
CREATE POLICY "visitor_seg_insert" ON visitor_segments
    FOR INSERT WITH CHECK (true);

-- 조회는 인증 사용자만 (관리자 분석용)
CREATE POLICY "visitor_seg_select" ON visitor_segments
    FOR SELECT USING (auth.role() = 'authenticated');
