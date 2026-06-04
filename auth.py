# auth.py — 반반 BanBan 인증 헬퍼
# 이메일 로그인 / 회원가입(학생/선생님) / 로그아웃 / 비밀번호 변경 / 회원 탈퇴

import os
import re
import uuid
import streamlit as st
from supabase_client import get_supabase

# 이메일 인증 후 돌아올 URL — .env의 SITE_URL 우선, 없으면 로컬 기본값
_SITE_URL = os.environ.get("SITE_URL", "http://localhost:8502")


# ─────────────────────────────────────────────────────────────────────────────
# 비밀번호 정책 검사
# ─────────────────────────────────────────────────────────────────────────────

PW_POLICY = {
    "min_length": 8,
    "require_upper":   True,   # 영문 대문자
    "require_lower":   True,   # 영문 소문자
    "require_digit":   True,   # 숫자
    "require_special": True,   # 특수문자
}

_SPECIAL_CHARS = r"!@#$%^&*()_\-+=\[\]{};':\"\\|,.<>\/?`~"


def validate_password(pw: str) -> list[str]:
    """비밀번호 정책 검사 → 위반 항목 메시지 리스트 (빈 리스트 = 통과)"""
    errors: list[str] = []
    if len(pw) < PW_POLICY["min_length"]:
        errors.append(f"최소 {PW_POLICY['min_length']}자 이상")
    if PW_POLICY["require_upper"] and not re.search(r"[A-Z]", pw):
        errors.append("영문 대문자 포함 (A-Z)")
    if PW_POLICY["require_lower"] and not re.search(r"[a-z]", pw):
        errors.append("영문 소문자 포함 (a-z)")
    if PW_POLICY["require_digit"] and not re.search(r"[0-9]", pw):
        errors.append("숫자 포함 (0-9)")
    if PW_POLICY["require_special"] and not re.search(rf"[{_SPECIAL_CHARS}]", pw):
        errors.append("특수문자 포함 (!@#$%^&* 등)")
    return errors


def password_strength_label(pw: str) -> tuple[str, str]:
    """비밀번호 강도 → (라벨, 색상)"""
    errors = validate_password(pw)
    n = len(errors)
    if n == 0:   return "강함 ✅", "#16a34a"
    if n <= 2:   return "보통 ⚠️", "#ca8a04"
    return "약함 ❌", "#dc2626"


# ─────────────────────────────────────────────────────────────────────────────
# 세션 복원 & 상태 조회
# ─────────────────────────────────────────────────────────────────────────────

def restore_session() -> bool:
    """페이지 리로드 시 Supabase 세션 복원. 로그인 상태면 True."""
    saved = st.session_state.get("sb_session")
    if not saved:
        return False
    try:
        sb = get_supabase()
        sb.auth.set_session(saved["access_token"], saved["refresh_token"])
        resp = sb.auth.get_user()
        if resp and resp.user:
            st.session_state["sb_user"] = resp.user
            return True
    except Exception:
        pass
    # 세션 만료
    for key in ("sb_session", "sb_user", "sb_student_id",
                "sb_student_name", "sb_role"):
        st.session_state.pop(key, None)
    return False


def is_logged_in() -> bool:
    return "sb_user" in st.session_state


def current_user():
    """현재 Supabase User 객체 (없으면 None)"""
    return st.session_state.get("sb_user")


def current_student_id() -> int | None:
    return st.session_state.get("sb_student_id")


def current_student_name() -> str:
    return st.session_state.get("sb_student_name", "")


def current_role() -> str:
    return st.session_state.get("sb_role", "student")


def current_grade() -> str:
    """로그인 학생의 학년 반환 (예: '중2'). 없으면 빈 문자열."""
    return st.session_state.get("sb_grade", "")


# ─────────────────────────────────────────────────────────────────────────────
# 로그인
# ─────────────────────────────────────────────────────────────────────────────

def sign_in(email_or_username: str, password: str) -> tuple[bool, str]:
    """이메일 또는 학생 아이디로 로그인. → (성공, 에러메시지)

    - '@' 포함 → 이메일 그대로 사용
    - '@' 미포함 → 학생 아이디: '{username}@students.banban.app' 변환
    """
    # 학생 아이디 자동 감지 (영문+숫자, @ 없음)
    if "@" not in email_or_username:
        username = email_or_username.strip().lower()
        email = f"{username}@students.banban.app"
    else:
        email = email_or_username.strip()

    try:
        sb = get_supabase()
        result = sb.auth.sign_in_with_password({"email": email, "password": password})
        session = result.session
        user    = result.user
        if not session:
            return False, "로그인 실패: 세션을 가져올 수 없습니다."

        # 세션 저장
        st.session_state["sb_session"] = {
            "access_token":  session.access_token,
            "refresh_token": session.refresh_token,
        }
        st.session_state["sb_user"] = user

        # 프로필 로드
        _load_profile(user.id)
        return True, ""

    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "이메일 또는 비밀번호가 올바르지 않습니다."
        if "Email not confirmed" in msg:
            return False, "이메일 인증을 완료해주세요. 받은 편지함을 확인하세요."
        return False, f"로그인 오류: {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# 회원가입
# ─────────────────────────────────────────────────────────────────────────────

def sign_up(email: str, password: str,
            name: str, grade: str = "") -> tuple[bool, str]:
    """회원가입. → (성공, 메시지)"""
    if not name.strip():
        return False, "이름을 입력해주세요."
    errors = validate_password(password)
    if errors:
        return False, "비밀번호 조건 미충족: " + " / ".join(errors)

    try:
        sb = get_supabase()
        result = sb.auth.sign_up({
            "email":    email,
            "password": password,
            "options":  {
                "data":        {"name": name.strip(), "grade": grade},
                "email_redirect_to": _SITE_URL,
            },
        })
        if result.user:
            confirmed = result.user.email_confirmed_at
            if confirmed:
                # 즉시 확인 (이메일 인증 비활성화된 경우)
                _ensure_profile(result.user.id, email, name.strip(), grade)
                return True, "회원가입 완료! 로그인해주세요."
            else:
                return True, (
                    f"가입 완료! {email}로 인증 메일을 보냈습니다.\n"
                    "이메일을 확인하고 링크를 클릭한 후 로그인해주세요."
                )
        return False, "회원가입 실패: 사용자를 생성할 수 없습니다."

    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return False, "이미 가입된 이메일 주소입니다."
        if "Password should be" in msg:
            return False, "비밀번호는 최소 6자 이상이어야 합니다."
        return False, f"가입 오류: {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# 초대코드 검증
# ─────────────────────────────────────────────────────────────────────────────

def validate_invite_code(code: str) -> tuple[bool, str, str, str]:
    """초대코드 유효성 검증.
    → (valid: bool, teacher_name: str, class_label: str, error_msg: str)
    """
    if not code.strip():
        return False, "", "", "코드를 입력해주세요."
    try:
        sb = get_supabase()
        # profiles join 제거 — invite_codes.teacher_id는 auth.users 참조
        result = sb.table("invite_codes") \
            .select("code, teacher_id, label, max_uses, current_uses, expires_at") \
            .eq("code", code.strip().upper()) \
            .execute()
        if not result.data:
            return False, "", "", "유효하지 않은 초대 코드입니다."

        c = result.data[0]

        # 만료 확인
        if c.get("expires_at"):
            from datetime import datetime, timezone
            exp = datetime.fromisoformat(c["expires_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                return False, "", "", "만료된 초대 코드입니다."

        # 최대 사용 횟수 확인
        if c["current_uses"] >= c["max_uses"]:
            return False, "", "", "사용 횟수가 초과된 코드입니다."

        # 선생님 이름: profiles 테이블에서 teacher_id로 별도 조회
        teacher_name = "반반쌤"
        try:
            t_res = sb.table("profiles") \
                .select("name") \
                .eq("id", c["teacher_id"]) \
                .single().execute()
            if t_res.data and t_res.data.get("name"):
                teacher_name = t_res.data["name"]
        except Exception:
            pass

        return True, teacher_name, c.get("label", ""), ""

    except Exception as e:
        return False, "", "", f"코드 확인 오류: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 학생 가입 (초대코드 기반, 이메일 불필요)
# ─────────────────────────────────────────────────────────────────────────────

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")

def sign_up_student(
    username: str,
    display_name: str,
    password: str,
    invite_code: str = "",
    contact_email: str = "",
    phone: str = "",
) -> tuple[bool, str]:
    """학생 가입. 학생 아이디(username) 기반 로그인.
    - 선생님 코드 입력 O → 선생님 반에 연결, 선생님 플랜을 따라감
    - 선생님 코드 입력 X → 개인 FREE 회원 (결제 시 유료)
    연락처(phone)·실이메일(contact_email)은 선택 입력.
    → (성공, 메시지)
    """
    username = username.strip().lower()

    if not _USERNAME_RE.match(username):
        return False, "학생 아이디는 영문/숫자/밑줄(_), 3~20자만 사용 가능합니다."
    if not display_name.strip():
        return False, "이름을 입력해주세요."
    pw_errors = validate_password(password)
    if pw_errors:
        return False, "비밀번호 조건 미충족: " + " / ".join(pw_errors)

    # 초대코드는 선택 — 입력한 경우에만 검증
    teacher_id  = None
    class_label = ""
    code_clean  = invite_code.strip().upper()
    if code_clean:
        valid, teacher_name, class_label, err = validate_invite_code(code_clean)
        if not valid:
            return False, err

    virtual_email = f"{username}@students.banban.app"

    try:
        sb = get_supabase()

        # 코드 있으면 teacher_id 조회
        if code_clean:
            code_row = sb.table("invite_codes") \
                .select("teacher_id, current_uses, max_uses") \
                .eq("code", code_clean) \
                .single() \
                .execute()
            teacher_id = code_row.data["teacher_id"]

        # Supabase Auth 계정 생성
        result = sb.auth.sign_up({
            "email":    virtual_email,
            "password": password,
            "options":  {
                "data": {
                    "name":        display_name.strip(),
                    "role":        "student",
                    "teacher_id":  teacher_id,
                    "class_label": class_label,
                }
            },
        })

        if not result.user:
            return False, "가입 실패: 계정을 생성할 수 없습니다."

        uid = result.user.id

        # profiles 행 생성/업데이트
        # 코드 없으면 plan='free'(개인), 코드 있으면 로그인 시 선생님 plan을 따라감
        sb.table("profiles").upsert({
            "id":            uid,
            "email":         virtual_email,
            "name":          display_name.strip(),
            "username":      username,
            "role":          "student",
            "teacher_id":    teacher_id,
            "class_label":   class_label,
            "join_code":     code_clean,
            "contact_email": contact_email.strip(),
            "phone":         phone.strip(),
            "plan":          "free",
        }, on_conflict="id").execute()

        # 코드 사용 시 카운트 증가
        if code_clean:
            try:
                sb.rpc("increment_invite_code_use",
                       {"p_code": code_clean}).execute()
            except Exception:
                pass

        if teacher_id:
            return True, (
                f"가입 완료! {display_name.strip()} 학생 환영해요.\n"
                f"선생님 반에 연결되었어요. 로그인: 학생 아이디 [{username}] + 비밀번호"
            )
        return True, (
            f"가입 완료! {display_name.strip()} 학생 환영해요.\n"
            f"개인 회원으로 가입됐어요. 로그인: 학생 아이디 [{username}] + 비밀번호"
        )

    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return False, f"이미 사용 중인 학생 아이디입니다: {username}"
        return False, f"가입 오류: {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# 선생님 가입 (이메일 기반)
# ─────────────────────────────────────────────────────────────────────────────

def sign_up_teacher(
    email: str,
    password: str,
    name: str,
    school: str = "",
) -> tuple[bool, str]:
    """선생님 계정 가입 (이메일+비밀번호). → (성공, 메시지)"""
    if not name.strip():
        return False, "이름을 입력해주세요."
    errors = validate_password(password)
    if errors:
        return False, "비밀번호 조건 미충족: " + " / ".join(errors)
    try:
        sb = get_supabase()
        result = sb.auth.sign_up({
            "email":    email.strip(),
            "password": password,
            "options":  {
                "data": {
                    "name":   name.strip(),
                    "role":   "teacher",
                    "school": school.strip(),
                },
                "email_redirect_to": _SITE_URL,
            },
        })
        if result.user:
            uid       = result.user.id
            confirmed = result.user.email_confirmed_at
            # profiles 생성
            sb.table("profiles").upsert({
                "id":     uid,
                "email":  email.strip(),
                "name":   name.strip(),
                "role":   "teacher",
                "school": school.strip(),
            }, on_conflict="id").execute()

            if confirmed:
                return True, "선생님 계정 가입 완료! 로그인해주세요."
            return True, (
                f"가입 완료! {email}로 인증 메일을 보냈습니다.\n"
                "이메일 링크 클릭 후 로그인하세요."
            )
        return False, "가입 실패"
    except Exception as e:
        msg = str(e)
        if "already registered" in msg or "already been registered" in msg:
            return False, "이미 가입된 이메일입니다."
        return False, f"가입 오류: {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# 학습 이벤트 기록 (학생 → Supabase)
# ─────────────────────────────────────────────────────────────────────────────

def log_learning_event(
    event_type: str,
    module: str,
    score: int | None = None,
    correct: int | None = None,
    total: int | None = None,
    details: dict | None = None,
) -> bool:
    """학습 이벤트를 Supabase learning_events 테이블에 기록.
    로그인된 학생만 기록 (비로그인 / 오류 시 조용히 무시).
    """
    user = current_user()
    if not user:
        return False
    try:
        sb = get_supabase()
        sb.table("learning_events").insert({
            "student_id": user.id,
            "event_type": event_type,
            "module":     module,
            "score":      score,
            "correct":    correct,
            "total":      total,
            "details":    details or {},
        }).execute()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 로그아웃
# ─────────────────────────────────────────────────────────────────────────────

def sign_out():
    """로그아웃 — Supabase 세션 종료 + Streamlit 세션 초기화 + 자동로그인 토큰 삭제"""
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    clear_auto_login()   # localStorage 토큰 삭제
    # 인증 관련 키 제거
    for key in ("sb_session", "sb_user", "sb_student_id",
                "sb_student_name", "sb_role", "study_student"):
        st.session_state.pop(key, None)
    # 학습 진행 중인 세션도 초기화
    for key in ("exam_state", "past_quiz_state", "upload_preview",
                "celebrate_word", "celebrate_word_kr"):
        st.session_state.pop(key, None)


# ─────────────────────────────────────────────────────────────────────────────
# 비밀번호 변경
# ─────────────────────────────────────────────────────────────────────────────

def update_password(new_password: str) -> tuple[bool, str]:
    errors = validate_password(new_password)
    if errors:
        return False, "비밀번호 조건 미충족: " + " / ".join(errors)
    try:
        get_supabase().auth.update_user({"password": new_password})
        return True, "비밀번호가 변경되었습니다."
    except Exception as e:
        return False, f"변경 실패: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 프로필 업데이트 (이름 / 학년)
# ─────────────────────────────────────────────────────────────────────────────

def update_profile(name: str = "", grade: str = "") -> tuple[bool, str]:
    user = current_user()
    if not user:
        return False, "로그인이 필요합니다."
    try:
        sb = get_supabase()
        update_data: dict = {}
        if name.strip():
            update_data["name"]  = name.strip()
        if grade:
            update_data["grade"] = grade
        if update_data:
            sb.table("profiles").update(update_data).eq("id", user.id).execute()
            # session_state 갱신
            if "name" in update_data:
                st.session_state["sb_student_name"] = update_data["name"]
                st.session_state["study_student"]   = update_data["name"]
        return True, "프로필이 업데이트되었습니다."
    except Exception as e:
        return False, f"업데이트 실패: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 회원 탈퇴
# ─────────────────────────────────────────────────────────────────────────────

def delete_account() -> tuple[bool, str]:
    """회원 탈퇴 — SUPABASE_SERVICE_KEY 필요 (.env에 설정)"""
    import os
    from supabase import create_client

    user = current_user()
    if not user:
        return False, "로그인이 필요합니다."

    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not service_key:
        return False, (
            "관리자 키가 설정되지 않았습니다.\n"
            ".env 파일에 SUPABASE_SERVICE_KEY를 추가해주세요."
        )
    try:
        url = os.environ.get("SUPABASE_URL", "")
        admin = create_client(url, service_key)
        admin.auth.admin.delete_user(user.id)
        sign_out()
        return True, "계정이 완전히 삭제되었습니다."
    except Exception as e:
        return False, f"탈퇴 실패: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 비밀번호 재설정 이메일 발송
# ─────────────────────────────────────────────────────────────────────────────

def send_password_reset(email: str) -> tuple[bool, str]:
    try:
        get_supabase().auth.reset_password_email(email)
        return True, f"{email}으로 비밀번호 재설정 이메일을 보냈습니다."
    except Exception as e:
        return False, f"발송 실패: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_profile(uid: str, email: str, name: str, grade: str):
    """profiles 행이 없으면 생성 (신규 사용자)"""
    try:
        sb = get_supabase()
        sb.table("profiles").upsert(
            {"id": uid, "email": email, "name": name, "grade": grade},
            on_conflict="id",
        ).execute()
    except Exception:
        pass


def _load_profile(uid: str):
    """profiles 로드 → session_state에 저장.
    profiles 행이 없거나 role이 비어있으면 user_metadata에서 fallback.
    """
    try:
        sb   = get_supabase()
        user = st.session_state.get("sb_user")
        # user_metadata fallback 값
        meta      = {}
        if user:
            try:
                meta = user.user_metadata or {}
            except Exception:
                meta = {}

        result = sb.table("profiles").select("*").eq("id", uid).single().execute()
        if result.data:
            p    = result.data
            role = p.get("role") or meta.get("role", "student")

            # profiles에 role이 없으면 자동 보정 저장
            if not p.get("role") and role:
                try:
                    sb.table("profiles").update({"role": role}).eq("id", uid).execute()
                except Exception:
                    pass

            st.session_state["sb_student_id"]   = p.get("student_id")
            st.session_state["sb_student_name"] = p.get("name", "") or meta.get("name", "")
            st.session_state["sb_role"]         = role
            st.session_state["sb_teacher_id"]   = p.get("teacher_id")
            st.session_state["sb_class_label"]  = p.get("class_label", "")
            st.session_state["sb_grade"]        = p.get("grade", "") or meta.get("grade", "")
            st.session_state["study_student"]   = p.get("name", "") or meta.get("name", "")
            _own_plan = p.get("plan", "free") or "free"
            _own_exp  = p.get("plan_expires_at")
            # 선생님 코드로 연결된 학생 → 선생님 플랜을 따라감 (동적 상속)
            _t_id = p.get("teacher_id")
            if role == "student" and _t_id:
                try:
                    _t = sb.table("profiles").select("plan, plan_expires_at") \
                           .eq("id", _t_id).single().execute()
                    if _t.data and _t.data.get("plan"):
                        _own_plan = _t.data["plan"]
                        _own_exp  = _t.data.get("plan_expires_at")
                except Exception:
                    pass
            st.session_state["sb_plan"]         = _own_plan
            st.session_state["sb_plan_expires"] = _own_exp
        else:
            # profiles 행 자체가 없으면 metadata로만 세션 구성 + 행 생성 시도
            role = meta.get("role", "student")
            name = meta.get("name", "")
            st.session_state["sb_student_id"]   = None
            st.session_state["sb_student_name"] = name
            st.session_state["sb_role"]         = role
            st.session_state["sb_teacher_id"]   = None
            st.session_state["sb_class_label"]  = ""
            st.session_state["study_student"]   = name
            try:
                user_email = user.email if user else ""
                sb.table("profiles").upsert({
                    "id":    uid,
                    "email": user_email,
                    "name":  name,
                    "role":  role,
                }, on_conflict="id").execute()
            except Exception:
                pass
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 자동 로그인 (Auto-login) — localStorage ↔ Supabase 토큰 브릿지
#
# 흐름:
#   로그인 성공 + "자동 로그인" 체크 → save_auto_login() → 토큰 localStorage 저장
#   다음 방문 → inject_auto_login_check() → JS가 localStorage 토큰을 URL 파람으로 전달
#                → try_restore_from_params() → Supabase 세션 복원 → 자동 로그인 완료
#   로그아웃 → clear_auto_login() → localStorage 토큰 삭제
# ─────────────────────────────────────────────────────────────────────────────

def save_auto_login(access_token: str, refresh_token: str):
    """로그인 성공 시 토큰을 브라우저 localStorage에 저장."""
    import streamlit.components.v1 as _comp
    # 토큰에서 따옴표 이스케이프 (XSS 방지)
    safe_at = access_token.replace("\\", "\\\\").replace("'", "\\'")
    safe_rt = refresh_token.replace("\\", "\\\\").replace("'", "\\'")
    _comp.html(f"""<script>
(function(){{
  try {{
    localStorage.setItem('bb_at','{safe_at}');
    localStorage.setItem('bb_rt','{safe_rt}');
  }} catch(e) {{}}
}})();
</script>""", height=0)


def clear_auto_login():
    """로그아웃 시 localStorage 토큰 삭제."""
    import streamlit.components.v1 as _comp
    _comp.html("""<script>
(function(){
  try {
    localStorage.removeItem('bb_at');
    localStorage.removeItem('bb_rt');
  } catch(e) {}
})();
</script>""", height=0)


def inject_auto_login_check():
    """페이지 로드 시 localStorage 토큰을 URL 파라미터로 전달하는 JS 삽입.
    이미 로그인된 상태거나, 파람이 이미 있으면 아무것도 하지 않음.
    """
    import streamlit.components.v1 as _comp
    _comp.html("""<script>
(function(){
  try {
    var p = new URLSearchParams(window.parent.location.search);
    if (p.has('bb_at')) return;          // 이미 파람 있음
    var at = localStorage.getItem('bb_at');
    var rt = localStorage.getItem('bb_rt');
    if (!at || !rt) return;              // 저장된 토큰 없음
    p.set('bb_at', at);
    p.set('bb_rt', rt);
    window.parent.location.search = p.toString();
  } catch(e) {}
})();
</script>""", height=0)


def try_restore_from_params() -> bool:
    """URL 파라미터에서 토큰을 읽어 Supabase 세션 복원 시도.
    성공 시 True, 실패 시 False 반환.
    """
    try:
        params = st.query_params
        at = params.get("bb_at", "")
        rt = params.get("bb_rt", "")
        if not at or not rt:
            return False

        sb = get_supabase()
        sb.auth.set_session(at, rt)
        resp = sb.auth.get_user()
        if resp and resp.user:
            user    = resp.user
            session = sb.auth.get_session()
            if session:
                st.session_state["sb_session"] = {
                    "access_token":  session.access_token,
                    "refresh_token": session.refresh_token,
                }
                # 토큰 갱신 (localStorage도 새 토큰으로 업데이트)
                save_auto_login(session.access_token, session.refresh_token)
            st.session_state["sb_user"] = user
            _load_profile(user.id)
            # URL에서 토큰 파람 제거 (보안)
            st.query_params.clear()
            return True
    except Exception:
        pass
    # 토큰 무효 → localStorage도 삭제
    st.query_params.clear()
    clear_auto_login()
    return False
