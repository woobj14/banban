# study_weakness.py — 약점 처방전 페이지
# 학생 오답 패턴 AI 분석 → 맞춤형 처방전 카드

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, timedelta

from study_db import (
    get_supabase,
    get_wrong_notes,
    get_question_wrong_notes,
    get_rich_student_profile,
    get_or_create_student,
    list_students,
    save_weakness_profile,
    get_weakness_profile,
)
from icons import section_md, confirm_delete_btn


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _badge(text: str, color: str = "#4F46E5") -> str:
    return (f'<span style="background:{color};color:white;border-radius:20px;'
            f'padding:2px 10px;font-size:0.72rem;font-weight:700;'
            f'white-space:nowrap;">{text}</span>')


def _card(content: str, border_color: str = "#E2E8F0",
          bg: str = "#FFFFFF") -> str:
    return (f'<div style="background:{bg};border:1.5px solid {border_color};'
            f'border-radius:12px;padding:14px 16px;margin-bottom:10px;">'
            f'{content}</div>')


def _level_color(wrong_count: int) -> str:
    if wrong_count >= 4:
        return "#DC2626"   # 빨강
    if wrong_count >= 2:
        return "#D97706"   # 주황
    return "#059669"        # 초록


def _bar_html(pct: int, color: str = "#4F46E5", height: int = 8) -> str:
    return (f'<div style="background:#E5E7EB;border-radius:99px;height:{height}px;'
            f'overflow:hidden;margin-top:4px;">'
            f'<div style="width:{min(pct,100)}%;height:100%;'
            f'background:{color};border-radius:99px;transition:width 0.4s;"></div>'
            f'</div>')


def _render_word_weakness(wrong_words: list[dict]):
    """단어 오답 섹션"""
    section_md("📖 취약 단어 분석", "0.75rem", "#DC2626")
    if not wrong_words:
        st.markdown('<p style="color:#94A3B8;font-size:0.85rem;">오답 단어가 없습니다! 🎉</p>',
                    unsafe_allow_html=True)
        return

    html_parts = []
    for i, w in enumerate(wrong_words[:15]):
        en    = w.get("word_en", "")
        kr    = w.get("word_kr", "")
        cnt   = w.get("wrong_count", 1)
        color = _level_color(cnt)
        pct   = min(cnt * 20, 100)
        badge_label = "🔴 고위험" if cnt >= 4 else ("🟠 주의" if cnt >= 2 else "🟢 보통")
        html_parts.append(f"""
<div style="display:flex;align-items:center;gap:10px;padding:8px 0;
     border-bottom:1px solid #F1F5F9;">
  <div style="min-width:28px;font-size:0.75rem;color:#94A3B8;font-weight:700;">#{i+1}</div>
  <div style="flex:1;">
    <div style="font-weight:800;font-size:0.92rem;color:#1E293B;">{en}</div>
    <div style="font-size:0.78rem;color:#64748B;">{kr}</div>
    {_bar_html(pct, color, 5)}
  </div>
  <div style="text-align:right;min-width:70px;">
    <div style="font-size:0.72rem;color:{color};font-weight:700;">{badge_label}</div>
    <div style="font-size:0.72rem;color:#94A3B8;">{cnt}회 틀림</div>
  </div>
</div>""")

    st.markdown(
        '<div style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:12px;'
        'padding:4px 14px;">' + "".join(html_parts) + "</div>",
        unsafe_allow_html=True,
    )


def _render_question_weakness(wrong_qs: list[dict]):
    """문제 유형 오답 섹션"""
    section_md("📝 취약 문제 유형 분석", "0.75rem", "#7C3AED")
    if not wrong_qs:
        st.markdown('<p style="color:#94A3B8;font-size:0.85rem;">오답 문제가 없습니다! 🎉</p>',
                    unsafe_allow_html=True)
        return

    # 유형별 집계
    type_map: dict[str, dict] = {}
    for q in wrong_qs:
        snap = q.get("question_snapshot") or {}
        gp   = snap.get("gp_name", snap.get("type", q.get("source_type", "기타")))
        if gp not in type_map:
            type_map[gp] = {"count": 0, "wrong_count": 0, "examples": []}
        type_map[gp]["count"] += 1
        type_map[gp]["wrong_count"] += q.get("wrong_count", 1)
        if len(type_map[gp]["examples"]) < 2:
            txt = snap.get("question_text", "")
            if txt:
                type_map[gp]["examples"].append(txt[:50])

    max_wc = max((v["wrong_count"] for v in type_map.values()), default=1)
    sorted_types = sorted(type_map.items(), key=lambda x: -x[1]["wrong_count"])

    html_parts = []
    for gp, info in sorted_types[:8]:
        pct   = int(info["wrong_count"] / max_wc * 100)
        color = _level_color(info["wrong_count"])
        ex    = " / ".join(info["examples"][:2])
        ex_html = f'<div style="font-size:0.72rem;color:#94A3B8;margin-top:2px;">예: {ex}...</div>' if ex else ""
        html_parts.append(f"""
<div style="padding:8px 0;border-bottom:1px solid #F1F5F9;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <span style="font-weight:700;font-size:0.88rem;color:#1E293B;">{gp}</span>
    <span style="font-size:0.75rem;color:{color};font-weight:700;">{info["wrong_count"]}회 틀림</span>
  </div>
  {_bar_html(pct, color, 7)}
  {ex_html}
</div>""")

    st.markdown(
        '<div style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:12px;'
        'padding:4px 14px;">' + "".join(html_parts) + "</div>",
        unsafe_allow_html=True,
    )


def _render_activity_pattern(profile: dict):
    """학습 패턴 섹션"""
    section_md("📊 학습 패턴 분석", "0.75rem", "#059669")
    mod_map = {
        "word_quiz": ("단어 퀴즈", "#4F46E5"),
        "grammar":   ("문법 드릴", "#7C3AED"),
        "exam":      ("내신 문제", "#DC2626"),
        "past":      ("기출 문제", "#D97706"),
        "note_read": ("반반노트",  "#059669"),
    }
    mod_stats = profile.get("module_stats", {})

    rows = []
    for act, (label, color) in mod_map.items():
        stat = mod_stats.get(act)
        if not stat:
            continue
        sessions = stat.get("sessions", 0)
        avg      = stat.get("avg_score")
        avg_txt  = f"{avg:.0f}점" if avg is not None else "—"
        pct      = min(sessions * 10, 100)
        rows.append((label, sessions, avg_txt, color, pct))

    if not rows:
        st.markdown('<p style="color:#94A3B8;font-size:0.85rem;">학습 기록이 없습니다.</p>',
                    unsafe_allow_html=True)
        return

    streak = profile.get("streak", 0)
    total  = profile.get("total_sessions", 0)
    rd     = profile.get("recent_activity_days", 0)

    kpi_html = f"""
<div style="display:flex;gap:8px;margin-bottom:12px;">
  <div style="flex:1;text-align:center;background:#EEF2FF;border-radius:10px;padding:10px 4px;">
    <div style="font-size:1.5rem;font-weight:900;color:#4F46E5;">{streak}</div>
    <div style="font-size:0.68rem;color:#6366F1;">🔥 연속 학습일</div>
  </div>
  <div style="flex:1;text-align:center;background:#F0FDF4;border-radius:10px;padding:10px 4px;">
    <div style="font-size:1.5rem;font-weight:900;color:#059669;">{total}</div>
    <div style="font-size:0.68rem;color:#10B981;">📚 총 세션</div>
  </div>
  <div style="flex:1;text-align:center;background:#FFF7ED;border-radius:10px;padding:10px 4px;">
    <div style="font-size:1.5rem;font-weight:900;color:#D97706;">{rd}/7</div>
    <div style="font-size:0.68rem;color:#F59E0B;">📅 최근 7일</div>
  </div>
</div>"""

    bars_html = ""
    for label, sessions, avg_txt, color, pct in rows:
        bars_html += f"""
<div style="margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;font-size:0.78rem;">
    <span style="font-weight:700;color:#374151;">{label}</span>
    <span style="color:#94A3B8;">{sessions}회 &nbsp;|&nbsp; 평균 {avg_txt}</span>
  </div>
  {_bar_html(pct, color, 8)}
</div>"""

    st.markdown(
        f'<div style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:12px;padding:14px;">'
        f'{kpi_html}{bars_html}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_weakness(student_id, student_name: str, api_cfg: dict | None):
    """약점 처방전 페이지"""

    # ── 헤더 ───────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,#DC2626,#7C3AED);
     border-radius:14px;padding:18px 20px;margin-bottom:20px;color:white;">
  <div style="font-size:1.5rem;font-weight:900;">💊 약점 처방전</div>
  <div style="font-size:0.82rem;opacity:0.9;margin-top:4px;">
    오답 패턴 AI 분석 → 맞춤형 학습 처방
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 학생 선택 ──────────────────────────────────────────────────────────
    if not student_id:
        students = list_students()
        if not students:
            st.warning("학생 정보가 없습니다. 먼저 학습을 진행해 주세요.")
            return
        names = [s["name"] for s in students]
        sel = st.selectbox("학생 선택", names, key="weakness_student_sel")
        if sel:
            student_name = sel
            student_id   = get_or_create_student(sel)
        else:
            return

    st.markdown(
        f'<div style="background:#F0F9FF;border-radius:10px;padding:10px 14px;'
        f'margin-bottom:16px;font-weight:700;color:#0369A1;">'
        f'👤 {student_name} 님의 약점 처방전</div>',
        unsafe_allow_html=True,
    )

    # ── 데이터 로드 ────────────────────────────────────────────────────────
    with st.spinner("📊 데이터 분석 중..."):
        try:
            profile    = get_rich_student_profile(student_id)
            wrong_words = sorted(
                get_wrong_notes(student_id),
                key=lambda x: -x.get("wrong_count", 1),
            )
            wrong_qs    = sorted(
                get_question_wrong_notes(student_id),
                key=lambda x: -x.get("wrong_count", 1),
            )
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
            return

    # ── 탭 ─────────────────────────────────────────────────────────────────
    tab_overview, tab_words, tab_questions, tab_prescription = st.tabs([
        "📊 전체 현황", "📖 단어 오답", "📝 문제 오답", "💊 AI 처방전"
    ])

    with tab_overview:
        _render_activity_pattern(profile)
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            total_ww = len(wrong_words)
            color_ww = "#DC2626" if total_ww >= 10 else ("#D97706" if total_ww >= 5 else "#059669")
            st.markdown(
                _card(
                    f'<div style="font-size:0.72rem;color:#94A3B8;font-weight:700;">단어 오답 누적</div>'
                    f'<div style="font-size:2rem;font-weight:900;color:{color_ww};">{total_ww}</div>'
                    f'<div style="font-size:0.75rem;color:#64748B;">개 단어</div>',
                    border_color=color_ww,
                ),
                unsafe_allow_html=True,
            )
        with col2:
            total_qw = len(wrong_qs)
            color_qw = "#DC2626" if total_qw >= 10 else ("#D97706" if total_qw >= 5 else "#059669")
            st.markdown(
                _card(
                    f'<div style="font-size:0.72rem;color:#94A3B8;font-weight:700;">문제 오답 누적</div>'
                    f'<div style="font-size:2rem;font-weight:900;color:{color_qw};">{total_qw}</div>'
                    f'<div style="font-size:0.75rem;color:#64748B;">개 문제</div>',
                    border_color=color_qw,
                ),
                unsafe_allow_html=True,
            )

    with tab_words:
        _render_word_weakness(wrong_words)

    with tab_questions:
        _render_question_weakness(wrong_qs)

    with tab_prescription:
        _render_ai_prescription(
            student_id, student_name, profile,
            wrong_words, wrong_qs, api_cfg,
        )


def _render_ai_prescription(
    student_id, student_name, profile,
    wrong_words, wrong_qs, api_cfg,
):
    """AI 처방전 탭"""
    if not api_cfg:
        st.warning("AI 처방전을 사용하려면 API 키를 설정해 주세요.")
        return

    # 캐시된 처방전 확인
    cached_html = ""
    try:
        sb = get_supabase()
        res = sb.table("weakness_profile") \
                .select("summary,updated_at") \
                .eq("student_id", student_id) \
                .maybe_single().execute()
        if res.data and res.data.get("summary", "").startswith("<!DOCTYPE"):
            cached_html  = res.data["summary"]
            updated_at   = res.data.get("updated_at", "")[:10]
    except Exception:
        cached_html = ""
        updated_at  = ""

    col_gen, col_clear = st.columns([3, 1])
    with col_gen:
        gen_label = "🔄 처방전 새로 생성" if cached_html else "💊 AI 처방전 생성하기"
        gen_btn   = st.button(gen_label, type="primary", use_container_width=True,
                              key="gen_prescription_btn")
    with col_clear:
        if cached_html:
            if confirm_delete_btn(
                "삭제", key="clear_prescription_btn",
                item_name="처방전",
                use_container_width=True,
            ):
                try:
                    sb = get_supabase()
                    sb.table("weakness_profile").delete() \
                      .eq("student_id", student_id).execute()
                    st.session_state.pop("prescription_html", None)
                    st.rerun()
                except Exception:
                    pass

    if gen_btn:
        from plans import can_use_ai, increment_ai_usage, upgrade_banner, ai_usage_bar
        _aiok, _, _ = can_use_ai()
        ai_usage_bar()
        if not _aiok:
            upgrade_banner("student", compact=True)
            st.stop()
        increment_ai_usage()
        with st.spinner("💊 AI가 처방전을 작성 중입니다... (10~30초)"):
            try:
                from study_ai import generate_weakness_prescription
                html = generate_weakness_prescription(
                    student_name, profile, wrong_words, wrong_qs, api_cfg
                )
                # Supabase에 저장 (summary 컬럼 재활용)
                try:
                    sb = get_supabase()
                    existing = sb.table("weakness_profile") \
                                 .select("id") \
                                 .eq("student_id", student_id) \
                                 .maybe_single().execute()
                    if existing.data:
                        sb.table("weakness_profile") \
                          .update({"summary": html}) \
                          .eq("student_id", student_id).execute()
                    else:
                        sb.table("weakness_profile").insert({
                            "student_id": student_id,
                            "note_id": 0,
                            "summary": html,
                        }).execute()
                except Exception:
                    pass
                st.session_state["prescription_html"] = html
                st.rerun()
            except Exception as e:
                st.error(f"처방전 생성 실패: {e}")
                return

    # 처방전 렌더링
    display_html = st.session_state.get("prescription_html", cached_html)
    if display_html:
        if cached_html and not st.session_state.get("prescription_html"):
            st.markdown(
                f'<div style="font-size:0.72rem;color:#94A3B8;margin-bottom:8px;">'
                f'마지막 생성: {updated_at}</div>',
                unsafe_allow_html=True,
            )
        components.html(display_html, height=900, scrolling=True)

        # 다운로드
        st.download_button(
            "📥 처방전 저장 (HTML)",
            data=display_html.encode("utf-8"),
            file_name=f"약점처방전_{student_name}_{date.today()}.html",
            mime="text/html",
            use_container_width=True,
        )
    else:
        st.markdown("""
<div style="text-align:center;padding:40px 20px;background:#FFF7ED;
     border-radius:12px;border:2px dashed #FDE68A;">
  <div style="font-size:2.5rem;">💊</div>
  <div style="font-weight:700;color:#92400E;margin-top:8px;">처방전이 아직 없습니다</div>
  <div style="font-size:0.82rem;color:#B45309;margin-top:4px;">
    위 버튼을 눌러 AI 처방전을 생성하세요
  </div>
</div>
""", unsafe_allow_html=True)
