# study_ranking.py — 클래스 랭킹 + 뱃지 공유
# 학생 학습 데이터 기반 랭킹, 주간/전체 필터, 공유 뱃지 HTML 생성

import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta
from collections import defaultdict

from study_db import get_supabase, list_students, get_or_create_student


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 집계
# ─────────────────────────────────────────────────────────────────────────────

RANK_CRITERIA = {
    "종합 점수":   "total_score",
    "학습 횟수":   "sessions",
    "연속 학습일": "streak",
    "정확도":      "accuracy",
}

MEDAL = {1: "🥇", 2: "🥈", 3: "🥉"}
TIER_COLORS = {
    "다이아": "#60A5FA",
    "플래티넘": "#A78BFA",
    "골드": "#FBBF24",
    "실버": "#94A3B8",
    "브론즈": "#D97706",
}


def _get_tier(score: int) -> str:
    if score >= 500: return "다이아"
    if score >= 300: return "플래티넘"
    if score >= 150: return "골드"
    if score >= 50:  return "실버"
    return "브론즈"


def _load_ranking_data(days: int | None = None) -> list[dict]:
    """전체 학생 랭킹 데이터 로드."""
    sb       = get_supabase()
    students = list_students()
    if not students:
        return []

    # 날짜 필터
    cutoff = None
    if days:
        cutoff = str(date.today() - timedelta(days=days))

    # 학습 로그 가져오기
    q = sb.table("study_logs").select("student_id,activity,score,total,created_at") \
          .order("created_at", desc=True)
    if cutoff:
        q = q.gte("created_at", cutoff)
    logs_data = q.execute().data or []

    # 학생별 집계
    stats: dict[int, dict] = {}
    for s in students:
        sid = s["id"]
        stats[sid] = {
            "id":       sid,
            "name":     s["name"],
            "sessions": 0,
            "scores":   [],
            "dates":    set(),
            "streak":   0,
        }

    for row in logs_data:
        sid = row.get("student_id")
        if sid not in stats:
            continue
        st_data = stats[sid]
        st_data["sessions"] += 1
        dt = row.get("created_at", "")[:10]
        st_data["dates"].add(dt)
        sc  = row.get("score")
        tot = row.get("total")
        if sc is not None and tot:
            st_data["scores"].append(sc / tot * 100)

    # 연속 학습일 계산 (전체 기간)
    all_logs_q = sb.table("study_logs").select("student_id,created_at") \
                   .order("created_at", desc=True).execute()
    all_logs = all_logs_q.data or []
    sid_dates: dict[int, set] = defaultdict(set)
    for row in all_logs:
        sid = row.get("student_id")
        if sid is not None:
            sid_dates[sid].add(row.get("created_at", "")[:10])

    today = date.today()
    for sid, dates_set in sid_dates.items():
        if sid not in stats:
            continue
        streak = 0
        cur = today
        while str(cur) in dates_set:
            streak += 1
            cur -= timedelta(days=1)
        stats[sid]["streak"] = streak

    # 종합 점수 계산
    result = []
    for sid, data in stats.items():
        sessions  = data["sessions"]
        avg_acc   = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0.0
        streak    = data["streak"]
        # 종합 점수: 세션 × 5 + 정확도 × 2 + 연속학습 × 10
        total_sc  = sessions * 5 + int(avg_acc * 2) + streak * 10
        tier      = _get_tier(total_sc)
        result.append({
            "id":          sid,
            "name":        data["name"],
            "sessions":    sessions,
            "accuracy":    avg_acc,
            "streak":      streak,
            "total_score": total_sc,
            "tier":        tier,
        })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 뱃지 HTML 생성
# ─────────────────────────────────────────────────────────────────────────────

def _make_badge_html(rank: int, name: str, tier: str, score: int,
                     sessions: int, accuracy: float, streak: int,
                     period_label: str = "이번 주") -> str:
    medal     = MEDAL.get(rank, f"#{rank}")
    tier_clr  = TIER_COLORS.get(tier, "#94A3B8")
    header_bg = {
        "다이아":   "linear-gradient(135deg,#1D4ED8,#60A5FA)",
        "플래티넘": "linear-gradient(135deg,#6D28D9,#A78BFA)",
        "골드":     "linear-gradient(135deg,#B45309,#FBBF24)",
        "실버":     "linear-gradient(135deg,#475569,#94A3B8)",
        "브론즈":   "linear-gradient(135deg,#92400E,#D97706)",
    }.get(tier, "linear-gradient(135deg,#4F46E5,#7C3AED)")

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{{margin:0;background:#F8FAFC;font-family:system-ui,-apple-system,sans-serif;}}
.badge{{max-width:360px;margin:20px auto;background:white;border-radius:16px;
  box-shadow:0 4px 24px rgba(0,0,0,0.12);overflow:hidden;}}
.header{{background:{header_bg};padding:20px;text-align:center;color:white;}}
.medal{{font-size:2.5rem;}}
.rank{{font-size:1rem;opacity:0.85;font-weight:600;}}
.name{{font-size:1.6rem;font-weight:900;margin-top:4px;}}
.tier-badge{{display:inline-block;background:rgba(255,255,255,0.25);
  border-radius:20px;padding:3px 12px;font-size:0.78rem;font-weight:700;margin-top:6px;}}
.body{{padding:16px 20px;}}
.stats{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px;}}
.stat{{text-align:center;background:#F8FAFC;border-radius:10px;padding:10px 4px;}}
.stat-val{{font-size:1.3rem;font-weight:900;color:#1E293B;}}
.stat-lbl{{font-size:0.65rem;color:#94A3B8;margin-top:2px;}}
.score-bar{{background:#E5E7EB;border-radius:99px;height:8px;margin:8px 0;}}
.score-fill{{background:{header_bg};height:100%;border-radius:99px;width:{min(score/800*100,100):.0f}%;}}
.total-score{{display:flex;justify-content:space-between;font-size:0.8rem;margin-top:4px;}}
.footer{{text-align:center;padding:10px;background:#F1F5F9;
  font-size:0.65rem;color:#94A3B8;}}
</style></head><body>
<div class="badge">
  <div class="header">
    <div class="medal">{medal}</div>
    <div class="rank">{period_label} {rank}위</div>
    <div class="name">{name}</div>
    <div class="tier-badge">✨ {tier} 티어</div>
  </div>
  <div class="body">
    <div class="stats">
      <div class="stat">
        <div class="stat-val">{sessions}</div>
        <div class="stat-lbl">📚 학습 횟수</div>
      </div>
      <div class="stat">
        <div class="stat-val">{accuracy:.0f}%</div>
        <div class="stat-lbl">🎯 정확도</div>
      </div>
      <div class="stat">
        <div class="stat-val">{streak}일</div>
        <div class="stat-lbl">🔥 연속학습</div>
      </div>
    </div>
    <div class="total-score">
      <span style="font-weight:700;color:#374151;">종합 점수</span>
      <span style="font-weight:900;color:{tier_clr};">{score}점</span>
    </div>
    <div class="score-bar"><div class="score-fill"></div></div>
  </div>
  <div class="footer">반반 BanBan 🎓 | 영어학습 파트너 | {date.today()}</div>
</div>
</body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_ranking(student_id, student_name: str):
    """클래스 랭킹 페이지"""

    # ── 헤더 ───────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,#B45309,#FBBF24,#4F46E5);
     border-radius:14px;padding:18px 20px;margin-bottom:20px;color:white;">
  <div style="font-size:1.5rem;font-weight:900;">🏆 클래스 랭킹</div>
  <div style="font-size:0.82rem;opacity:0.9;margin-top:4px;">
    학습 열정 TOP 순위 · 달성 뱃지 공유
  </div>
</div>
""", unsafe_allow_html=True)

    # ── 기간 필터 ──────────────────────────────────────────────────────────
    col_period, col_sort, col_buf = st.columns([2, 2, 2])
    with col_period:
        period = st.selectbox("기간", ["이번 주 (7일)", "이번 달 (30일)", "전체"],
                               key="ranking_period")
    with col_sort:
        sort_by = st.selectbox("기준", list(RANK_CRITERIA.keys()),
                                key="ranking_sort")

    days_map = {"이번 주 (7일)": 7, "이번 달 (30일)": 30, "전체": None}
    days = days_map[period]

    with st.spinner("📊 랭킹 집계 중..."):
        ranking_data = _load_ranking_data(days=days)

    if not ranking_data:
        st.info("학습 데이터가 없습니다. 학생들이 학습을 시작하면 랭킹이 나타납니다.")
        return

    # 정렬
    sort_key = RANK_CRITERIA[sort_by]
    ranking_data.sort(key=lambda x: -x.get(sort_key, 0))

    # ── 랭킹 테이블 ────────────────────────────────────────────────────────
    tab_table, tab_badge = st.tabs(["🏆 랭킹 보드", "🎖 내 뱃지"])

    with tab_table:
        _render_ranking_table(ranking_data, student_name, sort_key)

    with tab_badge:
        _render_my_badge(ranking_data, student_name, period)


def _render_ranking_table(data: list[dict], current_student: str, sort_key: str):

    html_rows = []
    for i, d in enumerate(data):
        rank    = i + 1
        is_me   = (d["name"] == current_student)
        medal   = MEDAL.get(rank, f"<b>#{rank}</b>")
        tier    = d["tier"]
        tc      = TIER_COLORS.get(tier, "#94A3B8")
        bg      = "#FFF7ED" if is_me else ("#FFFBEB" if rank <= 3 else "#FFFFFF")
        border  = "2px solid #FBBF24" if is_me else "1px solid #F1F5F9"
        me_tag  = ' <span style="background:#4F46E5;color:white;border-radius:10px;padding:1px 6px;font-size:0.65rem;">나</span>' if is_me else ""

        sessions  = d.get("sessions", 0)
        accuracy  = d.get("accuracy", 0.0)
        streak    = d.get("streak", 0)
        total_sc  = d.get("total_score", 0)

        sort_highlight = {
            "total_score": f'<b style="color:{tc};">{total_sc}점</b>',
            "sessions":    f'<b style="color:#4F46E5;">{sessions}회</b>',
            "streak":      f'<b style="color:#D97706;">{streak}일</b>',
            "accuracy":    f'<b style="color:#059669;">{accuracy:.0f}%</b>',
        }
        highlight = sort_highlight.get(sort_key, f"{total_sc}점")

        html_rows.append(f"""
<div style="background:{bg};border:{border};border-radius:10px;
     padding:10px 14px;margin-bottom:6px;
     display:flex;align-items:center;gap:12px;">
  <div style="min-width:32px;text-align:center;font-size:1.2rem;">{medal}</div>
  <div style="flex:1;">
    <div style="font-weight:700;font-size:0.92rem;color:#1E293B;">{d["name"]}{me_tag}</div>
    <div style="font-size:0.72rem;color:{tc};font-weight:700;">{tier} 티어</div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:0.9rem;">{highlight}</div>
    <div style="font-size:0.68rem;color:#94A3B8;">{sessions}회 | {accuracy:.0f}% | 🔥{streak}일</div>
  </div>
</div>""")

    st.markdown("".join(html_rows), unsafe_allow_html=True)


def _render_my_badge(data: list[dict], current_student: str, period: str):

    if not current_student:
        st.info("학생 이름을 입력하면 내 뱃지를 만들 수 있습니다.")
        return

    # 내 순위 찾기
    my_data = next((d for d in data if d["name"] == current_student), None)
    if not my_data:
        st.info(f"'{current_student}' 학생의 학습 기록이 없습니다.")
        return

    rank = next((i+1 for i, d in enumerate(data) if d["name"] == current_student), 0)
    period_label = period.split(" ")[0]

    badge_html = _make_badge_html(
        rank=rank,
        name=current_student,
        tier=my_data["tier"],
        score=my_data["total_score"],
        sessions=my_data["sessions"],
        accuracy=my_data["accuracy"],
        streak=my_data["streak"],
        period_label=period_label,
    )

    components.html(badge_html, height=400, scrolling=False)

    col_dl, col_share = st.columns(2)
    with col_dl:
        st.download_button(
            "📥 뱃지 저장 (HTML)",
            data=badge_html.encode("utf-8"),
            file_name=f"반반뱃지_{current_student}_{date.today()}.html",
            mime="text/html",
            use_container_width=True,
        )
    with col_share:
        kakao_text = (f"반반 BanBan 학습 뱃지 🎓\n"
                      f"👤 {current_student}\n"
                      f"🏆 {period_label} {rank}위 | {my_data['tier']} 티어\n"
                      f"📚 {my_data['sessions']}회 학습 | 🎯 {my_data['accuracy']:.0f}% | 🔥 {my_data['streak']}일 연속\n"
                      f"💯 종합 {my_data['total_score']}점\n\n"
                      f"반반 BanBan에서 영어 실력 키우기 →")
        st.text_area("📤 공유 텍스트 복사", value=kakao_text, height=130,
                     key="badge_share_text")
