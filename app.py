# app.py — D.Y. 담당: 반반 BanBan 메인 앱 (반반노트 / 학습센터 / 대시보드)

import os
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from streamlit_option_menu import option_menu

from generator   import generate, generate_combined, sheet_preview
from library     import save_note, list_notes, get_note, delete_note, get_all_values, update_note, duplicate_note, count_my_notes
from sample_data import SAMPLE_WORDS, SAMPLE_DIALOGUES, SAMPLE_TEXT
from icons       import icon, title_md, section_md, confirm_delete_btn, ctype_tag, tag
from study_db    import get_or_create_student, list_students, init_db as study_init_db
from chatbot     import render_chatbot
from plans       import current_plan, has_plan, can_use_ai, upgrade_banner, ai_usage_bar, checkout_url, can_create_note, can_print, increment_print_usage, increment_ai_usage

study_init_db()  # 학습 DB 초기화 (Supabase 전환 후 no-op)

load_dotenv()

# ── Supabase 인증 ─────────────────────────────────────────────────────────────
from supabase_client import is_supabase_configured
import auth as _auth

# ── 개발 모드: 로그인 페이지 임시 비활성화 ─────────────────────────────────────
# 정식 오픈 전 확인용. 배포 시 .env 에서 DEV_SKIP_AUTH=false 로 변경.
_DEV_SKIP_AUTH = os.environ.get("DEV_SKIP_AUTH", "true").lower() == "true"

st.set_page_config(page_title="반반 BanBan", page_icon="📖",
                   layout="wide", initial_sidebar_state="expanded")


# ─────────────────────────────────────────────────────────────────────────────
# 인증 게이트 — Supabase 미설정 시 건너뜀 (로컬 개발 호환)
# ─────────────────────────────────────────────────────────────────────────────

def _render_auth_page():
    """로그인 / 회원가입 / 비밀번호 재설정 페이지 — Light"""

    # ── 밝은 배경 + 전역 라이트 스타일 ──────────────────────────
    st.markdown("""
<style>
.stApp {
  background: #F0F4FF !important;
}
/* 탭 텍스트 라이트 모드 */
.stTabs [data-baseweb="tab"] {
  color: #374151 !important;
  font-weight: 600;
}
.stTabs [aria-selected="true"] {
  color: #4F46E5 !important;
  border-bottom: 2px solid #4F46E5 !important;
}
/* 입력 필드 */
.stTextInput input {
  background: #FFFFFF !important;
  border: 1.5px solid #D1D5DB !important;
  border-radius: 8px !important;
  color: #1F2937 !important;
}
.stTextInput input:focus {
  border-color: #4F46E5 !important;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.1) !important;
}
/* 폼 라벨 */
.stTextInput label, .stSelectbox label { color: #374151 !important; font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

    # ── 헤더 ──────────────────────────────────────────────────────
    st.markdown(f"""
<div style="text-align:center;padding:48px 0 28px;">
  <div style="display:inline-flex;align-items:center;justify-content:center;
       width:64px;height:64px;border-radius:20px;
       background:linear-gradient(135deg,#4F46E5,#6366F1);
       box-shadow:0 8px 28px rgba(79,70,229,0.35);margin-bottom:18px;">
    {icon("book-open", 32, "white")}
  </div>
  <div style="font-size:2.6rem;font-weight:900;letter-spacing:-1.5px;line-height:1.05;
       color:#1E1B4B;">
    반반 <span style="color:#4F46E5;">BanBan</span>
  </div>
  <div style="color:#6B7280;font-size:0.88rem;margin-top:8px;font-weight:500;">
    영어 반반노트 학습 플랫폼
  </div>
</div>
""", unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 1.6, 1])
    with center_col:

        # 흰색 카드 래퍼
        st.markdown("""
<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:20px;
     padding:28px 28px 20px;
     box-shadow:0 4px 24px rgba(79,70,229,0.08),0 1px 3px rgba(0,0,0,0.06);">
""", unsafe_allow_html=True)

        tab_login, tab_signup, tab_reset = st.tabs(["로그인", "회원가입", "비밀번호 재설정"])

        # ── 로그인 탭 ───────────────────────────────────────────
        with tab_login:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            with st.form("login_form"):
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;
     font-size:0.8rem;color:#374151;font-weight:600;">
  {icon("mail", 12, "#4F46E5")} 이메일 또는 학생 아이디
</div>""", unsafe_allow_html=True)
                email = st.text_input("이메일_lbl", label_visibility="collapsed",
                                      placeholder="이메일 또는 학생 아이디 (예: kimj2025)",
                                      key="login_email")
                st.markdown(f"""
<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;margin-top:12px;
     font-size:0.8rem;color:#374151;font-weight:600;">
  {icon("lock", 12, "#4F46E5")} 비밀번호
</div>""", unsafe_allow_html=True)
                password = st.text_input("비밀번호_lbl", label_visibility="collapsed",
                                         type="password", placeholder="비밀번호 입력",
                                         key="login_pw")
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                auto_login = st.checkbox(
                    "자동 로그인 (이 기기에서 자동으로 로그인)",
                    value=True,
                    key="auto_login_check"
                )
                st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button(
                    "로그인", use_container_width=True, type="primary"
                )

            if submitted:
                if not email or not password:
                    st.error("이메일과 비밀번호를 모두 입력해주세요.")
                else:
                    with st.spinner("로그인 중…"):
                        ok, msg = _auth.sign_in(email.strip(), password)
                    if ok:
                        # 자동 로그인 체크 시 토큰을 localStorage에 저장
                        if auto_login:
                            saved = st.session_state.get("sb_session", {})
                            if saved.get("access_token") and saved.get("refresh_token"):
                                _auth.save_auto_login(
                                    saved["access_token"],
                                    saved["refresh_token"]
                                )
                        st.rerun()
                    else:
                        st.error(msg)


        # ── 회원가입 탭 ─────────────────────────────────────────
        with tab_signup:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            sub_student, sub_teacher = st.tabs(["학생 계정", "선생님 계정"])

            # ┌─ 학생 계정 ──────────────────────────────────────┐
            with sub_student:
                st.markdown(f"""
<div style="background:#EEF2FF;border:1px solid #C7D2FE;
     border-radius:10px;padding:10px 14px;font-size:0.8rem;color:#3730A3;
     margin:10px 0 14px;line-height:1.9;">
  {icon("info", 13, "#4F46E5")} <b>학생 가입 방법</b><br>
  {icon("check-circle", 11, "#4F46E5")} 선생님 코드가 <b>없어도</b> 가입할 수 있어요 (개인 회원)<br>
  {icon("check-circle", 11, "#4F46E5")} 선생님 코드를 넣으면 우리 반에 자동 연결돼요<br>
  {icon("check-circle", 11, "#4F46E5")} 학생 아이디는 영문+숫자, 3~20자 (예: kimj2025)
</div>
""", unsafe_allow_html=True)
                with st.form("student_signup_form"):
                    s_username = st.text_input(
                        "학생 아이디 *",
                        placeholder="영문+숫자 (예: kimj2025)",
                        help="로그인 시 사용할 나만의 아이디 — 영문/숫자/밑줄, 3~20자"
                    )
                    s_name = st.text_input("이름 (표시 이름) *", placeholder="홍길동")
                    s_pw = st.text_input("비밀번호 *", type="password",
                                         placeholder="8자 이상, 대소문자+숫자+특수문자")
                    s_code = st.text_input(
                        "선생님 초대 코드 (선택)",
                        placeholder="있으면 입력 (예: BB-ABCD12) · 없으면 비워두세요",
                        help="선생님께 받은 코드가 있으면 입력하세요. 없으면 개인 회원으로 가입돼요."
                    )
                    sc1, sc2 = st.columns(2)
                    s_email = sc1.text_input(
                        "이메일", placeholder="결제·복구·리포트용",
                        help="선생님 코드가 있으면 선택. 없으면(개인 회원) 결제 연동·계정 복구를 위해 필수예요.")
                    s_phone = sc2.text_input(
                        "연락처 (선택)", placeholder="010-0000-0000")
                    st.caption("ℹ️ 선생님 코드가 없는 개인 회원은 결제 연동을 위해 이메일이 필요해요.")
                    s_submitted = st.form_submit_button(
                        "학생 계정 만들기", use_container_width=True, type="primary"
                    )

                if s_submitted:
                    if not s_username.strip():
                        st.error("학생 아이디를 입력해주세요.")
                    elif not s_name.strip():
                        st.error("이름을 입력해주세요.")
                    elif not s_pw:
                        st.error("비밀번호를 입력해주세요.")
                    elif not s_code.strip() and not s_email.strip():
                        # 선생님 코드 없는 개인 회원 → 결제 연동·복구 위해 이메일 필수
                        st.error("선생님 코드가 없는 개인 회원은 이메일을 입력해주세요. "
                                 "결제 연동과 계정 복구에 사용돼요.")
                    else:
                        with st.spinner("가입 처리 중…"):
                            ok, msg = _auth.sign_up_student(
                                s_username.strip(),
                                s_name.strip(),
                                s_pw,
                                invite_code=s_code.strip(),
                                contact_email=s_email.strip(),
                                phone=s_phone.strip(),
                            )
                        if ok:
                            st.success(msg)
                            st.info(f"로그인 탭에서 학생 아이디 [{s_username.strip().lower()}]로 로그인하세요!")
                        else:
                            st.error(msg)

            # ┌─ 선생님 계정 ────────────────────────────────────┐
            with sub_teacher:
                st.markdown(f"""
<div style="background:#F0FDF4;border:1px solid #BBF7D0;
     border-radius:10px;padding:10px 14px;font-size:0.8rem;color:#14532D;
     margin:10px 0 14px;line-height:2.0;">
  {icon("info", 13, "#16A34A")} <b>비밀번호 조건</b><br>
  {icon("check-circle", 11, "#16A34A")} 최소 8자 &nbsp;
  {icon("check-circle", 11, "#16A34A")} 대문자 &nbsp;
  {icon("check-circle", 11, "#16A34A")} 소문자 &nbsp;
  {icon("check-circle", 11, "#16A34A")} 숫자 &nbsp;
  {icon("check-circle", 11, "#16A34A")} 특수문자
</div>
""", unsafe_allow_html=True)
                with st.form("teacher_signup_form"):
                    t_name   = st.text_input("이름", placeholder="박선생")
                    t_school = st.text_input("학교 (선택)", placeholder="반반중학교")
                    t_email  = st.text_input("이메일", placeholder="teacher@school.com")
                    t_pw     = st.text_input("비밀번호", type="password",
                                              placeholder="대소문자+숫자+특수문자, 8자 이상")
                    t_pw2    = st.text_input("비밀번호 확인", type="password")
                    t_submitted = st.form_submit_button(
                        "선생님 계정 만들기", use_container_width=True, type="primary"
                    )

                if t_submitted:
                    if t_pw != t_pw2:
                        st.error("비밀번호가 일치하지 않습니다.")
                    else:
                        errors = _auth.validate_password(t_pw)
                        if errors:
                            for e in errors:
                                st.error(f"• {e}")
                        else:
                            with st.spinner("가입 처리 중…"):
                                ok, msg = _auth.sign_up_teacher(
                                    t_email.strip(), t_pw,
                                    t_name.strip(), t_school.strip(),
                                )
                            if ok:  st.success(msg)
                            else:   st.error(msg)

        # ── 비밀번호 재설정 탭 ──────────────────────────────────
        with tab_reset:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            st.markdown(f"""
<div style="background:#FFFBEB;border:1px solid #FCD34D;
     border-radius:10px;padding:10px 14px;font-size:0.82rem;color:#92400E;margin-bottom:14px;">
  {icon("mail", 13, "#D97706")} 가입 시 사용한 이메일로 재설정 링크를 보내드립니다.
</div>
""", unsafe_allow_html=True)
            with st.form("reset_form"):
                reset_email = st.text_input("이메일", placeholder="student@example.com")
                reset_submitted = st.form_submit_button(
                    "재설정 이메일 발송", use_container_width=True
                )
            if reset_submitted and reset_email:
                ok, msg = _auth.send_password_reset(reset_email.strip())
                if ok:  st.success(msg)
                else:   st.error(msg)

        # 카드 닫기
        st.markdown("</div>", unsafe_allow_html=True)

    # ── 하단 기능 소개 3칸 ─────────────────────────────────────
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    _, feat_col, _ = st.columns([1, 3.2, 1])
    with feat_col:
        fc1, fc2, fc3 = st.columns(3)
        for col, ic_name, bg_color, fg_color, title, desc in [
            (fc1, "zap",         "#EEF2FF", "#4F46E5", "단어학습",  "플래시카드 + 4가지 퀴즈"),
            (fc2, "file-text",   "#F0FDFA", "#0F766E", "내신문제",  "AI 자동 생성 · 즉각 채점"),
            (fc3, "alert-circle","#FEF2F2", "#DC2626", "오답노트",  "틀린 패턴 자동 분석"),
        ]:
            col.markdown(f"""
<div style="background:#FFFFFF;border:1px solid #E5E7EB;
     border-radius:14px;padding:16px 12px;text-align:center;
     box-shadow:0 1px 4px rgba(0,0,0,0.06);">
  <div style="display:flex;justify-content:center;margin-bottom:10px;">
    <div style="width:40px;height:40px;border-radius:12px;
         background:{bg_color};
         display:flex;align-items:center;justify-content:center;">
      {icon(ic_name, 20, fg_color)}
    </div>
  </div>
  <div style="font-size:0.87rem;font-weight:700;color:#1F2937;margin-bottom:4px;">{title}</div>
  <div style="font-size:0.74rem;color:#6B7280;line-height:1.5;">{desc}</div>
</div>
""", unsafe_allow_html=True)


    # ── 푸터 + 관리자 꽃 버튼 ──────────────────────────────────
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)

    # 푸터 텍스트
    st.markdown(
        '<div style="text-align:center;font-size:0.75rem;color:#C4C9D4;margin-bottom:8px;">'
        '© 2026 반반 BanBan &nbsp;·&nbsp; 과장 없는 서비스 &nbsp;·&nbsp; 진심만 담았습니다'
        '</div>',
        unsafe_allow_html=True,
    )

    # 꽃 아이콘 관리자 버튼 — 마커 span + CSS로 버튼 chrome 완전 제거
    flower_svg = icon("flower", 20, "#6366F1")
    st.markdown(f"""
<style>
div:has(span#admflower) + div [data-testid="stButton"] > button {{
  all: unset !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
  cursor: pointer !important;
  opacity: 0.18 !important;
  transition: opacity 0.2s !important;
  padding: 4px !important;
}}
div:has(span#admflower) + div [data-testid="stButton"] > button:hover {{
  opacity: 0.6 !important;
}}
</style>
<span id="admflower" style="display:none;"></span>
""", unsafe_allow_html=True)
    _, c_flower, _ = st.columns([1, 0.15, 1])
    with c_flower:
        st.markdown(flower_svg, unsafe_allow_html=True)
        if st.button("꽃", key="admin_flower_btn", use_container_width=True):
            _admin_quick_login()


def _onboarding_steps(role: str):
    """역할별 온보딩 스텝 정의 — (아이콘, 제목, 설명, [(아이콘, 항목)...])"""
    if role in ("teacher", "admin"):
        return [
            ("party-popper", "반반 BanBan에 오신 것을 환영해요!",
             "교재 제작·학생 관리·AI 분석을 한 곳에서. 3단계만 익히면 바로 수업에 쓸 수 있어요.",
             [("book-open", "라이브러리에서 교재(반반노트) 만들기"),
              ("users", "학생 초대 코드로 우리 반 모으기"),
              ("trending-up", "대시보드로 학습 현황·AI 분석 보기")]),
            ("book-open", "1단계 · 반반노트 만들고 출력하기",
             "왼쪽 '반반노트 관리 → 라이브러리'에서 교재를 만들고, 행의 [출력] 버튼으로 학습지(엑셀·인쇄)를 바로 뽑을 수 있어요.",
             [("plus-circle", "새 노트 추가에서 단어·대화문·본문 입력"),
              ("printer", "라이브러리 → 출력 → 엑셀/인쇄 학습지 생성"),
              ("layers", "여러 노트를 합쳐서 한 번에 다운로드")]),
            ("users", "2단계 · 학생 초대 & 현황 보기",
             "대시보드 → 학생 관리 → 초대 코드 탭에서 코드를 발급해 학생에게 공유하세요. 가입하면 학습 현황이 실시간으로 쌓여요.",
             [("trending-up", "학생 현황 탭 · 7일 학습 히트맵"),
              ("sparkles", "심층 분석 탭 · AI 맞춤 추천"),
              ("mail", "주간 리포트로 학부모 소통")]),
        ]
    return [
        ("party-popper", "반반 BanBan에 오신 걸 환영해요!",
         "영어 내신을 단어 → 문법 → 본문 → 복습까지 한 번에. 딱 3분만 따라와 보세요.",
         [("arrow-counterclockwise", "망각곡선 복습으로 자동 암기"),
          ("volume-2", "원어민 발음으로 듣고 따라하기"),
          ("trophy", "꾸준히 하면 성장 그래프가 쑥쑥")]),
        ("book-open", "1단계 · 학습 시작하기",
         "왼쪽 '학습하기 → 단어학습'에서 우리 선생님이 만든 교과서를 고르고 학습을 시작하세요.",
         [("file-text", "단어학습 · 교과서 선택 후 시작"),
          ("check-square", "알아요 / 모르겠어요로 체크"),
          ("bookmark", "문법·본문도 같은 방식으로 학습")]),
        ("arrow-counterclockwise", "2단계 · 복습으로 기억 굳히기",
         "틀린 단어는 자동으로 복습 예약돼요. '복습하기'에서 까먹을 때쯤 다시 만나면 진짜 내 것이 됩니다.",
         [("clock", "1일·3일·7일… 최적 타이밍 복습"),
          ("x-circle", "오답노트에서 틀린 것만 모아보기"),
          ("trophy", "5번 연속 맞추면 마스터 달성")]),
    ]


@st.dialog("반반 BanBan 시작 가이드", width="large")
def _render_onboarding():
    """첫 로그인 온보딩 마법사 — 역할별 3단계 가이드 (st.dialog 정식 모달)."""
    role  = _auth.current_role()
    step  = st.session_state.get("_onboarding_step", 1)
    steps = _onboarding_steps(role)
    total = len(steps)
    step  = max(1, min(step, total))

    icon_name, title, desc, points = steps[step - 1]

    # ── 헤더: 아이콘 뱃지 + 제목 ──────────────────────────────
    st.markdown(f"""
<div style="text-align:center;margin:4px 0 18px;">
  <div style="display:inline-flex;align-items:center;justify-content:center;
       width:56px;height:56px;border-radius:18px;margin-bottom:12px;
       background:linear-gradient(135deg,#4F46E5,#6366F1);
       box-shadow:0 8px 24px rgba(79,70,229,0.32);">
    {icon(icon_name, 28, "white")}
  </div>
  <div style="font-size:1.18rem;font-weight:900;color:#1E1B4B;letter-spacing:-0.3px;">
    {title}
  </div>
  <div style="font-size:0.86rem;color:#6B7280;line-height:1.6;margin-top:8px;
       max-width:380px;margin-left:auto;margin-right:auto;">{desc}</div>
</div>
""", unsafe_allow_html=True)

    # ── 체크리스트 카드 ────────────────────────────────────────
    rows = "".join(
        f'<div style="display:flex;align-items:center;gap:10px;padding:9px 4px;'
        f'border-bottom:1px solid #EEF2FF;">'
        f'<span style="flex-shrink:0;display:inline-flex;">{icon(pi, 16, "#6366F1")}</span>'
        f'<span style="font-size:0.88rem;color:#374151;font-weight:500;">{ptxt}</span>'
        f'</div>'
        for pi, ptxt in points
    )
    st.markdown(
        f'<div style="background:#F7F8FB;border:1px solid #ECEEF3;border-radius:14px;'
        f'padding:8px 16px;margin-bottom:18px;">{rows}</div>',
        unsafe_allow_html=True,
    )

    # ── 진행 도트 ──────────────────────────────────────────────
    dots = "".join(
        f'<div style="width:8px;height:8px;border-radius:50%;margin:0 4px;'
        f'background:{"#4F46E5" if i+1==step else "#D1D5DB"};"></div>'
        for i in range(total)
    )
    st.markdown(
        f'<div style="display:flex;justify-content:center;margin-bottom:16px;">{dots}</div>',
        unsafe_allow_html=True,
    )

    # ── 버튼 ───────────────────────────────────────────────────
    col_skip, col_next = st.columns([1, 2])
    with col_skip:
        if st.button("건너뛰기", key="onboard_skip", use_container_width=True):
            st.session_state["_onboarding_done"] = True
            st.session_state["_show_onboarding"] = False
            st.session_state["_onboarding_step"] = 1
            st.rerun()
    with col_next:
        if step < total:
            if st.button(f"다음 단계 ({step}/{total})", key="onboard_next",
                         use_container_width=True, type="primary"):
                st.session_state["_onboarding_step"] = step + 1
                st.rerun()
        else:
            if st.button("학습 시작하기", key="onboard_done",
                         use_container_width=True, type="primary"):
                st.session_state["_onboarding_done"] = True
                st.session_state["_show_onboarding"] = False
                st.session_state["_onboarding_step"] = 1
                st.rerun()


def _admin_quick_login():
    """관리자 꽃 버튼 → 관리자 계정 자동 로그인"""
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    admin_pw    = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_email or not admin_pw:
        st.error("관리자 계정이 .env에 설정되지 않았습니다.")
        return
    with st.spinner(""):
        ok, msg = _auth.sign_in(admin_email, admin_pw)
    if ok:
        # 관리자 role 설정
        from supabase_client import get_supabase
        user = _auth.current_user()
        if user:
            try:
                get_supabase().table("profiles") \
                    .update({"role": "admin"}) \
                    .eq("id", user.id).execute()
                st.session_state["sb_role"] = "admin"
            except Exception:
                pass
        st.rerun()
    else:
        st.error(msg)


# Supabase 설정된 경우에만 인증 게이트 적용
# DEV_SKIP_AUTH=true (기본값) → 로그인 페이지 건너뜀 (개발·검토용)
# DEV_SKIP_AUTH=false          → 정식 로그인 게이트 활성화
if is_supabase_configured():
    _auth.restore_session()   # 현재 탭 세션 복원 시도

    # 자동 로그인: 아직 미로그인 + URL 파람에 토큰 있으면 복원
    if not _auth.is_logged_in() and not _DEV_SKIP_AUTH:
        if _auth.try_restore_from_params():
            st.rerun()        # 복원 성공 → 재렌더 (로그인 상태로)

    # 자동 로그인: 미로그인 + URL 파람도 없으면 → JS가 localStorage 체크
    if not _auth.is_logged_in() and not _DEV_SKIP_AUTH:
        _auth.inject_auto_login_check()   # JS → localStorage → URL 파람 → rerun

    if not _auth.is_logged_in() and not _DEV_SKIP_AUTH:
        _render_auth_page()
        st.stop()             # 로그인 전에는 이하 코드 실행 안 함

# ─────────────────────────────────────────────────────────────────────────────
# 사이드바 계정 관리 위젯
# ─────────────────────────────────────────────────────────────────────────────

_PLAN_BADGE = {
    "free":    ("#F1F5F9", "#64748B", "FREE"),
    "student": ("#E0F2FE", "#0369A1", "STUDENT"),
    "pro":     ("#FEF3C7", "#92400E", "PRO"),
}


@st.dialog("계정 관리", width="small")
def _account_dialog():
    """계정 관리 팝업 — 프로필·비밀번호·로그아웃·탈퇴 (프리미엄 디자인)."""
    name  = _auth.current_student_name()
    role  = _auth.current_role()
    user  = _auth.current_user()
    email = user.email if user else ""
    plan  = current_plan()
    role_label = {"student": "학생", "teacher": "선생님", "admin": "관리자"}.get(role, role)
    _pbg, _pfc, _plabel = _PLAN_BADGE.get(plan, _PLAN_BADGE["free"])

    # ── 프로필 헤더 (그라디언트 카드) ─────────────────────────────
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#4F46E5,#7C3AED);'
        f'border-radius:16px;padding:18px 20px;margin-bottom:16px;'
        f'box-shadow:0 8px 24px rgba(79,70,229,0.28);">'
        f'<div style="display:flex;align-items:center;gap:13px;">'
        f'<div style="background:rgba(255,255,255,0.2);border-radius:50%;'
        f'width:46px;height:46px;display:flex;align-items:center;justify-content:center;'
        f'flex-shrink:0;backdrop-filter:blur(8px);">{icon("user",22,"white")}</div>'
        f'<div style="min-width:0;flex:1;">'
        f'<div style="font-weight:800;color:white;font-size:1.05rem;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name or "사용자"}</div>'
        f'<div style="font-size:0.74rem;color:rgba(255,255,255,0.85);'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{email}</div>'
        f'</div></div>'
        f'<div style="display:flex;gap:6px;margin-top:12px;">'
        f'<span style="background:rgba(255,255,255,0.22);color:white;border-radius:6px;'
        f'padding:2px 10px;font-size:0.7rem;font-weight:700;">{role_label}</span>'
        f'<span style="background:{_pbg};color:{_pfc};border-radius:6px;'
        f'padding:2px 10px;font-size:0.7rem;font-weight:800;">{_plabel} 플랜</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── 플랜 업그레이드 (FREE/STUDENT) ────────────────────────────
    if plan != "pro":
        target = "pro" if role in ("teacher", "admin") else "student"
        label  = "PRO 19,900원/월" if target == "pro" else "STUDENT 4,900원/월"
        st.markdown(
            f'<a href="{checkout_url(target)}" target="_blank" style="display:flex;'
            f'align-items:center;justify-content:space-between;'
            f'background:#F5F3FF;border:1px solid #DDD6FE;border-radius:12px;'
            f'padding:11px 15px;margin-bottom:14px;text-decoration:none;">'
            f'<span style="font-size:0.84rem;color:#4338CA;font-weight:700;">'
            f'{icon("zap",14,"#4338CA")} {label}로 업그레이드</span>'
            f'<span style="color:#4F46E5;font-weight:800;">→</span></a>',
            unsafe_allow_html=True,
        )

    tab_profile, tab_pw, tab_danger = st.tabs(["프로필", "비밀번호", "계정"])

    with tab_profile:
        new_name  = st.text_input("표시 이름", value=name, key="acct_name")
        new_grade = st.selectbox("학년", ["", "중1", "중2", "중3", "고1", "고2", "고3", "기타"],
                                 key="acct_grade")
        if st.button("프로필 저장", key="acct_save", use_container_width=True, type="primary"):
            ok, msg = _auth.update_profile(new_name, new_grade)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    with tab_pw:
        st.caption("대문자+소문자+숫자+특수문자, 8자 이상")
        new_pw  = st.text_input("새 비밀번호", type="password", key="acct_pw")
        new_pw2 = st.text_input("새 비밀번호 확인", type="password", key="acct_pw2")
        if new_pw:
            label, color = _auth.password_strength_label(new_pw)
            st.markdown(
                f'<div style="font-size:0.78rem;color:{color};font-weight:700;">'
                f'강도: {label}</div>',
                unsafe_allow_html=True,
            )
        if st.button("비밀번호 변경", key="acct_pw_save", use_container_width=True, type="primary"):
            if new_pw != new_pw2:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                ok, msg = _auth.update_password(new_pw)
                if ok:  st.success(msg)
                else:   st.error(msg)

    with tab_danger:
        if st.button("로그아웃", use_container_width=True, key="acct_logout"):
            _auth.sign_out()
            st.rerun()
        st.markdown(
            '<div style="font-size:0.74rem;color:#94A3B8;margin:10px 0 6px;">위험 구역</div>',
            unsafe_allow_html=True,
        )
        confirm = st.text_input("탈퇴하려면 '탈퇴합니다' 입력",
                                key="acct_delete_confirm",
                                placeholder="탈퇴합니다")
        if st.button("계정 영구 삭제", use_container_width=True, key="acct_delete"):
            if confirm == "탈퇴합니다":
                ok, msg = _auth.delete_account()
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.error("'탈퇴합니다'를 정확히 입력해주세요.")


def _render_account_sidebar():
    """로그인 사용자 카드 — 이름·역할·플랜 뱃지 + 계정 관리 버튼."""
    name  = _auth.current_student_name()
    role  = _auth.current_role()
    user  = _auth.current_user()
    email = user.email if user else ""
    plan  = current_plan()
    role_label = {"student": "학생", "teacher": "선생님", "admin": "관리자"}.get(role, role)
    role_color = "#F59E0B" if role == "admin" else "#6366F1"
    role_bg    = "rgba(245,158,11,0.15)" if role == "admin" else "rgba(99,102,241,0.15)"
    _pbg, _pfc, _plabel = _PLAN_BADGE.get(plan, _PLAN_BADGE["free"])

    # 이름 오른쪽에 역할 + 플랜 뱃지 함께 표시
    st.markdown(f"""
<div style="background:#F7F8FB;border:1px solid #ECEEF3;
     border-radius:12px;padding:10px 12px;margin:4px 0 6px;">
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="background:linear-gradient(135deg,#4F46E5,#6366F1);
         border-radius:50%;width:34px;height:34px;flex-shrink:0;
         display:flex;align-items:center;justify-content:center;
         box-shadow:0 3px 10px rgba(79,70,229,0.3);">
      {icon("user", 17, "white")}
    </div>
    <div style="min-width:0;flex:1;">
      <div style="display:flex;align-items:center;gap:5px;">
        <span style="font-weight:700;color:#1E293B;font-size:0.86rem;
             white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          {name or "사용자"}
        </span>
        <span style="background:{role_bg};color:{role_color};
               border-radius:4px;padding:1px 6px;font-size:0.62rem;font-weight:700;flex-shrink:0;">
          {role_label}
        </span>
        <span style="background:{_pbg};color:{_pfc};
               border-radius:4px;padding:1px 6px;font-size:0.62rem;font-weight:800;flex-shrink:0;">
          {_plabel}
        </span>
      </div>
      <div style="font-size:0.68rem;color:#94A3B8;margin-top:2px;
           overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
        {email}
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    if st.button("계정 관리", key="open_acct_dialog", use_container_width=True):
        _account_dialog()


# ─────────────────────────────────────────────────────────────────────────────
# API (내부 전용)
# ─────────────────────────────────────────────────────────────────────────────

def _api_config() -> dict | None:
    """멀티키 폴백 체인 설정.

    호출 순서:
      1) Gemini 키1 (GEMINI_API_KEY)
      2) Gemini 키2 (GEMINI_API_KEY_2) — 키1 429/실패 시
      3) Claude Haiku (ANTHROPIC_API_KEY) — Gemini 전부 실패 시
    키가 하나도 없으면 None.
    """
    gemini_key    = os.environ.get("GEMINI_API_KEY",   "").strip()
    gemini_key2   = os.environ.get("GEMINI_API_KEY_2", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY","").strip()

    gemini_keys = [k for k in [gemini_key, gemini_key2] if k]

    if not gemini_keys and not anthropic_key:
        return None

    primary = gemini_keys[0] if gemini_keys else anthropic_key
    return {
        "type":          "gemini" if gemini_keys else "anthropic",
        "key":           primary,
        "gemini_keys":   gemini_keys,        # Gemini 키 목록 (폴백 순서)
        "anthropic_key": anthropic_key,
        # 하위 호환
        "gemini_key":    gemini_keys[0] if gemini_keys else "",
    }

def _has_api() -> bool:
    return _api_config() is not None


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════
   반반 BanBan — Premium Design System v4 (SaaS CRM 스타일)
   Primary : #6366F1 (Indigo, 단일 강조색)
   Base    : #F7F8FB (살짝 푸른 화이트)
   원칙    : 헤어라인 테두리 · 부드러운 1종 그림자 · 넉넉한 여백
   ═══════════════════════════════════════════════════════════ */
:root {
  --p4:#6366F1; --p5:#4F46E5; --p6:#4338CA;
  --p-light:#EEF2FF; --p-mid:#C7D2FE;
  --a4:#0891B2; --a5:#0E7490; --a-light:#E0F2FE;
  --s1:#F7F8FB; --s2:#F1F3F7; --s3:#FFFFFF; --s4:#ECEEF3;
  --t1:#1E293B; --t2:#334155; --t3:#64748B; --t4:#94A3B8;
  --gb:rgba(0,0,0,0.07); --gf:rgba(255,255,255,0.95);
  --r:14px; --ri:12px;
  --soft:0 6px 24px rgba(31,38,135,0.06), 0 1px 2px rgba(0,0,0,0.03);
  --line:#ECEEF3;
}

/* ── App Base ──────────────────────────────── */
.stApp { background:var(--s1) !important; }
.stApp > header { background:transparent !important; border-bottom:none !important; }
.main .block-container {
  background:transparent !important;
  padding-top:1.6rem !important;
  padding-left:2rem !important;
  padding-right:2rem !important;
  max-width:1160px !important;
}

/* ── Sidebar ───────────────────────────────── */
[data-testid="stSidebar"] {
  background:#FFFFFF !important;
  border-right:1px solid var(--line) !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] small { color:var(--t2) !important; }

/* ── Sidebar 섹션 라벨 ─────────────────────── */
.sb-section-label {
  font-size: 0.65rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  color: var(--t4) !important;
  padding: 16px 12px 4px !important;
  display: block !important;
}

/* ── option_menu 전역 재정의: SaaS 좌측 보더 스타일 ── */
section[data-testid="stSidebar"] .nav-link {
  border-left: 3px solid transparent !important;
  border-radius: 0 8px 8px 0 !important;
  padding-left: 10px !important;
  margin: 1px 0 !important;
  transition: all 0.13s ease !important;
}
section[data-testid="stSidebar"] .nav-link:hover {
  background: rgba(99,102,241,0.06) !important;
  border-left-color: rgba(99,102,241,0.3) !important;
}
section[data-testid="stSidebar"] .nav-link-selected {
  border-left: 3px solid #4F46E5 !important;
  border-radius: 0 8px 8px 0 !important;
  background: rgba(99,102,241,0.09) !important;
}

/* ── Buttons: Primary ──────────────────────── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
  background:linear-gradient(135deg,#4F46E5,#6366F1) !important;
  border:none !important;
  border-radius:var(--r) !important;
  color:white !important;
  font-weight:700 !important;
  box-shadow:0 2px 10px rgba(79,70,229,0.28) !important;
  transition:all 0.18s !important;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
  box-shadow:0 4px 18px rgba(79,70,229,0.42) !important;
  transform:translateY(-1px) !important;
}

/* ── Buttons: Secondary ────────────────────── */
.stButton > button:not([kind="primary"]),
.stFormSubmitButton > button:not([kind="primary"]) {
  background:#FFFFFF !important;
  border:1px solid var(--line) !important;
  border-radius:var(--ri) !important;
  color:var(--t2) !important;
  font-weight:600 !important;
  box-shadow:0 1px 2px rgba(16,24,40,0.04) !important;
  transition:all 0.15s !important;
}
.stButton > button:not([kind="primary"]):hover {
  border-color:rgba(99,102,241,0.35) !important;
  color:var(--p5) !important;
  background:#F5F3FF !important;
}

/* ── Text Inputs ───────────────────────────── */
.stTextInput > label, .stPasswordInput > label,
.stTextArea > label, .stSelectbox > label,
.stNumberInput > label { color:var(--t2) !important; font-size:0.82rem !important; }

.stTextInput input, .stPasswordInput input,
[data-testid="stTextInput"] input,
[data-testid="stPasswordInput"] input {
  background:#FFFFFF !important;
  border:1px solid var(--line) !important;
  border-radius:var(--ri) !important;
  color:var(--t1) !important;
  caret-color:var(--p5) !important;
  box-shadow:0 1px 2px rgba(16,24,40,0.04) !important;
  transition:border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput input:focus, .stPasswordInput input:focus {
  border-color:var(--p5) !important;
  box-shadow:0 0 0 3px rgba(99,102,241,0.12) !important;
  outline:none !important;
}
.stTextInput input::placeholder,
.stPasswordInput input::placeholder { color:var(--t4) !important; }

/* ── Text Area ─────────────────────────────── */
.stTextArea textarea {
  background:#FFFFFF !important;
  border:1px solid var(--line) !important;
  border-radius:var(--ri) !important;
  color:var(--t1) !important;
  box-shadow:0 1px 2px rgba(16,24,40,0.04) !important;
}
.stTextArea textarea:focus {
  border-color:var(--p5) !important;
  box-shadow:0 0 0 3px rgba(99,102,241,0.1) !important;
}

/* ── Selectbox ─────────────────────────────── */
[data-baseweb="select"] > div {
  background:#FFFFFF !important;
  border:1px solid var(--line) !important;
  border-radius:var(--ri) !important;
  color:var(--t1) !important;
  box-shadow:0 1px 2px rgba(16,24,40,0.04) !important;
}
[data-baseweb="popover"], [data-baseweb="menu"] {
  background:#FFFFFF !important;
  border:1px solid #E2E8F0 !important;
  border-radius:10px !important;
  box-shadow:0 8px 24px rgba(0,0,0,0.1) !important;
}
[data-baseweb="option"] { color:var(--t2) !important; }
[data-baseweb="option"]:hover { background:#F5F3FF !important; color:var(--p5) !important; }

/* ── Number Input ──────────────────────────── */
[data-testid="stNumberInput"] input {
  background:#FFFFFF !important;
  border:1.5px solid #E2E8F0 !important;
  border-radius:var(--r) !important;
  color:var(--t1) !important;
}

/* ── Tabs ──────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background:var(--s2) !important;
  border-radius:var(--ri) !important;
  padding:4px !important;
  gap:2px !important;
  border-bottom:none !important;
}
.stTabs [data-baseweb="tab"] {
  background:transparent !important;
  border-radius:9px !important;
  color:var(--t3) !important;
  font-weight:600 !important;
  padding:6px 18px !important;
  border:none !important;
  transition:all 0.15s !important;
}
.stTabs [data-baseweb="tab"]:hover { color:var(--t2) !important; background:rgba(0,0,0,0.04) !important; }
.stTabs [aria-selected="true"] {
  background:#FFFFFF !important;
  color:var(--p5) !important;
  box-shadow:0 1px 6px rgba(0,0,0,0.1) !important;
  font-weight:700 !important;
}

/* ── Expander ──────────────────────────────── */
[data-testid="stExpander"] {
  background:#FFFFFF !important;
  border:1px solid var(--line) !important;
  border-radius:var(--r) !important;
  box-shadow:var(--soft) !important;
}
[data-testid="stExpander"] summary { color:var(--t1) !important; font-weight:600 !important; }

/* ── Metrics ───────────────────────────────── */
[data-testid="metric-container"] {
  background:#FFFFFF !important;
  border:1px solid var(--line) !important;
  border-radius:var(--r) !important;
  padding:16px 18px !important;
  box-shadow:var(--soft) !important;
}
[data-testid="metric-container"]:hover { border-color:rgba(99,102,241,0.3) !important; }
[data-testid="stMetricLabel"] p { color:var(--t3) !important; }
[data-testid="stMetricValue"] { color:var(--t1) !important; font-weight:800 !important; }

/* ── Alerts ────────────────────────────────── */
.stSuccess { background:#F0FDF4 !important; border:1px solid #BBF7D0 !important; border-radius:10px !important; }
.stSuccess p { color:#15803D !important; }
.stError   { background:#FEF2F2 !important; border:1px solid #FECACA !important; border-radius:10px !important; }
.stError p { color:#DC2626 !important; }
.stWarning { background:#FFFBEB !important; border:1px solid #FDE68A !important; border-radius:10px !important; }
.stWarning p { color:#B45309 !important; }
.stInfo    { background:#EFF6FF !important; border:1px solid #BFDBFE !important; border-radius:10px !important; }
.stInfo p  { color:#1D4ED8 !important; }

/* ── Progress Bar ──────────────────────────── */
[data-testid="stProgress"] > div > div { background:#E2E8F0 !important; border-radius:99px !important; }
[data-testid="stProgress"] > div > div > div { background:linear-gradient(90deg,#4F46E5,#818CF8) !important; border-radius:99px !important; }

/* ── Divider ───────────────────────────────── */
hr, [data-testid="stDivider"] { border-color:var(--line) !important; }

/* ── File Uploader ─────────────────────────── */
[data-testid="stFileUploader"] section {
  background:#FAFAFA !important;
  border:1.5px dashed #CBD5E1 !important;
  border-radius:var(--r) !important;
}
[data-testid="stFileUploader"] section:hover {
  border-color:var(--p5) !important;
  background:#F5F3FF !important;
}

/* ── Download Button ───────────────────────── */
[data-testid="stDownloadButton"] > button {
  background:#FFFBEB !important;
  border:1px solid #FDE68A !important;
  border-radius:var(--r) !important;
  color:#92400E !important;
  font-weight:700 !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background:#FEF3C7 !important;
}

/* ── Checkbox / Radio ──────────────────────── */
[data-baseweb="checkbox"] span { border-color:#CBD5E1 !important; }
[data-baseweb="checkbox"] [aria-checked="true"] span { background:var(--p5) !important; border-color:var(--p5) !important; }
[data-baseweb="radio"] span { border-color:#CBD5E1 !important; }
[data-baseweb="radio"] [aria-checked="true"] span { background:var(--p5) !important; border-color:var(--p5) !important; }

/* ── Spinner ───────────────────────────────── */
.stSpinner > div { border-top-color:var(--p5) !important; }

/* ── Form wrapper ──────────────────────────── */
[data-testid="stForm"] {
  background:transparent !important;
  border:none !important;
  padding:0 !important;
}

/* ── Scrollbar ─────────────────────────────── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#CBD5E1; border-radius:10px; }
::-webkit-scrollbar-thumb:hover { background:rgba(99,102,241,0.4); }

/* ══ CUSTOM COMPONENT CLASSES ════════════════════════════ */
.badge-단어   { background:#EEF2FF; color:#4338CA; border:1px solid #C7D2FE; border-radius:6px; padding:2px 10px; font-size:.78rem; font-weight:700; }
.badge-대화문 { background:#ECFDF5; color:#065F46; border:1px solid #A7F3D0; border-radius:6px; padding:2px 10px; font-size:.78rem; font-weight:700; }
.badge-본문   { background:#FFFBEB; color:#78350F; border:1px solid #FDE68A; border-radius:6px; padding:2px 10px; font-size:.78rem; font-weight:700; }
.badge-전체   { background:#F5F3FF; color:#5B21B6; border:1px solid #DDD6FE; border-radius:6px; padding:2px 10px; font-size:.78rem; font-weight:700; }
.hint-box { background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:.45rem .9rem; font-size:.82rem; color:#78350F; margin-bottom:.5rem; }
.sidebar-credit { font-size:.74rem; color:var(--t4); line-height:2; }

/* ══ 반쌤 플로팅 액션 버튼 (FAB) ═══════════════════════════ */
#bb-fab-wrap {
  position:fixed;
  bottom:28px;
  right:24px;
  z-index:9999;
  display:flex;
  flex-direction:column;
  align-items:flex-end;
  gap:8px;
  pointer-events:none;
}
#bb-fab-label {
  background:rgba(255,255,255,0.96);
  border:1px solid #E2E8F0;
  border-radius:8px;
  padding:5px 12px;
  font-size:0.74rem;
  color:#4F46E5;
  font-weight:600;
  white-space:nowrap;
  pointer-events:none;
  box-shadow:0 2px 10px rgba(0,0,0,0.1);
  /* 등장 애니메이션 제거 — Streamlit rerun마다 재생되어 깜빡이던 문제 해결 */
}
#bb-fab {
  width:54px;
  height:54px;
  border-radius:50%;
  background:linear-gradient(135deg,#4F46E5,#7C3AED);
  box-shadow:0 4px 20px rgba(79,70,229,0.55);
  display:flex;
  align-items:center;
  justify-content:center;
  cursor:pointer;
  pointer-events:all;
  text-decoration:none;
  transition:transform 0.2s cubic-bezier(0.34,1.56,0.64,1),
             box-shadow 0.2s ease;
  border:none;
}
#bb-fab:hover {
  transform:scale(1.12);
  box-shadow:0 8px 32px rgba(79,70,229,0.7);
}
#bb-fab:hover + #bb-fab-label { opacity:1; }
@keyframes bbFabLabelIn {
  from { opacity:0; transform:translateX(8px); }
  to   { opacity:1; transform:translateX(0);   }
}

/* ═══════════════════════════════════════════════════════════
   📱 모바일 우선 반응형 레이어 (v3 — 핵심 대중 S2 리텐션)
   중학생 다수가 스마트폰 사용 → 터치 타깃·가독성·오버플로 대응
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {

  /* ── 가로 오버플로 차단 (좌측 글자 잘림의 근본 원인 제거) ── */
  html, body, .stApp, [data-testid="stAppViewContainer"],
  .main, [data-testid="stMain"] {
    overflow-x: hidden !important;
    max-width: 100vw !important;
  }

  /* flex 자식이 콘텐츠보다 작아질 수 있게 → 넘침/밀림 방지 (핵심) */
  [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
  [data-testid="stHorizontalBlock"] > div,
  [data-testid="column"],
  [data-testid="stVerticalBlock"] > div {
    min-width: 0 !important;
  }

  /* 한글 단어 중간에서 끊김 방지 ("양쪽 보/기" → "양쪽 보기") */
  .stButton > button, .stButton > button *,
  .stRadio label, [data-baseweb="radio"],
  .stTabs [data-baseweb="tab"],
  [data-testid="stMetricLabel"], [data-baseweb="select"] {
    word-break: keep-all !important;
    overflow-wrap: break-word !important;
  }

  /* 가로 라디오: 줄바꿈 허용 (칸 넘침 방지) */
  [role="radiogroup"] {
    flex-wrap: wrap !important;
    gap: 6px !important;
  }
  .stRadio [role="radiogroup"] > label { font-size: 0.86rem !important; }

  /* ── 메인 컨테이너: 좌우 여백 최소화 (콘텐츠 폭 확보) ── */
  .main .block-container {
    padding-left: 0.7rem !important;
    padding-right: 0.7rem !important;
    padding-top: 0.8rem !important;
    max-width: 100% !important;
  }

  /* ── 제목 크기 축소 ── */
  h1 { font-size: 1.45rem !important; line-height: 1.25 !important; }
  h2 { font-size: 1.2rem !important; }
  h3 { font-size: 1.05rem !important; }

  /* ── 터치 타깃: 버튼 최소 높이 48px (Apple HIG 권장) ── */
  .stButton > button,
  .stFormSubmitButton > button,
  .stDownloadButton > button {
    min-height: 48px !important;
    font-size: 0.95rem !important;
    padding: 10px 14px !important;
  }

  /* ── 입력/선택: 터치 친화 + iOS 자동 줌 방지(폰트 16px↑) ── */
  .stTextInput input,
  .stPasswordInput input,
  .stTextArea textarea,
  [data-testid="stNumberInput"] input,
  [data-baseweb="select"] > div {
    min-height: 46px !important;
    font-size: 16px !important;
  }

  /* ── 체크박스/라디오: 터치 영역 확대 ── */
  [data-baseweb="checkbox"], [data-baseweb="radio"] {
    transform: scale(1.15);
    transform-origin: left center;
  }

  /* ── 탭: 가로 스크롤 (잘림 방지) ── */
  .stTabs [data-baseweb="tab-list"] {
    overflow-x: auto !important;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
  .stTabs [data-baseweb="tab"] {
    padding: 7px 13px !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
    font-size: 0.86rem !important;
  }

  /* ── 표/데이터프레임: 가로 스크롤 (옆으로 잘림 방지) ── */
  [data-testid="stTable"], .stDataFrame, [data-testid="stDataFrame"] {
    overflow-x: auto !important;
    display: block !important;
  }

  /* ── 메트릭: 폰트 축소로 줄바꿈 방지 ── */
  [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
  [data-testid="stMetricLabel"] p { font-size: 0.75rem !important; }
  [data-testid="metric-container"] { padding: 12px 14px !important; }

  /* ── 컬럼 간격 축소 (모바일에서 세로 적층 시 답답함 완화) ── */
  [data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }

  /* ── iframe(반반노트 미리보기): 높이 축소 ── */
  iframe { max-height: 70vh !important; }

  /* ── 사이드바: 펼쳐질 때 화면을 거의 다 덮으므로 폭 제한 ── */
  [data-testid="stSidebar"] { min-width: 80vw !important; }

  /* ── FAB(반쌤): 모바일에서 작게 + 라벨 숨김(콘텐츠 가림·깜빡임 방지) ── */
  #bb-fab-wrap { bottom: 16px !important; right: 14px !important; }
  #bb-fab { width: 50px !important; height: 50px !important; }
  #bb-fab-label { display: none !important; }

  /* ── 글래스 카드 패딩 축소 ── */
  [data-testid="stExpander"] summary { font-size: 0.9rem !important; }
}

/* ── 초소형 화면(아이폰 SE 등) 추가 보정 ── */
@media (max-width: 380px) {
  .main .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
  h1 { font-size: 1.3rem !important; }
  .stTabs [data-baseweb="tab"] { padding: 6px 10px !important; font-size: 0.8rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ─── 반쌤 플로팅 버튼 HTML ──────────────────────────────────────────────────
st.markdown("""
<div id="bb-fab-wrap">
  <div id="bb-fab-label">반쌤에게 질문하기</div>
  <a id="bb-fab" href="?chat=open" title="반쌤 AI 튜터">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
         stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  </a>
</div>
""", unsafe_allow_html=True)

# ─── 채팅 URL 파라미터 감지 → 반쌤 채팅 페이지로 자동 이동 ────────────────
if st.query_params.get("chat") == "open":
    st.session_state["study_page"] = "반쌤 채팅"
    st.session_state["page"]       = "__study__"
    st.query_params.clear()
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# 진입 세그먼트 팝업 — 랜딩 "지금 무료로 시작하기" → 학생/선생님 + 학년 선택
# 2탭 카드 + 건너뛰기 + 즉시 맞춤 웰컴 (회의 결론 반영)
# ─────────────────────────────────────────────────────────────────────────────

_WELCOME_MSG = {
    ("student", "중1"): "중학교 영어, 지금 습관 들이면 3년이 편해져요. 첫 단어부터 같이 시작해요!",
    ("student", "중2"): "딱 지금이 영어 실력 가르는 시기예요. 틀린 것만 골라 복습하며 앞서가요!",
    ("student", "중3"): "내신·고입까지 시간이 많지 않아요. 가장 빠른 복습 루트, 지금 시작합니다.",
    ("student", "고1"): "고등 영어의 시작. 탄탄한 기초로 1등급의 발판을 만들어요!",
    ("student", "고2"): "수능형 사고력까지. 약점만 정밀하게 잡아 효율적으로 올라가요!",
    ("student", "고3"): "수능까지 D-day. 약점만 정밀 타격하는 맞춤 학습으로 마지막 스퍼트!",
    ("teacher", "*"):   "교재 만드는 시간, 이제 5분이면 충분해요. 첫 반반노트를 만들어볼까요?",
}

def _welcome_for(role: str, level: str) -> str:
    if role == "teacher":
        return _WELCOME_MSG[("teacher", "*")]
    return _WELCOME_MSG.get((role, level),
                            "환영합니다! 당신만의 맞춤 학습을 설계해드릴게요.")


def _log_visitor_segment(role: str, level: str):
    """방문자 세그먼트 익명 집계 (best-effort)."""
    try:
        from supabase_client import get_supabase, is_supabase_configured
        if not is_supabase_configured():
            return
        uid = None
        u = _auth.current_user()
        if u:
            uid = u.id
        get_supabase().table("visitor_segments").insert(
            {"role": role, "level": level, "user_id": uid}
        ).execute()
    except Exception:
        pass


@st.dialog("반반 BanBan에 오신 걸 환영해요", width="small")
def _segment_dialog():
    step = st.session_state.get("_seg_step", 1)

    if step == 1:
        st.markdown(
            '<div style="font-size:0.92rem;color:#475569;margin-bottom:14px;">'
            '어떤 분이신가요? 딱 맞는 학습을 준비해드릴게요.</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div style="text-align:center;padding:6px 0;">'
                f'{icon("user",34,"#4F46E5")}</div>', unsafe_allow_html=True)
            if st.button("학생이에요", key="seg_student", use_container_width=True, type="primary"):
                st.session_state["_seg_role"] = "student"
                st.session_state["_seg_step"] = 2
                st.rerun()
        with c2:
            st.markdown(
                f'<div style="text-align:center;padding:6px 0;">'
                f'{icon("users",34,"#0891B2")}</div>', unsafe_allow_html=True)
            if st.button("선생님이에요", key="seg_teacher", use_container_width=True):
                st.session_state["_seg_role"] = "teacher"
                st.session_state["_seg_step"] = 2
                st.rerun()
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if st.button("그냥 둘러볼게요", key="seg_skip1", use_container_width=True):
            st.session_state["_seg_done"] = True
            st.rerun()

    else:  # step 2 — 학년/구분
        role = st.session_state.get("_seg_role", "student")
        st.markdown(
            f'<div style="font-size:0.92rem;color:#475569;margin-bottom:6px;">'
            f'{"학년을 알려주세요." if role=="student" else "어디서 가르치세요?"}</div>'
            f'<div style="display:flex;gap:4px;margin-bottom:12px;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:#D1D5DB;"></span>'
            f'<span style="width:8px;height:8px;border-radius:50%;background:#4F46E5;"></span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if role == "student":
            opts = ["중1", "중2", "중3", "고1", "고2", "고3", "기타"]
        else:
            opts = ["공부방", "학원", "과외", "공교육", "기타"]

        cols = st.columns(3)
        for i, o in enumerate(opts):
            if cols[i % 3].button(o, key=f"seg_lv_{o}", use_container_width=True):
                level = o
                if o == "기타":
                    level = st.session_state.get("_seg_etc", "기타")
                st.session_state["_seg_level"] = level
                st.session_state["_seg_done"]  = True
                st.session_state["_seg_welcome"] = _welcome_for(role, level)
                _log_visitor_segment(role, level)
                # 로그인 사용자면 학년도 프로필에 반영(학생만)
                st.rerun()

        if "기타" in opts:
            st.text_input("기타 (직접 입력)", key="_seg_etc",
                          placeholder="예: 인강 / 홈스쿨 …", label_visibility="collapsed")
        if st.button("건너뛰기", key="seg_skip2", use_container_width=True):
            st.session_state["_seg_done"] = True
            st.rerun()


# 트리거: 랜딩에서 ?start=1 로 진입 시 (세션당 1회)
if st.query_params.get("start") == "1":
    st.session_state["_seg_pending"] = True
    st.query_params.clear()
    st.rerun()

if st.session_state.get("_seg_pending") and not st.session_state.get("_seg_done"):
    _segment_dialog()

# ── 업그레이드 페이지 (?upgrade=1) ────────────────────────────────
if st.query_params.get("upgrade") == "1":
    from plans import checkout_url, STUDENT_FEATURES, PRO_FEATURES, current_plan
    _cur = current_plan()
    st.query_params.clear()
    st.markdown(f"""
<div style="max-width:780px;margin:0 auto;padding:24px 0;">
  <div style="text-align:center;margin-bottom:28px;">
    <div style="font-size:1.6rem;font-weight:900;color:#1E293B;letter-spacing:-0.5px;">
      반반 BanBan 요금제
    </div>
    <div style="color:#64748B;margin-top:6px;font-size:0.9rem;">
      첫 달 무료 · 언제든지 취소 가능
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    col_free, col_stu, col_pro = st.columns(3)

    def _plan_card(col, name, price, features, btn_label, btn_url,
                   accent, is_current, recommended=False):
        badge = ('<span style="background:#4F46E5;color:white;font-size:0.65rem;'
                 'font-weight:700;border-radius:20px;padding:2px 10px;margin-left:8px;">추천</span>'
                 if recommended else "")
        cur_badge = ('<span style="background:#DCFCE7;color:#166534;font-size:0.65rem;'
                     'font-weight:700;border-radius:20px;padding:2px 10px;margin-left:8px;">현재 플랜</span>'
                     if is_current else "")
        rows = "".join(
            f'<div style="display:flex;align-items:center;gap:7px;padding:4px 0;font-size:0.84rem;color:#374151;">'
            f'{icon("check-circle",14,accent)}<span>{f}</span></div>'
            for f in features
        )
        btn_html = (
            f'<a href="{btn_url}" target="_blank" style="display:block;margin-top:18px;'
            f'background:{"linear-gradient(135deg,#4F46E5,#6366F1)" if btn_url else "#E2E8F0"};'
            f'color:{"white" if btn_url else "#94A3B8"};border-radius:10px;padding:11px;'
            f'text-align:center;font-weight:800;font-size:0.9rem;text-decoration:none;">'
            f'{btn_label}</a>'
            if btn_url
            else f'<div style="margin-top:18px;background:#F1F5F9;border-radius:10px;padding:11px;'
                 f'text-align:center;font-size:0.9rem;color:#94A3B8;font-weight:700;">{btn_label}</div>'
        )
        _border  = f"2px solid {accent}" if recommended else "1px solid #ECEEF3"
        _shadow  = "0 8px 28px rgba(79,70,229,0.12)" if recommended else "0 2px 8px rgba(0,0,0,0.05)"
        _price_lbl = "무료" if not price else price
        _sub_lbl   = "" if not price else '<div style="font-size:0.75rem;color:#94A3B8;margin-top:2px;">첫 달 무료 · 이후 월 결제</div>'
        col.markdown(
            f'<div style="background:white;border:{_border};'
            f'border-radius:16px;padding:22px 18px;height:100%;box-shadow:{_shadow};">'
            f'<div style="font-size:0.8rem;font-weight:800;color:{accent};text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:6px;">{name}{badge}{cur_badge}</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#1E293B;">{_price_lbl}</div>'
            f'{_sub_lbl}'
            f'<hr style="border:none;border-top:1px solid #ECEEF3;margin:14px 0;">'
            f'{rows}{btn_html}</div>',
            unsafe_allow_html=True,
        )

    _plan_card(col_free, "FREE", "", [
        "단어학습·복습 무제한",
        "AI 문제 생성 월 10회",
        "반반노트 출력 월 3회",
        "오답노트",
    ], "현재 이용 중" if _cur == "free" else "무료로 시작", "",
    "#64748B", _cur == "free")

    _plan_card(col_stu, "STUDENT", "4,900원/월", [
        "AI 문제 생성 무제한",
        "반반노트 출력 월 10회",
        "약점 처방전 AI 분석",
        "문제뱅크 전체 접근",
    ], "현재 플랜" if _cur == "student" else "학생 플랜 시작",
    "" if _cur == "student" else checkout_url("student"),
    "#0891B2", _cur == "student")

    _plan_card(col_pro, "PRO", "19,900원/월", [
        "AI 문제 생성 무제한",
        "반반노트 출력·배치 무제한",
        "정답지 동시 생성",
        "학생 관리 무제한",
        "학부모 리포트",
        "약점 처방전 AI 분석",
    ], "현재 플랜" if _cur == "pro" else "PRO 시작하기",
    "" if _cur == "pro" else checkout_url("pro"),
    "#4F46E5", _cur == "pro", recommended=True)

    st.markdown(
        '<div style="text-align:center;margin-top:20px;font-size:0.78rem;color:#94A3B8;">'
        'Polar로 안전하게 결제 · 언제든지 취소 가능 · 첫 달 무료 후 자동 결제</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# 세션 상태 초기화
# ─────────────────────────────────────────────────────────────────────────────
_PAGES = ["라이브러리", "새 노트 추가", "합치기 & 다운로드"]

if "page"         not in st.session_state: st.session_state["page"]         = "__dashboard__"  # 로그인 첫 화면 = 내 학습현황
if "selected_ids" not in st.session_state: st.session_state["selected_ids"] = set()
if "xlsx_bytes"   not in st.session_state: st.session_state["xlsx_bytes"]   = None
if "current_xlsx" not in st.session_state: st.session_state["current_xlsx"] = None
if "current_fn"   not in st.session_state: st.session_state["current_fn"]   = ""

# 텍스트 영역 위젯 키 초기화 (빈 상태로 시작)
if "wi" not in st.session_state: st.session_state["wi"] = ""
if "di" not in st.session_state: st.session_state["di"] = ""
if "ti" not in st.session_state: st.session_state["ti"] = ""

# 라이브러리 수정 상태 (편집 중인 note_id)
if "lib_edit_id"   not in st.session_state: st.session_state["lib_edit_id"]   = None
if "lib_print_id"  not in st.session_state: st.session_state["lib_print_id"]  = None

# ── 학습 시스템 세션 상태 ──────────────────────────────────────────────────
_STUDY_PAGES = ["반반 학습", "단어학습", "문법학습", "내신문제", "서술형 DNA", "기출문제", "복습하기"]
_MGMT_PAGES  = ["오답노트", "약점 처방전", "비법노트", "숙제", "시험 요약노트", "내 클래스"]

# 역할별 대시보드 메뉴 분리
_DASH_PAGES_TEACHER = ["내 학습현황", "학생 관리", "클래스 랭킹", "학부모 리포트", "주간 리포트 발송"]
_DASH_PAGES_STUDENT = ["내 학습현황", "클래스 랭킹"]
_DASH_PAGES = _DASH_PAGES_TEACHER if _auth.current_role() in ("teacher", "admin") else _DASH_PAGES_STUDENT

if "study_page"    not in st.session_state: st.session_state["study_page"]    = "반반 학습"
if "dash_page"     not in st.session_state: st.session_state["dash_page"]     = "내 학습현황"
if "study_student" not in st.session_state: st.session_state["study_student"] = ""
if "study_note_id" not in st.session_state: st.session_state["study_note_id"] = None

# ── 섹션 접힘/펼침 상태 ──────────────────────────────────────
if "_acc_note"  not in st.session_state: st.session_state["_acc_note"]  = True
if "_acc_study" not in st.session_state: st.session_state["_acc_study"] = True
if "_acc_mgmt"  not in st.session_state: st.session_state["_acc_mgmt"]  = True
if "_acc_dash"  not in st.session_state: st.session_state["_acc_dash"]  = False

# ─────────────────────────────────────────────────────────────────────────────
# 로그인 직후 역할별 대시보드 자동 이동
# ─────────────────────────────────────────────────────────────────────────────
if is_supabase_configured() and _auth.is_logged_in():
    if not st.session_state.get("_post_login_redirected"):
        st.session_state["_post_login_redirected"] = True
        _role = _auth.current_role()
        if _role == "teacher":
            st.session_state["page"]      = "__dashboard__"
            st.session_state["dash_page"] = "학생 관리"
            st.session_state["_acc_dash"] = True
        else:
            st.session_state["page"]      = "__dashboard__"
            st.session_state["dash_page"] = "내 학습현황"
            st.session_state["_acc_dash"] = True
        # 온보딩 필요 여부 확인 — 첫 로그인이면 마법사 시작
        if not st.session_state.get("_onboarding_done"):
            st.session_state["_show_onboarding"] = True

# ─────────────────────────────────────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:

    # (아코디언 CSS는 _section_toggle 내부에서 marker id 기반으로 주입)

    # ── 브랜드 헤더 ──────────────────────────────────────────────
    st.markdown(
        f'<div style="padding:14px 4px 10px 2px;">'
        f'<div style="display:flex;align-items:center;gap:9px;">'
        f'<div style="width:30px;height:30px;border-radius:9px;flex-shrink:0;'
        f'background:linear-gradient(135deg,#4F46E5,#6366F1);'
        f'display:flex;align-items:center;justify-content:center;'
        f'box-shadow:0 3px 10px rgba(79,70,229,0.45);">'
        f'{icon("zap", 15, "white")}'
        f'</div>'
        f'<span style="font-size:1.28rem;font-weight:900;letter-spacing:-0.5px;'
        f'background:linear-gradient(130deg,#4F46E5 0%,#6366F1 60%,#0891B2 100%);'
        f'-webkit-background-clip:text;-webkit-text-fill-color:transparent;">'
        f'반반 BanBan</span>'
        f'</div>'
        f'<div style="font-size:.7rem;color:#94A3B8;padding-left:39px;'
        f'margin-top:2px;letter-spacing:0.04em;">영어 반반노트 학습 플랫폼</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='margin-bottom:2px;'></div>", unsafe_allow_html=True)

    # ── 이전 상태 추적 (메뉴 클릭 감지용) ──────────────────────────
    _prev_note_sel  = st.session_state.get("_prev_note_sel",  "라이브러리")
    _prev_study_sel = st.session_state.get("_prev_study_sel", "반반 학습")
    _prev_mgmt_sel  = st.session_state.get("_prev_mgmt_sel",  "오답노트")
    _prev_dash_sel  = st.session_state.get("_prev_dash_sel",  "내 학습현황")

    # ── 공통 option_menu 스타일 (PM Dashboard 좌측 보더 스타일) ────
    def _omenu_styles(icon_color: str, sel_color: str, sel_border_rgb: str):
        return {
            "container":         {"padding": "0 0 4px 0", "background": "transparent"},
            "icon":              {"color": icon_color, "font-size": "14px"},
            "nav-link":          {
                "font-size": "13px",
                "padding": "8px 12px 8px 10px",
                "border-radius": "0 8px 8px 0",
                "border-left": "3px solid transparent",
                "color": "#64748B",
                "font-weight": "500",
                "margin-bottom": "1px",
                "--hover-color": f"rgba({sel_border_rgb},0.06)",
            },
            "nav-link-selected": {
                "background": f"rgba({sel_border_rgb},0.09)",
                "color": sel_color,
                "font-weight": "700",
                "border-left": f"3px solid {sel_color}",
                "border-radius": "0 8px 8px 0",
            },
        }

    # ── 섹션 그룹 라벨 (아코디언 없음, 항상 표시) ──────────────────
    def _sb_label(text: str, top_gap: bool = True):
        mt = "14px" if top_gap else "2px"
        st.markdown(
            f'<span class="sb-section-label" style="margin-top:{mt};">{text}</span>',
            unsafe_allow_html=True,
        )

    # ── 현재 활성 섹션 판별 ────────────────────────────────────────
    _cur_page = st.session_state["page"]
    _sp       = st.session_state["study_page"]
    _dp       = st.session_state.get("dash_page", "내 학습현황")

    # ── 계정 정보 (사이드바 상단) ──────────────────────────────────
    if is_supabase_configured() and _auth.is_logged_in():
        _render_account_sidebar()
    else:
        with st.expander("학생 선택", expanded=False):
            students = list_students()
            names    = [s["name"] for s in students]
            new_name = st.text_input("새 학생 이름 추가", key="new_student_name",
                                     placeholder="이름 입력 후 Enter")
            if new_name.strip() and st.button("추가", key="add_student"):
                get_or_create_student(new_name.strip())
                st.session_state["study_student"] = new_name.strip()
                st.rerun()
            if names:
                cur_student = st.session_state.get("study_student", "")
                sel_idx = names.index(cur_student) if cur_student in names else 0
                chosen = st.selectbox("학생 선택", names, index=sel_idx,
                                      key="student_sel")
                if chosen != st.session_state.get("study_student"):
                    st.session_state["study_student"] = chosen
                    st.rerun()
            else:
                st.caption("학생을 추가하면 개인별 오답 기록이 저장됩니다.")

    # ── 플랜 업그레이드 CTA는 사이드바 하단으로 이동 (디자인 회의 결정) ──
    #    첫 시선을 가리지 않도록 메뉴 아래쪽에 미니멀 텍스트 링크로 배치.

    # ── 헤어라인 구분선 ────────────────────────────────────────────
    st.markdown(
        '<hr style="border:none;border-top:1px solid #ECEEF3;margin:6px 0 4px;">',
        unsafe_allow_html=True,
    )

    # ═══════════════════════════════════════════════════════════════
    # 섹션 1: 학습하기
    # ═══════════════════════════════════════════════════════════════
    _sb_label("학습하기", top_gap=False)
    study_cur_idx = (
        _STUDY_PAGES.index(_sp)
        if _cur_page == "__study__" and _sp in _STUDY_PAGES else -1
    )
    study_selected = option_menu(
        menu_title=None,
        options=_STUDY_PAGES,
        icons=["house", "bookmark", "book-half", "pencil-square",
               "vector-pen", "cloud-upload", "arrow-counterclockwise"],
        default_index=study_cur_idx,
        key="study_menu",
        styles=_omenu_styles("#7C3AED", "#5B21B6", "109,40,217"),
    )

    # ═══════════════════════════════════════════════════════════════
    # 섹션 2: 학습 관리
    # ═══════════════════════════════════════════════════════════════
    _sb_label("학습 관리")
    # FREE 사용자: 잠금 기능 뱃지 힌트
    if current_plan() == "free":
        st.markdown(
            f'<div style="display:flex;gap:4px;flex-wrap:wrap;padding:2px 4px 6px;">'
            f'<span style="background:#EEF2FF;color:#4338CA;border-radius:5px;'
            f'padding:2px 7px;font-size:0.65rem;font-weight:700;">'
            f'{icon("lock",10,"#4338CA")} 약점 처방전 PRO</span>'
            f'<span style="background:#EEF2FF;color:#4338CA;border-radius:5px;'
            f'padding:2px 7px;font-size:0.65rem;font-weight:700;">'
            f'{icon("lock",10,"#4338CA")} 비법노트 PRO</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    mgmt_cur_idx = (
        _MGMT_PAGES.index(_sp)
        if _cur_page == "__study__" and _sp in _MGMT_PAGES else -1
    )
    mgmt_selected = option_menu(
        menu_title=None,
        options=_MGMT_PAGES,
        icons=["x-circle", "activity", "lightbulb", "check2-square", "file-text", "people"],
        default_index=mgmt_cur_idx,
        key="mgmt_menu",
        styles=_omenu_styles("#DC2626", "#B91C1C", "220,38,38"),
    )

    # ═══════════════════════════════════════════════════════════════
    # 섹션 3: 대시보드
    # ═══════════════════════════════════════════════════════════════
    _sb_label("대시보드")
    dash_cur_idx = (
        _DASH_PAGES.index(_dp)
        if _cur_page == "__dashboard__" and _dp in _DASH_PAGES else -1
    )
    dash_selected = option_menu(
        menu_title=None,
        options=_DASH_PAGES,
        icons=["bar-chart-line", "people", "trophy", "envelope", "send"],
        default_index=dash_cur_idx,
        key="dash_menu",
        styles=_omenu_styles("#0891B2", "#0E7490", "8,145,178"),
    )

    # ═══════════════════════════════════════════════════════════════
    # 섹션 4: 반반노트 — 선생님 / 관리자만 표시
    # ═══════════════════════════════════════════════════════════════
    _sidebar_role        = _auth.current_role()
    _is_teacher_or_admin = _sidebar_role in ("teacher", "admin")

    if _is_teacher_or_admin:
        _sb_label("반반노트 관리")
        note_cur_idx = (
            _PAGES.index(_cur_page)
            if _cur_page in _PAGES else -1
        )
        selected = option_menu(
            menu_title=None,
            options=_PAGES,
            icons=["bookmarks", "plus-circle", "layers"],
            default_index=note_cur_idx,
            key="note_menu",
            styles=_omenu_styles("#6366F1", "#4338CA", "99,102,241"),
        )
        sel_count = len(st.session_state["selected_ids"])
        if sel_count:
            st.markdown(
                f'<div style="background:#ECFDF5;border:1px solid #A7F3D0;'
                f'border-radius:9px;padding:8px 12px;margin:4px 8px;font-size:.82rem;color:#065F46;">'
                f'{icon("check-circle",14,"#059669")} {sel_count}개 노트 선택됨</div>',
                unsafe_allow_html=True,
            )
            if st.button("합치기 페이지로 →", use_container_width=True):
                st.session_state["page"]           = "합치기 & 다운로드"
                st.session_state["_prev_note_sel"] = "합치기 & 다운로드"
                st.rerun()
    else:
        selected = "__study__"
        if _cur_page in _PAGES:
            st.session_state["page"] = "__study__"

    # ── PRO 업그레이드 — 사이드바 하단 미니멀 텍스트 링크 ──────────
    #    FREE 사용자에게만. 첫 시선을 가리지 않게 메뉴 맨 아래에 가볍게.
    if current_plan() == "free" and is_supabase_configured() and _auth.is_logged_in():
        st.markdown(
            f'<div style="padding:14px 12px 4px;">'
            f'<a href="{checkout_url("pro")}" target="_blank" style="'
            f'display:inline-flex;align-items:center;gap:5px;text-decoration:none;'
            f'font-size:0.78rem;font-weight:700;color:#6366F1;">'
            f'{icon("sparkles",13,"#6366F1")} PRO로 업그레이드 '
            f'<span style="font-weight:800;">→</span></a>'
            f'<div style="font-size:0.66rem;color:#94A3B8;margin-top:2px;">'
            f'첫 달 무료 · 19,900원/월</div></div>',
            unsafe_allow_html=True,
        )

    # ── 네비게이션 결정 ────────────────────────────────────────────
    if study_selected != _prev_study_sel and study_selected in _STUDY_PAGES:
        st.session_state["study_page"]      = study_selected
        st.session_state["page"]            = "__study__"
        st.session_state["_prev_study_sel"] = study_selected
        st.rerun()
    elif mgmt_selected != _prev_mgmt_sel and mgmt_selected in _MGMT_PAGES:
        st.session_state["study_page"]     = mgmt_selected
        st.session_state["page"]           = "__study__"
        st.session_state["_prev_mgmt_sel"] = mgmt_selected
        st.rerun()
    elif dash_selected != _prev_dash_sel:
        st.session_state["dash_page"]      = dash_selected
        st.session_state["page"]           = "__dashboard__"
        st.session_state["_prev_dash_sel"] = dash_selected
        st.rerun()
    elif selected != _prev_note_sel and _is_teacher_or_admin:
        st.session_state["page"]           = selected
        st.session_state["_prev_note_sel"] = selected
        st.rerun()
    else:
        st.session_state["_prev_note_sel"]  = selected
        st.session_state["_prev_study_sel"] = study_selected
        st.session_state["_prev_mgmt_sel"]  = mgmt_selected
        st.session_state["_prev_dash_sel"]  = dash_selected

    # ── 하단 크레딧 ───────────────────────────────────────────────
    st.markdown(
        '<hr style="border:none;border-top:1px solid #ECEEF3;margin:10px 0 8px;">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="sidebar-credit">'
        f'{icon("zap", 11, "#C7D2FE")} 반반 BanBan v4 &nbsp;·&nbsp; 2026<br>'
        f'M.J. PM &nbsp;·&nbsp; S.Y. 백엔드 &nbsp;·&nbsp; D.Y. 프론트 &nbsp;·&nbsp; A.R. QA'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 파싱 유틸
# ─────────────────────────────────────────────────────────────────────────────

def parse_words(text):
    result = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        parts = line.split("|", 1)
        if len(parts) == 2:
            en, kr = parts[0].strip(), parts[1].strip()
            if en and kr: result.append((en, kr))
    return result

def parse_dialogues(text):
    dialogues, current = [], None
    for line in text.strip().splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith("[") and line.endswith("]"):
            if current: dialogues.append(current)
            current = {"title": line[1:-1], "lines": []}
        elif "|" in line and current is not None:
            parts = line.split("|", 1)
            en, kr = parts[0].strip(), parts[1].strip()
            if en: current["lines"].append((en, kr))
    if current: dialogues.append(current)
    return dialogues

_SEC_MARKERS = {"[서론]": "서론", "[본론]": "본론", "[결론]": "결론"}

def parse_text(text):
    """본문 텍스트 파싱.

    형식 A (섹션 없음):
        영어제목|한글제목
        01 영어문장|한글번역
        ...

    형식 B (섹션 있음):
        영어제목|한글제목
        [서론]
        01 영어문장|한글번역
        [본론]
        05 영어문장|한글번역
        [결론]
        20 영어문장|한글번역
    """
    lines = [l.strip() for l in text.strip().splitlines()
             if l.strip() and not l.startswith("#")]
    if not lines:
        return {"title_en": "", "title_kr": "", "sentences": []}

    first    = lines[0].split("|", 1)
    title_en = first[0].strip()
    title_kr = first[1].strip() if len(first) > 1 else ""

    rest = lines[1:]
    has_sections = any(l in _SEC_MARKERS for l in rest)

    if has_sections:
        sections      = []
        all_sentences = []
        cur_label     = None
        cur_sents     = []

        for line in rest:
            if line in _SEC_MARKERS:
                if cur_label is not None and cur_sents:
                    sections.append({"label": cur_label, "sentences": cur_sents})
                cur_label = _SEC_MARKERS[line]
                cur_sents = []
            elif "|" in line:
                parts = line.split("|", 1)
                en, kr = parts[0].strip(), parts[1].strip()
                if en:
                    pair = (en, kr)
                    cur_sents.append(pair)
                    all_sentences.append(pair)

        if cur_label is not None and cur_sents:
            sections.append({"label": cur_label, "sentences": cur_sents})

        return {
            "title_en":  title_en,
            "title_kr":  title_kr,
            "sentences": all_sentences,
            "sections":  sections,
        }
    else:
        sentences = []
        for line in rest:
            parts = line.split("|", 1)
            if len(parts) == 2:
                en, kr = parts[0].strip(), parts[1].strip()
                if en: sentences.append((en, kr))
        return {"title_en": title_en, "title_kr": title_kr, "sentences": sentences}

def words_to_text(words):
    return "\n".join(f"{e}|{k}" for e, k in words)

def dlg_to_text(dialogues):
    lines = []
    for d in dialogues:
        lines.append(f"[{d['title']}]")
        for en, kr in d["lines"]:
            lines.append(f"{en}|{kr}")
        lines.append("")
    return "\n".join(lines).strip()

def text_to_text(td):
    """text_data dict → 텍스트 영역 문자열 (섹션 마커 포함)."""
    lines    = [f"{td.get('title_en','')}|{td.get('title_kr','')}"]
    sections = td.get("sections")
    if sections:
        for sec in sections:
            lines.append(f"[{sec['label']}]")
            for en, kr in sec.get("sentences", []):
                lines.append(f"{en}|{kr}")
    else:
        for en, kr in td.get("sentences", []):
            lines.append(f"{en}|{kr}")
    return "\n".join(lines)

def _is_plain_english(text: str) -> bool:
    """한글 번역 없는 순수 영어 텍스트인지 확인"""
    stripped = text.strip()
    if not stripped: return False
    lines_with_content = [l for l in stripped.splitlines() if l.strip()]
    if not lines_with_content: return False
    pipe_lines = sum(1 for l in lines_with_content if "|" in l)
    return pipe_lines == 0  # 파이프 구분자가 전혀 없으면 순수 영어


# ─────────────────────────────────────────────────────────────────────────────
# 홈 "오늘 할 일" 카드
# ─────────────────────────────────────────────────────────────────────────────

def _render_today_card(student_id: int | None):
    """로그인한 학생에게 오늘 할 일 요약 카드를 보여준다."""
    if not student_id:
        return

    from study_db import get_today_summary
    from datetime import date

    try:
        s = get_today_summary(student_id)
    except Exception:
        return

    due       = s["due"]
    mastered  = s["mastered"]
    streak    = s["streak"]
    sessions  = s["today_sessions"]
    avg       = s["today_avg"]
    wrong     = s["word_wrong"]

    import datetime as _dt
    hour = _dt.datetime.now().hour
    if hour < 12:   greet = "좋은 아침이에요"
    elif hour < 18: greet = "안녕하세요"
    else:           greet = "오늘도 수고했어요"

    if streak == 0:    streak_msg = "오늘 첫 학습을 시작해봐요!"
    elif streak < 3:   streak_msg = f"{streak}일 연속 학습 중"
    elif streak < 7:   streak_msg = f"{streak}일 연속! 불타고 있어요"
    else:              streak_msg = f"{streak}일 연속! 전설이에요"

    actions = []
    if due > 0: actions.append(f"복습 {due}개 ")
    actions.append("단어 퀴즈 ")
    actions.append("오답노트 확인" if wrong > 0 else "내신문제 도전")
    action_str = " → ".join(actions)

    # 색상 변수 분리 (중첩 f-string 금지)
    due_color   = "#FCA5A5" if due > 0 else "#86EFAC"
    avg_val     = f"{avg:.0f}점" if avg is not None else "-"
    avg_color   = "#16A34A" if avg is not None else "#9CA3AF"
    avg_size    = "1.4rem" if avg is not None else "1.1rem"

    icon_zap      = icon("zap",        12, "rgba(255,255,255,0.55)")
    icon_sparkles = icon("sparkles",   14, "#FCD34D")
    icon_refresh  = icon("refresh-cw", 11, "rgba(255,255,255,0.8)")
    icon_book     = icon("book-open",  13, "#A5B4FC")

    card_html = (
        '<div style="background:linear-gradient(135deg,#1E1B4B 0%,#312E81 55%,#4C1D95 100%);'
        'border-radius:16px;padding:20px 22px;margin-bottom:20px;'
        'box-shadow:0 8px 28px rgba(30,27,75,0.30);">'

        '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px;">'
        '<div>'
        '<div style="font-size:0.75rem;color:rgba(255,255,255,0.55);font-weight:600;'
        'letter-spacing:0.4px;margin-bottom:4px;">'
        + icon_zap + ' 오늘 할 일</div>'
        '<div style="font-size:1.05rem;font-weight:800;color:white;">'
        + greet + ' ' + icon_sparkles + '</div>'
        '</div>'
        '<div style="background:rgba(255,255,255,0.1);border-radius:20px;'
        'padding:4px 12px;font-size:0.72rem;font-weight:700;color:rgba(255,255,255,0.8);">'
        + icon_refresh + ' ' + streak_msg +
        '</div></div>'

        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">'

        '<div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:12px 8px;text-align:center;">'
        '<div style="font-size:1.6rem;font-weight:900;color:' + due_color + ';">' + str(due) + '</div>'
        '<div style="font-size:0.62rem;color:rgba(255,255,255,0.55);margin-top:3px;">복습 대기</div>'
        '</div>'

        '<div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:12px 8px;text-align:center;">'
        '<div style="font-size:1.6rem;font-weight:900;color:#86EFAC;">' + str(mastered) + '</div>'
        '<div style="font-size:0.62rem;color:rgba(255,255,255,0.55);margin-top:3px;">마스터</div>'
        '</div>'

        '<div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:12px 8px;text-align:center;">'
        '<div style="font-size:1.6rem;font-weight:900;color:#FDE68A;">' + str(wrong) + '</div>'
        '<div style="font-size:0.62rem;color:rgba(255,255,255,0.55);margin-top:3px;">오답 단어</div>'
        '</div>'

        '<div style="background:rgba(255,255,255,0.08);border-radius:12px;padding:12px 8px;text-align:center;">'
        '<div style="font-size:' + avg_size + ';font-weight:900;color:' + avg_color + ';">' + avg_val + '</div>'
        '<div style="font-size:0.65rem;color:rgba(255,255,255,0.55);margin-top:2px;">오늘 평균</div>'
        '</div>'

        '</div>'

        '<div style="background:rgba(255,255,255,0.07);border-radius:10px;'
        'padding:10px 14px;display:flex;align-items:center;gap:8px;">'
        + icon_book +
        '<span style="font-size:0.8rem;color:rgba(255,255,255,0.75);font-weight:600;">'
        '오늘 권장: ' + action_str + '</span>'
        '</div>'

        '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)

    # 복습 대기가 있으면 바로가기 버튼
    if due > 0:
        if st.button(f"지금 바로 복습하기 ({due}개)", type="primary",
                     key="home_review_btn", use_container_width=True):
            st.session_state["page"]       = "__study__"
            st.session_state["study_page"] = "복습하기"
            st.rerun()
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# 반반노트 인쇄 뷰 생성기
# ─────────────────────────────────────────────────────────────────────────────

def _render_banban_print(note_id: int):
    """라이브러리에서 노트 선택 → 인쇄용 반반노트 워크시트 렌더링."""
    nd = get_note(note_id)
    if not nd:
        st.error("노트 데이터를 불러올 수 없습니다.")
        return

    words     = nd.get("words", [])
    dialogues = nd.get("dialogues", [])
    td        = nd.get("text_data", {})
    sentences = td.get("sentences", [])
    title     = nd.get("title", "반반노트")
    grade     = nd.get("grade", "")
    publisher = nd.get("publisher", "")
    chapter   = nd.get("chapter", "")

    # ── 인쇄 옵션 선택 ────────────────────────────────────────────
    st.markdown(
        f'<div style="background:#F0F4FF;border:1px solid #C7D2FE;border-radius:12px;'
        f'padding:16px 20px;margin:10px 0 6px;">'
        f'<div style="font-size:0.9rem;font-weight:800;color:#4F46E5;margin-bottom:10px;">'
        f'{icon("printer",16,"#4F46E5")} 반반노트 출력 설정</div>',
        unsafe_allow_html=True,
    )

    # FREE 플랜: 이번 달 남은 출력 횟수 안내
    if not has_plan("pro"):
        _pok, _pused, _plimit = can_print()
        st.markdown(
            f'<div style="font-size:0.74rem;color:#64748B;margin:-2px 0 6px;">'
            f'이번 달 출력 <b style="color:#4F46E5;">{_pused}/{_plimit}회</b> 사용</div>',
            unsafe_allow_html=True,
        )

    oc1, oc2, oc3 = st.columns(3)
    print_type  = oc1.selectbox(
        "출력 유형",
        ["단어 빈칸채우기", "대화문 빈칸채우기", "본문 빈칸채우기", "전체 종합"],
        key=f"print_type_{note_id}",
    )
    blank_side  = oc2.selectbox(
        "빈칸 방향",
        ["한글 가리기 (영→한)", "영어 가리기 (한→영)", "모두 보기"],
        key=f"print_blank_{note_id}",
    )
    cols_count  = oc3.selectbox(
        "단어 컬럼 수",
        [2, 3, 4],
        index=1,
        key=f"print_cols_{note_id}",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── HTML 생성 ─────────────────────────────────────────────────
    hide_kr  = blank_side == "한글 가리기 (영→한)"
    hide_en  = blank_side == "영어 가리기 (한→영)"
    show_all = blank_side == "모두 보기"

    def _blank(text: str, hide: bool) -> str:
        if hide:
            return '<span style="border-bottom:1.5px solid #374151;display:inline-block;min-width:80px;color:transparent;">hidden</span>'
        return f'<span>{text}</span>'

    # ─ 단어 HTML ─
    word_html = ""
    if words and print_type in ("단어 빈칸채우기", "전체 종합"):
        word_rows = ""
        for en, kr in words:
            en_cell = _blank(en, hide_en)
            kr_cell = _blank(kr, hide_kr)
            word_rows += (
                f'<tr>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #E5E7EB;font-size:13px;">{en_cell}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #E5E7EB;font-size:13px;color:#374151;">{kr_cell}</td>'
                f'</tr>'
            )
        word_html = f"""
<div class="section">
  <div class="section-title">단어 (Vocabulary) — {len(words)}개</div>
  <table style="width:100%;border-collapse:collapse;">
    <thead>
      <tr style="background:#F8FAFC;">
        <th style="padding:6px 8px;text-align:left;font-size:12px;color:#6B7280;border-bottom:2px solid #E5E7EB;">English</th>
        <th style="padding:6px 8px;text-align:left;font-size:12px;color:#6B7280;border-bottom:2px solid #E5E7EB;">한국어</th>
      </tr>
    </thead>
    <tbody>{word_rows}</tbody>
  </table>
</div>"""

    # ─ 대화문 HTML ─
    dlg_html = ""
    if dialogues and print_type in ("대화문 빈칸채우기", "전체 종합"):
        dlg_body = ""
        for d in dialogues:
            dlg_body += f'<div class="dlg-title">[{d["title"]}]</div>'
            for i, (en, kr) in enumerate(d["lines"]):
                en_cell = _blank(en, hide_en)
                kr_cell = _blank(kr, hide_kr)
                dlg_body += (
                    f'<div class="dlg-line">'
                    f'<span class="dlg-num">{i+1}.</span>'
                    f'<span class="dlg-en">{en_cell}</span>'
                    f'<span class="dlg-kr">{kr_cell}</span>'
                    f'</div>'
                )
        dlg_html = f"""
<div class="section">
  <div class="section-title">대화문 (Dialogue)</div>
  {dlg_body}
</div>"""

    # ─ 본문 HTML ─
    text_html = ""
    if sentences and print_type in ("본문 빈칸채우기", "전체 종합"):
        sent_body = ""
        if td.get("title_en"):
            sent_body += f'<div class="text-title">{td["title_en"]} <span style="color:#9CA3AF;font-size:12px;">{td.get("title_kr","")}</span></div>'
        for i, (en, kr) in enumerate(sentences):
            en_cell = _blank(en, hide_en)
            kr_cell = _blank(kr, hide_kr)
            sent_body += (
                f'<div class="sent-line">'
                f'<span class="sent-num">{i+1:02d}</span>'
                f'<span class="sent-en">{en_cell}</span>'
                f'<span class="sent-kr">{kr_cell}</span>'
                f'</div>'
            )
        text_html = f"""
<div class="section">
  <div class="section-title">본문 (Reading)</div>
  {sent_body}
</div>"""

    meta_str = " | ".join(filter(None, [grade, publisher, chapter]))
    full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title} — 반반노트</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
        color: #1F2937; background: #fff; padding: 28px 36px; font-size: 13px; }}
.header {{ border-bottom: 2.5px solid #1E293B; padding-bottom: 12px; margin-bottom: 20px; }}
.header h1 {{ font-size: 20px; font-weight: 900; letter-spacing: -0.5px; }}
.header .meta {{ font-size: 11px; color: #6B7280; margin-top: 4px; }}
.info-row {{ display: flex; gap: 24px; margin: 14px 0 20px; font-size: 12px; }}
.info-box {{ border-bottom: 1.5px solid #374151; min-width: 120px; padding: 2px 4px; }}
.info-label {{ font-size: 10px; color: #9CA3AF; margin-bottom: 2px; }}
.section {{ margin-bottom: 28px; }}
.section-title {{ font-size: 13px; font-weight: 800; color: #4F46E5;
                  border-left: 4px solid #4F46E5; padding-left: 8px;
                  margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }}
.dlg-title {{ font-size: 12px; font-weight: 700; color: #374151;
              margin: 10px 0 4px; background: #F8FAFC; padding: 4px 8px; border-radius: 4px; }}
.dlg-line {{ display: flex; align-items: baseline; gap: 8px;
             padding: 4px 0; border-bottom: 1px solid #F1F5F9; }}
.dlg-num {{ font-size: 11px; color: #9CA3AF; min-width: 18px; flex-shrink: 0; }}
.dlg-en {{ flex: 1; font-size: 13px; }}
.dlg-kr {{ flex: 1; font-size: 12px; color: #6B7280; }}
.text-title {{ font-weight: 800; margin-bottom: 10px; font-size: 14px; }}
.sent-line {{ display: flex; align-items: baseline; gap: 8px;
              padding: 5px 0; border-bottom: 1px solid #F1F5F9; }}
.sent-num {{ font-size: 11px; color: #9CA3AF; min-width: 22px; flex-shrink: 0; font-weight: 700; }}
.sent-en {{ flex: 2; font-size: 13px; line-height: 1.5; }}
.sent-kr {{ flex: 1.5; font-size: 12px; color: #6B7280; line-height: 1.5; }}
.print-btn {{ display:inline-flex; align-items:center; gap:8px;
              background:#4F46E5; color:white; border:none; border-radius:8px;
              padding:10px 22px; font-size:14px; font-weight:700; cursor:pointer;
              margin: 0 0 24px; box-shadow:0 2px 10px rgba(79,70,229,0.3); }}
.print-btn:hover {{ background:#4338CA; }}
@media print {{
  .print-btn {{ display: none !important; }}
  body {{ padding: 10px 18px; }}
  .header h1 {{ font-size: 17px; }}
}}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <div class="meta">{meta_str} &nbsp;·&nbsp; 반반 BanBan 영어 학습지</div>
</div>
<div class="info-row">
  <div><div class="info-label">학년/반</div><div class="info-box" style="min-width:100px;">&nbsp;</div></div>
  <div><div class="info-label">번호</div><div class="info-box" style="min-width:60px;">&nbsp;</div></div>
  <div><div class="info-label">이름</div><div class="info-box" style="min-width:120px;">&nbsp;</div></div>
  <div><div class="info-label">날짜</div><div class="info-box" style="min-width:100px;">&nbsp;</div></div>
  <div><div class="info-label">점수</div><div class="info-box" style="min-width:60px;">&nbsp;</div></div>
</div>
<button class="print-btn" onclick="window.print()">🖨️ 인쇄하기</button>
{word_html}
{dlg_html}
{text_html}
</body>
</html>"""

    # ── 엑셀 다운로드 (기존 generator 사용) ──────────────────────
    meta = {
        "grade":     nd.get("grade", ""),
        "publisher": nd.get("publisher", ""),
        "author":    nd.get("author", ""),
        "chapter":   nd.get("chapter", ""),
        "title":     title,
        "tags":      nd.get("tags", ""),
    }
    try:
        xlsx_bytes = generate(meta, words, dialogues, td)
        dc1, dc2 = st.columns([2, 3])
        dc1.download_button(
            label="📥 반반노트 엑셀 다운로드 (.xlsx)",
            data=xlsx_bytes,
            file_name=f"반반노트_{title}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl_xlsx_{note_id}",
            use_container_width=True,
            type="primary",
        )
    except Exception as e:
        st.error(f"엑셀 생성 오류: {e}")

    # ── HTML 인쇄용 미리보기 (브라우저에서 직접 인쇄) ────────────
    import base64
    b64 = base64.b64encode(full_html.encode("utf-8")).decode()
    st.markdown(
        f'<div style="font-size:0.8rem;color:#6B7280;margin:12px 0 4px;">'
        f'아래 미리보기에서 <b>🖨️ 인쇄하기</b> 버튼을 누르면 바로 프린트할 수 있습니다.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<iframe src="data:text/html;base64,{b64}" '
        f'width="100%" height="620" style="border:1px solid #E2E8F0;border-radius:12px;'
        f'margin-top:4px;background:white;">'
        f'</iframe>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI 자동 정리 블록 — 원문 붙여넣기 → 구조화(+번역) → 수정 폼에 주입
# (반드시 대상 text_area 위젯보다 먼저 호출해야 session_state 주입이 안전)
# ─────────────────────────────────────────────────────────────────────────────

def _ai_organize_block(label: str, ctype: str, raw_key: str,
                       target_key: str, to_text) -> None:
    api_cfg = _api_config()
    with st.expander(f"원문 붙여넣고 AI로 {label} 자동 정리", expanded=False):
        if not api_cfg:
            st.caption("AI 정리는 API 키가 설정되어야 사용할 수 있어요.")
            return
        st.caption("형식을 몰라도 돼요. 영어만 붙여넣으면 한국어 번역까지 AI가 만들어줘요.")
        raw = st.text_area(f"{label} 원문", key=raw_key, height=120,
                           label_visibility="collapsed",
                           placeholder="여기에 원문을 붙여넣으세요…")
        c1, c2 = st.columns([3, 2])
        mode = c1.radio("적용 방식", ["기존에 추가", "전체 교체"],
                        horizontal=True, key=raw_key + "_mode",
                        label_visibility="collapsed")
        if c2.button("AI 정리", key=raw_key + "_btn", use_container_width=True,
                     type="primary"):
            if not raw.strip():
                st.warning("원문을 입력해주세요.")
                return
            from ocr_extractor import organize_text_input
            with st.spinner(f"AI가 {label}을(를) 정리하는 중…"):
                try:
                    result  = organize_text_input(raw, ctype, api_cfg)
                    new_txt = to_text(result)
                except Exception as e:
                    st.error(f"정리 실패: {e}")
                    return
            if not new_txt.strip():
                st.warning("정리 결과가 비었어요. 원문을 확인해주세요.")
                return
            if mode == "기존에 추가":
                cur    = st.session_state.get(target_key, "")
                merged = (cur.rstrip() + "\n\n" + new_txt).strip() if cur.strip() else new_txt
            else:
                merged = new_txt
            st.session_state[target_key] = merged
            st.rerun()


# PAGE 1: 라이브러리
# ─────────────────────────────────────────────────────────────────────────────

def page_library():
    st.markdown(title_md("book-open", "반반노트 라이브러리"), unsafe_allow_html=True)

    # 복제 성공 알림
    if st.session_state.pop("lib_dup_toast", None) is not None:
        st.success("노트를 복제했어요. 목록에서 '(복사본)'을 찾아 자유롭게 수정하세요.")

    # ── 현재 사용자 + 뷰 선택 (내 노트 / 공용 자료실) ──────────────
    _lib_user = _auth.current_user()
    _lib_uid  = _lib_user.id if _lib_user else None
    _lib_admin = _auth.current_role() == "admin"

    lib_view = st.radio(
        "보기", ["📁 내 노트", "🌐 공용 자료실"], horizontal=True, key="lib_view",
        label_visibility="collapsed",
    )
    _mine_view = lib_view.startswith("📁")
    st.caption(
        "내가 만든 노트만 보여요. 수정·삭제할 수 있어요."
        if _mine_view else
        "다른 선생님들이 공개한 노트예요. '복제'로 내 것으로 가져와 수정하세요."
    )
    _lib_scope = "mine" if _mine_view else "public"

    # ── 학년 탭 ────────────────────────────────────────────────────
    _GRADE_TABS = ["전체", "중1", "중2", "중3", "고1", "고2", "고3"]
    _tab_objs   = st.tabs(_GRADE_TABS)

    # 세션에서 선택 학년 유지
    if "lib_grade_tab" not in st.session_state:
        st.session_state["lib_grade_tab"] = "전체"

    # 각 탭 안에서 처리
    for _tab_obj, _grade_label in zip(_tab_objs, _GRADE_TABS):
        with _tab_obj:
            st.session_state["lib_grade_tab"] = _grade_label

            # ── 출판사 / 유형 / 검색 필터 (학년 선택 후 표시) ──────
            all_pubs = ["전체"] + get_all_values("publisher")
            all_ctypes = ["전체", "단어", "대화문", "본문"]

            fc1, fc2, fc3 = st.columns([2, 2, 3])
            f_pub    = fc1.selectbox("출판사", all_pubs,   index=0,
                                     key=f"f_pub_{_grade_label}")
            f_ctype  = fc2.selectbox("유형",   all_ctypes, index=0,
                                     key=f"f_ctype_{_grade_label}")
            f_search = fc3.text_input("제목 검색", placeholder="검색어...",
                                      key=f"f_search_{_grade_label}")

            notes = list_notes(
                grade        = "" if _grade_label == "전체" else _grade_label,
                publisher    = "" if f_pub        == "전체" else f_pub,
                content_type = "" if f_ctype      == "전체" else f_ctype,
                search       = f_search,
                scope        = "all" if (_lib_admin and _mine_view) else _lib_scope,
                owner_id     = _lib_uid,
            )

            hc1, hc2, _, hc4 = st.columns([2, 2, 2, 4])
            if hc1.button("전체 선택", use_container_width=True,
                          key=f"sel_all_{_grade_label}"):
                st.session_state["selected_ids"] = {n["id"] for n in notes}
                st.rerun()
            if hc2.button("선택 해제", use_container_width=True,
                          key=f"sel_none_{_grade_label}"):
                st.session_state["selected_ids"] = set()
                st.rerun()
            hc4.markdown(
                f'<div style="padding:6px 0;font-size:.9rem;color:#6b7280;">'
                f'총 <b>{len(notes)}</b>개 &nbsp;/&nbsp; '
                f'<b style="color:#1a4fa0;">{len(st.session_state["selected_ids"])}</b>개 선택됨</div>',
                unsafe_allow_html=True,
            )

            if not notes:
                st.markdown(
                    f'<div style="text-align:center;padding:3rem 0;color:#9ca3af;">'
                    f'{icon("book-open",40,"#d1d5db")}'
                    f'<br><span style="font-size:1rem;">'
                    f'{"이 학년에" if _grade_label != "전체" else "저장된"} 노트가 없습니다.</span><br>'
                    f'<span style="font-size:.85rem;">새 노트 추가 메뉴에서 노트를 만들어보세요.</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                continue

            st.divider()
            selected   = st.session_state["selected_ids"]
            edit_id    = st.session_state["lib_edit_id"]

            _GRADES = ["중1","중2","중3","고1","고2","고3"]
            _PUBS   = ["YBM","NE능률","천재교육","동아출판","비상교육","미래엔","지학사","금성출판사","기타"]

            # ── 페이지네이션 ────────────────────────────────────
            PER_PAGE   = 10
            page_key   = f"lib_page_{_grade_label}"
            total_pgs  = max(1, (len(notes) + PER_PAGE - 1) // PER_PAGE)
            cur_pg     = st.session_state.get(page_key, 1)
            cur_pg     = max(1, min(cur_pg, total_pgs))   # 범위 보정
            st.session_state[page_key] = cur_pg
            start      = (cur_pg - 1) * PER_PAGE
            page_notes = notes[start:start + PER_PAGE]

            for note in page_notes:
                nid = note["id"]

                # ── 노트 행 ──────────────────────────────────
                c_chk, c_info, c_act = st.columns([1, 7, 5])
                with c_chk:
                    checked = st.checkbox("", value=(nid in selected), key=f"chk_{_grade_label}_{nid}")
                    if checked: selected.add(nid)
                    else:       selected.discard(nid)

                with c_info:
                    ctype    = note["content_type"]
                    icon_map = {"단어":"file-text","대화문":"message-circle","본문":"book","전체":"layers"}
                    cnt      = note["item_count"]
                    unit     = {"단어":"개 단어","대화문":"줄","본문":"문장","전체":"개 항목"}.get(ctype,"개")
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:7px;flex-wrap:wrap;">'
                        f'{icon(icon_map.get(ctype,"file-text"),14,"#6b7280")}'
                        f'<b style="font-size:0.95rem;">{note["title"]}</b>'
                        f'{ctype_tag(ctype)}'
                        f'<span style="color:#9ca3af;font-size:.8rem;">'
                        f'{cnt}{unit} · {note["created_at"]}</span></div>',
                        unsafe_allow_html=True,
                    )
                    if note.get("tags"):
                        st.caption(f"  {note['tags']}")

                with c_act:
                    is_editing  = (edit_id == nid)
                    is_printing = (st.session_state.get("lib_print_id") == nid)
                    # 편집·삭제는 제작자(또는 관리자)만. 공용 자료실의 남 노트는 복제만.
                    is_mine     = _lib_admin or (note.get("owner_id") == _lib_uid)

                    if is_mine:
                        bvis, ba1, ba2, ba3, ba4 = st.columns([1.8, 1, 1, 1, 1])
                    else:
                        ba3, ba4 = st.columns(2)

                    # ── 공용 공개 토글 (내 노트만) — 켜면 공용 자료실 공개 ──
                    if is_mine:
                        with bvis:
                            _is_pub = note.get("visibility") == "public"
                            _new_pub = st.toggle(
                                "Public", value=_is_pub,
                                key=f"vis_{_grade_label}_{nid}",
                                help="켜면 공용 자료실에 공개돼 다른 선생님이 복제해 쓸 수 있어요. "
                                     "끄면 나와 내 학생만 봐요.",
                            )
                            if _new_pub != _is_pub:
                                update_note(nid, visibility="public" if _new_pub else "private")
                                st.rerun()

                    # ── 수정 (내 노트만) ─────────────────────────
                    if is_mine:
                        edit_label = "닫기" if is_editing else "수정"
                        if ba1.button(edit_label, key=f"edit_btn_{_grade_label}_{nid}", use_container_width=True):
                            if is_editing:
                                st.session_state["lib_edit_id"] = None
                            else:
                                nd_pre = get_note(nid)
                                if nd_pre:
                                    st.session_state[f"etitle_{_grade_label}_{nid}"]  = nd_pre.get("title", "")
                                    st.session_state[f"egrade_{_grade_label}_{nid}"]  = nd_pre.get("grade", "중1")
                                    st.session_state[f"epub_{_grade_label}_{nid}"]    = nd_pre.get("publisher", "YBM")
                                    st.session_state[f"eauthor_{_grade_label}_{nid}"] = nd_pre.get("author", "")
                                    st.session_state[f"echap_{_grade_label}_{nid}"]   = nd_pre.get("chapter", "")
                                    st.session_state[f"etags_{_grade_label}_{nid}"]   = nd_pre.get("tags", "")
                                    st.session_state[f"ewi_{_grade_label}_{nid}"] = words_to_text(nd_pre.get("words", []))
                                    st.session_state[f"edi_{_grade_label}_{nid}"] = dlg_to_text(nd_pre.get("dialogues", []))
                                    td_pre = nd_pre.get("text_data", {})
                                    st.session_state[f"eti_{_grade_label}_{nid}"] = (
                                        text_to_text(td_pre) if td_pre.get("sentences") else ""
                                    )
                                st.session_state["lib_edit_id"] = nid
                            st.rerun()

                        # ── 삭제 (내 노트만) ─────────────────────
                        with ba2:
                            if confirm_delete_btn(
                                "삭제", key=f"del_{_grade_label}_{nid}",
                                item_name=note.get("title", ""),
                                use_container_width=True,
                            ):
                                delete_note(nid)
                                selected.discard(nid)
                                if edit_id == nid:
                                    st.session_state["lib_edit_id"] = None
                                st.rerun()

                    # ── 반반노트 출력 버튼 (공통) — 무료 플랜 월 출력 한도 게이팅 ──
                    print_label = "닫기" if is_printing else "출력"
                    if ba3.button(print_label, key=f"print_btn_{_grade_label}_{nid}", use_container_width=True):
                        if is_printing:
                            st.session_state["lib_print_id"] = None
                        else:
                            _pok, _pu, _pl = can_print()
                            if _pok:
                                increment_print_usage()          # 출력 1회 차감
                                st.session_state["lib_print_id"] = nid
                            else:
                                st.session_state["lib_print_id"] = f"denied_{nid}"
                        st.rerun()

                    # ── 복제 버튼 — 내 것으로 가져오기 (공통) ────
                    dup_label = "복제" if is_mine else "내 것으로"
                    if ba4.button(dup_label, key=f"dup_btn_{_grade_label}_{nid}",
                                  use_container_width=True,
                                  help="이 노트를 내 사본으로 복제해 수정할 수 있어요"):
                        new_id = duplicate_note(nid, owner_id=_lib_uid)
                        if new_id:
                            st.session_state["lib_dup_toast"] = note.get("title", "")
                        st.rerun()

                # ── 편집 폼 or 내용 보기 ──────────────────────
                if edit_id == nid:
                    st.markdown(
                        f'<div style="border-left:3px solid #3b82f6;'
                        f'padding:2px 0 2px 10px;margin:2px 0 4px 0;'
                        f'color:#1a4fa0;font-weight:700;font-size:.88rem;">'
                        f'{icon("pencil",13,"#3b82f6")} 수정 중</div>',
                        unsafe_allow_html=True,
                    )
                    em1, em2, em3, em4, em5 = st.columns(5)
                    e_title  = em1.text_input("제목",    key=f"etitle_{_grade_label}_{nid}")
                    e_grade  = em2.selectbox("학년",     _GRADES, key=f"egrade_{_grade_label}_{nid}")
                    e_pub    = em3.selectbox("출판사",   _PUBS,   key=f"epub_{_grade_label}_{nid}")
                    e_author = em4.text_input("저자",    key=f"eauthor_{_grade_label}_{nid}")
                    e_chap   = em5.text_input("과",      key=f"echap_{_grade_label}_{nid}")
                    e_tags   = st.text_input(
                        "태그 (쉼표 구분)", key=f"etags_{_grade_label}_{nid}",
                        placeholder="예: 4과,기말고사,중요",
                    )
                    etab_w, etab_d, etab_t = st.tabs(["단어", "대화문", "본문"])
                    with etab_w:
                        st.markdown('<div class="hint-box">한 줄에 하나씩 &nbsp;<code>영어단어|한글뜻</code></div>', unsafe_allow_html=True)
                        _ai_organize_block(
                            "단어", "단어",
                            raw_key=f"eraw_w_{_grade_label}_{nid}",
                            target_key=f"ewi_{_grade_label}_{nid}",
                            to_text=lambda r: words_to_text(r.get("words", [])),
                        )
                        ew_text = st.text_area("단어 내용", key=f"ewi_{_grade_label}_{nid}", height=200, label_visibility="collapsed")
                        e_words = parse_words(ew_text)
                        st.caption(f"{len(e_words)}개 단어")
                    with etab_d:
                        st.markdown('<div class="hint-box"><code>[대화문1]</code> 제목 줄 → <code>영어|한국어</code></div>', unsafe_allow_html=True)
                        _ai_organize_block(
                            "대화문", "대화문",
                            raw_key=f"eraw_d_{_grade_label}_{nid}",
                            target_key=f"edi_{_grade_label}_{nid}",
                            to_text=lambda r: dlg_to_text(r.get("dialogues", [])),
                        )
                        ed_text = st.text_area("대화문 내용", key=f"edi_{_grade_label}_{nid}", height=200, label_visibility="collapsed")
                        e_dlgs  = parse_dialogues(ed_text)
                        st.caption(f"{len(e_dlgs)}개 대화문")
                    with etab_t:
                        st.markdown('<div class="hint-box"><b>첫 줄:</b> <code>영어제목|한글제목</code> / 이후: <code>영어문장|한글문장</code></div>', unsafe_allow_html=True)
                        _ai_organize_block(
                            "본문", "본문",
                            raw_key=f"eraw_t_{_grade_label}_{nid}",
                            target_key=f"eti_{_grade_label}_{nid}",
                            to_text=lambda r: text_to_text(r),
                        )
                        et_text = st.text_area("본문 내용", key=f"eti_{_grade_label}_{nid}", height=200, label_visibility="collapsed")
                        e_tdata = parse_text(et_text)
                        st.caption(f"{len(e_tdata.get('sentences',[]))}개 문장")

                    sv_col, cn_col, _ = st.columns([2, 2, 6])
                    if sv_col.button("저장하기", type="primary", key=f"save_edit_{_grade_label}_{nid}", use_container_width=True):
                        has_w = len(e_words) > 0
                        has_d = len(e_dlgs)  > 0
                        has_t = len(e_tdata.get("sentences", [])) > 0
                        types_cnt = sum([has_w, has_d, has_t])
                        if types_cnt > 1:   new_ct = "전체"
                        elif has_w:         new_ct = "단어"
                        elif has_d:         new_ct = "대화문"
                        elif has_t:         new_ct = "본문"
                        else:               new_ct = note.get("content_type", "전체")
                        update_note(nid, title=e_title, grade=e_grade, publisher=e_pub,
                                    author=e_author, chapter=e_chap, tags=e_tags,
                                    content_type=new_ct, words=e_words,
                                    dialogues=e_dlgs, text_data=e_tdata)
                        st.session_state["lib_edit_id"] = None
                        st.rerun()
                    if cn_col.button("취소", key=f"cancel_edit_{_grade_label}_{nid}", use_container_width=True):
                        st.session_state["lib_edit_id"] = None
                        st.rerun()

                else:
                    with st.expander("내용 보기", expanded=False):
                        nd = get_note(nid)
                        if nd is None:
                            st.caption("데이터를 불러올 수 없습니다.")
                        else:
                            tab_labels = []
                            if nd.get("words"):         tab_labels.append("단어")
                            if nd.get("dialogues"):     tab_labels.append("대화문")
                            td = nd.get("text_data", {})
                            if td.get("sentences"):     tab_labels.append("본문")
                            if not tab_labels:
                                st.caption("저장된 내용이 없습니다.")
                            else:
                                tabs = st.tabs(tab_labels)
                                ti   = 0
                                if nd.get("words"):
                                    with tabs[ti]:
                                        for en, kr in nd["words"][:20]:
                                            st.markdown(f'<div style="padding:2px 0;"><b style="color:#1d4ed8;">{en}</b><span style="color:#9ca3af;"> → </span>{kr}</div>', unsafe_allow_html=True)
                                        if len(nd["words"]) > 20:
                                            st.caption(f"… 외 {len(nd['words'])-20}개")
                                    ti += 1
                                if nd.get("dialogues"):
                                    with tabs[ti]:
                                        for d in nd["dialogues"]:
                                            st.markdown(f"**{d['title']}**")
                                            for en, kr in d["lines"]:
                                                st.markdown(f'<div style="padding:1px 0 1px 8px;border-left:3px solid #dbeafe;"><span style="font-size:.85rem;">{en}</span><br><span style="font-size:.82rem;color:#6b7280;">{kr}</span></div>', unsafe_allow_html=True)
                                    ti += 1
                                if td.get("sentences"):
                                    with tabs[ti]:
                                        if td.get("title_en"):
                                            st.markdown(f'<b>{td["title_en"]}</b> <span style="color:#9ca3af;font-size:.85rem;">{td.get("title_kr","")}</span>', unsafe_allow_html=True)
                                            st.divider()
                                        for en, kr in td["sentences"][:15]:
                                            st.markdown(f'<div style="padding:3px 0;"><span style="font-size:.88rem;">{en}</span><br><span style="font-size:.84rem;color:#6b7280;">{kr}</span></div>', unsafe_allow_html=True)
                                        if len(td["sentences"]) > 15:
                                            st.caption(f"… 외 {len(td['sentences'])-15}개 문장")

                # ── 반반노트 출력 뷰 ─────────────────────────────
                if st.session_state.get("lib_print_id") == nid:
                    _render_banban_print(nid)
                elif st.session_state.get("lib_print_id") == f"denied_{nid}":
                    _pu = can_print()[1]; _pl = can_print()[2]
                    st.warning(f"무료 플랜은 이번 달 출력 {_pl}회를 모두 사용했어요 "
                               f"(현재 {_pu}회). PRO로 업그레이드하면 무제한이에요.")
                    upgrade_banner("pro", compact=True)

                st.markdown('<hr style="margin:6px 0 4px 0;border:none;border-top:1px solid #f1f5f9;">', unsafe_allow_html=True)

            st.session_state["selected_ids"] = selected

            # ── 번호식 페이지네이션 (CRM 키트 스타일) ──────────────
            if total_pgs > 1:
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

                # 윈도우: 현재 페이지 주변 ±2 + 양끝
                window = sorted(set(
                    [1, total_pgs]
                    + list(range(max(1, cur_pg - 2), min(total_pgs, cur_pg + 2) + 1))
                ))
                # 페이지 토큰 구성 ("…" 삽입)
                tokens, prev = [], 0
                for p in window:
                    if prev and p - prev > 1:
                        tokens.append("…")
                    tokens.append(p)
                    prev = p

                # 레이아웃: [이전] [번호들...] [다음]
                col_specs = [1] + [0.6] * len(tokens) + [1]
                cols = st.columns(col_specs)

                with cols[0]:
                    if st.button("← 이전", key=f"pg_prev_{_grade_label}",
                                 use_container_width=True, disabled=(cur_pg <= 1)):
                        st.session_state[page_key] = cur_pg - 1
                        st.rerun()

                for i, tk in enumerate(tokens):
                    with cols[i + 1]:
                        if tk == "…":
                            st.markdown(
                                "<div style='text-align:center;color:#94A3B8;"
                                "padding:8px 0;'>…</div>", unsafe_allow_html=True)
                        elif tk == cur_pg:
                            # 활성 페이지 — 솔리드 (primary 버튼)
                            st.button(str(tk), key=f"pg_{_grade_label}_{tk}",
                                      use_container_width=True, type="primary")
                        else:
                            if st.button(str(tk), key=f"pg_{_grade_label}_{tk}",
                                         use_container_width=True):
                                st.session_state[page_key] = tk
                                st.rerun()

                with cols[-1]:
                    if st.button("다음 →", key=f"pg_next_{_grade_label}",
                                 use_container_width=True, disabled=(cur_pg >= total_pgs)):
                        st.session_state[page_key] = cur_pg + 1
                        st.rerun()

                st.markdown(
                    f'<div style="text-align:center;font-size:0.76rem;color:#94A3B8;'
                    f'margin-top:4px;">총 {len(notes)}개 · {cur_pg}/{total_pgs} 페이지</div>',
                    unsafe_allow_html=True,
                )
    st.divider()

    if selected:
        if st.button(f"선택된 {len(selected)}개 노트 합치기 →",
                     type="primary", use_container_width=True):
            st.session_state["page"] = "합치기 & 다운로드"
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2: 새 노트 추가
# ─────────────────────────────────────────────────────────────────────────────

def page_add_note():
    st.markdown(title_md("plus-circle", "새 노트 추가"), unsafe_allow_html=True)

    # ── 교과서 정보 ──────────────────────────────────────────
    with st.expander("교과서 정보", expanded=True):
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        grade     = mc1.selectbox("학년",
                       ["중1","중2","중3","고1","고2","고3"], key="add_grade")
        publisher = mc2.selectbox("출판사",
                       ["YBM","NE능률","천재교육","동아출판","비상교육","미래엔","지학사","금성출판사","기타"],
                       key="add_pub")
        author    = mc3.text_input("저자",
                       value=st.session_state.get("_ocr_meta", {}).get("author", ""),
                       key="add_author")
        chapter   = mc4.text_input("과",
                       value=st.session_state.get("_ocr_meta", {}).get("chapter", ""),
                       key="add_chapter")
        ctype     = mc5.selectbox("콘텐츠 유형",
                       ["단어","대화문","본문","전체(단어+대화+본문)"], key="add_ctype")
        tags      = st.text_input("태그 (쉼표 구분)",
                       placeholder="예: 4과,기말고사,중요", key="add_tags")

    meta       = {"grade": grade, "publisher": publisher,
                  "author": author, "chapter": chapter, "section": "본문"}
    # 멀티스캔 자동 제목이 있으면 사용
    _auto_title = st.session_state.pop("_auto_note_title", None)
    base_title  = _auto_title if _auto_title else f"{grade} {publisher} {author} {chapter}과"

    # ct 정규화 (여기서 한 번만 계산)
    ct_map = {"단어":"단어","대화문":"대화문","본문":"본문","전체(단어+대화+본문)":"전체"}
    ct = ct_map.get(ctype, ctype)

    # ── 🤖 AI 자동 생성 (교육과정 → 콘텐츠 창작, 저작권 0) ────────
    if _has_api():
        st.markdown(section_md("sparkles", "AI 자동 생성 (교육과정 기반)"), unsafe_allow_html=True)
        with st.expander("🤖 주제만 주면 AI가 지문·단어를 새로 창작해요 (선생님 입력 없이)", expanded=False):
            st.caption("실제 교과서를 베끼지 않고 교육과정 수준에 맞춰 새 콘텐츠를 만들어요.")
            gc1, gc2 = st.columns([2, 1])
            gen_topic = gc1.text_input("주제", placeholder="예: 환경보호, 학교 축제, 우정, 인공지능…",
                                       key="gc_topic")
            gen_type  = gc2.selectbox("유형", ["본문", "대화문"], key="gc_type")
            gc3, gc4, gc5 = st.columns(3)
            gen_units = gc3.slider("문장/줄 수", 5, 20, 10, key="gc_units")
            gen_words = gc4.slider("단어 수", 5, 30, 15, key="gc_words")
            gen_diff  = gc5.selectbox("난이도", ["easy", "medium", "hard"],
                                      format_func=lambda x: {"easy":"쉬움","medium":"보통","hard":"심화"}[x],
                                      index=1, key="gc_diff")

            _ai_ok, _, _ = can_use_ai()
            ai_usage_bar()
            if not _ai_ok:
                upgrade_banner("student", compact=True)
            elif st.button("🤖 AI로 콘텐츠 생성", type="primary",
                           use_container_width=True, key="gc_gen_btn"):
                if not gen_topic.strip():
                    st.warning("주제를 입력해주세요.")
                else:
                    increment_ai_usage()
                    with st.spinner(f"'{gen_topic}' 주제로 콘텐츠를 창작하는 중… (20~40초)"):
                        try:
                            from study_ai import generate_curriculum_content
                            _content = generate_curriculum_content(
                                grade, gen_topic.strip(), _api_config(),
                                content_type=gen_type, n_words=gen_words,
                                n_units=gen_units, difficulty=gen_diff,
                            )
                            st.session_state["gc_result"]      = _content
                            st.session_state["gc_result_type"] = gen_type
                            st.session_state["gc_result_topic"] = gen_topic.strip()
                        except Exception as e:
                            st.error(f"생성 실패: {e}")

            # ── 생성 결과 미리보기 + 노트로 저장 ──────────────
            _gc = st.session_state.get("gc_result")
            if _gc:
                st.success(f"✅ '{_gc.get('title_en','')}' / {_gc.get('title_kr','')} 생성 완료!")
                _gtype = st.session_state.get("gc_result_type", "본문")
                if _gtype == "대화문":
                    for d in _gc.get("dialogues", []):
                        for en, kr in d.get("lines", [])[:4]:
                            st.markdown(f"<div style='font-size:0.84rem;'>{en}<br>"
                                        f"<span style='color:#94a3b8;'>{kr}</span></div>",
                                        unsafe_allow_html=True)
                else:
                    for en, kr in _gc.get("sentences", [])[:3]:
                        st.markdown(f"<div style='font-size:0.84rem;'>{en}<br>"
                                    f"<span style='color:#94a3b8;'>{kr}</span></div>",
                                    unsafe_allow_html=True)
                st.caption(f"문장/줄 {len(_gc.get('sentences') or _gc.get('dialogues') or [])}개 · "
                           f"단어 {len(_gc.get('words', []))}개")

                st.checkbox(
                    "✏️ 생각 유도형 문제(서술형 DNA)도 함께 만들기",
                    value=True, key="gc_with_essay",
                    help="저장과 동시에 '외우지 말고 생각하게' 만드는 서술형 문제를 자동 생성해 "
                         "학습센터 ▸ 서술형 DNA에 넣어둡니다. (AI 호출 +1회)")
                if st.button("📚 이 콘텐츠를 노트로 저장", type="primary",
                             use_container_width=True, key="gc_save_btn"):
                    _u   = _auth.current_user()
                    _uid = _u.id if _u else None
                    _cnt = count_my_notes(_uid) if _uid else 0
                    _ok, _used, _limit = can_create_note(_cnt)
                    if not _ok:
                        st.error(f"무료 플랜은 노트 {_limit}개까지예요 (현재 {_used}). PRO로 무제한.")
                        upgrade_banner("pro", compact=True)
                    else:
                        _td = ({"title_en": _gc.get("title_en",""),
                                "title_kr": _gc.get("title_kr",""),
                                "sentences": _gc.get("sentences", [])}
                               if _gtype == "본문" else {})
                        _nid = save_note(
                            title        = f"{_gc.get('title_kr') or st.session_state.get('gc_result_topic','')} (AI생성)",
                            grade        = grade, publisher = "AI생성",
                            author       = "", chapter = "",
                            content_type = _gtype,
                            words        = _gc.get("words", []),
                            dialogues    = _gc.get("dialogues", []),
                            text_data    = _td,
                            tags         = f"AI생성,{st.session_state.get('gc_result_topic','')}",
                            owner_id     = _uid, visibility = "private",
                        )
                        st.success(f"📚 노트로 저장됐어요! (ID #{_nid}) — 라이브러리·학습에서 바로 쓸 수 있어요.")
                        # ── 생각 유도형(서술형 DNA) 자동 동봉 ──────────────
                        if st.session_state.get("gc_with_essay") and _nid:
                            _eai_ok, _, _ = can_use_ai()
                            if not _eai_ok:
                                st.caption("생각 유도형 문제는 AI 사용량 한도로 건너뛰었어요. "
                                           "학습센터 ▸ 서술형 DNA에서 직접 만들 수 있어요.")
                            else:
                                increment_ai_usage()
                                with st.spinner("생각 유도형(서술형 DNA) 문제를 함께 만드는 중… (15~30초)"):
                                    try:
                                        from study_ai    import generate_essay_questions
                                        from study_essay import _to_bank
                                        from study_db    import save_to_question_bank
                                        _scope = "대화문" if _gtype == "대화문" else "본문"
                                        _diff  = st.session_state.get("gc_diff", "medium")
                                        _eqs   = generate_essay_questions(
                                            _td, _gc.get("words", []), _gc.get("dialogues", []),
                                            _api_config(), n_questions=3, scope=_scope, difficulty=_diff)
                                        _sv = save_to_question_bank(
                                            _nid, [_to_bank(q, _diff) for q in _eqs],
                                            source_type="essay") if _eqs else 0
                                        if _sv:
                                            st.info(f"✏️ 생각 유도형 문제 {_sv}개도 함께 저장됐어요 — "
                                                    f"학습센터 ▸ 서술형 DNA에서 바로 풀 수 있어요.")
                                        else:
                                            st.caption("생각 유도형 문제 자동 생성은 이번엔 건너뛰었어요.")
                                    except Exception as _ee:
                                        st.caption(f"생각 유도형 문제 자동 생성 건너뜀: {_ee}")
                        st.session_state.pop("gc_result", None)
                        st.balloons()

    # ── ✍️ 텍스트 직접 입력 → AI 정리 ────────────────────────
    if _has_api():
        st.markdown(section_md("type", "텍스트 직접 입력 → AI 정리"), unsafe_allow_html=True)
        with st.expander("✍️ 텍스트 붙여넣기 → AI가 깔끔하게 정리해서 노트에 채우기", expanded=False):
            st.markdown(
                '<div style="font-size:0.82rem;color:#64748B;margin-bottom:10px;">'
                '교과서 내용을 그냥 붙여넣으면 AI가 단어/대화문/본문 형식으로 자동 정리합니다.</div>',
                unsafe_allow_html=True,
            )
            txt_type = st.radio(
                "정리 유형",
                ["단어", "대화문", "본문"],
                horizontal=True,
                key="txt_input_type",
            )
            raw_txt = st.text_area(
                "원문 텍스트 입력",
                height=200,
                placeholder=(
                    "예시 (단어): blind 눈이 먼 / amusement park 놀이공원\n"
                    "예시 (대화문): G: Hi! How are you? B: I'm great!\n"
                    "예시 (본문): Jimin woke up early. She decided to help others..."
                ),
                key="raw_text_input",
            )
            if st.button("🤖 AI로 정리하기", type="primary",
                         use_container_width=True, key="txt_organize_btn"):
                if not raw_txt.strip():
                    st.warning("텍스트를 입력해 주세요.")
                else:
                    from ocr_extractor import organize_text_input
                    api_cfg = _api_config()
                    with st.spinner(f"AI가 {txt_type} 형식으로 정리 중..."):
                        try:
                            result = organize_text_input(raw_txt, txt_type, api_cfg)
                            if txt_type == "단어" and result.get("words"):
                                st.session_state["wi"] = words_to_text(result["words"])
                                st.success(f"✅ {len(result['words'])}개 단어 정리 완료 — 아래 단어 탭 확인")
                            elif txt_type == "대화문" and result.get("dialogues"):
                                st.session_state["di"] = dlg_to_text(result["dialogues"])
                                n = sum(len(d["lines"]) for d in result["dialogues"])
                                st.success(f"✅ {len(result['dialogues'])}개 대화문 / {n}줄 정리 완료")
                            elif txt_type == "본문":
                                st.session_state["ti"] = text_to_text(result)
                                total_s = sum(len(s.get("sentences",[])) for s in result.get("sections",[]))
                                st.success(f"✅ {total_s}개 문장 정리 완료")
                            # st.rerun() 제거 — 탭 text_area가 스크립트 아래에서 렌더되므로
                            # 같은 run에서 session_state 값을 바로 읽음. rerun 하면 오히려
                            # 이전 session_state 값이 덮어씌워져 단어/대화 데이터가 사라짐.
                        except Exception as e:
                            st.error(f"정리 실패: {e}")

    # ── 파일 업로드 (사진 + PDF 통합) ───────────────────────────
    if _has_api():
        st.markdown(section_md("camera", "파일 업로드 → AI 자동 추출"), unsafe_allow_html=True)

        # 단일 통합 업로더 — JPG/PNG/WEBP + PDF 모두 허용, 여러 파일 동시 선택 가능
        uploaded_files = st.file_uploader(
            "사진 또는 PDF 업로드 (여러 파일 동시 선택 가능)",
            type=["jpg", "jpeg", "png", "webp", "pdf"],
            accept_multiple_files=True,
            key="ocr_unified_upload",
            help="교과서 사진(JPG/PNG/WEBP) 또는 PDF 파일을 올리면 AI가 자동으로 단어·대화문·본문을 추출합니다.",
        )

        if uploaded_files:
            # ── 파일 분류 ─────────────────────────────────────
            _pdf_files = [f for f in uploaded_files if f.name.lower().endswith(".pdf")]
            _img_files = [f for f in uploaded_files if not f.name.lower().endswith(".pdf")]

            # ── 요약 칩 ───────────────────────────────────────
            badge_parts = []
            if _img_files: badge_parts.append(f"🖼 사진 {len(_img_files)}장")
            if _pdf_files: badge_parts.append(f"📄 PDF {len(_pdf_files)}개")
            st.markdown(
                f'<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;'
                f'padding:6px 12px;font-size:.85rem;color:#1E40AF;margin-bottom:10px;">'
                f'{"  ·  ".join(badge_parts)} 선택됨</div>',
                unsafe_allow_html=True,
            )

            # ── 이미지 미리보기 ───────────────────────────────
            if _img_files:
                preview_n = min(len(_img_files), 5)
                prev_cols = st.columns(preview_n)
                for i, uf in enumerate(_img_files[:preview_n]):
                    prev_cols[i].image(uf.read(), use_container_width=True,
                                       caption=uf.name[:18])
                    uf.seek(0)

            # ── PDF 페이지 범위 선택 ──────────────────────────
            _pdf_ranges: dict[str, tuple[int, int]] = {}
            if _pdf_files:
                from ocr_extractor import pdf_page_count
                for pdf_f in _pdf_files:
                    _pdf_bytes_tmp = pdf_f.read()
                    pdf_f.seek(0)
                    _total_pg = pdf_page_count(_pdf_bytes_tmp)
                    st.markdown(
                        f'<div style="font-size:.82rem;color:#374151;margin:4px 0;">'
                        f'📄 <b>{pdf_f.name}</b> — 총 {_total_pg}페이지</div>',
                        unsafe_allow_html=True,
                    )
                    _pc1, _pc2, _pc3 = st.columns([1, 1, 3])
                    _ps = _pc1.number_input("시작", min_value=1,
                                            max_value=max(_total_pg, 1), value=1,
                                            key=f"_ps_{pdf_f.name}")
                    _pe = _pc2.number_input("끝", min_value=1,
                                            max_value=max(_total_pg, 1),
                                            value=min(_total_pg, 6),
                                            key=f"_pe_{pdf_f.name}")
                    _pdf_ranges[pdf_f.name] = (_ps, _pe)

            # ── 추출 옵션 + 버튼 ──────────────────────────────
            opt_col, btn_col = st.columns([2, 1])
            with opt_col:
                _etype = st.radio(
                    "추출 유형",
                    ["단어", "대화문", "본문"],
                    horizontal=True,
                    key="ocr_unified_etype",
                )
            with btn_col:
                _auto_title_val = st.text_input(
                    "노트 제목 (선택)",
                    value="",
                    placeholder=base_title,
                    key="ocr_unified_title",
                )

            if st.button("🤖 AI 자동 추출 시작",
                         type="primary", use_container_width=True,
                         key="ocr_unified_btn"):
                from ocr_extractor import (pdf_to_images, extract_words,
                                           extract_dialogues, extract_text,
                                           detect_metadata)
                api_cfg = _api_config()
                all_words, all_dialogues, all_sections = [], [], []
                title_en = title_kr = ""

                # 처리할 이미지 바이트 목록 수집
                _all_img_bytes: list[bytes] = []

                # 이미지 파일
                for uf in _img_files:
                    _all_img_bytes.append(uf.read())
                    uf.seek(0)

                # PDF → 페이지별 이미지 변환
                for pdf_f in _pdf_files:
                    _pb = pdf_f.read()
                    pdf_f.seek(0)
                    _ps, _pe = _pdf_ranges.get(pdf_f.name, (1, 5))
                    all_pdf_imgs = pdf_to_images(_pb)
                    _all_img_bytes.extend(all_pdf_imgs[_ps - 1:_pe])

                total_items = len(_all_img_bytes)
                if total_items == 0:
                    st.warning("처리할 파일이 없습니다.")
                else:
                    progress_bar = st.progress(0)
                    _sp_msg = (f"🔍 총 {total_items}개 페이지/이미지 분석 중… "
                               f"AI가 {_etype} 추출 중입니다!")
                    with st.spinner(_sp_msg):
                        for idx, img_b in enumerate(_all_img_bytes):
                            try:
                                if idx == 0:
                                    meta_r = detect_metadata(img_b, api_cfg)
                                    if meta_r.get("grade"):
                                        st.session_state["_ocr_meta"] = meta_r
                                if _etype == "단어":
                                    ws = extract_words(img_b, api_cfg)
                                    all_words.extend(ws)
                                elif _etype == "대화문":
                                    ds = extract_dialogues(img_b, api_cfg)
                                    all_dialogues.extend(ds)
                                else:
                                    ts = extract_text(img_b, api_cfg)
                                    if not title_en and ts.get("title_en"):
                                        title_en = ts["title_en"]
                                        title_kr = ts.get("title_kr", "")
                                    all_sections.extend(ts.get("sections", []))
                            except Exception:
                                pass
                            progress_bar.progress((idx + 1) / total_items)

                    # 결과 저장
                    if all_words:
                        st.session_state["wi"] = words_to_text(
                            [(w["en"], w["kr"]) if isinstance(w, dict) else w
                             for w in all_words]
                        )
                    if all_dialogues:
                        st.session_state["di"] = dlg_to_text(all_dialogues)
                    if all_sections:
                        merged_text = {
                            "title_en": title_en, "title_kr": title_kr,
                            "sentences": [s for sec in all_sections
                                          for s in sec.get("sentences", [])],
                        }
                        st.session_state["ti"] = text_to_text(merged_text)

                    # 노트 제목 자동 세팅
                    _final_title = _auto_title_val.strip() or base_title
                    if _final_title:
                        st.session_state["_auto_note_title"] = _final_title

                    st.success(
                        f"✅ 추출 완료!  단어 {len(all_words)}개 · "
                        f"대화문 {len(all_dialogues)}개 · 본문 섹션 {len(all_sections)}개"
                    )
                    # st.rerun() 제거 — session_state를 설정한 뒤 rerun하면
                    # 이전 run의 text_area 위젯값이 새 값을 덮어씌우는 문제 발생.
                    # 탭 text_area들이 스크립트 아래에 있으므로 같은 run에서 즉시 반영됨.
        else:
            st.markdown(
                f'<div style="background:#f8fafc;border:2px dashed #e2e8f0;'
                f'border-radius:10px;padding:1.4rem;text-align:center;color:#94a3b8;">'
                f'{icon("upload-cloud",36,"#cbd5e1")}'
                f'<br><span style="font-size:.88rem;">'
                f'사진(JPG/PNG/WEBP) 또는 PDF를 올리면 AI가 자동으로 내용을 추출합니다'
                f'<br><span style="font-size:.78rem;">여러 파일 동시 선택 가능</span>'
                f'</span></div>',
                unsafe_allow_html=True,
            )

        st.divider()

    # ── 내용 입력 탭 ─────────────────────────────────────────
    # 안전장치: 어떤 rerun에서도 타 탭 데이터가 사라지지 않도록 백업/복원
    for _wk, _bk in [("wi", "_wi_bak"), ("di", "_di_bak"), ("ti", "_ti_bak")]:
        cur = st.session_state.get(_wk, "")
        if cur:                                   # 값이 있으면 백업
            st.session_state[_bk] = cur
        elif st.session_state.get(_bk):           # 값이 비었는데 백업이 있으면 복원
            st.session_state[_wk] = st.session_state[_bk]

    st.markdown(section_md("pencil", "내용 입력 및 수정"), unsafe_allow_html=True)

    tab_w, tab_d, tab_t, tab_prev = st.tabs(["단어", "대화문", "본문", "미리보기"])

    with tab_w:
        rc1, rc2 = st.columns([5, 1])
        rc1.markdown(
            f'<b style="font-size:1rem;">{icon("file-text",16,"#3b82f6")}단어 목록</b>',
            unsafe_allow_html=True,
        )
        if rc2.button("샘플", key="sw"):
            st.session_state["wi"] = SAMPLE_WORDS
        st.markdown(
            '<div class="hint-box">한 줄에 하나씩 &nbsp;<code>영어단어|한글뜻</code>&nbsp; 형식</div>',
            unsafe_allow_html=True,
        )
        word_text = st.text_area(
            "단어", key="wi", height=340, label_visibility="collapsed",
        )
        words = parse_words(word_text)
        st.caption(f"{len(words)}개 단어  ·  {(len(words)+24)//25 if words else 0}페이지 분량")

    with tab_d:
        rc1, rc2 = st.columns([5, 1])
        rc1.markdown(
            f'<b style="font-size:1rem;">{icon("message-circle",16,"#22c55e")}대화문 목록</b>',
            unsafe_allow_html=True,
        )
        if rc2.button("샘플", key="sd"):
            st.session_state["di"] = SAMPLE_DIALOGUES
        st.markdown(
            '<div class="hint-box"><code>[대화문1]</code> 제목 줄 → 아래에 <code>영어|한국어</code></div>',
            unsafe_allow_html=True,
        )
        dlg_text = st.text_area(
            "대화문", key="di", height=340, label_visibility="collapsed",
        )
        dialogues = parse_dialogues(dlg_text)
        st.caption(f"{len(dialogues)}개 대화문  ·  {sum(len(d['lines']) for d in dialogues)}줄")

    with tab_t:
        rc1, rc2 = st.columns([5, 1])
        rc1.markdown(
            f'<b style="font-size:1rem;">{icon("book",16,"#f59e0b")}본문 내용</b>',
            unsafe_allow_html=True,
        )
        if rc2.button("샘플", key="st_"):
            st.session_state["ti"] = SAMPLE_TEXT

        # ── 순수 영어 감지 → 번역 버튼 ────────────────────
        current_ti = st.session_state.get("ti", "")
        if _has_api() and _is_plain_english(current_ti):
            warn_col, btn_col = st.columns([4, 1])
            warn_col.warning(
                "한글 번역이 없습니다. '번역하기'를 눌러 자동으로 추가할 수 있습니다."
            )
            if btn_col.button("번역하기", type="primary", key="translate_btn"):
                from ocr_extractor import translate_to_pairs
                api_cfg = _api_config()
                with st.spinner("AI가 영어를 한국어로 갈아입히는 중… 뚝딱뚝딱!"):
                    try:
                        result = translate_to_pairs(current_ti, api_cfg)
                        st.session_state["ti"] = text_to_text(result)
                        st.success(f"{len(result['sentences'])}개 문장 번역 완료!")
                        # st.rerun() 제거 — text_area "ti"가 아래에서 렌더되므로
                        # 같은 run에서 번역 결과를 즉시 반영함.
                    except Exception as e:
                        st.error(f"번역 실패: {e}")

        st.markdown(
            '<div class="hint-box">'
            '<b>첫 줄:</b> <code>영어제목|한글제목</code> &nbsp;/&nbsp; '
            '이후: <code>영어문장|한글문장</code><br>'
            '단락 구분: <code>[서론]</code> <code>[본론]</code> <code>[결론]</code> 마커를 '
            '삽입하면 섹션별 핵심 내용 정리 칸이 추가됩니다.'
            '</div>',
            unsafe_allow_html=True,
        )
        text_inp = st.text_area(
            "본문", key="ti", height=320, label_visibility="collapsed",
        )
        text_data = parse_text(text_inp)
        st.caption(f"{len(text_data.get('sentences', []))}개 문장")

    with tab_prev:
        p1, p2, p3 = st.columns(3)
        p1.metric("단어",     len(words))
        p2.metric("대화문",   len(dialogues))
        p3.metric("본문 문장", len(text_data.get("sentences", [])))
        st.divider()
        if words:
            st.markdown(f'<b>{icon("file-text",14,"#3b82f6")} 단어 미리보기</b>',
                        unsafe_allow_html=True)
            for en, kr in words[:5]: st.write(f"• {en} → {kr}")
        if dialogues:
            st.markdown(f'<b>{icon("message-circle",14,"#22c55e")} 대화문</b>',
                        unsafe_allow_html=True)
            for d in dialogues[:2]: st.write(f"• {d['title']} ({len(d['lines'])}줄)")

    # ── 반반노트 생성 ────────────────────────────────────────
    st.divider()
    st.markdown(section_md("wand-2", "반반노트 생성"), unsafe_allow_html=True)

    # 콘텐츠 유형별 내용 선택
    w_use = words     if ct in ("단어",   "전체") else []
    d_use = dialogues if ct in ("대화문", "전체") else []
    t_use = text_data if ct in ("본문",   "전체") else {}

    total = (len(w_use)
             + sum(len(d["lines"]) for d in d_use)
             + len(t_use.get("sentences", [])))

    # 내용 요약
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("유형",   ct)
    s2.metric("단어",   len(w_use))
    s3.metric("대화문", sum(len(d["lines"]) for d in d_use), "줄")
    s4.metric("본문",   len(t_use.get("sentences", [])), "문장")

    if total == 0:
        st.warning("선택한 유형에 내용이 없습니다. 입력 탭에서 내용을 확인해주세요.")
    else:
        if st.button("반반노트 생성하기", type="primary",
                     use_container_width=True, key="gen_btn"):
            with st.spinner("단어·문장을 반반노트에 예쁘게 쌓는 중… 두근두근!"):
                xlsx = generate(meta, w_use, d_use, t_use)
            st.session_state["current_xlsx"] = xlsx
            st.session_state["current_fn"]   = f"반반노트_{grade}_{publisher}_{author}_{chapter}과.xlsx"
            # 생성된 시트 정보
            sheets = []
            if w_use: sheets += ["단어", "단어 테스트 뜻쓰기", "단어 테스트 단어쓰기"]
            if d_use: sheets += ["대화문"]
            if t_use.get("sentences"): sheets += ["본문"]
            st.success(f"✅ 생성 완료! 포함 시트: 표지 + {', '.join(sheets)}")

    # 생성된 엑셀이 있으면 다운로드 + 저장 버튼
    if st.session_state.get("current_xlsx"):
        st.divider()
        ba1, ba2 = st.columns(2)

        with ba1:
            st.download_button(
                "다운로드",
                data      = st.session_state["current_xlsx"],
                file_name = st.session_state["current_fn"],
                mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with ba2:
            _save_public = st.checkbox(
                "🌐 공용 자료실에 공개", key="save_lib_public",
                help="체크하면 다른 선생님들도 이 노트를 복제해 쓸 수 있어요. "
                     "(내 학생은 공개 여부와 무관하게 사용 가능)",
            )
            if st.button("라이브러리에 저장", type="primary", use_container_width=True,
                         key="save_lib_btn"):
                _u   = _auth.current_user()
                _uid = _u.id if _u else None
                _cnt = count_my_notes(_uid) if _uid else 0
                _ok, _used, _limit = can_create_note(_cnt)
                if not _ok:
                    st.error(f"무료 플랜은 노트 {_limit}개까지 만들 수 있어요 "
                             f"(현재 {_used}개). PRO로 업그레이드하면 무제한이에요.")
                    upgrade_banner("pro", compact=True)
                else:
                    nid = save_note(
                        title        = f"{base_title} - {ct}",
                        grade        = grade,     publisher = publisher,
                        author       = author,    chapter   = chapter,
                        content_type = ct,
                        words        = w_use,
                        dialogues    = d_use,
                        text_data    = t_use,
                        tags         = tags,
                        owner_id     = _uid,
                        visibility   = "public" if _save_public else "private",
                    )
                    st.success(f"라이브러리에 저장했습니다 (ID #{nid})"
                               + (" · 공용 자료실 공개됨" if _save_public else ""))
                    st.balloons()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3: 합치기 & 다운로드
# ─────────────────────────────────────────────────────────────────────────────

def page_combine():
    st.markdown(title_md("layers", "합치기 & 다운로드"), unsafe_allow_html=True)
    st.caption("선택된 노트들을 하나의 엑셀 파일로 합칩니다. 각 노트가 별도 시트로 들어갑니다.")

    selected_ids = st.session_state.get("selected_ids", set())

    if not selected_ids:
        st.markdown(
            f'<div style="text-align:center;padding:3rem 0;color:#9ca3af;">'
            f'{icon("layers",40,"#d1d5db")}'
            f'<br><span style="font-size:1rem;">선택된 노트가 없습니다.</span><br>'
            f'<span style="font-size:.85rem;">라이브러리에서 노트를 선택해주세요.</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("라이브러리로 이동"):
            st.session_state["page"] = "라이브러리"
            st.rerun()
        return

    notes = [get_note(nid) for nid in selected_ids]
    notes = [n for n in notes if n]
    if not notes:
        st.error("선택된 노트를 불러오지 못했습니다.")
        return

    st.markdown(section_md("list", f"선택된 노트 ({len(notes)}개)"), unsafe_allow_html=True)

    order_map = {}
    for i, note in enumerate(notes):
        c1, c2, c3 = st.columns([1, 8, 2])
        with c1:
            order = st.number_input(
                "순서", value=i+1, min_value=1, max_value=len(notes),
                step=1, key=f"order_{note['id']}", label_visibility="collapsed",
            )
            order_map[note["id"]] = order
        with c2:
            ctype = note["content_type"]
            icon_map = {"단어":"file-text","대화문":"message-circle","본문":"book","전체":"layers"}
            st.markdown(
                f'{icon(icon_map.get(ctype,"file-text"),14,"#6b7280")} '
                f'<b>{note["title"]}</b> &nbsp;'
                f'<span class="badge-{ctype}">{ctype}</span> &nbsp;'
                f'<span style="color:#9ca3af;">{note["item_count"]}개</span>',
                unsafe_allow_html=True,
            )
        with c3:
            if st.button("제외", key=f"excl_{note['id']}", use_container_width=True):
                st.session_state["selected_ids"].discard(note["id"])
                st.rerun()

    notes_sorted = sorted(notes, key=lambda n: order_map.get(n["id"], 999))

    st.divider()
    st.markdown(section_md("eye", "생성될 시트 미리보기"), unsafe_allow_html=True)

    preview = sheet_preview(notes_sorted)
    if not preview:
        st.warning("선택된 노트에 내용이 없습니다.")
        return

    cols = st.columns(min(4, len(preview)))
    for i, item in enumerate(preview):
        cols[i % 4].markdown(
            f'<div style="background:#f8fafc;border:1px solid #e2e8f0;'
            f'border-radius:8px;padding:8px 10px;margin-bottom:6px;">'
            f'<span style="font-size:.85rem;">{item["icon"]}</span> '
            f'<code style="font-size:.8rem;">{item["name"]}</code><br>'
            f'<span style="color:#9ca3af;font-size:.72rem;">{item["note_title"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.caption(f"총 {len(preview)}개 시트가 생성됩니다.")
    st.divider()

    labels     = [f"{n['chapter']}과" for n in notes_sorted if n.get("chapter")]
    default_fn = (f"반반노트_통합_{'·'.join(labels[:4])}.xlsx"
                  if labels else f"반반노트_통합_{len(notes)}개.xlsx")

    fc1, fc2 = st.columns([3, 1])
    filename  = fc1.text_input("파일명", value=default_fn, key="combine_filename")

    with fc2:
        st.write("")
        if st.button("합치기 실행", type="primary", use_container_width=True):
            with st.spinner(f"노트 {len(notes_sorted)}개를 하나로 합체 중… 합체!"):
                xlsx = generate_combined(notes_sorted)
            st.session_state["xlsx_bytes"]    = xlsx
            st.session_state["xlsx_filename"] = filename
            st.success("생성 완료!")

    if st.session_state.get("xlsx_bytes"):
        st.download_button(
            label     = f"다운로드 — {st.session_state['xlsx_filename']}",
            data      = st.session_state["xlsx_bytes"],
            file_name = st.session_state["xlsx_filename"],
            mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        with st.expander("시트 구조 상세"):
            for i, item in enumerate(preview, 1):
                st.write(f"{i}. {item['icon']} `{item['name']}` ← {item['note_title']}")


# ─────────────────────────────────────────────────────────────────────────────
# 학습 시스템 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _visible_study_notes() -> list[dict]:
    """학습·대시보드에서 보이는 노트 — 역할별 가시성.
      학생  : 우리 선생님 노트 + 공용 자료실
      선생님: 내 노트 + 공용 자료실
      관리자/비로그인: 전체
    """
    role = _auth.current_role()
    u    = _auth.current_user()
    uid  = u.id if u else None
    if role == "admin" or not uid:
        return list_notes(scope="all")
    if role == "teacher":
        return list_notes(scope="student", owner_id=uid)        # 내것 OR 공용
    tid = st.session_state.get("sb_teacher_id")                 # student
    return list_notes(scope="student", owner_id=tid)            # 우리쌤 OR 공용 (tid None→공용만)


def _get_study_note() -> dict | None:
    """현재 선택된 노트를 학습용 dict로 반환 (words_data, dialogues_data, text_data 포함)"""
    notes = _visible_study_notes()
    if not notes:
        return None
    note_id = st.session_state.get("study_note_id")
    if note_id:
        note = get_note(note_id)
        if note:
            return _enrich_note(note)
    # 기본: 첫 번째 노트
    return _enrich_note(get_note(notes[0]["id"]))


def _enrich_note(note: dict) -> dict:
    """노트 dict에 학습용 키 매핑 (library.py get_note() 결과 기반)"""
    if not note:
        return {}
    return {
        **note,
        "words_data":     note.get("words", []),
        "dialogues_data": note.get("dialogues", []),
        "text_data":      note.get("text_data", {}),
    }


def _study_note_selector(notes: list[dict],
                         page_label: str = "학습",
                         page_icon: str = "book-open",
                         accent: str = "#6366F1"):
    """학습 통합 헤더 (글래스) — 과목 + 노트 정보 + 노트 변경 토글.
    각 학습 페이지의 중복 헤더를 대체하는 단일 헤더 역할.
    """
    if not notes:
        st.markdown(
            f'<div style="text-align:center;padding:32px;'
            f'background:rgba(255,255,255,0.7);backdrop-filter:blur(20px);'
            f'border-radius:20px;border:1px solid rgba(255,255,255,0.7);'
            f'box-shadow:0 8px 32px rgba(31,38,135,0.07);">'
            f'{icon("book-open", 34, "#C7D2FE")}'
            f'<div style="font-weight:700;color:#64748B;margin-top:10px;">등록된 노트가 없어요</div>'
            f'<div style="font-size:0.82rem;color:#94A3B8;margin-top:4px;">'
            f'선생님께 문의해주세요</div></div>',
            unsafe_allow_html=True,
        )
        return None

    # 학생 학년 기반 자동 필터 (로그인 학생만)
    role          = _auth.current_role()
    student_grade = _auth.current_grade() if role == "student" else ""
    GRADE_ORDER   = ["중1","중2","중3","고1","고2","고3"]

    if student_grade and student_grade in GRADE_ORDER:
        filtered = [n for n in notes if n.get("grade","") == student_grade] or notes
        grade_label = student_grade
    else:
        filtered = notes
        grade_label = ""

    # ── 정렬·포맷 헬퍼 (선택/표시 공용) ───────────────────────────
    def _grade_key(n):
        g = n.get("grade", "")
        return (GRADE_ORDER.index(g) if g in GRADE_ORDER else len(GRADE_ORDER),
                n.get("title", ""))
    sorted_notes = sorted(filtered, key=_grade_key)
    opt_ids = [n["id"] for n in sorted_notes]

    def _fmt(nid):
        n = next((x for x in sorted_notes if x["id"] == nid), None)
        if not n:
            return str(nid)
        g     = n.get("grade", "")
        pub   = n.get("publisher", "")
        c     = n.get("item_count", 0)
        ct    = n.get("content_type", "전체")
        u     = {"단어":"단어","대화문":"줄","본문":"문장","전체":"항목"}.get(ct, "항목")
        prefix = f"[{g}] " if g else ""
        tail   = f" · {pub}" if pub else ""
        return f"{prefix}{n.get('title','')}{tail} · {c}{u}"

    # ── 불러오기 게이트: 명시적으로 '불러오기'한 노트만 학습 ──────
    # study_note_loaded = 확정 로딩된 노트. 없으면 선택 화면만 노출.
    loaded_id = st.session_state.get("study_note_loaded")
    if loaded_id not in opt_ids:
        loaded_id = None

    # ── 공통: 불러오기 + 계단식 선택 헬퍼 (게이트/변경 양쪽 재사용) ──
    def _do_load(_nid):
        st.session_state["study_note_loaded"] = _nid
        st.session_state["study_note_id"]     = _nid
        _rec = [i for i in st.session_state.get("recent_notes", []) if i != _nid]
        st.session_state["recent_notes"] = [_nid] + _rec[:4]   # 최근 5개 유지
        for k in ["quiz", "exam_state", "ox_state", "_rv"]:
            st.session_state.pop(k, None)
        st.rerun()

    def _cascade(key_prefix):
        """학년 → 출판사 → 단원 계단식 → 선택된 note_id 반환 (없으면 None)."""
        _GORDER = ["중1", "중2", "중3", "고1", "고2", "고3"]
        _grades = sorted({n.get("grade", "") for n in filtered if n.get("grade")},
                         key=lambda g: _GORDER.index(g) if g in _GORDER else 99)
        if student_grade and student_grade in _grades:
            _sg = student_grade                                  # 학생은 내 학년 자동
            st.caption(f"학년 · {student_grade} (내 학년 자동 선택)")
        elif _grades:
            _sg = st.selectbox("① 학년", ["전체"] + _grades, key=f"{key_prefix}_grade")
        else:
            _sg = "전체"
        _p1 = [n for n in filtered if _sg == "전체" or n.get("grade") == _sg]

        _pubs = sorted({n.get("publisher", "") for n in _p1 if n.get("publisher")})
        _sp = (st.selectbox("② 출판사", ["전체"] + _pubs, key=f"{key_prefix}_pub")
               if _pubs else "전체")
        _p2 = [n for n in _p1 if _sp == "전체" or n.get("publisher") == _sp]

        if not _p2:
            st.info("해당 조건의 교과서가 없어요. 위 단계를 바꿔보세요.")
            return None
        _ids = [n["id"] for n in _p2]
        def _fu(_i):
            _n  = next((x for x in _p2 if x["id"] == _i), {})
            _ct = _n.get("content_type", "")
            return f"{_n.get('title','')}" + (f" · {_ct}" if _ct else "")
        return st.selectbox("③ 단원 선택", _ids, format_func=_fu,
                            key=f"{key_prefix}_unit", help="단원명으로 검색할 수 있어요")

    if loaded_id is None:
        # 선택 카드 + 불러오기 버튼 (자동 로딩 X)
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.72);backdrop-filter:blur(20px);'
            f'border:1px solid rgba(255,255,255,0.75);border-left:4px solid {accent};'
            f'border-radius:20px;padding:18px 22px;margin-bottom:12px;'
            f'box-shadow:0 8px 32px rgba(31,38,135,0.07);">'
            f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">'
            f'{icon(page_icon,15,accent)}'
            f'<span style="font-size:0.74rem;font-weight:700;color:{accent};">{page_label}</span>'
            f'</div>'
            f'<div style="font-size:1.15rem;font-weight:800;color:#1E293B;">'
            f'학습할 단원을 선택하세요</div>'
            f'<div style="font-size:0.78rem;color:#94A3B8;margin-top:3px;">'
            f'교과서·단원을 고른 뒤 <b>반반노트 불러오기</b>를 누르면 학습이 시작돼요.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        # ── ① 최근 학습한 교과서 (빠른 진입) ──────────────────────
        recent_ids = [i for i in st.session_state.get("recent_notes", []) if i in opt_ids][:4]
        if recent_ids:
            st.markdown('<div style="font-size:0.72rem;font-weight:800;color:#94A3B8;'
                        'letter-spacing:.04em;margin:2px 0 5px;">최근 학습한 교과서</div>',
                        unsafe_allow_html=True)
            rcols = st.columns(len(recent_ids))
            for _col, _rid in zip(rcols, recent_ids):
                _rn = next((n for n in filtered if n["id"] == _rid), None)
                if _rn and _col.button(f"📘 {_rn.get('title','')[:16]}",
                                       key=f"recent_note_{_rid}",
                                       use_container_width=True):
                    _do_load(_rid)
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

        # ── ② 계단식 선택: 학년 → 출판사 → 단원 ───────────────────
        _chosen = _cascade("nav")
        if _chosen is not None and st.button(
                "반반노트 불러오기", type="primary", use_container_width=True,
                key="study_note_load_btn"):
            _do_load(_chosen)
        return None

    # ── 로딩됨: 헤더 + '다른 단원 선택' 토글 ──────────────────────
    cur_id   = loaded_id
    st.session_state["study_note_id"] = cur_id
    cur_note = next((n for n in filtered if n["id"] == cur_id), filtered[0])

    # 메타
    ctype     = cur_note.get("content_type", "전체")
    cnt       = cur_note.get("item_count", 0)
    unit      = {"단어":"개 단어","대화문":"줄","본문":"문장","전체":"개 항목"}.get(ctype, "개")
    meta_parts = [p for p in [cur_note.get("grade",""), cur_note.get("publisher","")] if p]
    meta_parts.append(f"{cnt}{unit}")
    meta_str  = "  ·  ".join(meta_parts)

    subj_icon = icon(page_icon, 15, accent)
    pill_icon = icon("layers", 11, accent)

    # ── 글래스 통합 헤더 ──────────────────────────────────────────
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.72);'
        f'backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);'
        f'border:1px solid rgba(255,255,255,0.75);border-radius:20px;'
        f'border-left:4px solid {accent};padding:16px 22px;margin-bottom:10px;'
        f'box-shadow:0 8px 32px rgba(31,38,135,0.07),0 1px 2px rgba(0,0,0,0.03);">'
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px;">'
        f'{subj_icon}'
        f'<span style="font-size:0.74rem;font-weight:700;color:{accent};'
        f'letter-spacing:0.3px;">{page_label}</span>'
        f'<span style="margin-left:auto;display:inline-flex;align-items:center;gap:4px;'
        f'background:{accent}14;color:{accent};border-radius:20px;padding:2px 9px;'
        f'font-size:0.66rem;font-weight:700;">{pill_icon}{ctype}</span>'
        f'</div>'
        f'<div style="font-size:1.35rem;font-weight:800;color:#1E293B;'
        f'letter-spacing:-0.5px;line-height:1.2;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
        f'{cur_note["title"]}</div>'
        f'<div style="font-size:0.76rem;color:#94A3B8;margin-top:4px;">{meta_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 다른 단원으로 변경 (계단식, 게이트와 동일 UX) ─────────────
    with st.expander("다른 단원 선택 / 변경", expanded=False):
        _chg = _cascade("chg")
        if st.button("이 단원으로 불러오기", type="primary",
                     use_container_width=True, key="study_note_reload_btn"):
            if _chg is not None and _chg != cur_id:
                _do_load(_chg)
            else:
                st.rerun()

    return cur_id


# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# 온보딩 마법사 — 첫 로그인 사용자에게만 표시
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.get("_show_onboarding") and _auth.is_logged_in():
    _render_onboarding()

# 라우터
# ─────────────────────────────────────────────────────────────────────────────
current = st.session_state["page"]

# 세그먼트 선택 직후 맞춤 웰컴 1회 표시
_seg_welcome = st.session_state.pop("_seg_welcome", None)
if _seg_welcome:
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#4F46E5,#7C3AED);color:white;'
        f'border-radius:14px;padding:16px 20px;margin-bottom:14px;'
        f'box-shadow:0 8px 24px rgba(79,70,229,0.25);">'
        f'<div style="display:flex;align-items:center;gap:9px;font-size:0.98rem;font-weight:700;">'
        f'{icon("party-popper",18,"white")} {_seg_welcome}</div></div>',
        unsafe_allow_html=True,
    )

if current == "라이브러리":
    page_library()
elif current == "새 노트 추가":
    page_add_note()
elif current == "합치기 & 다운로드":
    page_combine()
elif current == "__study__":
    # ── 학습 시스템 라우팅 ─────────────────────────────────────────
    study_page = st.session_state.get("study_page", "단어학습")
    api_cfg    = _api_config()

    # 공통: 노트 선택 (역할별 가시성 — 학생=우리쌤+공용, 선생님=내것+공용)
    notes      = _visible_study_notes()

    # 학생 ID
    student_name = st.session_state.get("study_student", "")
    student_id   = None
    if student_name.strip():
        student_id = get_or_create_student(student_name.strip())
    # Supabase 로그인 사용자 자동 매핑 (study_student 미설정 시)
    if student_id is None and is_supabase_configured() and _auth.is_logged_in():
        _sb_name = _auth.current_student_name()
        if _sb_name:
            student_id = get_or_create_student(_sb_name.strip())

    if study_page == "반반 학습":
        from study_note_reader import page_note_reader
        from study_review import render_review_widget
        render_review_widget(student_id)
        note_id = _study_note_selector(notes, "반반 학습", "graduation-cap", "#6366F1")
        if note_id:
            note = _enrich_note(get_note(note_id))
            page_note_reader(note, student_id, api_cfg)
        else:
            st.markdown(f"""
<div style="text-align:center;padding:60px 20px;background:#F8FAFC;border-radius:16px;
     border:2px dashed #C7D2FE;margin-top:20px;">
  <div style="margin-bottom:6px;">{icon("book-open",40,"#C7D2FE")}</div>
  <div style="font-size:1.2rem;font-weight:800;color:#4F46E5;margin-top:12px;">
    반반노트 온라인 학습
  </div>
  <div style="color:#94A3B8;font-size:0.88rem;margin-top:8px;">
    위에서 단원을 선택하고 '반반노트 불러오기'를 누르세요
  </div>
</div>
""", unsafe_allow_html=True)

    elif study_page == "복습하기":
        from study_review import page_review
        page_review(student_id, api_cfg)

    elif study_page == "단어학습":
        from study_vocab import page_vocab
        note_id = _study_note_selector(notes, "단어학습", "file-text", "#0891B2")
        if note_id:
            note = _enrich_note(get_note(note_id))
            page_vocab(note, student_id, api_cfg)

    elif study_page == "문법학습":
        from study_grammar import page_grammar
        note_id = _study_note_selector(notes, "문법학습", "check-square", "#7C3AED")
        if note_id:
            note = _enrich_note(get_note(note_id))
            page_grammar(note, student_id, api_cfg)

    elif study_page == "내신문제":
        from study_exam import page_exam
        note_id = _study_note_selector(notes, "내신문제", "file-text", "#16A34A")
        if note_id:
            note = _enrich_note(get_note(note_id))
            page_exam(note, student_id, api_cfg)

    elif study_page == "서술형 DNA":
        from study_essay import page_essay
        note_id = _study_note_selector(notes, "서술형 DNA", "vector-pen", "#7C3AED")
        if note_id:
            note = _enrich_note(get_note(note_id))
            page_essay(note, student_id, student_name, api_cfg)

    elif study_page == "오답노트":
        from study_wrongnote import page_wrong_note
        page_wrong_note(student_id, student_name, api_cfg, notes)

    elif study_page == "약점 처방전":
        from study_weakness import page_weakness
        page_weakness(student_id, student_name, api_cfg)

    elif study_page == "숙제":
        from study_homework import page_homework
        page_homework(student_id, student_name, api_cfg, notes)

    elif study_page == "비법노트":
        from study_secret import page_secret_note
        note_id = _study_note_selector(notes, "비법노트", "sparkles", "#D97706")
        note    = _enrich_note(get_note(note_id)) if note_id else None
        page_secret_note(note, api_cfg)

    elif study_page == "기출문제":
        from study_upload import page_upload
        note_id = _study_note_selector(notes, "기출문제", "cloud-upload", "#0F766E")
        note    = _enrich_note(get_note(note_id)) if note_id else None
        page_upload(note, api_cfg, student_id)

    elif study_page == "시험 요약노트":
        from study_cheatsheet import page_cheatsheet
        page_cheatsheet(student_id, student_name, api_cfg, notes)

    elif study_page == "내 클래스":
        from study_class import page_class_teacher, page_class_student
        import auth as _auth_mod
        _role = st.session_state.get("sb_role", "student")
        if _role == "teacher":
            page_class_teacher(student_id or 0, notes)
        else:
            page_class_student(student_id or 0, notes)

    elif study_page == "반쌤 채팅":
        render_chatbot()

elif current == "__dashboard__":
    # ── 대시보드 라우팅 ────────────────────────────────────────────
    dash_page    = st.session_state.get("dash_page", "내 학습현황")
    api_cfg      = _api_config()
    student_name = st.session_state.get("study_student", "")
    student_id   = None
    if student_name.strip():
        student_id = get_or_create_student(student_name.strip())
    if student_id is None and is_supabase_configured() and _auth.is_logged_in():
        _sb_name2 = _auth.current_student_name()
        if _sb_name2:
            student_id = get_or_create_student(_sb_name2.strip())

    # 학부모 리포트는 독립 라우팅
    if dash_page == "주간 리포트 발송":
        from study_parent_report import page_parent_report
        page_parent_report(student_id, student_name, api_cfg)
    else:
        try:
            from study_dashboard import page_dashboard
            page_dashboard(dash_page, student_id, student_name, api_cfg, _visible_study_notes())
        except ImportError:
            # 대시보드 모듈 준비 중 — 플레이스홀더
            _dash_icon = "bar-chart-line" if dash_page == "내 학습현황" else "people"
            st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f766e,#14b8a6);color:white;
     border-radius:14px;padding:18px 20px;margin-bottom:20px;">
  <div style="font-size:0.85rem;opacity:0.85;">{icon("bar-chart-2",14,"rgba(255,255,255,0.85)")} 대시보드</div>
  <div style="font-size:1.4rem;font-weight:800;margin-top:4px;">{dash_page}</div>
  <div style="font-size:0.82rem;opacity:0.85;margin-top:4px;">
    학습 현황을 한눈에 확인하세요
  </div>
</div>
""", unsafe_allow_html=True)
            st.info("🚧 대시보드 기능을 준비 중입니다. 곧 완성됩니다!")
            if dash_page == "내 학습현황":
                if student_id:
                    from study_db import get_student_stats
                    stats = get_student_stats(student_id)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("단어 오답 수", stats.get("word_wrong_count", 0))
                    c2.metric("문제 오답 수", stats.get("question_wrong_count", 0))
                    vocab_acc = stats.get("vocab_accuracy")
                    c3.metric("단어 정확도", f"{vocab_acc}%" if vocab_acc is not None else "—")
                    exam_scores = stats.get("exam_scores", [])
                    if exam_scores:
                        last = exam_scores[0]
                        c4.metric("최근 내신 점수", f"{last[0]}/{last[1]}")
                    else:
                        c4.metric("최근 내신 점수", "—")
                    if exam_scores:
                        st.markdown("**최근 내신 점수 이력**")
                        for sc, tot in exam_scores:
                            pct = int(sc/tot*100) if tot else 0
                            st.progress(pct/100, text=f"{sc}/{tot}점 ({pct}%)")
                else:
                    st.info("👤 왼쪽 사이드바에서 학생을 선택하면 학습 통계를 볼 수 있습니다.")
            else:
                st.markdown("### 학생 목록")
                from study_db import list_students
                _stu = list_students()
                if _stu:
                    for s in _stu:
                        st.markdown(f"- **{s['name']}** (ID: {s['id']})")
                else:
                    st.caption("등록된 학생이 없습니다.")

else:
    # 기본값: 라이브러리
    page_library()
