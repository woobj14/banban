# study_review.py — 망각 곡선 복습 스케줄러
# 에빙하우스 SM-2 알고리즘 기반 스페이스드 리피티션 시스템
# 단어 / 문법 / 문장 통합 복습 세션 + 홈 위젯

import streamlit as st
import streamlit.components.v1 as components
from icons import icon

from study_db import (
    get_due_reviews, count_due_reviews, update_review_result,
    get_review_stats, delete_review_item, schedule_review,
)

# ─────────────────────────────────────────────────────────────────────────────
# TTS 헬퍼 — Web Speech API (브라우저 내장, 별도 API 키 없음)
# ─────────────────────────────────────────────────────────────────────────────

def _tts_button(text: str, btn_key: str = "", label: str = "🔊 발음 듣기",
                compact: bool = False):
    """Web Speech API TTS 버튼 컴포넌트.
    compact=True → 작은 인라인 버튼 (카드 내 삽입용)
    """
    safe = text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
    h = 44 if compact else 52
    pad = "6px 14px" if compact else "9px 20px"
    fsize = "0.78rem" if compact else "0.88rem"
    components.html(f"""
<script>
function tts_{btn_key or "x"}() {{
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  var u = new SpeechSynthesisUtterance('{safe}');
  u.lang = 'en-US'; u.rate = 0.85; u.pitch = 1.0;
  var vv = window.speechSynthesis.getVoices();
  var v = vv.find(function(x){{
    return (x.name.indexOf('Google')>-1||x.name.indexOf('Samantha')>-1||x.name.indexOf('Alex')>-1)
           && x.lang.indexOf('en')===0;
  }}) || vv.find(function(x){{return x.lang==='en-US';}})
     || vv.find(function(x){{return x.lang.indexOf('en')===0;}});
  if (v) u.voice = v;
  var b = document.getElementById('ttsb_{btn_key or "x"}');
  if (b) b.textContent = '🔊 재생 중…';
  u.onend = function(){{ if(b) b.textContent = '{label}'; }};
  window.speechSynthesis.speak(u);
}}
if (window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined)
  window.speechSynthesis.onvoiceschanged = function(){{}};
</script>
<button id="ttsb_{btn_key or "x"}"
  onclick="tts_{btn_key or 'x'}()"
  style="background:linear-gradient(135deg,#4F46E5,#818CF8);color:white;
         border:none;border-radius:20px;padding:{pad};
         font-size:{fsize};font-weight:700;cursor:pointer;width:100%;
         box-shadow:0 2px 8px rgba(79,70,229,0.25);transition:all 0.15s;">
  {label}
</button>
""", height=h)


# ─────────────────────────────────────────────────────────────────────────────
# 복습 간격 시각화 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

_INTERVAL_LABEL = {
    0:  ("오늘 추가됨",  "#6B7280"),
    1:  ("1일 후 예정",  "#6366F1"),
    3:  ("3일 후 예정",  "#0891B2"),
    7:  ("7일 후 예정",  "#059669"),
    21: ("21일 후 예정", "#D97706"),
    60: ("60일 후 예정", "#7C3AED"),
}

def _interval_badge(days: int) -> str:
    label, color = _INTERVAL_LABEL.get(days, (f"{days}일 후", "#374151"))
    return (f'<span style="background:{color}20;color:{color};'
            f'border-radius:20px;padding:2px 9px;font-size:0.7rem;font-weight:700;">'
            f'{label}</span>')

def _rep_stars(reps: int) -> str:
    """반복 숙련도를 점(dot) 게이지로 표시 (채움/빈칸)."""
    filled = min(reps, 5)
    dots = ""
    for i in range(5):
        col = "#F59E0B" if i < filled else "#E5E7EB"
        dots += (f'<span style="display:inline-block;width:7px;height:7px;'
                 f'border-radius:50%;background:{col};margin:0 1px;"></span>')
    return dots

def _type_icon(item_type: str) -> str:
    name = {"word": "file-text", "grammar": "check-square",
            "sentence": "book-open"}.get(item_type, "bookmark")
    return f'<span style="display:inline-flex;vertical-align:middle;">{icon(name, 14, "#7C3AED")}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# 홈 위젯 — 상단에 삽입해서 오늘 복습 알림
# ─────────────────────────────────────────────────────────────────────────────

def render_review_widget(student_id: int):
    """홈 화면 '오늘 할 일' 대시보드 카드.
    복습 현황 + 추천 액션 + 학습 통계를 한눈에 보여줌.
    """
    if not student_id:
        return

    # ── 데이터 수집 ────────────────────────────────────────────
    try:
        due = count_due_reviews(student_id)
    except Exception:
        due = 0

    try:
        from study_db import get_review_stats, get_study_logs
        stats   = get_review_stats(student_id)
        mastered = stats.get("mastered", 0)
        total_rv = stats.get("total", 0)
    except Exception:
        mastered, total_rv = 0, 0

    try:
        from study_db import get_wrong_notes
        wn = get_wrong_notes(student_id)
        word_wrong = len(wn)
    except Exception:
        word_wrong = 0

    try:
        from study_db import get_study_logs
        from datetime import date, timedelta
        today_str  = str(date.today())
        cutoff7    = str(date.today() - timedelta(days=6))
        week_logs  = get_study_logs(student_id, days=7)
        today_logs = [r for r in week_logs if r.get("created_at","")[:10] == today_str]
        week_days  = len({r["created_at"][:10] for r in week_logs})
        today_cnt  = len(today_logs)
    except Exception:
        week_days = today_cnt = 0

    # ── 인사말 (시간대별) ───────────────────────────────────────
    from datetime import datetime
    h = datetime.now().hour
    if h < 6:    greeting, g_icon = "늦은 밤에도 공부하는군요", "moon"
    elif h < 12: greeting, g_icon = "좋은 아침이에요", "sunrise"
    elif h < 18: greeting, g_icon = "오늘도 열심히 해봐요", "book-open"
    else:        greeting, g_icon = "오늘 하루 수고했어요", "sunset"

    name = st.session_state.get("sb_student_name","") or st.session_state.get("study_student","")
    name_txt = f"{name}님, " if name else ""

    # ── 오늘 상태 판단 ──────────────────────────────────────────
    if today_cnt >= 3:
        status_msg, status_c, status_icon = "오늘 학습 완료! 훌륭해요", "#15803D", "check-circle"
    elif today_cnt >= 1:
        status_msg, status_c, status_icon = f"오늘 {today_cnt}회 학습했어요. 조금 더 해볼까요?", "#B45309", "info"
    else:
        status_msg, status_c, status_icon = "오늘 아직 학습을 시작하지 않았어요.", "#DC2626", "alert-circle"

    # 색상 변수 (네모 박스 없이 숫자에만 색상 신호)
    due_color  = "#EF4444" if due >= 5 else "#F59E0B" if due >= 2 else "#6366F1"
    wrong_color = "#EF4444" if word_wrong > 10 else "#F59E0B" if word_wrong > 0 else "#10B981"

    g_icon_svg   = icon(g_icon, 13, "#6366F1")
    status_svg   = icon(status_icon, 14, status_c)
    divider      = ('<div style="width:1px;align-self:stretch;'
                    'background:linear-gradient(180deg,transparent,rgba(99,102,241,0.15),transparent);"></div>')

    def _stat(num, label, color):
        return (
            f'<div style="flex:1;text-align:center;padding:4px 0;">'
            f'<div style="font-size:1.7rem;font-weight:800;color:{color};'
            f'line-height:1;letter-spacing:-0.5px;">{num}</div>'
            f'<div style="font-size:0.7rem;color:#94A3B8;margin-top:6px;'
            f'font-weight:500;">{label}</div>'
            f'</div>'
        )

    # ── 메인 카드 — 글래스 표면, 박스 없이 헤어라인 구분 ──────────
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.72);'
        f'backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);'
        f'border:1px solid rgba(255,255,255,0.7);border-radius:22px;'
        f'padding:22px 26px;margin-bottom:14px;'
        f'box-shadow:0 8px 32px rgba(31,38,135,0.08),0 1px 2px rgba(0,0,0,0.04);">'

        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">'
        f'<div>'
        f'<div style="font-size:0.78rem;color:#94A3B8;font-weight:500;'
        f'display:flex;align-items:center;gap:5px;margin-bottom:3px;">'
        f'{g_icon_svg} {greeting}</div>'
        f'<div style="font-size:1.3rem;font-weight:800;color:#1E293B;'
        f'letter-spacing:-0.5px;">{name_txt}오늘 할 일</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="font-size:1.6rem;font-weight:800;color:#6366F1;line-height:1;">{week_days}</div>'
        f'<div style="font-size:0.68rem;color:#94A3B8;margin-top:3px;">이번주 활동일</div>'
        f'</div>'
        f'</div>'

        f'<div style="display:flex;align-items:center;'
        f'background:rgba(248,250,252,0.6);border-radius:16px;padding:14px 8px;">'
        + _stat(due, "복습 대기", due_color)
        + divider
        + _stat(mastered, "마스터 완료", "#10B981")
        + divider
        + _stat(word_wrong, "오답 단어", wrong_color)
        + '</div>'
        + '</div>',
        unsafe_allow_html=True,
    )

    # ── 오늘 상태 — 박스 없이 텍스트 + 아이콘만 ──────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:7px;'
        f'padding:2px 6px 14px;font-size:0.85rem;">'
        f'{status_svg}'
        f'<span style="color:{status_c};font-weight:600;">{status_msg}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 추천 액션 버튼들 ── 오늘 할 일과 직결된 것만 (단어학습은 사이드바 메뉴로 대체) ──
    actions = []
    if due > 0:
        actions.append(("primary", f"복습하기 ({due}개)", "복습하기", "review_home_btn"))
    if word_wrong > 0:
        actions.append(("secondary", f"오답 단어 ({word_wrong}개)", "오답노트", "wrongnote_home_btn"))

    if actions:
        cols = st.columns(len(actions))
        for i, (btn_type, label, target_page, btn_key) in enumerate(actions):
            with cols[i]:
                if st.button(label, key=btn_key, use_container_width=True,
                             type=btn_type if btn_type == "primary" else "secondary"):
                    st.session_state["study_page"] = target_page
                    st.session_state["page"]       = "__study__"
                    st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 복습 세션 상태 초기화
# ─────────────────────────────────────────────────────────────────────────────

def _init_session(items: list[dict]):
    st.session_state["_rv"] = {
        "items":    items,
        "idx":      0,
        "score":    0,
        "wrong":    [],
        "answered": False,
        "last_ok":  None,
        "result":   None,   # update_review_result 결과
        "done":     False,
        "flipped":  False,  # 플래시카드 앞/뒷면
    }


# ─────────────────────────────────────────────────────────────────────────────
# 복습 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_review(student_id: int | None, api_cfg: dict | None):
    """복습 메인 페이지"""

    # 헤더
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#7C3AED,#6D28D9);color:white;
     border-radius:14px;padding:18px 20px;margin-bottom:20px;">
  <div style="font-size:0.85rem;opacity:0.85;display:flex;align-items:center;gap:4px;">
    {icon("arrow-repeat", 14, "rgba(255,255,255,0.85)")} 망각 곡선 복습
  </div>
  <div style="font-size:1.4rem;font-weight:800;margin-top:4px;">오늘의 복습</div>
  <div style="font-size:0.82rem;opacity:0.85;margin-top:4px;">
    에빙하우스 망각 곡선 기반 — 딱 맞는 타이밍에 복습해야 기억이 오래 남아요
  </div>
</div>
""", unsafe_allow_html=True)

    if not student_id:
        st.info("로그인하면 복습 스케줄이 저장돼요.")
        return

    # 세션 진행 중이면 바로 복습 화면
    if "_rv" in st.session_state and not st.session_state["_rv"].get("done"):
        _render_session(api_cfg)
        return

    # 완료 후 결과 표시
    if "_rv" in st.session_state and st.session_state["_rv"].get("done"):
        _render_done()
        return

    # ── 대기 항목 조회 ─────────────────────────────────────────────
    try:
        due_items = get_due_reviews(student_id)
        stats     = get_review_stats(student_id)
    except Exception as e:
        err = str(e)
        if "does not exist" in err or "42P01" in err:
            st.error(
                "❌ **테이블 미설치** — Supabase SQL Editor에서 "
                "`supabase_migration_v5.sql`을 실행해주세요."
            )
        else:
            st.error(f"조회 오류: {err}")
        return

    # ── 통계 카드 ──────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("오늘 복습", f"{stats['due']}개", delta=None)
    c2.metric("학습 중",   f"{stats['in_progress']}개")
    c3.metric("마스터",    f"{stats['mastered']}개")
    c4.metric("총 등록",   f"{stats['total']}개")

    st.divider()

    if not due_items:
        # ── 미래 예정 항목 확인 ────────────────────────────────────
        try:
            upcoming = _get_upcoming(student_id)
        except Exception:
            upcoming = []

        # ① 학습 이력 자체가 없는 경우 → 사용 방법 안내
        if stats.get("total", 0) == 0:
            st.markdown(f"""
<div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);
     border:1px solid #C7D2FE;border-radius:20px;padding:32px 28px;margin-bottom:20px;">
  <div style="font-size:1.2rem;font-weight:900;color:#4338CA;margin-bottom:18px;
       display:flex;align-items:center;gap:8px;">
    {icon("book-open",20,"#4338CA")} 복습하기 사용 방법
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px;">
    <div style="background:white;border-radius:14px;padding:18px 16px;
         border:1px solid #E0E7FF;box-shadow:0 2px 8px rgba(79,70,229,0.06);">
      <div style="font-size:1.4rem;margin-bottom:8px;">① 단어 학습</div>
      <div style="font-size:0.85rem;color:#374151;line-height:1.7;">
        왼쪽 메뉴 <b>단어학습</b>에서<br>
        교과서를 선택하고 단어를 학습해요.<br>
        <span style="color:#6366F1;font-weight:700;">알아요 / 모르겠어요</span>를 누르면<br>
        자동으로 복습 스케줄이 잡혀요.
      </div>
    </div>
    <div style="background:white;border-radius:14px;padding:18px 16px;
         border:1px solid #E0E7FF;box-shadow:0 2px 8px rgba(79,70,229,0.06);">
      <div style="font-size:1.4rem;margin-bottom:8px;">② 복습 알림</div>
      <div style="font-size:0.85rem;color:#374151;line-height:1.7;">
        학습 후 1일, 3일, 7일, 14일…<br>
        <b>최적의 타이밍</b>에 이 화면에<br>
        복습할 단어가 자동으로 나타나요.<br>
        <span style="color:#6366F1;font-weight:700;">까먹기 직전에 다시 보는 게 핵심!</span>
      </div>
    </div>
    <div style="background:white;border-radius:14px;padding:18px 16px;
         border:1px solid #E0E7FF;box-shadow:0 2px 8px rgba(79,70,229,0.06);">
      <div style="font-size:1.4rem;margin-bottom:8px;">③ 복습 방법</div>
      <div style="font-size:0.85rem;color:#374151;line-height:1.7;">
        단어 카드가 앞면(영어)으로 보여요.<br>
        뜻을 떠올린 후 <b>카드를 뒤집어</b><br>
        확인하고 <span style="color:#16A34A;font-weight:700;">맞았어요</span> /<span style="color:#DC2626;font-weight:700;"> 틀렸어요</span><br>
        를 선택하면 다음 복습일이 조정돼요.
      </div>
    </div>
    <div style="background:white;border-radius:14px;padding:18px 16px;
         border:1px solid #E0E7FF;box-shadow:0 2px 8px rgba(79,70,229,0.06);">
      <div style="font-size:1.4rem;margin-bottom:8px;">④ 마스터</div>
      <div style="font-size:0.85rem;color:#374151;line-height:1.7;">
        같은 단어를 <b>5번 연속 맞추면</b><br>
        🏆 마스터 등급이 돼요.<br>
        마스터된 단어는 시험에서<br>
        <span style="color:#6366F1;font-weight:700;">거의 틀리지 않아요!</span>
      </div>
    </div>
  </div>

  <div style="background:#4F46E5;border-radius:12px;padding:14px 18px;
       color:white;font-size:0.88rem;line-height:1.7;">
    {icon("zap",14,"white")}
    <b>지금 바로 시작하려면:</b> 왼쪽 메뉴 → <b>단어학습</b> → 교과서 선택 → 학습 시작!<br>
    단어를 학습하면 이 화면에 복습 항목이 자동으로 채워집니다.
  </div>
</div>
""", unsafe_allow_html=True)

        # ② 이미 학습했는데 오늘 복습 없음 → 완료 메시지
        else:
            st.markdown(f"""
<div style="text-align:center;padding:40px 20px;background:#F5F3FF;
     border-radius:16px;border:2px dashed #DDD6FE;margin-bottom:20px;">
  <div style="display:inline-flex;align-items:center;justify-content:center;
       width:56px;height:56px;border-radius:50%;background:#EDE9FE;margin-bottom:6px;">
    {icon("party-popper",28,"#7C3AED")}
  </div>
  <div style="font-size:1.15rem;font-weight:800;color:#6D28D9;margin-top:12px;">
    오늘 복습 완료!
  </div>
  <div style="color:#9CA3AF;font-size:0.88rem;margin-top:8px;line-height:1.8;">
    지금 당장 복습할 항목이 없어요.<br>
    마스터 <b style="color:#6D28D9;">{stats.get("mastered",0)}개</b> 달성 중 · 총 등록 <b style="color:#6D28D9;">{stats.get("total",0)}개</b><br>
    꾸준히 학습하면 모든 단어가 장기기억에 저장돼요
  </div>
</div>
""", unsafe_allow_html=True)
            if upcoming:
                st.markdown(
                    f'<div style="font-size:0.88rem;font-weight:700;color:#374151;margin-bottom:8px;">'
                    f'{icon("clock",14,"#6366F1")} 다가오는 복습 예정 — {len(upcoming)}개</div>',
                    unsafe_allow_html=True,
                )
                for u in upcoming[:5]:
                    d = u.get("item_data", {})
                    label = d.get("word_en") or d.get("point_name") or u.get("item_key", "")
                    st.markdown(
                        f'<div style="background:#F8FAFC;border:1px solid #E2E8F0;'
                        f'border-radius:8px;padding:8px 12px;margin:3px 0;font-size:0.85rem;">'
                        f'{_type_icon(u["item_type"])} {label} '
                        f'&nbsp;{_interval_badge(u["interval_days"])}'
                        f'&nbsp;<span style="color:#94A3B8;">'
                        f'{u["next_review"]} 복습 예정</span></div>',
                        unsafe_allow_html=True,
                    )
        return

    # ── 복습 시작 버튼 ─────────────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;font-size:1.1rem;'
        f'font-weight:800;color:#1E293B;margin:8px 0 10px;">'
        f'{icon("clock",18,"#7C3AED")} 오늘 복습해야 할 항목 — {len(due_items)}개</div>',
        unsafe_allow_html=True,
    )

    # 미리보기 목록
    for item in due_items[:8]:
        d      = item.get("item_data", {})
        label  = d.get("word_en") or d.get("point_name") or item.get("item_key", "")
        sub    = d.get("word_kr") or d.get("category") or ""
        reps   = item.get("repetitions", 0)
        days_ago = _days_since(item.get("last_reviewed"))

        st.markdown(f"""
<div style="background:white;border:1px solid #E2E8F0;border-radius:10px;
     padding:10px 14px;margin:4px 0;
     display:flex;align-items:center;justify-content:space-between;">
  <div>
    <span style="font-weight:700;font-size:0.9rem;">{_type_icon(item["item_type"])} {label}</span>
    {f'<span style="color:#9CA3AF;font-size:0.78rem;margin-left:6px;">{sub}</span>' if sub else ''}
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:0.75rem;color:#9CA3AF;">
      {f"{days_ago}일 전 학습" if days_ago else "새 항목"}
    </span>
    <span style="font-size:0.78rem;">{_rep_stars(reps)}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    if len(due_items) > 8:
        st.caption(f"... 외 {len(due_items)-8}개 더")

    st.markdown("")

    # ── 일일 상한: 한 번에 너무 많으면 부담 → 분량 선택 ──────────
    total_due = len(due_items)
    if total_due > 20:
        st.markdown(
            f'<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;'
            f'padding:10px 14px;margin-bottom:10px;font-size:0.85rem;color:#92400E;'
            f'display:flex;align-items:center;gap:8px;">'
            f'{icon("alert-triangle",15,"#D97706")}'
            f'복습할 게 많이 쌓였어요. <b>오늘 분량을 정해서</b> 부담 없이 시작해 보세요.</div>',
            unsafe_allow_html=True,
        )
        # 추천 분량 옵션
        opts = [n for n in (15, 30, 50) if n < total_due] + [total_due]
        opt_labels = [f"{n}개" if n < total_due else f"전체 {total_due}개" for n in opts]
        default_idx = 0  # 가장 작은 분량을 기본 추천
        chosen_label = st.radio(
            "오늘 복습 분량",
            opt_labels,
            index=default_idx,
            horizontal=True,
            key="rv_daily_cap",
        )
        chosen_n = opts[opt_labels.index(chosen_label)]
    else:
        chosen_n = total_due

    if st.button(f"복습 시작 ({chosen_n}개)",
                 type="primary", use_container_width=True, key="rv_start"):
        _init_session(due_items[:chosen_n])
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 복습 세션 — 카드 UI
# ─────────────────────────────────────────────────────────────────────────────

def _render_session(api_cfg: dict | None):
    rv     = st.session_state["_rv"]
    items  = rv["items"]
    idx    = rv["idx"]

    if idx >= len(items):
        rv["done"] = True
        st.rerun()
        return

    item   = items[idx]
    tot    = len(items)
    pct    = int(idx / tot * 100)
    itype  = item.get("item_type", "word")
    d      = item.get("item_data", {})

    # 진행 바
    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
  <span style="font-size:0.82rem;color:#6B7280;">{idx+1} / {tot}</span>
  <span style="font-weight:700;color:#7C3AED;">점수 {rv['score']}</span>
</div>
<div style="background:#E5E7EB;border-radius:4px;height:6px;margin-bottom:14px;">
  <div style="background:linear-gradient(90deg,#7C3AED,#A78BFA);
       height:100%;width:{pct}%;border-radius:4px;transition:width 0.3s;"></div>
</div>
""", unsafe_allow_html=True)

    # 유형별 카드 렌더링
    if itype == "word":
        _render_word_card(rv, item, d, idx)
    elif itype == "grammar":
        _render_grammar_card_rv(rv, item, d, idx, api_cfg)
    elif itype == "sentence":
        _render_sentence_card(rv, item, d, idx)
    else:
        _render_word_card(rv, item, d, idx)   # fallback


def _render_word_card(rv, item, d, idx):
    """단어 복습 — 플래시카드 스타일 (앞: 영어, 뒤: 한국어)"""
    word_en = d.get("word_en", item.get("item_key", ""))
    word_kr = d.get("word_kr", "")
    flipped = rv.get("flipped", False)
    answered = rv.get("answered", False)

    if not answered:
        # 앞면: 영어 단어 표시
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#EDE9FE,#F5F3FF);
     border:2px solid #C4B5FD;border-radius:18px;
     padding:40px 20px;text-align:center;margin-bottom:16px;
     min-height:160px;display:flex;flex-direction:column;
     align-items:center;justify-content:center;">
  <div style="font-size:0.78rem;color:#7C3AED;font-weight:700;margin-bottom:12px;
       letter-spacing:1px;">📘 단어 복습</div>
  <div style="font-size:2rem;font-weight:900;color:#4C1D95;letter-spacing:-1px;">
    {word_en}
  </div>
  <div style="font-size:0.82rem;color:#8B5CF6;margin-top:10px;opacity:0.8;">
    이 단어의 뜻이 기억나나요?
  </div>
</div>
""", unsafe_allow_html=True)

        _tts_button(word_en, btn_key=f"rv_word_{idx}", compact=True)

        col_ok, col_no = st.columns(2)
        with col_ok:
            if st.button("✅ 알아요!", type="primary",
                         use_container_width=True, key=f"rv_ok_{idx}"):
                _process_answer(rv, item, True)
        with col_no:
            if st.button("❌ 모르겠어요", use_container_width=True,
                         key=f"rv_no_{idx}"):
                _process_answer(rv, item, False)

        # 힌트: 뒤집기
        if st.button("👀 정답 보기", use_container_width=True,
                     key=f"rv_flip_{idx}"):
            rv["flipped"] = True
            st.rerun()

    else:
        # 답변 후 결과
        is_ok  = rv["last_ok"]
        result = rv.get("result", {})

        bg     = "#F0FDF4" if is_ok else "#FEF2F2"
        border = "#BBF7D0" if is_ok else "#FECACA"
        emoji  = "✅" if is_ok else "❌"

        st.markdown(f"""
<div style="background:{bg};border:2px solid {border};border-radius:18px;
     padding:24px 20px;text-align:center;margin-bottom:16px;">
  <div style="font-size:1.8rem;margin-bottom:8px;">{emoji}</div>
  <div style="font-size:1.6rem;font-weight:900;color:#1F2937;">
    {word_en}
  </div>
  <div style="font-size:1.1rem;color:#374151;margin-top:6px;font-weight:600;">
    {word_kr}
  </div>
  <div style="font-size:0.8rem;color:#6B7280;margin-top:10px;">
    {result.get("message", "")}
    &nbsp;|&nbsp; 다음 복습: {result.get("next_review", "")}
  </div>
  {'<div style="margin-top:8px;font-size:1.2rem;">🏆 마스터!</div>' if result.get("is_mastered") else ''}
</div>
""", unsafe_allow_html=True)

        _tts_button(word_en, btn_key=f"rv_word_ans_{idx}", compact=True)

        if st.button("다음 →", type="primary",
                     use_container_width=True, key=f"rv_next_{idx}"):
            rv["idx"]      += 1
            rv["answered"]  = False
            rv["last_ok"]   = None
            rv["result"]    = None
            rv["flipped"]   = False
            st.rerun()


def _render_word_card_flipped(rv, item, d, idx):
    """정답 힌트 표시 후 자가 평가"""
    word_en = d.get("word_en", "")
    word_kr = d.get("word_kr", "")

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#FEF3C7,#FFFBEB);
     border:2px solid #FDE68A;border-radius:18px;
     padding:32px 20px;text-align:center;margin-bottom:16px;">
  <div style="font-size:0.78rem;color:#D97706;font-weight:700;margin-bottom:10px;">
    👀 정답 확인
  </div>
  <div style="font-size:1.8rem;font-weight:900;color:#92400E;">{word_en}</div>
  <div style="font-size:1.3rem;color:#374151;margin-top:8px;font-weight:700;">{word_kr}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("**알고 계셨나요?**")
    col_ok, col_no = st.columns(2)
    with col_ok:
        if st.button("✅ 알고 있었어요", type="primary",
                     use_container_width=True, key=f"rv_hint_ok_{idx}"):
            _process_answer(rv, item, True)
    with col_no:
        if st.button("❌ 몰랐어요", use_container_width=True,
                     key=f"rv_hint_no_{idx}"):
            _process_answer(rv, item, False)


def _render_grammar_card_rv(rv, item, d, idx, api_cfg):
    """문법 복습 — 패턴 암기 자가 평가"""
    point_name = d.get("point_name", item.get("item_key", "문법 포인트"))
    explanation = d.get("explanation_kr", "")
    patterns    = d.get("patterns", [])
    tip         = d.get("tip", "")
    answered    = rv.get("answered", False)
    flipped     = rv.get("flipped", False)

    if not answered:
        # 앞면: 포인트 이름만
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#EDE9FE,#F5F3FF);
     border:2px solid #C4B5FD;border-radius:18px;
     padding:36px 20px;text-align:center;margin-bottom:16px;min-height:150px;
     display:flex;flex-direction:column;align-items:center;justify-content:center;">
  <div style="font-size:0.78rem;color:#7C3AED;font-weight:700;margin-bottom:12px;">
    ✏️ 문법 복습
  </div>
  <div style="font-size:1.5rem;font-weight:900;color:#4C1D95;">
    {point_name}
  </div>
  <div style="font-size:0.85rem;color:#8B5CF6;margin-top:8px;">
    이 문법의 핵심 패턴을 설명할 수 있나요?
  </div>
</div>
""", unsafe_allow_html=True)

        if not flipped:
            col_ok, col_no = st.columns(2)
            with col_ok:
                if st.button("✅ 설명할 수 있어요", type="primary",
                             use_container_width=True, key=f"rv_gok_{idx}"):
                    _process_answer(rv, item, True)
            with col_no:
                if st.button("❌ 잘 모르겠어요", use_container_width=True,
                             key=f"rv_gno_{idx}"):
                    _process_answer(rv, item, False)
            if st.button("👀 내용 보기", use_container_width=True,
                         key=f"rv_gflip_{idx}"):
                rv["flipped"] = True
                st.rerun()
        else:
            # 뒤집기: 설명 표시
            if explanation:
                st.markdown(f"""
<div style="background:#F5F3FF;border-radius:12px;padding:14px;margin-bottom:10px;
     font-size:0.88rem;color:#374151;line-height:1.8;">
  {explanation.replace(chr(10), "<br>")}
</div>
""", unsafe_allow_html=True)
            for p in patterns[:3]:
                st.markdown(
                    f'<div style="background:rgba(255,255,255,0.7);border-radius:6px;'
                    f'padding:5px 10px;margin:3px 0;font-size:0.83rem;'
                    f'font-family:monospace;">{p}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("")
            col_ok, col_no = st.columns(2)
            with col_ok:
                if st.button("✅ 알고 있었어요", type="primary",
                             use_container_width=True, key=f"rv_gflip_ok_{idx}"):
                    _process_answer(rv, item, True)
            with col_no:
                if st.button("❌ 다시 복습해야겠어요", use_container_width=True,
                             key=f"rv_gflip_no_{idx}"):
                    _process_answer(rv, item, False)
    else:
        # 답변 후 결과
        is_ok  = rv["last_ok"]
        result = rv.get("result", {})
        bg     = "#F0FDF4" if is_ok else "#FEF2F2"
        border = "#BBF7D0" if is_ok else "#FECACA"
        emoji  = "✅" if is_ok else "❌"

        st.markdown(f"""
<div style="background:{bg};border:2px solid {border};border-radius:18px;
     padding:20px;text-align:center;margin-bottom:16px;">
  <div style="font-size:1.5rem;margin-bottom:6px;">{emoji}</div>
  <div style="font-size:1.1rem;font-weight:800;color:#1F2937;">{point_name}</div>
  {f'<div style="font-size:0.8rem;color:#6B7280;margin-top:6px;">{result.get("message","")}</div>' if result else ''}
  {'<div style="margin-top:8px;font-size:1.1rem;">🏆 마스터!</div>' if result.get("is_mastered") else ''}
</div>
""", unsafe_allow_html=True)

        if tip:
            st.markdown(
                f'<div style="background:#FFFBEB;border-radius:8px;padding:8px 12px;'
                f'font-size:0.82rem;color:#92400E;margin-bottom:10px;">'
                f'💡 {tip}</div>',
                unsafe_allow_html=True,
            )
        if st.button("다음 →", type="primary",
                     use_container_width=True, key=f"rv_gnext_{idx}"):
            rv["idx"]     += 1
            rv["answered"] = False
            rv["last_ok"]  = None
            rv["result"]   = None
            rv["flipped"]  = False
            st.rerun()


def _render_sentence_card(rv, item, d, idx):
    """문장 복습 — 번역 맞추기"""
    en_text  = d.get("en_text", item.get("item_key", ""))
    kr_text  = d.get("kr_text", "")
    answered = rv.get("answered", False)
    flipped  = rv.get("flipped", False)

    if not answered:
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#ECFDF5,#F0FDF4);
     border:2px solid #A7F3D0;border-radius:18px;
     padding:32px 20px;text-align:center;margin-bottom:16px;min-height:140px;
     display:flex;flex-direction:column;align-items:center;justify-content:center;">
  <div style="font-size:0.78rem;color:#059669;font-weight:700;margin-bottom:10px;">
    📖 문장 복습
  </div>
  <div style="font-size:1rem;font-weight:700;color:#065F46;line-height:1.7;
       font-style:italic;">
    "{en_text}"
  </div>
  <div style="font-size:0.82rem;color:#059669;margin-top:10px;">
    이 문장을 우리말로 말할 수 있나요?
  </div>
</div>
""", unsafe_allow_html=True)

        _tts_button(en_text, btn_key=f"rv_sent_{idx}", compact=True,
                    label="🔊 문장 발음 듣기")

        if not flipped:
            col_ok, col_no = st.columns(2)
            with col_ok:
                if st.button("✅ 번역할 수 있어요", type="primary",
                             use_container_width=True, key=f"rv_sok_{idx}"):
                    _process_answer(rv, item, True)
            with col_no:
                if st.button("❌ 잘 모르겠어요", use_container_width=True,
                             key=f"rv_sno_{idx}"):
                    _process_answer(rv, item, False)
            if st.button("👀 번역 보기", use_container_width=True,
                         key=f"rv_sflip_{idx}"):
                rv["flipped"] = True
                st.rerun()
        else:
            kr_display = kr_text if kr_text.strip() else "번역 정보가 없어요 — 스스로 번역해 보세요! 💪"
            kr_style   = "color:#374151;font-weight:600;" if kr_text.strip() else "color:#9CA3AF;font-style:italic;"
            st.markdown(f"""
<div style="background:#FFFBEB;border-radius:10px;padding:14px;margin-bottom:12px;">
  <div style="font-size:0.78rem;color:#D97706;font-weight:700;">우리말 번역</div>
  <div style="font-size:1rem;margin-top:4px;{kr_style}">
    {kr_display}
  </div>
</div>
""", unsafe_allow_html=True)
            col_ok, col_no = st.columns(2)
            with col_ok:
                if st.button("✅ 알고 있었어요", type="primary",
                             use_container_width=True, key=f"rv_sflip_ok_{idx}"):
                    _process_answer(rv, item, True)
            with col_no:
                if st.button("❌ 다시 봐야겠어요", use_container_width=True,
                             key=f"rv_sflip_no_{idx}"):
                    _process_answer(rv, item, False)
    else:
        is_ok  = rv["last_ok"]
        result = rv.get("result", {})
        bg     = "#F0FDF4" if is_ok else "#FEF2F2"
        border = "#BBF7D0" if is_ok else "#FECACA"

        st.markdown(f"""
<div style="background:{bg};border:2px solid {border};border-radius:18px;
     padding:20px;margin-bottom:16px;">
  <div style="font-size:0.92rem;font-weight:700;color:#1F2937;font-style:italic;
       margin-bottom:6px;">"{en_text}"</div>
  <div style="font-size:0.88rem;color:#374151;">{kr_text}</div>
  <div style="font-size:0.78rem;color:#6B7280;margin-top:8px;">
    {"✅" if is_ok else "❌"} {result.get("message", "")}
  </div>
  {'<div style="margin-top:6px;font-size:1rem;">🏆 마스터!</div>' if result.get("is_mastered") else ''}
</div>
""", unsafe_allow_html=True)

        if st.button("다음 →", type="primary",
                     use_container_width=True, key=f"rv_snext_{idx}"):
            rv["idx"]     += 1
            rv["answered"] = False
            rv["last_ok"]  = None
            rv["result"]   = None
            rv["flipped"]  = False
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 답안 처리 공통
# ─────────────────────────────────────────────────────────────────────────────

def _process_answer(rv: dict, item: dict, is_correct: bool):
    result = update_review_result(item["id"], is_correct)
    if is_correct:
        rv["score"] += 1
    else:
        rv["wrong"].append(item)
    rv["answered"] = True
    rv["last_ok"]  = is_correct
    rv["result"]   = result
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 완료 화면
# ─────────────────────────────────────────────────────────────────────────────

def _render_done():
    rv    = st.session_state.get("_rv", {})
    sc    = rv.get("score", 0)
    tot   = len(rv.get("items", []))
    wrong = rv.get("wrong", [])
    pct   = int(sc / tot * 100) if tot else 0

    if pct == 100: emoji, msg = "🏆", "완벽해요! 모두 기억하고 있어요!"
    elif pct >= 80: emoji, msg = "⭐", "훌륭해요! 거의 다 알고 있어요"
    elif pct >= 60: emoji, msg = "💪", "좋아요! 조금만 더 복습해요"
    else:           emoji, msg = "📚", "함께 열심히 복습해요!"

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#F5F3FF,#EDE9FE);border-radius:18px;
     padding:32px;text-align:center;margin-bottom:20px;
     box-shadow:0 4px 20px rgba(124,58,237,0.12);">
  <div style="font-size:3.5rem;">{emoji}</div>
  <div style="font-size:2.2rem;font-weight:900;color:#6D28D9;margin:8px 0;">
    {sc} / {tot} ({pct}점)
  </div>
  <div style="color:#6B7280;font-size:0.95rem;">{msg}</div>
</div>
""", unsafe_allow_html=True)

    # 다음 복습 예정 메시지
    st.markdown(f"""
<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:12px;
     padding:12px 16px;margin-bottom:16px;font-size:0.85rem;color:#1D4ED8;">
  🧠 <b>에빙하우스 스케줄이 업데이트됐어요!</b><br>
  맞힌 항목은 더 긴 간격으로, 틀린 항목은 내일 다시 복습 예정이에요.
</div>
""", unsafe_allow_html=True)

    # 틀린 항목 복습
    if wrong:
        st.markdown(f"**다시 봐야 할 항목 ({len(wrong)}개)**")
        for w in wrong:
            d     = w.get("item_data", {})
            label = d.get("word_en") or d.get("point_name") or w.get("item_key", "")
            sub   = d.get("word_kr") or d.get("category") or ""
            st.markdown(
                f'<div style="background:#FEF2F2;border:1px solid #FECACA;'
                f'border-radius:8px;padding:8px 12px;margin:3px 0;font-size:0.85rem;">'
                f'❌ {_type_icon(w["item_type"])} <b>{label}</b>'
                f'{f" — {sub}" if sub else ""}'
                f'<span style="color:#94A3B8;font-size:0.75rem;margin-left:8px;">'
                f'내일 다시 출제</span></div>',
                unsafe_allow_html=True,
            )

    col1, col2 = st.columns(2)
    if col1.button("🔄 다시 풀기", use_container_width=True):
        original = rv.get("items", [])
        _init_session(original)
        st.rerun()
    if col2.button("✅ 완료", type="primary", use_container_width=True):
        del st.session_state["_rv"]
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────────────────────

def _days_since(date_str: str | None) -> int | None:
    if not date_str:
        return None
    import datetime as dt
    try:
        past = dt.date.fromisoformat(str(date_str)[:10])
        return (dt.date.today() - past).days
    except Exception:
        return None


def _get_upcoming(student_id: int, limit: int = 10) -> list[dict]:
    from study_db import get_supabase
    import datetime as dt
    sb    = get_supabase()
    today = dt.date.today().isoformat()
    result = (
        sb.table("review_schedule")
        .select("*")
        .eq("student_id", student_id)
        .eq("is_mastered", False)
        .gt("next_review", today)
        .order("next_review")
        .limit(limit)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────────────────────────────────────────
# 오답 발생 시 자동 스케줄링 헬퍼 (다른 모듈에서 import해서 사용)
# ─────────────────────────────────────────────────────────────────────────────

def auto_schedule_word(student_id: int, note_id: int,
                       word_en: str, word_kr: str):
    """단어 오답 발생 시 호출 → 복습 스케줄 등록"""
    try:
        schedule_review(
            student_id = student_id,
            item_type  = "word",
            item_key   = f"n{note_id}_{word_en}",
            item_data  = {"word_en": word_en, "word_kr": word_kr},
            note_id    = note_id,
        )
    except Exception:
        pass  # 스케줄 실패해도 퀴즈 흐름 유지


def auto_schedule_grammar(student_id: int, note_id: int,
                          gp_id: int, gp_name: str,
                          category: str = "", explanation_kr: str = "",
                          patterns: list | None = None, tip: str = ""):
    """문법 오답 발생 시 호출 → 복습 스케줄 등록"""
    try:
        schedule_review(
            student_id = student_id,
            item_type  = "grammar",
            item_key   = f"gp_{gp_id}",
            item_data  = {
                "point_name":     gp_name,
                "category":       category,
                "explanation_kr": explanation_kr,
                "patterns":       patterns or [],
                "tip":            tip,
            },
            note_id = note_id,
        )
    except Exception:
        pass


def auto_schedule_sentence(student_id: int, note_id: int,
                           sent_idx: int, en_text: str, kr_text: str):
    """문장 오답 발생 시 호출 → 복습 스케줄 등록"""
    try:
        schedule_review(
            student_id = student_id,
            item_type  = "sentence",
            item_key   = f"n{note_id}_s{sent_idx}",
            item_data  = {"en_text": en_text, "kr_text": kr_text},
            note_id    = note_id,
        )
    except Exception:
        pass
