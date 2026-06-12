-- ═══════════════════════════════════════════════════════════════════
-- 반반 BanBan Migration v17 — RLS 전면 ENABLE (보안 잠금)
--   앱은 service_role 키로 접근(RLS 우회) → 정상 작동
--   anon 키 직접 접근은 차단 → 미성년자 데이터 보호
--
-- ⚠️ 전제: supabase_client가 SERVICE_KEY를 사용 중이어야 함 (코드 반영 완료).
--          .env에 SUPABASE_SERVICE_KEY 설정 필수.
--          배포(Render) 환경변수에도 SUPABASE_SERVICE_KEY 추가할 것!
-- Supabase SQL Editor에서 실행하세요.
-- ═══════════════════════════════════════════════════════════════════

-- public 스키마 전 테이블 RLS ENABLE (정책 없음 → anon/authenticated 차단, service_role 우회)
DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename)
            || ' ENABLE ROW LEVEL SECURITY';
  END LOOP;
END $$;

-- 확인: RLS 켜진 테이블 목록
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' ORDER BY tablename;

-- ───────────────────────────────────────────────────────────────────
-- 롤백 (문제 시): 아래를 실행하면 전 테이블 RLS 다시 OFF
-- DO $$ DECLARE r RECORD; BEGIN
--   FOR r IN SELECT tablename FROM pg_tables WHERE schemaname='public' LOOP
--     EXECUTE 'ALTER TABLE public.'||quote_ident(r.tablename)||' DISABLE ROW LEVEL SECURITY';
--   END LOOP; END $$;
-- ───────────────────────────────────────────────────────────────────
