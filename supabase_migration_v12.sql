-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v12 — 노트 하이브리드 소유권 모델
--   · owner_id    : 제작자(선생님). 편집·삭제는 owner만.
--   · visibility  : 'private'(나+내 학생) | 'public'(공용 자료실)
--   기본은 비공개, 선생님이 원하면 공용 자료실에 공개.
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- visibility 컬럼 추가 (owner_id는 v11에서 이미 존재)
ALTER TABLE notes
    ADD COLUMN IF NOT EXISTS visibility text DEFAULT 'private';  -- 'private' | 'public'

CREATE INDEX IF NOT EXISTS idx_notes_owner      ON notes (owner_id);
CREATE INDEX IF NOT EXISTS idx_notes_visibility ON notes (visibility);

-- ───────────────────────────────────────────────────────────────────
-- 기존 노트 11개 백필: 제작자 = 우병진(관리자), 공개 = public (기존처럼 모두 보이게)
-- ───────────────────────────────────────────────────────────────────
UPDATE notes
   SET owner_id = (SELECT id FROM auth.users
                    WHERE email = 'globutterspark@gmail.com' LIMIT 1)
 WHERE owner_id IS NULL;

UPDATE notes
   SET visibility = 'public'
 WHERE visibility IS NULL OR visibility = 'private';
