# supabase_client.py — Supabase 클라이언트 싱글톤
# 반반 BanBan: 모든 DB 작업은 이 모듈을 통해 Supabase에 연결합니다.

import os
from functools import lru_cache
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Supabase 클라이언트 싱글톤 (앱 전체에서 재사용)"""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL 및 SUPABASE_ANON_KEY를 .env 파일에 설정하세요.\n"
            "Supabase 대시보드 > Project Settings > API에서 확인할 수 있습니다."
        )
    return create_client(url, key)


def is_supabase_configured() -> bool:
    """Supabase 환경변수가 설정되어 있는지 확인"""
    return bool(
        os.environ.get("SUPABASE_URL") and
        os.environ.get("SUPABASE_ANON_KEY")
    )
