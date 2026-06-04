-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v10 — 학생 가입 개편 (이메일·연락처 + 선택적 코드)
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- profiles에 연락처·실이메일 컬럼 추가
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS phone        TEXT DEFAULT '',   -- 연락처 (선택)
    ADD COLUMN IF NOT EXISTS contact_email TEXT DEFAULT '';  -- 실제 이메일 (선택, 학부모 리포트·복구용)

-- 비고:
--  - 학생 로그인은 기존대로 학생 아이디(username) 기반 가상 이메일 사용
--  - contact_email/phone 은 연락·리포트·복구용 부가 정보 (선택 입력)
--  - 선생님 코드 없이 가입한 학생은 teacher_id = NULL → plan = 'free' (개인)
--  - 선생님 코드로 가입한 학생은 teacher_id 연결 → 로그인 시 선생님 plan을 따라감
