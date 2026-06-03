# study_parent_report.py — 학부모 주간 리포트 시스템
# 이메일 발송: Gmail SMTP (smtplib) — .env에 GMAIL_USER, GMAIL_APP_PASSWORD 설정
# AI 코멘트: Anthropic / Gemini API (api_cfg 전달 시)

import os
import smtplib
import datetime as dt
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st
from icons import icon
from supabase_client import get_supabase


# ─────────────────────────────────────────────────────────────────────────────
# DB 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def get_parent_contacts(student_id: int) -> list[dict]:
    sb = get_supabase()
    r  = sb.table("parent_contacts").select("*") \
           .eq("student_id", student_id).eq("is_active", True) \
           .order("created_at").execute()
    return r.data or []


def upsert_parent_contact(student_id: int, parent_name: str,
                           parent_email: str, relation: str = "부모") -> bool:
    try:
        get_supabase().table("parent_contacts").upsert({
            "student_id":   student_id,
            "parent_name":  parent_name.strip(),
            "parent_email": parent_email.strip().lower(),
            "relation":     relation,
            "is_active":    True,
            "updated_at":   dt.datetime.now().isoformat(),
        }, on_conflict="student_id,parent_email").execute()
        return True
    except Exception:
        return False


def delete_parent_contact(contact_id: int):
    get_supabase().table("parent_contacts") \
        .update({"is_active": False}).eq("id", contact_id).execute()


def _log_report(student_id: int, parent_email: str,
                report_week: str, status: str, error: str = ""):
    try:
        get_supabase().table("report_logs").upsert({
            "student_id":   student_id,
            "parent_email": parent_email,
            "report_week":  report_week,
            "status":       status,
            "error_msg":    error,
        }, on_conflict="student_id,parent_email,report_week").execute()
    except Exception:
        pass


def already_sent_this_week(student_id: int, parent_email: str) -> bool:
    today  = dt.date.today()
    monday = (today - dt.timedelta(days=today.weekday())).isoformat()
    r = get_supabase().table("report_logs").select("id") \
        .eq("student_id", student_id).eq("parent_email", parent_email) \
        .eq("report_week", monday).eq("status", "sent").execute()
    return bool(r.data)


# ─────────────────────────────────────────────────────────────────────────────
# 주간 학습 통계 수집
# ─────────────────────────────────────────────────────────────────────────────

def _collect_weekly_stats(student_id: int) -> dict:
    """이번 주 학습 통계를 Supabase에서 수집"""
    sb     = get_supabase()
    today  = dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    mon_s  = monday.isoformat()
    sun_s  = (monday + dt.timedelta(days=6)).isoformat()

    # 1) 학습 활동 로그 (study_logs 테이블)
    try:
        logs_r = sb.table("study_logs").select("*") \
                   .eq("student_id", student_id) \
                   .gte("created_at", mon_s).lte("created_at", sun_s + "T23:59:59") \
                   .execute()
        logs = logs_r.data or []
    except Exception:
        logs = []

    study_days = len({l["created_at"][:10] for l in logs})
    total_sessions = len(logs)
    vocab_sessions  = sum(1 for l in logs if l.get("activity_type") == "vocab")
    grammar_sessions = sum(1 for l in logs if l.get("activity_type") == "grammar")
    exam_sessions    = sum(1 for l in logs if l.get("activity_type") in ("exam", "past_exam"))

    # 2) 이번 주 마스터한 단어 (review_schedule)
    try:
        mastered_r = sb.table("review_schedule").select("item_data,item_type") \
                       .eq("student_id", student_id).eq("is_mastered", True) \
                       .gte("updated_at", mon_s).execute()
        mastered = mastered_r.data or []
    except Exception:
        mastered = []

    mastered_words = [
        m["item_data"].get("word_en", "")
        for m in mastered if m.get("item_type") == "word"
        and m.get("item_data", {}).get("word_en")
    ][:10]  # 최대 10개

    # 3) 복습 완료 횟수
    try:
        rv_r = sb.table("review_schedule").select("*", count="exact") \
                 .eq("student_id", student_id) \
                 .gte("last_reviewed", mon_s).lte("last_reviewed", sun_s) \
                 .execute()
        review_done = rv_r.count or 0
    except Exception:
        review_done = 0

    # 4) 오답 TOP 3 (취약 단어)
    try:
        wrong_r = sb.table("wrong_notes").select("word_en,wrong_count") \
                    .eq("student_id", student_id) \
                    .order("wrong_count", desc=True).limit(3).execute()
        weak_words = [w["word_en"] for w in (wrong_r.data or [])]
    except Exception:
        weak_words = []

    # 5) 복습 현황
    try:
        rv_stats_r = sb.table("review_schedule").select("*", count="exact") \
                       .eq("student_id", student_id).eq("is_mastered", False) \
                       .lte("next_review", today.isoformat()).execute()
        due_count = rv_stats_r.count or 0
    except Exception:
        due_count = 0

    # 6) 학생 이름
    try:
        prof_r = sb.table("profiles").select("name,grade") \
                   .eq("student_id", student_id).single().execute()
        student_name  = prof_r.data.get("name",  "학생")   if prof_r.data else "학생"
        student_grade = prof_r.data.get("grade", "")       if prof_r.data else ""
    except Exception:
        student_name  = "학생"
        student_grade = ""

    return {
        "student_name":    student_name,
        "student_grade":   student_grade,
        "week_start":      monday.strftime("%m월 %d일"),
        "week_end":        (monday + dt.timedelta(days=6)).strftime("%m월 %d일"),
        "study_days":      study_days,
        "total_sessions":  total_sessions,
        "vocab_sessions":  vocab_sessions,
        "grammar_sessions": grammar_sessions,
        "exam_sessions":   exam_sessions,
        "review_done":     review_done,
        "mastered_words":  mastered_words,
        "weak_words":      weak_words,
        "due_count":       due_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI 코멘트 생성
# ─────────────────────────────────────────────────────────────────────────────

def _generate_ai_comment(stats: dict, api_cfg: dict | None) -> str:
    """반반쌤 AI가 학부모에게 전하는 한마디"""
    if not api_cfg:
        # API 없을 때 기본 코멘트
        days = stats["study_days"]
        if days >= 5:
            return f"{stats['student_name']} 학생이 이번 주 {days}일이나 학습했어요! 정말 대단한 성실함입니다. 앞으로도 꾸준히 응원해 주세요 😊"
        elif days >= 3:
            return f"이번 주 {days}일 학습했습니다. 꾸준한 노력이 실력을 만들어요. 집에서도 격려의 말 한마디가 큰 힘이 됩니다!"
        elif days >= 1:
            return f"이번 주 학습을 시작했습니다. 매일 조금씩 꾸준히 공부하는 습관을 함께 만들어 봐요 💪"
        else:
            return f"이번 주는 학습 기록이 없었어요. 함께 학습 습관을 만들어 가면 어떨까요? 반반쌤이 항상 응원합니다!"

    prompt = f"""당신은 반반쌤입니다. 학부모님께 자녀의 이번 주 학습 결과를 따뜻하고 전문적으로 코멘트해주세요.
학생 이름: {stats['student_name']} ({stats['student_grade']})
학습 일수: {stats['study_days']}일 / 7일
복습 완료: {stats['review_done']}개
마스터 단어: {', '.join(stats['mastered_words']) if stats['mastered_words'] else '없음'}
취약 단어: {', '.join(stats['weak_words']) if stats['weak_words'] else '없음'}

2~3문장으로 따뜻하게 코멘트해주세요. 이모지 1~2개 포함. 존댓말 사용. 학부모 입장에서 와닿는 내용으로."""

    try:
        if api_cfg["type"] == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_cfg["key"])
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text.strip()
        elif api_cfg["type"] == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_cfg["key"])
            model = genai.GenerativeModel("gemini-1.5-flash")
            return model.generate_content(prompt).text.strip()
    except Exception:
        pass

    return f"{stats['student_name']} 학생이 이번 주 {stats['study_days']}일 열심히 공부했습니다. 가정에서도 따뜻한 응원 부탁드립니다 😊"


# ─────────────────────────────────────────────────────────────────────────────
# HTML 이메일 템플릿
# ─────────────────────────────────────────────────────────────────────────────

def _build_html_email(stats: dict, parent_name: str, ai_comment: str) -> str:
    mastered_html = ""
    if stats["mastered_words"]:
        chips = "".join(
            f'<span style="display:inline-block;background:#EEF2FF;color:#4338CA;'
            f'border-radius:20px;padding:3px 12px;font-size:0.78rem;font-weight:700;'
            f'margin:3px 2px;">{w}</span>'
            for w in stats["mastered_words"]
        )
        mastered_html = f"""
        <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
             padding:12px 16px;margin:10px 0;">
          <div style="font-weight:700;color:#15803D;margin-bottom:6px;">🏆 이번 주 마스터한 단어</div>
          <div>{chips}</div>
        </div>"""

    weak_html = ""
    if stats["weak_words"]:
        items = "".join(
            f'<span style="display:inline-block;background:#FEF2F2;color:#DC2626;'
            f'border-radius:20px;padding:3px 12px;font-size:0.78rem;font-weight:700;'
            f'margin:3px 2px;">{w}</span>'
            for w in stats["weak_words"]
        )
        weak_html = f"""
        <div style="background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;
             padding:12px 16px;margin:10px 0;">
          <div style="font-weight:700;color:#C2410C;margin-bottom:6px;">📌 집중 복습이 필요한 단어</div>
          <div>{items}</div>
        </div>"""

    due_badge = ""
    if stats["due_count"] > 0:
        due_badge = f"""
        <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;
             padding:10px 14px;margin:10px 0;font-size:0.85rem;color:#DC2626;">
          ⏰ 현재 복습 대기 중인 항목: <b>{stats['due_count']}개</b> — 오늘 복습을 격려해 주세요!
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:580px;margin:32px auto;background:white;border-radius:16px;
     box-shadow:0 4px 20px rgba(0,0,0,0.08);overflow:hidden;">

  <!-- 헤더 -->
  <div style="background:linear-gradient(135deg,#4F46E5,#6366F1);padding:28px 32px;">
    <div style="color:rgba(255,255,255,0.85);font-size:0.8rem;margin-bottom:4px;">반반 BanBan</div>
    <div style="color:white;font-size:1.5rem;font-weight:800;">주간 학습 리포트 📚</div>
    <div style="color:rgba(255,255,255,0.85);font-size:0.85rem;margin-top:4px;">
      {stats['week_start']} ~ {stats['week_end']}
    </div>
  </div>

  <!-- 본문 -->
  <div style="padding:24px 32px;">
    <p style="color:#374151;font-size:0.95rem;line-height:1.7;margin-top:0;">
      안녕하세요, <b>{parent_name}</b> 어머니/아버지께 😊<br>
      <b>{stats['student_name']}</b> 학생의 이번 주 학습 결과를 전달드립니다.
    </p>

    <!-- 통계 카드 4개 -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:16px 0;">
      <div style="background:#EEF2FF;border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:1.6rem;font-weight:800;color:#4338CA;">{stats['study_days']}일</div>
        <div style="font-size:0.75rem;color:#6B7280;margin-top:2px;">이번 주 학습일</div>
      </div>
      <div style="background:#ECFDF5;border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:1.6rem;font-weight:800;color:#059669;">{stats['review_done']}개</div>
        <div style="font-size:0.75rem;color:#6B7280;margin-top:2px;">복습 완료</div>
      </div>
      <div style="background:#FFF7ED;border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:1.6rem;font-weight:800;color:#EA580C;">{len(stats['mastered_words'])}개</div>
        <div style="font-size:0.75rem;color:#6B7280;margin-top:2px;">신규 마스터 단어</div>
      </div>
      <div style="background:#F5F3FF;border-radius:10px;padding:14px;text-align:center;">
        <div style="font-size:1.6rem;font-weight:800;color:#7C3AED;">{stats['total_sessions']}회</div>
        <div style="font-size:0.75rem;color:#6B7280;margin-top:2px;">총 학습 세션</div>
      </div>
    </div>

    {mastered_html}
    {weak_html}
    {due_badge}

    <!-- AI 반반쌤 코멘트 -->
    <div style="background:#F5F3FF;border:1px solid #DDD6FE;border-radius:12px;
         padding:16px 20px;margin:16px 0;">
      <div style="font-weight:800;color:#6D28D9;font-size:0.85rem;margin-bottom:8px;">
        💜 반반쌤의 한마디
      </div>
      <div style="color:#374151;font-size:0.9rem;line-height:1.75;">
        {ai_comment}
      </div>
    </div>

    <p style="color:#9CA3AF;font-size:0.78rem;line-height:1.7;margin-bottom:0;">
      본 리포트는 반반 BanBan 학습 플랫폼에서 자동 발송됩니다.<br>
      수신 거부를 원하시면 선생님께 문의해 주세요.
    </p>
  </div>

  <!-- 푸터 -->
  <div style="background:#F8FAFC;padding:14px 32px;text-align:center;
       border-top:1px solid #E5E7EB;">
    <span style="font-size:0.75rem;color:#9CA3AF;">반반 BanBan — 영어 반반노트 학습 플랫폼</span>
  </div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 이메일 발송 (Gmail SMTP)
# ─────────────────────────────────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Gmail SMTP로 HTML 이메일 발송.
    .env: GMAIL_USER, GMAIL_APP_PASSWORD (구글 앱 비밀번호)
    """
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pw   = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not gmail_user or not gmail_pw:
        return False, "GMAIL_USER 또는 GMAIL_APP_PASSWORD가 .env에 설정되지 않았습니다."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"반반 BanBan <{gmail_user}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_user, gmail_pw)
            server.sendmail(gmail_user, to_email, msg.as_string())
        return True, "발송 완료"
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail 인증 실패 — 앱 비밀번호를 확인하세요."
    except Exception as e:
        return False, f"발송 오류: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# 리포트 발송 메인 함수
# ─────────────────────────────────────────────────────────────────────────────

def send_weekly_report(student_id: int, api_cfg: dict | None = None,
                       force: bool = False) -> list[dict]:
    """모든 학부모에게 주간 리포트 발송.
    Returns: [{"email": ..., "ok": bool, "msg": ...}]
    """
    contacts = get_parent_contacts(student_id)
    if not contacts:
        return [{"email": "", "ok": False, "msg": "등록된 학부모 연락처가 없습니다."}]

    stats      = _collect_weekly_stats(student_id)
    ai_comment = _generate_ai_comment(stats, api_cfg)
    today      = dt.date.today()
    monday     = (today - dt.timedelta(days=today.weekday())).isoformat()
    subject    = f"[반반쌤] {stats['student_name']} 주간 학습 리포트 ({stats['week_start']}~{stats['week_end']})"

    results = []
    for c in contacts:
        email = c["parent_email"]

        if not force and already_sent_this_week(student_id, email):
            results.append({"email": email, "ok": True, "msg": "이미 이번 주 발송됨 (중복 생략)"})
            continue

        html_body = _build_html_email(stats, c.get("parent_name", "부모님"), ai_comment)
        ok, msg   = _send_email(email, subject, html_body)
        _log_report(student_id, email, monday, "sent" if ok else "failed", "" if ok else msg)
        results.append({"email": email, "ok": ok, "msg": msg})

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 학부모 관리 + 리포트 발송 UI (대시보드 탭에서 사용)
# ─────────────────────────────────────────────────────────────────────────────

def page_parent_report(student_id: int | None, student_name: str,
                       api_cfg: dict | None):
    """학부모 리포트 페이지 — 대시보드에서 호출"""
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#7C3AED,#6D28D9);color:white;
     border-radius:14px;padding:18px 20px;margin-bottom:20px;">
  <div style="font-size:0.85rem;opacity:0.85;">📧 학부모 주간 리포트</div>
  <div style="font-size:1.4rem;font-weight:800;margin-top:4px;">주간 학습 리포트 발송</div>
  <div style="font-size:0.82rem;opacity:0.85;margin-top:4px;">
    매주 학부모님께 학습 현황을 자동으로 전달해요
  </div>
</div>
""", unsafe_allow_html=True)

    if not student_id:
        st.info("로그인하면 학부모 리포트를 사용할 수 있어요.")
        return

    tab_contact, tab_send, tab_preview = st.tabs(["👨‍👩‍👧 연락처 관리", "📤 리포트 발송", "👀 미리보기"])

    # ── 탭 1: 연락처 관리 ─────────────────────────────────────────
    with tab_contact:
        st.markdown("#### 학부모 이메일 등록")
        contacts = get_parent_contacts(student_id)

        if contacts:
            for c in contacts:
                col_name, col_email, col_rel, col_del = st.columns([2, 3, 1.5, 1])
                col_name.markdown(f'<b>{c["parent_name"]}</b>', unsafe_allow_html=True)
                col_email.markdown(f'<span style="color:#6366F1;">{c["parent_email"]}</span>',
                                   unsafe_allow_html=True)
                col_rel.markdown(
                    f'<span style="background:#EEF2FF;color:#4338CA;border-radius:6px;'
                    f'padding:2px 8px;font-size:0.75rem;">{c["relation"]}</span>',
                    unsafe_allow_html=True
                )
                if col_del.button("🗑", key=f"del_parent_{c['id']}", help="연락처 삭제"):
                    delete_parent_contact(c["id"])
                    st.rerun()
            st.divider()

        with st.expander("➕ 새 연락처 추가", expanded=len(contacts) == 0):
            with st.form("add_parent_form"):
                p_name  = st.text_input("이름 (예: 홍길동 어머니)", placeholder="홍길동 어머니")
                p_email = st.text_input("이메일", placeholder="parent@email.com")
                p_rel   = st.selectbox("관계", ["부모님", "아버지", "어머니", "조부모님", "기타"])
                if st.form_submit_button("등록", type="primary", use_container_width=True):
                    if not p_name.strip() or not p_email.strip():
                        st.error("이름과 이메일을 모두 입력해주세요.")
                    elif "@" not in p_email:
                        st.error("올바른 이메일 주소를 입력해주세요.")
                    else:
                        if upsert_parent_contact(student_id, p_name, p_email, p_rel):
                            st.success(f"✅ {p_email} 등록 완료!")
                            st.rerun()
                        else:
                            st.error("등록 실패. 이미 등록된 이메일일 수 있습니다.")

        # Gmail 설정 안내
        gmail_ok = bool(os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_APP_PASSWORD"))
        if gmail_ok:
            st.markdown(
                '<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:8px;'
                'padding:8px 12px;font-size:0.82rem;color:#065F46;">✅ Gmail 발송 설정 완료</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning(
                "📧 **이메일 발송 미설정** — `.env` 파일에 다음을 추가하세요:\n\n"
                "```\nGMAIL_USER=your@gmail.com\nGMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx\n```\n\n"
                "Google 계정 → 보안 → 2단계 인증 → **앱 비밀번호** 에서 생성"
            )

    # ── 탭 2: 리포트 발송 ─────────────────────────────────────────
    with tab_send:
        contacts_send = get_parent_contacts(student_id)
        if not contacts_send:
            st.info("먼저 '연락처 관리' 탭에서 학부모 이메일을 등록해주세요.")
        else:
            st.markdown(f"**등록된 수신자 {len(contacts_send)}명**")
            for c in contacts_send:
                st.markdown(
                    f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                    f'border-radius:8px;padding:7px 12px;margin:3px 0;font-size:0.85rem;">'
                    f'📧 {c["parent_name"]} ({c["parent_email"]})</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            force_send = st.checkbox("이미 발송된 경우도 다시 보내기", value=False)

            if st.button("📤 지금 리포트 발송", type="primary",
                         use_container_width=True):
                with st.spinner("반반쌤이 리포트를 작성 중이에요… 잠깐만요!"):
                    results = send_weekly_report(student_id, api_cfg, force=force_send)

                for r in results:
                    if r["ok"]:
                        st.success(f"✅ {r['email']} — {r['msg']}")
                    else:
                        st.error(f"❌ {r['email']} — {r['msg']}")

    # ── 탭 3: 미리보기 ────────────────────────────────────────────
    with tab_preview:
        if st.button("📊 이번 주 리포트 미리보기", use_container_width=True):
            with st.spinner("학습 데이터 수집 중…"):
                stats      = _collect_weekly_stats(student_id)
                ai_comment = _generate_ai_comment(stats, api_cfg)

            # 통계 카드
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("학습 일수", f"{stats['study_days']}일")
            c2.metric("복습 완료", f"{stats['review_done']}개")
            c3.metric("마스터 단어", f"{len(stats['mastered_words'])}개")
            c4.metric("총 세션", f"{stats['total_sessions']}회")

            if stats["mastered_words"]:
                st.markdown("**🏆 이번 주 마스터한 단어**")
                st.write("  ".join(f"`{w}`" for w in stats["mastered_words"]))

            if stats["weak_words"]:
                st.markdown("**📌 집중 복습 필요 단어**")
                st.write("  ".join(f"`{w}`" for w in stats["weak_words"]))

            st.markdown(f"""
<div style="background:#F5F3FF;border:1px solid #DDD6FE;border-radius:12px;
     padding:16px;margin-top:12px;">
  <div style="font-weight:800;color:#6D28D9;margin-bottom:8px;">💜 반반쌤의 한마디</div>
  <div style="color:#374151;font-size:0.9rem;line-height:1.8;">{ai_comment}</div>
</div>
""", unsafe_allow_html=True)
