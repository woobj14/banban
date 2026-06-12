# supabase_client.py — Supabase 클라이언트 싱글톤
# 반반 BanBan: 모든 DB 작업은 이 모듈을 통해 Supabase에 연결합니다.

import os
from functools import lru_cache
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Supabase 클라이언트 싱글톤 (앱 전체에서 재사용).

    Streamlit은 서버측(신뢰 환경)이라 service_role 키를 사용 →
    RLS를 전 테이블에 켜도 앱은 정상 작동(우회), 외부 anon 직접 접근은 차단.
    service 키가 없으면 anon으로 폴백.
    사용자 격리는 코드 레벨 필터(owner_id/student_id/teacher_id)로 보장.
    """
    url = os.environ.get("SUPABASE_URL", "")
    key = (os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
           or os.environ.get("SUPABASE_ANON_KEY", "").strip())
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL 및 SUPABASE_SERVICE_KEY(또는 ANON_KEY)를 .env에 설정하세요.\n"
            "Supabase 대시보드 > Project Settings > API에서 확인할 수 있습니다."
        )
    return create_client(url, key)


def is_supabase_configured() -> bool:
    """Supabase 환경변수가 설정되어 있는지 확인"""
    return bool(
        os.environ.get("SUPABASE_URL") and
        (os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
    )
