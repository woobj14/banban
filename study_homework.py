# study_homework.py — 숙제 출제 + 완료 확인 UI
# 선생님: 숙제 출제, 진행 현황 모니터링
# 학생:  숙제 목록 확인 + 완료 체크 + 점수 제출

import streamlit as st
from datetime import date, timedelta

from study_db import (
    create_homework, list_homework, get_homework,
    deactivate_homework, submit_homework,
    get_homework_submission, get_homework_submissions_for,
    ensure_homework_tables, list_students,
    get_or_create_student, get_question_bank,
)
import auth as _auth
from icons import section_md, confirm_delete_btn


# ─────────────────────────────────────────────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

HW_TYPE_LABELS = {
    "word_quiz":  "📖 단어 퀴즈",
    "grammar":    "✏️ 문법 드릴",
    "exam":       "📋 내신 문제",
    "note_read":  "📚 반반노트 읽기",
    "mixed":      "🌀 혼합 과제",
}

HW_TYPE_COLORS = {
    "word_quiz": "#4F46E5",
    "grammar":   "#7C3AED",
    "exam":      "#DC2626",
    "note_read": "#059669",
    "mixed":     "#D97706",
}


def _days_left(due_date_str: str) -> int:
    try:
        due = date.fromisoformat(due_date_str)
        return (due - date.today()).days
    except Exception:
        return 999


def _due_badge(due_date_str: str) -> str:
    days = _days_left(due_date_str)
    if days < 0:
        return '<span style="background:#DC2626;color:white;border-radius:20px;padding:2px 8px;font-size:0.7rem;font-weight:700;">기한 초과</span>'
    if days == 0:
        return '<span style="background:#D97706;color:white;border-radius:20px;padding:2px 8px;font-size:0.7rem;font-weight:700;">오늘 마감</span>'
    if days <= 2:
        return f'<span style="background:#F59E0B;color:white;border-radius:20px;padding:2px 8px;font-size:0.7rem;font-weight:700;">{days}일 남음</span>'
    return f'<span style="background:#E0E7FF;color:#4F46E5;border-radius:20px;padding:2px 8px;font-size:0.7rem;font-weight:700;">{days}일 남음</span>'


def _hw_card(hw: dict, extra: str = "") -> str:
    hw_type = hw.get("hw_type", "mixed")
    color   = HW_TYPE_COLORS.get(hw_type, "#4F46E5")
    label   = HW_TYPE_LABELS.get(hw_type, hw_type)
    due     = hw.get("due_date", "")[:10]
    title   = hw.get("title", "제목 없음")
    desc    = hw.get("description", "")
    target  = hw.get("target_score", 80)
    return f"""
<div style="background:#FFFFFF;border:1.5px solid #E2E8F0;border-radius:12px;
     padding:14px 16px;margin-bottom:10px;border-left:4px solid {color};">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <span style="font-size:0.7rem;background:{color}20;color:{color};
            border-radius:20px;padding:2px 8px;font-weight:700;">{label}</span>
      <div style="font-weight:800;font-size:0.95rem;color:#1E293B;margin-top:4px;">{title}</div>
      {f'<div style="font-size:0.78rem;color:#64748B;margin-top:2px;">{desc}</div>' if desc else ''}
    </div>
    <div style="text-align:right;min-width:80px;">
      {_due_badge(due)}
      <div style="font-size:0.68rem;color:#94A3B8;margin-top:4px;">목표 {target}점</div>
    </div>
  </div>
  {extra}
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# 선생님: 숙제 출제 탭
# ─────────────────────────────────────────────────────────────────────────────

def _teacher_create_tab(notes: list):
    section_md("➕ 새 숙제 출제", "0.75rem", "#4F46E5")

    if not notes:
        st.warning("먼저 반반노트를 등록해 주세요.")
        return

    with st.form("hw_create_form", clear_on_submit=True):
        note_opts = {n["title"]: n["id"] for n in notes}
        sel_note  = st.selectbox("📚 노트 선택", list(note_opts.keys()))

        hw_type = st.selectbox(
            "📋 과제 유형",
            list(HW_TYPE_LABELS.keys()),
            format_func=lambda x: HW_TYPE_LABELS[x],
        )

        col_title, col_score = st.columns([3, 1])
        with col_title:
            title = st.text_input("숙제 제목", placeholder="예: Unit 4 단어 퀴즈 10개")
        with col_score:
            target_score = st.number_input("목표 점수", min_value=0, max_value=100,
                                           value=80, step=5)

        description = st.text_area("설명 (선택)", placeholder="숙제에 대한 추가 안내...",
                                   height=70)

        col_due, col_buf = st.columns([2, 2])
        with col_due:
            due_date = st.date_input("마감일", value=date.today() + timedelta(days=3))

        submitted = st.form_submit_button("📮 숙제 출제하기", type="primary",
                                          use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("숙제 제목을 입력해 주세요.")
            return
        try:
            hw_id = create_homework(
                note_id=note_opts[sel_note],
                title=title.strip(),
                description=description.strip(),
                due_date=str(due_date),
                hw_type=hw_type,
                target_score=target_score,
            )
            st.success(f"✅ 숙제가 출제되었습니다! (ID: {hw_id})")
            st.rerun()
        except Exception as e:
            st.error(f"출제 실패: {e}")


def _teacher_monitor_tab(notes: list):
    """선생님: 진행 현황"""
    section_md("📊 숙제 진행 현황", "0.75rem", "#7C3AED")

    students = list_students()
    total_students = len(students)

    # 노트 필터
    note_opts = {"전체 노트": None} | {n["title"]: n["id"] for n in notes}
    filter_note_label = st.selectbox("노트 필터", list(note_opts.keys()),
                                      key="hw_monitor_note_filter")
    filter_note_id = note_opts[filter_note_label]

    hw_list = list_homework(note_id=filter_note_id, active_only=False)
    if not hw_list:
        st.info("출제된 숙제가 없습니다.")
        return

    for hw in hw_list:
        submissions = get_homework_submissions_for(hw["id"])
        done_cnt    = sum(1 for s in submissions if s.get("submitted"))
        pct         = int(done_cnt / total_students * 100) if total_students else 0

        # 점수 통계
        scores = [s["score"]/s["total"]*100 for s in submissions
                  if s.get("score") is not None and s.get("total")]
        avg_score = f"{sum(scores)/len(scores):.0f}점" if scores else "—"

        bar_color  = "#059669" if pct >= 80 else ("#D97706" if pct >= 50 else "#DC2626")
        bar_html   = (f'<div style="background:#E5E7EB;border-radius:99px;height:6px;'
                      f'margin-top:6px;"><div style="width:{pct}%;height:100%;'
                      f'background:{bar_color};border-radius:99px;"></div></div>')
        extra_html = (f'<div style="margin-top:8px;font-size:0.75rem;color:#64748B;">'
                      f'제출 {done_cnt}/{total_students}명 ({pct}%) &nbsp;|&nbsp; 평균 {avg_score}</div>'
                      f'{bar_html}')

        st.markdown(_hw_card(hw, extra=extra_html), unsafe_allow_html=True)

        # 상세 보기 expander
        with st.expander(f"🔍 상세 제출 현황 — {hw['title']}"):
            if not submissions:
                st.caption("아직 제출한 학생이 없습니다.")
            else:
                for sub in submissions:
                    sid   = sub.get("student_id")
                    sname = next((s["name"] for s in students if s["id"] == sid), f"ID:{sid}")
                    sc    = sub.get("score")
                    tot   = sub.get("total")
                    score_txt = f"{sc}/{tot}점" if sc is not None else "점수 없음"
                    memo  = sub.get("memo", "")
                    st.markdown(
                        f'✅ **{sname}** — {score_txt}'
                        + (f' _{memo}_' if memo else ''),
                        unsafe_allow_html=False,
                    )

        # 마감 처리 버튼
        is_active = hw.get("is_active", True)
        if is_active:
            if confirm_delete_btn(
                "마감 처리", key=f"deact_hw_{hw['id']}",
                item_name=hw.get("title", "이 숙제"),
                use_container_width=False,
            ):
                deactivate_homework(hw["id"])
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 학생: 숙제 목록 + 완료 제출
# ─────────────────────────────────────────────────────────────────────────────

def _student_homework_tab(student_id: int, student_name: str, notes: list):
    section_md("📋 내 숙제 목록", "0.75rem", "#059669")

    hw_list = list_homework(active_only=True)
    if not hw_list:
        st.markdown("""
<div style="text-align:center;padding:30px;background:#F0FDF4;border-radius:12px;">
  <div style="font-size:2rem;">🎉</div>
  <div style="font-weight:700;color:#166534;margin-top:8px;">현재 숙제가 없습니다!</div>
</div>
""", unsafe_allow_html=True)
        return

    # 완료/미완료 분리
    pending  = []
    done     = []
    for hw in hw_list:
        sub = get_homework_submission(hw["id"], student_id)
        if sub and sub.get("submitted"):
            done.append((hw, sub))
        else:
            pending.append(hw)

    if pending:
        st.markdown(f'**미완료 숙제 ({len(pending)}개)**')
        for hw in pending:
            hw_type = hw.get("hw_type", "mixed")
            color   = HW_TYPE_COLORS.get(hw_type, "#4F46E5")
            label   = HW_TYPE_LABELS.get(hw_type, hw_type)
            due     = hw.get("due_date", "")[:10]
            title   = hw.get("title", "")
            desc    = hw.get("description", "")
            target  = hw.get("target_score", 80)

            with st.expander(f"{label} | {title} · {_days_left(due)}일 남음"):
                st.markdown(
                    _hw_card(hw),
                    unsafe_allow_html=True,
                )
                # 점수 입력 + 완료 제출
                note_title = ""
                for n in notes:
                    if n["id"] == hw.get("note_id"):
                        note_title = n["title"]
                if note_title:
                    st.markdown(f"📚 관련 노트: **{note_title}**")

                with st.form(f"hw_submit_{hw['id']}"):
                    col_s, col_t = st.columns(2)
                    with col_s:
                        score_in = st.number_input("내 점수", min_value=0,
                                                   max_value=200, value=0)
                    with col_t:
                        total_in = st.number_input("만점", min_value=1,
                                                   max_value=200, value=100)
                    memo_in = st.text_input("메모 (선택)", placeholder="예: 어려웠던 부분...")
                    submit_btn = st.form_submit_button("✅ 완료 제출", type="primary",
                                                       use_container_width=True)

                if submit_btn:
                    try:
                        submit_homework(hw["id"], student_id,
                                        score=score_in, total=total_in, memo=memo_in)
                        st.success("제출 완료! 🎉")
                        st.rerun()
                    except Exception as e:
                        st.error(f"제출 실패: {e}")

    if done:
        st.markdown(f"**완료한 숙제 ({len(done)}개)**")
        for hw, sub in done:
            sc  = sub.get("score")
            tot = sub.get("total")
            pct = int(sc / tot * 100) if sc is not None and tot else None
            pct_txt = f" ({pct}점)" if pct is not None else ""
            color = HW_TYPE_COLORS.get(hw.get("hw_type", ""), "#4F46E5")
            st.markdown(
                f'<div style="background:#F0FDF4;border-radius:10px;padding:10px 14px;'
                f'margin-bottom:6px;border-left:4px solid #059669;">'
                f'<span style="font-weight:700;color:#166534;">✅ {hw["title"]}</span>'
                f'<span style="font-size:0.78rem;color:#94A3B8;margin-left:8px;">'
                f'{sc}/{tot}{pct_txt}</span></div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# 메인 진입점
# ─────────────────────────────────────────────────────────────────────────────

def page_homework(student_id, student_name: str, api_cfg, notes: list):
    """숙제 페이지 진입점"""

    # 테이블 존재 확인
    if not ensure_homework_tables():
        st.error("""
**숙제 기능을 사용하려면 Supabase에 테이블 생성이 필요합니다.**

Supabase → SQL Editor에서 아래 SQL을 실행해 주세요:

```sql
CREATE TABLE IF NOT EXISTS homework (
  id           BIGSERIAL PRIMARY KEY,
  note_id      BIGINT,
  title        TEXT NOT NULL,
  description  TEXT DEFAULT '',
  due_date     DATE NOT NULL,
  hw_type      TEXT DEFAULT 'mixed',
  target_score INT  DEFAULT 80,
  question_ids JSONB,
  is_active    BOOLEAN DEFAULT TRUE,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS homework_submissions (
  id         BIGSERIAL PRIMARY KEY,
  hw_id      BIGINT REFERENCES homework(id) ON DELETE CASCADE,
  student_id BIGINT,
  submitted  BOOLEAN DEFAULT FALSE,
  score      INT,
  total      INT,
  memo       TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(hw_id, student_id)
);

ALTER TABLE homework          DISABLE ROW LEVEL SECURITY;
ALTER TABLE homework_submissions DISABLE ROW LEVEL SECURITY;
GRANT ALL ON homework, homework_submissions TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
```
""")
        return

    # ── 헤더 ───────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,#4F46E5,#059669);
     border-radius:14px;padding:18px 20px;margin-bottom:20px;color:white;">
  <div style="font-size:1.5rem;font-weight:900;">📚 숙제 관리</div>
  <div style="font-size:0.82rem;opacity:0.9;margin-top:4px;">
    선생님: 숙제 출제 + 완료 현황 모니터링 &nbsp;|&nbsp; 학생: 숙제 확인 + 제출
  </div>
</div>
""", unsafe_allow_html=True)

    is_teacher = _auth.is_teacher()

    if is_teacher:
        tab_create, tab_monitor = st.tabs(["➕ 숙제 출제", "📊 진행 현황"])
        with tab_create:
            _teacher_create_tab(notes)
        with tab_monitor:
            _teacher_monitor_tab(notes)
    else:
        # 학생 모드
        if not student_id:
            st.info("학생 이름을 입력하면 숙제 목록을 볼 수 있습니다.")
            return
        _student_homework_tab(student_id, student_name, notes)
