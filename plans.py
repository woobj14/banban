# plans.py — 반반 BanBan 요금제 정의 + 기능 잠금 헬퍼
# ─────────────────────────────────────────────────────────────────
# FREE    : 무료 (기본)
# STUDENT : 4,900원/월 — 학생 개인
# PRO     : 19,900원/월 — 선생님·공부방·학원
# admin   : 항상 PRO 취급

import os
import streamlit as st
from datetime import datetime

# ── Polar 결제 링크 ───────────────────────────────────────────────
CHECKOUT_STUDENT = os.environ.get(
    "POLAR_CHECKOUT_STUDENT",
    "https://buy.polar.sh/polar_cl_jT51tKXc6vp2cD9I4aBTqZVLCTcIhwHzrJtWq4PbBsx",
)
CHECKOUT_PRO = os.environ.get(
    "POLAR_CHECKOUT_PRO",
    "https://buy.polar.sh/polar_cl_09hv7yvmPfDSKDkjeoWkldxcDLOyuX7BhETyC49Xpkv",
)

def checkout_url(plan: str) -> str:
    """플랜별 Polar 체크아웃 URL."""
    return CHECKOUT_PRO if plan == "pro" else CHECKOUT_STUDENT

# ── 플랜 계층 순서 (낮을수록 낮은 등급) ──────────────────────────
_RANK = {"free": 0, "student": 1, "pro": 2}

# ── 플랜별 한도 ───────────────────────────────────────────────────
LIMITS = {
    "free": {
        "ai_per_month":    10,
        "print_per_month": 3,
        "max_students":    5,
    },
    "student": {
        "ai_per_month":    9999,
        "print_per_month": 10,
        "max_students":    0,   # 학생 플랜은 관리 학생 없음
    },
    "pro": {
        "ai_per_month":    9999,
        "print_per_month": 9999,
        "max_students":    9999,
    },
}

# ── PRO 전용 기능 설명 (업그레이드 모달에서 사용) ─────────────────
PRO_FEATURES = [
    "AI 문제 생성 무제한",
    "반반노트 출력 무제한 + 배치 출력",
    "정답지 동시 생성",
    "학생 관리 무제한",
    "학부모 리포트",
    "약점 처방전 AI 분석",
    "문제뱅크 전체 접근",
]

STUDENT_FEATURES = [
    "AI 문제 생성 무제한",
    "반반노트 출력 월 10회",
    "약점 처방전 AI 분석",
    "문제뱅크 전체 접근",
]


def current_plan() -> str:
    """현재 로그인 사용자의 플랜 ('free'|'student'|'pro').
    admin(서비스 운영자)만 항상 'pro'. 선생님·학생은 실제 결제 플랜을 따름.
    Supabase 미설정·비로그인 시 'free' 반환. 플랜 만료 확인 포함.
    """
    role = st.session_state.get("sb_role", "")
    if role == "admin":
        # 서비스 운영자(관리자)만 무조건 pro
        return "pro"

    plan = st.session_state.get("sb_plan", "free") or "free"

    # 만료 확인
    expires = st.session_state.get("sb_plan_expires")
    if expires and plan != "free":
        try:
            exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if datetime.now().astimezone() > exp_dt:
                return "free"
        except Exception:
            pass

    return plan if plan in _RANK else "free"


def has_plan(required: str) -> bool:
    """현재 플랜이 required 이상인지."""
    return _RANK.get(current_plan(), 0) >= _RANK.get(required, 0)


def get_limit(key: str) -> int:
    """현재 플랜의 한도값 반환."""
    return LIMITS.get(current_plan(), LIMITS["free"]).get(key, 0)


# ── AI 사용량 카운터 (Supabase) ───────────────────────────────────

def get_ai_usage() -> int:
    """이번 달 AI 사용 횟수 조회."""
    try:
        from supabase_client import get_supabase
        import auth as _auth
        user = _auth.current_user()
        if not user:
            return 0
        ym = datetime.now().strftime("%Y-%m")
        r = get_supabase().table("ai_usage") \
            .select("count").eq("user_id", user.id).eq("year_month", ym).execute()
        return (r.data[0]["count"] if r.data else 0)
    except Exception:
        return 0


def increment_ai_usage() -> int:
    """AI 사용 1회 증가. 증가 후 카운트 반환."""
    try:
        from supabase_client import get_supabase
        import auth as _auth
        user = _auth.current_user()
        if not user:
            return 0
        ym  = datetime.now().strftime("%Y-%m")
        sb  = get_supabase()
        row = sb.table("ai_usage").select("id,count") \
                .eq("user_id", user.id).eq("year_month", ym).execute()
        if row.data:
            new_cnt = row.data[0]["count"] + 1
            sb.table("ai_usage").update({"count": new_cnt, "updated_at": "now()"}) \
              .eq("id", row.data[0]["id"]).execute()
        else:
            new_cnt = 1
            sb.table("ai_usage").insert(
                {"user_id": user.id, "year_month": ym, "count": 1}
            ).execute()
        return new_cnt
    except Exception:
        return 0


def can_use_ai() -> tuple[bool, int, int]:
    """AI 사용 가능 여부. (가능여부, 현재사용, 한도)"""
    if has_plan("student"):      # student 이상은 무제한
        return True, 0, 9999
    limit = get_limit("ai_per_month")
    used  = get_ai_usage()
    return used < limit, used, limit


# ── 출력 사용량 카운터 ────────────────────────────────────────────

def get_print_usage() -> int:
    try:
        from supabase_client import get_supabase
        import auth as _auth
        user = _auth.current_user()
        if not user:
            return 0
        ym = datetime.now().strftime("%Y-%m")
        r = get_supabase().table("print_usage") \
            .select("count").eq("user_id", user.id).eq("year_month", ym).execute()
        return (r.data[0]["count"] if r.data else 0)
    except Exception:
        return 0


def increment_print_usage() -> int:
    try:
        from supabase_client import get_supabase
        import auth as _auth
        user = _auth.current_user()
        if not user:
            return 0
        ym  = datetime.now().strftime("%Y-%m")
        sb  = get_supabase()
        row = sb.table("print_usage").select("id,count") \
                .eq("user_id", user.id).eq("year_month", ym).execute()
        if row.data:
            new_cnt = row.data[0]["count"] + 1
            sb.table("print_usage").update({"count": new_cnt, "updated_at": "now()"}) \
              .eq("id", row.data[0]["id"]).execute()
        else:
            new_cnt = 1
            sb.table("print_usage").insert(
                {"user_id": user.id, "year_month": ym, "count": 1}
            ).execute()
        return new_cnt
    except Exception:
        return 0


def can_print() -> tuple[bool, int, int]:
    if has_plan("pro"):
        return True, 0, 9999
    limit = get_limit("print_per_month")
    used  = get_print_usage()
    return used < limit, used, limit


# ── UI 헬퍼 ──────────────────────────────────────────────────────

def upgrade_banner(required: str = "pro", compact: bool = False) -> None:
    """업그레이드 유도 배너 (기능 잠금 시 표시)."""
    from icons import icon

    url        = checkout_url(required)
    plan_label = {"student": "STUDENT 4,900원/월", "pro": "PRO 19,900원/월"}.get(required, "유료 플랜")
    features   = STUDENT_FEATURES if required == "student" else PRO_FEATURES

    if compact:
        st.markdown(
            f'<div style="background:#EEF2FF;border:1px solid #C7D2FE;border-radius:10px;'
            f'padding:10px 14px;font-size:0.84rem;color:#4338CA;'
            f'display:flex;align-items:center;justify-content:space-between;gap:8px;">'
            f'<span>{icon("lock",14,"#4338CA")} 이 기능은 <b>{plan_label}</b>에서 사용 가능해요.</span>'
            f'<a href="{url}" target="_blank" style="background:#4F46E5;color:white;'
            f'border-radius:8px;padding:5px 14px;font-size:0.8rem;font-weight:700;'
            f'text-decoration:none;white-space:nowrap;">업그레이드 →</a>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;padding:5px 0;">'
        f'{icon("check-circle",15,"#4F46E5")}'
        f'<span style="font-size:0.86rem;color:#374151;">{f}</span></div>'
        for f in features
    )
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);'
        f'border:1px solid #C7D2FE;border-radius:16px;padding:22px 24px;margin:12px 0;">'
        f'<div style="font-size:1rem;font-weight:800;color:#4338CA;margin-bottom:12px;">'
        f'{icon("lock",18,"#4338CA")} {plan_label} 전용 기능입니다</div>'
        f'{rows}'
        f'<a href="{url}" target="_blank" style="display:block;margin-top:16px;'
        f'background:linear-gradient(135deg,#4F46E5,#6366F1);color:white;'
        f'border-radius:10px;padding:12px;text-align:center;'
        f'font-weight:800;font-size:0.95rem;text-decoration:none;">'
        f'지금 결제하기 (Polar) →</a>'
        f'</div>',
        unsafe_allow_html=True,
    )


def ai_usage_bar() -> None:
    """FREE 플랜: 이번 달 AI 사용량 바 표시."""
    if has_plan("student"):
        return
    ok, used, limit = can_use_ai()
    pct = int(used / limit * 100) if limit else 0
    color = "#16A34A" if pct < 70 else "#D97706" if pct < 90 else "#DC2626"
    st.markdown(
        f'<div style="font-size:0.78rem;color:#64748B;margin-bottom:4px;">'
        f'이번 달 AI 사용 <b style="color:{color};">{used}/{limit}회</b>'
        f'{" — 한도 도달! PRO로 업그레이드하세요" if not ok else ""}</div>'
        f'<div style="background:#E2E8F0;border-radius:4px;height:5px;margin-bottom:10px;">'
        f'<div style="background:{color};width:{min(pct,100)}%;height:100%;border-radius:4px;"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )
