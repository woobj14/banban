# study_dashboard.py — 반반 BanBan 학습 대시보드 v2
# 학생 학습현황 시각화 + 선생님 AI 모니터링 + 맞춤 학습 추천

import math
from datetime import date, datetime, timedelta
from collections import defaultdict

import streamlit as st

from icons import icon, section_md
from supabase_client import get_supabase
import auth as _auth


# ─────────────────────────────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────────────────────────────

def _sb():
    return get_supabase()

def _teacher_check() -> bool:
    return _auth.current_role() in ("teacher", "admin")


# ─────────────────────────────────────────────────────────────────────────────
# 시각화 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _svg_ring(pct: int, color: str = "#7c3aed", size: int = 72,
              label: str = "") -> str:
    """SVG 원형 진행 링"""
    r = size * 0.40
    circ = 2 * math.pi * r
    offset = circ * (1 - max(0, min(100, pct)) / 100)
    fs = max(10, size // 6)
    half = size // 2
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">'
        f'<circle cx="{half}" cy="{half}" r="{r:.1f}" fill="none" '
        f'stroke="#e5e7eb" stroke-width="6"/>'
        f'<circle cx="{half}" cy="{half}" r="{r:.1f}" fill="none" '
        f'stroke="{color}" stroke-width="6" '
        f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" '
        f'stroke-linecap="round" '
        f'transform="rotate(-90 {half} {half})"/>'
        f'<text x="{half}" y="{half - (5 if label else 0)}" text-anchor="middle" '
        f'dominant-baseline="middle" font-size="{fs}" '
        f'font-weight="800" fill="#1f2937">{pct}%</text>'
        + (f'<text x="{half}" y="{half + fs}" text-anchor="middle" '
           f'font-size="{max(8, fs-3)}" fill="#6b7280">{label}</text>'
           if label else "")
        + f'</svg>'
    )


def _hbar(pct: int, color: str = "#7c3aed", height: int = 8,
          show_pct: bool = True) -> str:
    """CSS 수평 진행 바"""
    safe = max(0, min(100, pct))
    pct_txt = f'<span style="font-size:0.7rem;color:{color};font-weight:700;margin-left:6px;">{safe}%</span>' if show_pct else ""
    return (
        f'<div style="display:flex;align-items:center;gap:4px;">'
        f'<div style="flex:1;background:#e5e7eb;border-radius:{height}px;height:{height}px;overflow:hidden;">'
        f'<div style="background:{color};height:100%;width:{safe}%;border-radius:{height}px;'
        f'transition:width 0.6s ease;"></div></div>{pct_txt}</div>'
    )


def _week_heatmap(daily_counts: dict[str, int]) -> str:
    """지난 7일 활동 히트맵"""
    today = date.today()
    cells = ""
    for i in range(6, -1, -1):
        d     = today - timedelta(days=i)
        ds    = str(d)
        cnt   = daily_counts.get(ds, 0)
        day_kr = ["월", "화", "수", "목", "금", "토", "일"][d.weekday()]
        if cnt == 0:   bg, fc = "#f3f4f6", "#9ca3af"
        elif cnt <= 2: bg, fc = "#ddd6fe", "#5b21b6"
        elif cnt <= 4: bg, fc = "#a78bfa", "#ffffff"
        else:          bg, fc = "#7c3aed", "#ffffff"
        tip = f"{d.strftime('%m/%d')} {cnt}회"
        cells += (
            f'<div style="background:{bg};border-radius:6px;'
            f'display:flex;flex-direction:column;align-items:center;'
            f'justify-content:center;padding:6px 4px;gap:2px;" title="{tip}">'
            f'<span style="font-size:0.62rem;color:{fc};font-weight:700;">{day_kr}</span>'
            f'<span style="font-size:0.85rem;color:{fc};font-weight:900;">'
            f'{"●" if cnt > 0 else "○"}</span>'
            f'<span style="font-size:0.58rem;color:{fc};">{cnt}회</span>'
            f'</div>'
        )
    return (
        f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:4px;">'
        f'{cells}</div>'
    )


def _module_bar_chart(module_stats: dict) -> str:
    """모듈별 성과 수평 바 차트"""
    _LABEL = {
        "word_quiz": ("단어 퀴즈", "#818CF8"),
        "grammar":   ("문법 드릴", "#A78BFA"),
        "exam":      ("내신 문제", "#34D399"),
        "past":      ("기출 문제", "#2DD4BF"),
    }
    rows = ""
    for act, (label, color) in _LABEL.items():
        stat = module_stats.get(act, {})
        if not stat.get("sessions"):
            continue
        avg   = stat.get("avg_score") or 0
        sess  = stat.get("sessions", 0)
        last  = stat.get("last_score")
        trend = ""
        if last is not None and avg:
            if last > avg + 5:   trend = ' <span style="color:#16a34a;font-size:0.7rem;">▲</span>'
            elif last < avg - 5: trend = ' <span style="color:#dc2626;font-size:0.7rem;">▼</span>'
        rows += (
            f'<div style="margin-bottom:10px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:0.8rem;margin-bottom:4px;">'
            f'<span style="font-weight:700;color:#374151;">{label}</span>'
            f'<span style="color:{color};">{sess}회 · {avg:.0f}점{trend}</span></div>'
            + _hbar(int(avg), color, height=9, show_pct=False)
            + f'</div>'
        )
    return rows or '<div style="color:#9ca3af;font-size:0.85rem;">아직 기록 없음</div>'


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 로더
# ─────────────────────────────────────────────────────────────────────────────

def _load_student_summary(student_id: int) -> dict:
    """대시보드 학생 데이터 종합"""
    sb = _sb()

    # study_logs 전체 조회
    logs_res = sb.table("study_logs").select("*") \
                 .eq("student_id", student_id) \
                 .order("created_at", desc=True).execute()
    logs = logs_res.data or []

    # 모듈별 통계
    mod_stats: dict = {}
    for row in logs:
        act = row.get("activity", "")
        if act not in mod_stats:
            mod_stats[act] = {"sessions": 0, "scores": [], "last_score": None}
        mod_stats[act]["sessions"] += 1
        if row.get("score") is not None and row.get("total"):
            pct = row["score"] / row["total"] * 100
            mod_stats[act]["scores"].append(pct)
            if mod_stats[act]["last_score"] is None:
                mod_stats[act]["last_score"] = pct
    for stat in mod_stats.values():
        sc = stat["scores"]
        stat["avg_score"] = round(sum(sc) / len(sc), 1) if sc else None

    # 스트릭 계산 (연속 학습일)
    dates_set = {row["created_at"][:10] for row in logs}
    streak = 0
    cur = date.today()
    while str(cur) in dates_set:
        streak += 1
        cur -= timedelta(days=1)

    # 최근 7일 일별 학습 횟수
    daily: dict = defaultdict(int)
    cutoff7 = str(date.today() - timedelta(days=6))
    recent_logs = [r for r in logs if r.get("created_at", "") >= cutoff7]
    for r in recent_logs:
        daily[r["created_at"][:10]] += 1

    # 이번 주 총 세션
    week_sessions = sum(daily.values())

    # 오답 카운트
    try:
        word_wrong_cnt = (sb.table("wrong_notes").select("*", count="exact")
                           .eq("student_id", student_id).execute().count or 0)
    except Exception:
        word_wrong_cnt = 0
    try:
        q_wrong_cnt = (sb.table("question_wrong_notes").select("*", count="exact")
                        .eq("student_id", student_id).execute().count or 0)
    except Exception:
        q_wrong_cnt = 0

    # 전체 평균 점수
    all_scores = [s for stat in mod_stats.values() for s in stat["scores"]]
    overall_avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else None

    return {
        "logs":               logs,
        "mod_stats":          mod_stats,
        "streak":             streak,
        "week_sessions":      week_sessions,
        "daily_counts":       dict(daily),
        "word_wrong_count":   word_wrong_cnt,
        "q_wrong_count":      q_wrong_cnt,
        "overall_avg":        overall_avg,
        "total_sessions":     len(logs),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 학생 개인 대시보드
# ─────────────────────────────────────────────────────────────────────────────

def _render_my_stats(student_id: int | None, student_name: str = ""):
    user = _auth.current_user()
    if not user and not student_id:
        st.info("로그인이 필요합니다.")
        return

    # student_id: BIGINT 정수 우선 / auth.current_student_id() 폴백 / UUID는 사용 안 함
    sid = student_id or _auth.current_student_id()
    if not sid:
        st.info("학생 계정으로 로그인하세요.")
        return

    # 로딩
    with st.spinner("학습 현황 불러오는 중…"):
        try:
            summary = _load_student_summary(sid)
        except Exception as e:
            st.error(f"데이터 조회 오류: {e}")
            return

    streak        = summary["streak"]
    week_sessions = summary["week_sessions"]
    word_wrong    = summary["word_wrong_count"]
    q_wrong       = summary["q_wrong_count"]
    overall_avg   = summary["overall_avg"]
    mod_stats     = summary["mod_stats"]
    daily_counts  = summary["daily_counts"]

    # ── 히어로 헤더 ─────────────────────────────────────────
    if streak >= 14: level_label, level_color, level_icon = "전설",  "#FCD34D", "award"
    elif streak >= 7: level_label, level_color, level_icon = "강자",  "#C4B5FD", "zap"
    elif streak >= 3: level_label, level_color, level_icon = "성장",  "#86EFAC", "trending-up"
    else:             level_label, level_color, level_icon = "새싹",  "#BAE6FD", "book-open"

    hero_icon   = icon("bar-chart-2", 13, "rgba(255,255,255,0.65)")
    streak_icon = icon(level_icon,    22, level_color)
    name_txt    = student_name + "의 " if student_name else ""

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#3730A3 0%,#4F46E5 50%,#6D28D9 100%);'
        f'color:white;border-radius:20px;padding:24px 26px;margin-bottom:18px;'
        f'box-shadow:0 4px 20px rgba(79,70,229,0.30),0 1px 4px rgba(0,0,0,0.08);'
        f'position:relative;overflow:hidden;">'
        f'<div style="position:absolute;top:-40px;right:-40px;width:180px;height:180px;'
        f'border-radius:50%;background:rgba(255,255,255,0.04);pointer-events:none;"></div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div>'
        f'<div style="font-size:0.72rem;color:rgba(255,255,255,0.6);font-weight:600;'
        f'letter-spacing:0.5px;margin-bottom:6px;display:flex;align-items:center;gap:5px;">'
        f'{hero_icon} 내 학습 현황</div>'
        f'<div style="font-size:1.5rem;font-weight:900;letter-spacing:-0.5px;line-height:1.1;">'
        f'{name_txt}학습 대시보드</div>'
        f'<div style="display:inline-flex;align-items:center;gap:6px;margin-top:10px;'
        f'background:rgba(255,255,255,0.12);border-radius:20px;padding:4px 12px;">'
        f'{icon(level_icon, 12, level_color)}'
        f'<span style="font-size:0.72rem;font-weight:700;color:{level_color};">{level_label}</span>'
        f'</div>'
        f'</div>'
        f'<div style="text-align:center;background:rgba(255,255,255,0.1);'
        f'border-radius:16px;padding:14px 18px;">'
        f'{streak_icon}'
        f'<div style="font-size:1.8rem;font-weight:900;line-height:1;margin-top:4px;">{streak}</div>'
        f'<div style="font-size:0.65rem;color:rgba(255,255,255,0.65);margin-top:2px;">일 연속</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── KPI — 글래스 한 판 + 헤어라인 구분 (네모 박스 제거) ────────
    streak_color = "#7C3AED" if streak >= 7 else "#0891B2" if streak >= 3 else "#64748B"
    w_color = "#EF4444" if word_wrong > 10 else "#F59E0B" if word_wrong > 0 else "#10B981"
    q_color = "#EF4444" if q_wrong > 10 else "#F59E0B" if q_wrong > 0 else "#10B981"

    _kpi_div = ('<div style="width:1px;align-self:stretch;margin:8px 0;'
                'background:linear-gradient(180deg,transparent,rgba(100,116,139,0.16),transparent);"></div>')

    def _kpi_cell(icon_name, value, label, color):
        return (
            f'<div style="flex:1;text-align:center;padding:6px 4px;">'
            f'<div style="display:inline-flex;align-items:center;gap:5px;'
            f'justify-content:center;margin-bottom:8px;">'
            f'{icon(icon_name, 15, color)}'
            f'<span style="font-size:1.55rem;font-weight:800;color:{color};'
            f'line-height:1;letter-spacing:-0.5px;">{value}</span></div>'
            f'<div style="font-size:0.72rem;color:#94A3B8;font-weight:500;">{label}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div style="display:flex;align-items:center;'
        f'background:rgba(255,255,255,0.72);'
        f'backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);'
        f'border:1px solid rgba(255,255,255,0.7);border-radius:20px;'
        f'padding:12px 8px;margin-bottom:14px;'
        f'box-shadow:0 8px 32px rgba(31,38,135,0.07),0 1px 2px rgba(0,0,0,0.03);">'
        + _kpi_cell("zap", f"{streak}일", "연속 학습", streak_color)
        + _kpi_div
        + _kpi_cell("calendar", f"{week_sessions}회", "이번주 학습", "#0891B2")
        + _kpi_div
        + _kpi_cell("book-open", f"{word_wrong}개", "단어 오답", w_color)
        + _kpi_div
        + _kpi_cell("alert-circle", f"{q_wrong}개", "문제 오답", q_color)
        + '</div>',
        unsafe_allow_html=True,
    )

    # ── 이번 주 활동 + 모듈 성과 ─────────────────────────────
    col_left, col_right = st.columns([1, 1])

    _CARD = ('background:rgba(255,255,255,0.72);'
             'backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);'
             'border:1px solid rgba(255,255,255,0.7);border-radius:20px;padding:18px 22px;'
             'box-shadow:0 8px 32px rgba(31,38,135,0.07),0 1px 2px rgba(0,0,0,0.03);')

    with col_left:
        st.markdown(
            f'<div style="{_CARD}">'
            f'<div style="font-size:0.75rem;font-weight:700;color:#6B7280;'
            f'margin-bottom:12px;display:flex;align-items:center;gap:5px;">'
            f'{icon("calendar",13,"#6B7280")} 이번 주 활동</div>'
            f'{_week_heatmap(daily_counts)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_right:
        avg_txt = f"{overall_avg}점" if overall_avg is not None else "—"
        avg_color_val = "#16A34A" if (overall_avg or 0) >= 80 else "#D97706" if (overall_avg or 0) >= 60 else "#DC2626"
        st.markdown(
            f'<div style="{_CARD}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">'
            f'<div style="font-size:0.75rem;font-weight:700;color:#6B7280;'
            f'display:flex;align-items:center;gap:5px;">'
            f'{icon("trending-up",13,"#6B7280")} 모듈별 성과</div>'
            f'<div style="font-size:0.8rem;font-weight:800;color:{avg_color_val};">전체 {avg_txt}</div>'
            f'</div>'
            f'{_module_bar_chart(mod_stats)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── 성과 링 ─────────────────────────────────────────────
    _RING_INFO = [
        ("word_quiz", "단어", "#6366F1"),
        ("grammar",   "문법", "#8B5CF6"),
        ("exam",      "내신", "#10B981"),
        ("past",      "기출", "#06B6D4"),
    ]
    ring_html = '<div style="display:flex;gap:12px;justify-content:space-around;flex-wrap:wrap;">'
    for act, label, color in _RING_INFO:
        stat = mod_stats.get(act, {})
        avg  = int(stat.get("avg_score") or 0)
        ring_html += (
            f'<div style="text-align:center;">'
            + _svg_ring(avg, color, 76, label)
            + f'</div>'
        )
    ring_html += '</div>'

    st.markdown(
        f'<div style="{_CARD}margin-bottom:14px;">'
        f'<div style="font-size:0.75rem;font-weight:700;color:#6B7280;'
        f'margin-bottom:16px;display:flex;align-items:center;gap:5px;">'
        f'{icon("award",13,"#6B7280")} 모듈 숙련도 (평균 정확도)</div>'
        f'{ring_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 최근 학습 이력 ───────────────────────────────────────
    logs = summary["logs"][:8]
    if logs:
        _ACT = {"word_quiz":"단어퀴즈","grammar":"문법드릴","exam":"내신문제","past":"기출"}
        rows_html = ""
        for r in logs:
            act   = _ACT.get(r.get("activity", ""), r.get("activity", "기타"))
            score = r.get("score")
            total = r.get("total")
            sc_txt = f"{score}/{total}" if score is not None and total else "—"
            pct    = int(score / total * 100) if score is not None and total else 0
            ts     = r.get("created_at", "")[:16].replace("T", " ")
            color  = "#16a34a" if pct >= 80 else "#f59e0b" if pct >= 60 else "#dc2626"
            rows_html += (
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:7px 0;border-bottom:1px solid #f3f4f6;font-size:0.82rem;">'
                f'<span style="color:#374151;font-weight:600;">{act}</span>'
                f'<span style="color:{color};font-weight:700;">{sc_txt}점</span>'
                f'<span style="color:#9ca3af;">{ts}</span></div>'
            )
        st.markdown(
            f'<div style="{_CARD}">'
            f'<div style="font-size:0.75rem;font-weight:700;color:#6B7280;'
            f'margin-bottom:12px;display:flex;align-items:center;gap:5px;">'
            f'{icon("clock",13,"#6B7280")} 최근 학습 이력</div>'
            f'{rows_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _kpi(col, icon_name: str, value: str, label: str, color: str,
         bg: str = "white", subtitle: str = ""):
    icon_svg  = icon(icon_name, 20, color)
    sub_html  = (f'<div style="font-size:0.68rem;color:#9CA3AF;margin-top:2px;">'
                 f'{subtitle}</div>') if subtitle else ""
    col.markdown(
        f'<div style="background:{bg};border-radius:16px;padding:18px 14px;text-align:center;'
        f'box-shadow:0 1px 3px rgba(0,0,0,0.04),0 8px 24px rgba(0,0,0,0.06);">'
        f'<div style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:38px;height:38px;border-radius:11px;'
        f'background:linear-gradient(135deg,{color}18,{color}30);margin-bottom:10px;">'
        f'{icon_svg}</div>'
        f'<div style="font-size:1.55rem;font-weight:900;color:{color};line-height:1;">{value}</div>'
        f'<div style="font-size:0.72rem;color:#6B7280;font-weight:600;margin-top:5px;">{label}</div>'
        f'{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 선생님 대시보드  — Premium Edition
#
# ■ 심리학 자문 원칙 (학술 근거 기반 — 추측·허위 정보 배제)
#
# [Dr. 이수진 — 교육심리학자, 자기결정이론(SDT) 전문]
#   • Deci & Ryan (1985) 자기결정이론: 유능감(Competence), 자율성(Autonomy),
#     관계성(Relatedness) 충족 시 내재 동기 극대화.
#   → 선생님에게 학생 데이터를 시각화해 "유능감"을 강화. 내가 학생에게
#     실질적 영향을 미치고 있다는 증거를 제공한다.
#
# [Dr. 박민호 — 소비자심리학자, 지각된 가치(Perceived Value) 전문]
#   • Zeithaml (1988) 지각된 가치 모델: 고객이 지불 대비 받는다고 느끼는
#     가치가 만족도와 재구매 의도를 결정.
#   → 선생님이 "이 가격에 이런 프리미엄 도구를"이라고 느끼게 해야 함.
#     시각적 완성도, 맞춤 인사, 전용 배지로 지각된 가치를 높인다.
#   • Endowment Effect (Thaler, 1980): 소유한 것은 더 가치 있다고 인식.
#   → "선생님의 클래스", "선생님의 학생들"처럼 소유격 표현 사용.
#
# [Dr. 김아영 — 사회심리학자, 사회적 정체성 이론 전문]
#   • Tajfel & Turner (1979) 사회적 정체성 이론: 자신이 속한 집단의 위상이
#     자아 존중감에 직결됨.
#   → "프리미엄 선생님" 뱃지로 긍정적 집단 정체성 강화. 교사는 서비스
#     제공자이면서 동시에 서비스 소비자 — 그들도 대우받아야 함.
#   • Cialdini (1984) 상호성 원칙: 예상보다 더 많이 받으면 충성도 상승.
#   → 기대를 초과하는 UI 퀄리티가 충성도를 만든다.
#
# ■ 디자인 지침
#   • 모든 아이콘: Lucide Icons (icons.py의 icon() 함수 사용 — 항상 준수)
#   • 색상: 딥 인디고(신뢰·권위) + 앰버 골드(프리미엄·온기) 조합
#   • 어조: 따뜻하고 전문적, "선생님의 ~" 소유격으로 소속감 강화
# ─────────────────────────────────────────────────────────────────────────────

def _render_teacher_dashboard(api_config: dict | None):
    user = _auth.current_user()
    if not user:
        st.info("로그인이 필요합니다.")
        return

    if not _teacher_check():
        st.warning("선생님/관리자 계정이 필요합니다.")
        return

    teacher_name = _auth.current_student_name() or "선생님"

    # ── 학생 수 미리 조회 (히어로 섹션용) ───────────────────
    try:
        total_students = _sb().table("profiles") \
            .select("id", count="exact") \
            .eq("teacher_id", user.id).eq("role", "student") \
            .execute().count or 0
    except Exception:
        total_students = 0

    # ── 이번 주 전체 학습 세션 수 ────────────────────────────
    cutoff7 = (datetime.now() - timedelta(days=7)).isoformat()
    try:
        week_sessions = _sb().table("study_logs") \
            .select("id", count="exact") \
            .gte("created_at", cutoff7).execute().count or 0
    except Exception:
        week_sessions = 0

    # ── 시간대별 인사 (Personalization — 지각된 가치 강화) ───
    hour = datetime.now().hour
    if hour < 12:   greeting = "좋은 아침이에요"
    elif hour < 18: greeting = "안녕하세요"
    else:           greeting = "수고 많으셨어요"

    # ── 프리미엄 히어로 배너 ─────────────────────────────────
    # [Dr. 박민호] 지각된 가치 + [Dr. 김아영] 사회적 정체성:
    # "프리미엄" 뱃지 + 소유격 + 개인화된 인사로 자아존중감 강화
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#1E1B4B 0%,#312E81 50%,#3730A3 100%);
     color:white;border-radius:20px;padding:28px 28px 24px;margin-bottom:6px;
     position:relative;overflow:hidden;">
  <div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;
       border-radius:50%;background:rgba(255,255,255,0.03);pointer-events:none;"></div>
  <div style="position:absolute;bottom:-60px;left:30%;width:300px;height:300px;
       border-radius:50%;background:rgba(167,139,250,0.05);pointer-events:none;"></div>

  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px;">
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
      <span style="background:linear-gradient(135deg,#D97706,#F59E0B);color:white;
             border-radius:20px;padding:4px 12px;font-size:0.72rem;font-weight:800;
             letter-spacing:0.5px;box-shadow:0 2px 8px rgba(217,119,6,0.4);">
        ✦ PREMIUM
      </span>
      <span style="background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.8);
             border-radius:20px;padding:4px 12px;font-size:0.72rem;font-weight:600;
             border:1px solid rgba(255,255,255,0.15);">
        {icon("graduation-cap", 12, "rgba(255,255,255,0.8)")} 선생님 플랜
      </span>
    </div>
    <div style="font-size:0.75rem;opacity:0.55;text-align:right;">
      {date.today().strftime("%Y년 %m월 %d일")}
    </div>
  </div>

  <div style="margin-bottom:20px;">
    <div style="font-size:0.85rem;opacity:0.7;margin-bottom:5px;
         display:flex;align-items:center;gap:6px;">
      {icon("sparkles", 13, "rgba(253,230,138,0.9)")}
      {greeting}, <strong style="color:#FDE68A;">{teacher_name}</strong>님
    </div>
    <div style="font-size:1.55rem;font-weight:900;letter-spacing:-0.5px;line-height:1.2;">
      학습 모니터링 센터
    </div>
    <div style="font-size:0.8rem;opacity:0.65;margin-top:6px;">
      선생님의 클래스를 AI가 함께 분석합니다
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
    <div style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);
         border-radius:12px;padding:12px 14px;backdrop-filter:blur(10px);">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;opacity:0.7;font-size:0.72rem;">
        {icon("users", 12, "rgba(255,255,255,0.7)")} 등록 학생
      </div>
      <div style="font-size:1.6rem;font-weight:900;line-height:1;">{total_students}</div>
      <div style="font-size:0.7rem;opacity:0.55;margin-top:2px;">명</div>
    </div>
    <div style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.12);
         border-radius:12px;padding:12px 14px;backdrop-filter:blur(10px);">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;opacity:0.7;font-size:0.72rem;">
        {icon("zap", 12, "rgba(255,255,255,0.7)")} 이번 주 학습
      </div>
      <div style="font-size:1.6rem;font-weight:900;line-height:1;">{week_sessions}</div>
      <div style="font-size:0.7rem;opacity:0.55;margin-top:2px;">세션</div>
    </div>
    <div style="background:rgba(253,230,138,0.12);border:1px solid rgba(253,230,138,0.2);
         border-radius:12px;padding:12px 14px;backdrop-filter:blur(10px);">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;
           opacity:0.85;font-size:0.72rem;color:#FDE68A;">
        {icon("brain", 12, "#FDE68A")} AI 분석
      </div>
      <div style="font-size:1.1rem;font-weight:800;line-height:1;color:#FDE68A;">준비됨</div>
      <div style="font-size:0.7rem;opacity:0.65;margin-top:2px;color:#FDE68A;">학생별 맞춤</div>
    </div>
  </div>
</div>
<div style="height:4px"></div>
""", unsafe_allow_html=True)

    # ── 탭 ─────────────────────────────────────────────────
    tab_students, tab_detail, tab_invite = st.tabs([
        "학생 현황", "심층 분석", "초대 코드"
    ])

    # ══ 탭 1: 학생 현황 ════════════════════════════════════
    with tab_students:
        try:
            students_res = _sb().table("profiles") \
                .select("id, student_id, name, class_label, created_at") \
                .eq("teacher_id", user.id) \
                .eq("role", "student") \
                .order("name").execute()
            students = students_res.data or []
        except Exception:
            students = []

        if not students:
            st.markdown(f"""
<div style="background:#F8FAFF;border:1.5px dashed #C7D2FE;border-radius:16px;
     padding:36px 24px;text-align:center;margin:16px 0;">
  <div style="font-size:2rem;margin-bottom:12px;">{icon("user-plus", 32, "#6366F1")}</div>
  <div style="font-weight:800;color:#312E81;font-size:1rem;margin-bottom:6px;">
    아직 등록된 학생이 없습니다
  </div>
  <div style="font-size:0.82rem;color:#6B7280;line-height:1.6;">
    <b>초대 코드</b> 탭에서 코드를 발급하고<br>학생들에게 공유하세요
  </div>
</div>
""", unsafe_allow_html=True)

        # 배치 조회 — profiles.student_id(BIGINT) = study_logs.student_id
        student_ids = [s["student_id"] for s in students if s.get("student_id")]
        try:
            logs_res = _sb().table("study_logs") \
                .select("student_id, activity, score, total, created_at") \
                .in_("student_id", student_ids) \
                .gte("created_at", cutoff7).execute()
            recent_by_student: dict = defaultdict(list)
            for r in (logs_res.data or []):
                recent_by_student[r["student_id"]].append(r)
        except Exception:
            recent_by_student = {}

        if students:
            # 요약 헤더
            active_count = sum(
                1 for s in students
                if s.get("student_id") and
                   len({r["created_at"][:10] for r in recent_by_student.get(s["student_id"], [])}) >= 3
            )
            st.markdown(f"""
<div style="display:flex;gap:10px;margin:12px 0 14px;flex-wrap:wrap;">
  <div style="background:#EEF2FF;border-radius:10px;padding:8px 16px;
       font-size:0.8rem;font-weight:700;color:#4338CA;
       display:flex;align-items:center;gap:6px;">
    {icon("users", 14, "#4338CA")} 전체 {len(students)}명
  </div>
  <div style="background:#F0FDF4;border-radius:10px;padding:8px 16px;
       font-size:0.8rem;font-weight:700;color:#15803D;
       display:flex;align-items:center;gap:6px;">
    {icon("trending-up", 14, "#15803D")} 이번 주 활발 {active_count}명
  </div>
  <div style="background:#FFFBEB;border-radius:10px;padding:8px 16px;
       font-size:0.8rem;font-weight:700;color:#B45309;
       display:flex;align-items:center;gap:6px;">
    {icon("alert-circle", 14, "#B45309")} 관심 필요 {len(students) - active_count}명
  </div>
</div>
""", unsafe_allow_html=True)

        for s in students:
            sid  = s.get("student_id")
            name = s.get("name", "—")
            cls  = s.get("class_label", "")
            if not sid:
                continue
            rlogs       = recent_by_student.get(sid, [])
            n_week      = len(rlogs)
            active_days = len({r["created_at"][:10] for r in rlogs})
            scores      = [r["score"] / r["total"] * 100
                           for r in rlogs
                           if r.get("score") is not None and r.get("total")]
            avg         = round(sum(scores) / len(scores)) if scores else None
            avg_txt     = f"{avg}점" if avg is not None else "—"

            # [Dr. 김아영] 신호등 시스템 — 즉각적 상태 파악 (인지 용이성)
            if active_days >= 5:
                health_c, health_t, health_bg, health_icon = "#15803D","활발","#F0FDF4","check-circle"
            elif active_days >= 2:
                health_c, health_t, health_bg, health_icon = "#B45309","보통","#FFFBEB","clock"
            else:
                health_c, health_t, health_bg, health_icon = "#DC2626","관심필요","#FEF2F2","alert-circle"

            week_html = _week_mini(rlogs)
            # 점수 색상
            score_c = "#15803D" if avg and avg >= 80 else "#B45309" if avg and avg >= 60 else "#DC2626"

            st.markdown(f"""
<div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
     padding:16px 18px;margin-bottom:10px;
     box-shadow:0 1px 4px rgba(0,0,0,0.05);
     transition:box-shadow .2s;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:42px;height:42px;border-radius:50%;flex-shrink:0;
         background:linear-gradient(135deg,#EEF2FF,#C7D2FE);
         display:flex;align-items:center;justify-content:center;
         font-weight:900;font-size:1rem;color:#4338CA;">
      {name[0] if name else "?"}
    </div>
    <div style="flex:1;min-width:0;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="font-weight:800;color:#111827;font-size:0.95rem;">{name}</span>
        {f'<span style="font-size:0.72rem;color:#9CA3AF;font-weight:500;">{cls}</span>' if cls else ""}
        <span style="background:{health_bg};color:{health_c};border-radius:8px;
               padding:2px 8px;font-size:0.7rem;font-weight:700;
               display:inline-flex;align-items:center;gap:3px;">
          {icon(health_icon, 10, health_c)} {health_t}
        </span>
      </div>
      <div style="display:flex;gap:14px;margin-top:6px;flex-wrap:wrap;">
        <span style="font-size:0.75rem;color:#6B7280;display:flex;align-items:center;gap:3px;">
          {icon("book-open", 11, "#6B7280")} {n_week}회 학습
        </span>
        <span style="font-size:0.75rem;color:#6B7280;display:flex;align-items:center;gap:3px;">
          {icon("calendar", 11, "#6B7280")} {active_days}일 활동
        </span>
        <span style="font-size:0.75rem;font-weight:700;color:{score_c};
               display:flex;align-items:center;gap:3px;">
          {icon("target", 11, score_c)} 평균 {avg_txt}
        </span>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;">
      <div style="font-size:0.65rem;color:#9CA3AF;font-weight:600;">최근 7일</div>
      {week_html}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

        if students:
            col_r, _ = st.columns([1, 4])
            with col_r:
                if st.button("🔄 새로고침",
                             key="refresh_list", use_container_width=True):
                    st.rerun()

    # ══ 탭 2: 심층 분석 ════════════════════════════════════
    with tab_detail:
        try:
            students_res2 = _sb().table("profiles") \
                .select("id, student_id, name, class_label") \
                .eq("teacher_id", user.id).eq("role", "student") \
                .order("name").execute()
            students2 = students_res2.data or []
        except Exception:
            students2 = []

        if not students2:
            st.markdown(f"""
<div style="background:#F8FAFF;border:1.5px dashed #C7D2FE;border-radius:16px;
     padding:36px 24px;text-align:center;margin:16px 0;">
  <div style="margin-bottom:10px;">{icon("search", 32, "#6366F1")}</div>
  <div style="font-weight:800;color:#312E81;">학생을 먼저 등록하세요</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div style="background:#F8FAFF;border:1px solid #E0E7FF;border-radius:12px;
     padding:12px 16px;margin:10px 0 14px;
     display:flex;align-items:center;gap:8px;font-size:0.82rem;color:#3730A3;">
  {icon("brain", 15, "#4F46E5")}
  <span><b>AI 심층 분석</b> — 학생을 선택하면 학습 패턴과 맞춤 지도 방향을 분석합니다</span>
</div>
""", unsafe_allow_html=True)
            sel_name  = st.selectbox(
                "분석할 학생",
                [f"{s['name']} ({s.get('class_label','')})" for s in students2],
                key="teacher_sel_student",
            )
            sel_idx   = [f"{s['name']} ({s.get('class_label','')})" for s in students2].index(sel_name)
            sel_s     = students2[sel_idx]
            sel_sid   = sel_s.get("student_id") or sel_s["id"]
            sel_sname = sel_s["name"]

            with st.spinner(f"{sel_sname} 학생 데이터 불러오는 중…"):
                try:
                    from study_db import get_rich_student_profile
                    profile = get_rich_student_profile(sel_sid)
                except Exception as e:
                    st.error(f"프로파일 조회 실패: {e}")
                    profile = {}

            if profile:
                _render_student_detail(sel_sname, profile, api_config)

    # ══ 탭 3: 초대 코드 ════════════════════════════════════
    with tab_invite:
        _render_invite_tab(user)


def _week_mini(logs: list) -> str:
    """학생 카드용 7일 미니 히트맵 — Lucide 없이 순수 CSS dot"""
    today = date.today()
    daily: dict = defaultdict(int)
    for r in logs:
        daily[r["created_at"][:10]] += 1
    cells = ""
    day_labels = ["월","화","수","목","금","토","일"]
    for i in range(6, -1, -1):
        d   = today - timedelta(days=i)
        cnt = daily.get(str(d), 0)
        if cnt == 0:   bg, border = "#F3F4F6", "#E5E7EB"
        elif cnt <= 2: bg, border = "#C7D2FE", "#A5B4FC"
        else:          bg, border = "#6366F1", "#4F46E5"
        label = day_labels[d.weekday()]
        cells += (
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:2px;">'
            f'<div style="width:14px;height:14px;border-radius:4px;'
            f'background:{bg};border:1px solid {border};" title="{d.strftime("%m/%d")} {cnt}회"></div>'
            f'<div style="font-size:0.55rem;color:#9CA3AF;">{label}</div>'
            f'</div>'
        )
    return f'<div style="display:flex;gap:3px;">{cells}</div>'


def _render_student_detail(name: str, profile: dict, api_config: dict | None):
    """선생님용 학생 개별 심층 분석 — Premium UI"""
    # [Dr. 이수진] 유능감 강화: 선생님에게 충분한 정보를 제공해 "내가 이 학생을 안다"는
    # 확신을 준다 (Competence need, SDT)
    mod_stats = profile.get("module_stats", {})
    streak    = profile.get("streak", 0)
    tot_sess  = profile.get("total_sessions", 0)
    act_days  = profile.get("recent_activity_days", 0)
    ww        = profile.get("word_wrong_count", 0)
    wwords    = profile.get("weak_words", [])
    wtopics   = profile.get("weak_q_topics", [])

    # 학생 요약 헤더
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#F8FAFF,#EEF2FF);
     border:1px solid #C7D2FE;border-radius:14px;padding:16px 20px;margin:12px 0 16px;">
  <div style="display:flex;align-items:center;gap:10px;">
    <div style="width:48px;height:48px;border-radius:50%;flex-shrink:0;
         background:linear-gradient(135deg,#4F46E5,#6366F1);
         display:flex;align-items:center;justify-content:center;
         font-weight:900;font-size:1.2rem;color:white;">
      {name[0] if name else "?"}
    </div>
    <div>
      <div style="font-weight:900;color:#1E1B4B;font-size:1.05rem;">{name} 학생</div>
      <div style="font-size:0.78rem;color:#6B7280;margin-top:2px;
           display:flex;align-items:center;gap:4px;">
        {icon("bar-chart-2", 12, "#6366F1")} 총 {tot_sess}회 학습 &nbsp;·&nbsp;
        {icon("flame", 12, "#EF4444")} {streak}일 연속 &nbsp;·&nbsp;
        {icon("calendar-check", 12, "#16A34A")} 이번 주 {act_days}일 활동
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # KPI 4개
    col1, col2, col3, col4 = st.columns(4)
    _kpi_icon(col1, "flame",          f"{streak}일",   "연속 학습",    "#7C3AED", "#FAF5FF", "#EDE9FE")
    _kpi_icon(col2, "bar-chart-2",    f"{tot_sess}회", "총 세션",       "#0891B2", "#F0F9FF", "#BAE6FD")
    _kpi_icon(col3, "alert-triangle", f"{ww}개",       "단어 오답",
              "#DC2626" if ww > 10 else "#D97706",
              "#FEF2F2" if ww > 10 else "#FFFBEB",
              "#FECACA" if ww > 10 else "#FDE68A")
    _kpi_icon(col4, "calendar",       f"{act_days}일", "이번 주 활동",
              "#15803D" if act_days >= 5 else "#D97706",
              "#F0FDF4" if act_days >= 5 else "#FFFBEB",
              "#BBF7D0" if act_days >= 5 else "#FDE68A")

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # 모듈 성과
    st.markdown(f"""
<div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
     padding:18px 20px;margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
  <div style="display:flex;align-items:center;gap:7px;margin-bottom:14px;">
    {icon("bar-chart-2", 15, "#4338CA")}
    <span style="font-size:0.88rem;font-weight:800;color:#1E1B4B;">모듈별 학습 성과</span>
  </div>
  {_module_bar_chart(mod_stats)}
</div>
""", unsafe_allow_html=True)

    # 취약 영역
    colA, colB = st.columns(2)
    with colA:
        wwords_html = "".join(
            f'<span style="background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;'
            f'border-radius:8px;padding:3px 10px;font-size:0.78rem;font-weight:600;margin:2px;">{w}</span>'
            for w in wwords
        ) or f'<span style="color:#9CA3AF;font-size:0.82rem;">{icon("check-circle", 13, "#16A34A")} 없음</span>'
        st.markdown(f"""
<div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
     padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
    {icon("alert-circle", 14, "#DC2626")}
    <span style="font-size:0.85rem;font-weight:800;color:#1E1B4B;">취약 단어 Top 5</span>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:5px;">{wwords_html}</div>
</div>
""", unsafe_allow_html=True)

    with colB:
        wtopics_html = "".join(
            f'<span style="background:#FFFBEB;color:#92400E;border:1px solid #FDE68A;'
            f'border-radius:8px;padding:3px 10px;font-size:0.78rem;font-weight:600;margin:2px;">{t}</span>'
            for t in wtopics
        ) or f'<span style="color:#9CA3AF;font-size:0.82rem;">{icon("check-circle", 13, "#16A34A")} 없음</span>'
        st.markdown(f"""
<div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
     padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;">
    {icon("target", 14, "#D97706")}
    <span style="font-size:0.85rem;font-weight:800;color:#1E1B4B;">취약 문제 유형</span>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:5px;">{wtopics_html}</div>
</div>
""", unsafe_allow_html=True)

    # ── AI 맞춤 추천 ─────────────────────────────────────────
    # [Dr. 박민호] 기대 초과 제공(Reciprocity) — AI 추천은 "예상보다 더 많이 주는" 경험
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    cache_key  = f"teacher_rec_{name}"
    cached_rec = st.session_state.get(cache_key, "")

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#FAF5FF,#F5F3FF);
     border:1px solid #DDD6FE;border-radius:14px;padding:18px 20px;margin-bottom:10px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
    {icon("sparkles", 16, "#7C3AED")}
    <span style="font-weight:900;color:#3B0764;font-size:0.92rem;">AI 맞춤 지도 추천</span>
    <span style="background:#7C3AED;color:white;border-radius:8px;
           padding:1px 8px;font-size:0.68rem;font-weight:700;margin-left:4px;">BETA</span>
  </div>
  <div style="font-size:0.78rem;color:#6B7280;">
    {name} 학생의 학습 데이터를 분석해 맞춤 지도 방향을 제안합니다
  </div>
</div>
""", unsafe_allow_html=True)

    colBtn, colInfo = st.columns([1, 2])
    with colBtn:
        btn_label = "🤖 AI 추천 생성" if not cached_rec else "🔄 다시 생성"
        if api_config and st.button(btn_label,
                                    key=f"gen_rec_{name}",
                                    use_container_width=True, type="primary"):
            from plans import can_use_ai, increment_ai_usage, upgrade_banner
            _aiok, _, _ = can_use_ai()
            if not _aiok:
                upgrade_banner("student", compact=True)
                st.stop()
            increment_ai_usage()
            with st.spinner(f"반반쌤이 {name} 학생을 분석하는 중…"):
                from study_ai import generate_learning_recommendations
                try:
                    rec = generate_learning_recommendations(name, profile, api_config)
                    st.session_state[cache_key] = rec
                    cached_rec = rec
                except Exception as e:
                    st.error(f"추천 생성 실패: {e}")
    with colInfo:
        if not api_config:
            st.caption("API 키를 설정하면 AI 추천을 사용할 수 있어요.")
        elif not cached_rec:
            st.caption("버튼을 클릭하면 이 학생의 맞춤 학습 방향을 분석합니다.")

    if cached_rec:
        st.markdown(f"""
<div style="background:white;border:1px solid #DDD6FE;border-radius:14px;
     padding:20px;margin-top:10px;box-shadow:0 2px 8px rgba(124,58,237,0.06);">
  <div style="display:flex;align-items:center;gap:7px;margin-bottom:12px;">
    {icon("graduation-cap", 15, "#7C3AED")}
    <span style="font-size:0.78rem;font-weight:800;color:#5B21B6;">
      반반쌤 × AI 맞춤 추천 — {name}
    </span>
  </div>
""", unsafe_allow_html=True)
        st.markdown(cached_rec)
        st.markdown("</div>", unsafe_allow_html=True)


def _kpi_icon(col, icon_name: str, value: str, label: str,
              color: str, bg: str = "#F8FAFF", border: str = "#E0E7FF"):
    """아이콘 기반 KPI 카드 — Lucide 아이콘 사용 (모든 KPI는 이 함수 사용)"""
    col.markdown(f"""
<div style="background:{bg};border:1.5px solid {border};border-radius:14px;
     padding:14px 12px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
  <div style="display:flex;justify-content:center;margin-bottom:6px;">
    {icon(icon_name, 20, color)}
  </div>
  <div style="font-size:1.45rem;font-weight:900;color:{color};letter-spacing:-0.5px;">{value}</div>
  <div style="font-size:0.7rem;color:#6B7280;margin-top:3px;font-weight:500;">{label}</div>
</div>
""", unsafe_allow_html=True)


def _render_invite_tab(user):
    """초대 코드 관리 탭 — Premium Edition
    [Dr. 박민호] Endowment Effect: 코드를 "발급"하는 행위가 소유감을 강화
    """
    # 상단 안내
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#FFFBEB,#FEF3C7);
     border:1px solid #FDE68A;border-radius:14px;padding:16px 20px;margin:12px 0 18px;">
  <div style="display:flex;align-items:flex-start;gap:10px;">
    <div style="flex-shrink:0;margin-top:2px;">{icon("key", 18, "#D97706")}</div>
    <div>
      <div style="font-weight:800;color:#92400E;font-size:0.9rem;margin-bottom:3px;">
        학생 초대 코드
      </div>
      <div style="font-size:0.8rem;color:#B45309;line-height:1.6;">
        코드를 발급하고 학생들에게 공유하세요.<br>
        학생이 이 코드로 가입하면 자동으로 선생님 클래스에 연결됩니다.
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # 코드 발급 폼
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:7px;margin-bottom:10px;">
  {icon("plus-circle", 16, "#4338CA")}
  <span style="font-weight:800;color:#1E1B4B;font-size:0.92rem;">새 코드 발급</span>
</div>
""", unsafe_allow_html=True)

    with st.form("new_invite_code_form"):
        code_label = st.text_input(
            "반/그룹 이름",
            placeholder="예: 3학년 1반 · 목요일반 · 심화반",
            help="이 코드를 사용할 그룹 이름 (코드 목록에 표시됩니다)"
        )
        issue_btn = st.form_submit_button(
            "코드 발급하기", use_container_width=True, type="primary"
        )

    if issue_btn:
        try:
            result = _sb().rpc("generate_invite_code", {
                "p_teacher_id": user.id,
                "p_label":      code_label.strip(),
            }).execute()
            new_code = result.data
            if new_code:
                st.markdown(f"""
<div style="background:#F0FDF4;border:1.5px solid #86EFAC;border-radius:14px;
     padding:18px 20px;margin:10px 0;">
  <div style="display:flex;align-items:center;gap:7px;margin-bottom:8px;">
    {icon("check-circle", 16, "#16A34A")}
    <span style="font-weight:800;color:#14532D;font-size:0.9rem;">코드 발급 완료!</span>
  </div>
  <div style="font-size:0.8rem;color:#166534;margin-bottom:10px;">
    아래 코드를 학생들에게 공유하세요
  </div>
  <div style="background:white;border:2px solid #4ADE80;border-radius:10px;
       padding:12px 18px;font-family:monospace;font-size:1.4rem;font-weight:900;
       color:#166534;letter-spacing:3px;text-align:center;">
    {new_code}
  </div>
</div>
""", unsafe_allow_html=True)
            else:
                st.error("코드 생성에 실패했습니다. 다시 시도해주세요.")
        except Exception as e:
            st.error(f"오류: {e}")

    # 발급 코드 목록
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:7px;margin:20px 0 12px;">
  {icon("list", 16, "#4338CA")}
  <span style="font-weight:800;color:#1E1B4B;font-size:0.92rem;">발급한 코드 목록</span>
</div>
""", unsafe_allow_html=True)

    try:
        codes = _sb().table("invite_codes") \
            .select("*").eq("teacher_id", user.id) \
            .order("created_at", desc=True).execute().data or []
    except Exception:
        codes = []

    if not codes:
        st.markdown(f"""
<div style="background:#F8FAFF;border:1.5px dashed #C7D2FE;border-radius:12px;
     padding:24px;text-align:center;color:#6B7280;font-size:0.85rem;">
  {icon("inbox", 20, "#A5B4FC")} 아직 발급한 코드가 없습니다
</div>
""", unsafe_allow_html=True)

    for c in codes:
        uses  = c["current_uses"]
        maxu  = c["max_uses"]
        pct   = int(uses / max(maxu, 1) * 100)
        exp   = (c.get("expires_at", "") or "")[:10] or "무기한"
        label = c.get("label", "—") or "—"
        created = (c.get("created_at", "") or "")[:10]

        if pct == 0:      bar_c = "#6366F1"
        elif pct < 70:    bar_c = "#16A34A"
        elif pct < 100:   bar_c = "#D97706"
        else:             bar_c = "#DC2626"

        remaining = maxu - uses
        remain_txt = f"잔여 {remaining}명" if remaining > 0 else "사용 완료"
        remain_c   = "#374151" if remaining > 0 else "#DC2626"

        st.markdown(f"""
<div style="background:white;border:1px solid #E5E7EB;border-radius:14px;
     padding:16px 18px;margin-bottom:10px;
     box-shadow:0 1px 4px rgba(0,0,0,0.04);">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
    <div>
      <div style="font-family:monospace;font-size:1.1rem;font-weight:900;
           color:#4338CA;letter-spacing:2px;">{c['code']}</div>
      <div style="font-size:0.75rem;color:#6B7280;margin-top:3px;
           display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="display:flex;align-items:center;gap:3px;">
          {icon("tag", 11, "#9CA3AF")} {label}
        </span>
        <span style="display:flex;align-items:center;gap:3px;">
          {icon("calendar", 11, "#9CA3AF")} 발급 {created}
        </span>
        <span style="display:flex;align-items:center;gap:3px;">
          {icon("clock", 11, "#9CA3AF")} 만료 {exp}
        </span>
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0;">
      <div style="font-size:1rem;font-weight:900;color:{bar_c};">{uses}/{maxu}명</div>
      <div style="font-size:0.72rem;color:{remain_c};font-weight:600;margin-top:2px;">
        {remain_txt}
      </div>
    </div>
  </div>
  <div style="background:#F3F4F6;border-radius:6px;height:6px;overflow:hidden;">
    <div style="background:{bar_c};height:100%;width:{pct}%;
         border-radius:6px;transition:width 0.6s ease;"></div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 메인 진입점
# ─────────────────────────────────────────────────────────────────────────────

def page_dashboard(dash_page: str, student_id, student_name: str,
                   api_cfg: dict | None, notes: list):
    """대시보드 페이지 라우팅"""
    if dash_page == "학생 관리":
        _render_teacher_dashboard(api_cfg)
    elif dash_page == "클래스 랭킹":
        from study_ranking import page_ranking
        page_ranking(student_id, student_name)
    elif dash_page == "학부모 리포트":
        _render_parent_report(student_id, student_name, api_cfg)
    else:
        _render_my_stats(student_id, student_name)


# ─────────────────────────────────────────────────────────────────────────────
# 학부모 주간 리포트
# ─────────────────────────────────────────────────────────────────────────────

def _render_parent_report(student_id, student_name: str, api_cfg):
    import streamlit.components.v1 as components
    from study_db import get_rich_student_profile, get_study_logs, list_students, get_or_create_student

    st.markdown("""
<div style="background:linear-gradient(135deg,#0F766E,#14B8A6);
     border-radius:14px;padding:18px 20px;margin-bottom:20px;color:white;">
  <div style="font-size:1.5rem;font-weight:900;">📨 학부모 주간 리포트</div>
  <div style="font-size:0.82rem;opacity:0.9;margin-top:4px;">
    AI가 자동 작성하는 학습 주간 보고서
  </div>
</div>
""", unsafe_allow_html=True)

    # 학생 선택
    if not student_id:
        students = list_students()
        if not students:
            st.warning("학생 정보가 없습니다.")
            return
        sel = st.selectbox("학생 선택", [s["name"] for s in students], key="parent_rpt_sel")
        if sel:
            student_name = sel
            student_id   = get_or_create_student(sel)
        else:
            return

    if not api_cfg:
        st.warning("AI 리포트 생성에는 API 키가 필요합니다.")
        return

    st.markdown(
        f'<div style="background:#F0FDFA;border-radius:10px;padding:10px 14px;'
        f'margin-bottom:16px;font-weight:700;color:#0F766E;">'
        f'👤 {student_name} 학생 주간 리포트</div>',
        unsafe_allow_html=True,
    )

    # 캐시 키
    cache_key = f"parent_report_{student_id}"
    cached    = st.session_state.get(cache_key, "")

    col_gen, col_dl = st.columns([3, 1])
    with col_gen:
        gen_btn = st.button(
            "📊 주간 리포트 생성" if not cached else "🔄 새로 생성",
            type="primary", use_container_width=True, key="parent_rpt_gen"
        )

    if gen_btn:
        with st.spinner("📊 이번 주 학습 리포트 작성 중... (10~25초)"):
            try:
                profile   = get_rich_student_profile(student_id)
                week_logs = get_study_logs(student_id, days=7)
                from study_ai import generate_parent_weekly_report
                html = generate_parent_weekly_report(student_name, profile, week_logs, api_cfg)
                st.session_state[cache_key] = html
                st.rerun()
            except Exception as e:
                st.error(f"리포트 생성 실패: {e}")
                return

    if cached:
        components.html(cached, height=800, scrolling=True)
        with col_dl:
            st.download_button(
                "📥 저장",
                data=cached.encode("utf-8"),
                file_name=f"주간리포트_{student_name}_{date.today()}.html",
                mime="text/html",
                use_container_width=True,
                key="parent_rpt_dl",
            )
    else:
        st.markdown("""
<div style="text-align:center;padding:40px;background:#F0FDFA;border-radius:12px;
     border:2px dashed #99F6E4;">
  <div style="font-size:2.5rem;">📨</div>
  <div style="font-weight:700;color:#134E4A;margin-top:8px;">리포트가 아직 없습니다</div>
  <div style="font-size:0.82rem;color:#0F766E;margin-top:4px;">
    위 버튼으로 이번 주 학습 리포트를 자동 생성하세요
  </div>
</div>
""", unsafe_allow_html=True)
