# study_wrongnote.py — 반반 BanBan 오답노트 v2
# 단어 + 문법/내신/기출 문제 통합 오답노트 + 스마트 복습 큐 (망각곡선 기반)

import math
from datetime import datetime, date, timedelta

import streamlit as st
import streamlit.components.v1 as components

from icons import icon, section_md
from study_db import (
    get_wrong_notes, save_ai_explain, get_weakness_profile,
    save_weakness_profile, delete_wrong_note,
    get_question_wrong_notes, save_question_wrong_explain,
    remove_question_wrong, log_study_activity,
)
from study_ai import explain_wrong_word, analyze_weakness


# ─────────────────────────────────────────────────────────────────────────────
# 망각곡선 기반 복습 긴급도
# ─────────────────────────────────────────────────────────────────────────────

def _review_urgency(wrong_count: int, last_wrong_str: str) -> float:
    """에빙하우스 망각곡선 기반 복습 긴급도 (높을수록 오늘 복습 필요).

    urgency = wrong_count / max(days_since_wrong, 0.5)
    """
    try:
        lw   = datetime.fromisoformat(last_wrong_str[:19])
        days = max((datetime.now() - lw).total_seconds() / 86400, 0.1)
    except Exception:
        days = 0.5
    return wrong_count / days


def _review_interval(wrong_count: int) -> int:
    """오답 빈도에 따른 권장 복습 주기 (일)"""
    if wrong_count >= 5: return 1
    if wrong_count >= 3: return 2
    return 4


def _needs_review_today(wrong_count: int, last_wrong_str: str) -> bool:
    try:
        lw   = datetime.fromisoformat(last_wrong_str[:19])
        days = (datetime.now() - lw).total_seconds() / 86400
    except Exception:
        return True
    return days >= _review_interval(wrong_count)


def _urgency_badge(wrong_count: int, last_wrong_str: str) -> str:
    if _needs_review_today(wrong_count, last_wrong_str):
        return '<span style="background:#dc2626;color:white;border-radius:8px;padding:1px 7px;font-size:0.68rem;font-weight:700;margin-left:6px;">오늘 복습!</span>'
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# 🎉 "내 머릿속 저장" 폭발 애니메이션
# ─────────────────────────────────────────────────────────────────────────────

def _render_memorize_celebration(word_en: str, word_kr: str):
    st.balloons()
    components.html(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:transparent;overflow:hidden;font-family:-apple-system,'Segoe UI',sans-serif;}}
.stage{{width:100%;height:170px;display:flex;align-items:center;justify-content:center;position:relative;}}
.word-pop{{position:absolute;z-index:10;background:linear-gradient(135deg,#7c3aed,#a78bfa);
  color:white;border-radius:22px;padding:14px 30px;text-align:center;
  box-shadow:0 6px 30px rgba(124,58,237,0.45);
  animation:popIn 0.55s cubic-bezier(0.34,1.72,0.64,1) forwards;}}
.word-pop .eng{{font-size:1.6rem;font-weight:900;}}
.word-pop .kr{{font-size:0.95rem;opacity:0.88;margin-top:2px;}}
@keyframes popIn{{
  0%{{transform:scale(0.05) rotate(-8deg);opacity:0;}}
  35%{{transform:scale(1.25) rotate(4deg);opacity:1;}}
  55%{{transform:scale(0.93) rotate(-2deg);}}
  75%{{transform:scale(1.07) rotate(1deg);}}
  100%{{transform:scale(1) rotate(0deg);opacity:1;}}
}}
.brain{{position:absolute;font-size:2.8rem;right:12%;top:14px;
  animation:brainPulse 0.6s ease-out 0.25s both;}}
@keyframes brainPulse{{
  0%{{transform:scale(0) rotate(-20deg);opacity:0;}}
  60%{{transform:scale(1.35) rotate(6deg);opacity:1;}}
  80%{{transform:scale(0.88) rotate(-3deg);}}
  100%{{transform:scale(1.1) rotate(0deg);opacity:1;}}
}}
.msg{{position:absolute;bottom:12px;font-size:0.88rem;font-weight:700;color:#6d28d9;
  animation:slideUp 0.4s ease-out 0.4s both;}}
@keyframes slideUp{{from{{opacity:0;transform:translateY(12px);}}to{{opacity:1;transform:translateY(0);}}}}
.ring{{position:absolute;width:80px;height:80px;border:4px solid rgba(167,139,250,0.7);
  border-radius:50%;animation:ringBurst 0.7s ease-out forwards;}}
.ring2{{animation-delay:0.12s;border-color:rgba(196,181,253,0.5);}}
.ring3{{animation-delay:0.24s;border-color:rgba(221,214,254,0.4);}}
@keyframes ringBurst{{0%{{transform:scale(0.2);opacity:0.9;}}100%{{transform:scale(3.5);opacity:0;}}}}
</style></head><body>
<div class="stage">
  <div class="ring"></div><div class="ring ring2"></div><div class="ring ring3"></div>
  <div class="word-pop"><div class="eng">{word_en}</div><div class="kr">{word_kr}</div></div>
  <div class="brain">🧠</div>
  <div class="msg">내 머릿속에 쏙! 완벽하게 기억됨 ✨</div>
  <canvas id="c" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:5;"></canvas>
</div>
<script>
const canvas=document.getElementById('c'),ctx=canvas.getContext('2d');
function resize(){{canvas.width=canvas.offsetWidth;canvas.height=canvas.offsetHeight;}}
resize();
const cx=canvas.width/2,cy=canvas.height/2;
const colors=['#ff6b6b','#ffd93d','#6bcb77','#4d96ff','#ff922b','#cc5de8','#a78bfa','#34d399'];
const particles=[];
for(let i=0;i<55;i++){{
  const angle=(i/55)*Math.PI*2+(Math.random()-0.5)*0.4;
  const speed=4+Math.random()*6.5;
  const isRect=Math.random()>0.45;
  particles.push({{x:cx,y:cy,vx:Math.cos(angle)*speed,vy:Math.sin(angle)*speed-1.5,
    size:isRect?(5+Math.random()*8):(3+Math.random()*5),
    color:colors[Math.floor(Math.random()*colors.length)],
    life:1,decay:0.018+Math.random()*0.022,rot:Math.random()*Math.PI*2,
    drot:(Math.random()-0.5)*0.25,isRect}});
}}
function draw(){{
  ctx.clearRect(0,0,canvas.width,canvas.height);
  let any=false;
  for(const p of particles){{
    if(p.life<=0)continue;any=true;
    p.x+=p.vx;p.y+=p.vy;p.vy+=0.18;p.vx*=0.985;p.rot+=p.drot;p.life-=p.decay;
    ctx.globalAlpha=Math.max(0,p.life);ctx.fillStyle=p.color;
    if(p.isRect){{ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.rot);
      ctx.fillRect(-p.size/2,-p.size/4,p.size,p.size/2);ctx.restore();}}
    else{{ctx.beginPath();ctx.arc(p.x,p.y,p.size/2,0,Math.PI*2);ctx.fill();}}
  }}
  ctx.globalAlpha=1;
  if(any)requestAnimationFrame(draw);
}}
draw();
</script></body></html>""", height=175, scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
# 탭 1: 단어 오답노트
# ─────────────────────────────────────────────────────────────────────────────

def _render_word_wrongnotes(student_id: int, student_name: str,
                             api_config: dict | None, notes: list):
    wrongs = get_wrong_notes(student_id, None)

    # 오늘 복습 필요 수
    due_today = sum(1 for w in wrongs
                    if _needs_review_today(w["wrong_count"], w.get("last_wrong", "")))

    if due_today > 0:
        st.markdown(f"""
<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:10px;
     padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;gap:8px;">
  <span style="font-size:1.2rem;">⏰</span>
  <div>
    <div style="font-weight:700;color:#dc2626;font-size:0.88rem;">
      오늘 복습 필요: {due_today}개 단어
    </div>
    <div style="font-size:0.76rem;color:#6b7280;">
      망각 곡선 분석 결과 — 지금 복습하면 장기 기억에 효과적이에요!
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    if not wrongs:
        st.markdown(f"""
<div style="text-align:center;padding:40px;background:#f9fafb;border-radius:14px;
     border:2px dashed #e5e7eb;">
  <div>{icon("check-circle", 52, "#16a34a")}</div>
  <div style="font-size:1.1rem;font-weight:700;color:#1f2937;margin-top:8px;">
    단어 오답이 없어요! 🎉
  </div>
  <div style="color:#6b7280;font-size:0.9rem;margin-top:4px;">
    단어 퀴즈를 풀면 틀린 단어가 여기에 기록됩니다.
  </div>
</div>
""", unsafe_allow_html=True)
        return

    # 통계 요약 — 박스 metric 대신 인라인 글래스 한 줄
    total   = len(wrongs)
    max_cnt = max(w["wrong_count"] for w in wrongs)
    top_w   = wrongs[0]["word_en"]
    st.markdown(
        f'<div style="display:flex;gap:22px;align-items:center;'
        f'background:rgba(255,255,255,0.7);backdrop-filter:blur(18px);'
        f'border:1px solid rgba(255,255,255,0.7);border-radius:16px;'
        f'padding:12px 20px;margin-bottom:12px;'
        f'box-shadow:0 6px 24px rgba(31,38,135,0.06);">'
        f'<span style="font-size:0.82rem;color:#64748B;">전체 오답 '
        f'<b style="color:#1E293B;font-size:1.05rem;">{total}</b>개</span>'
        f'<span style="font-size:0.82rem;color:#64748B;">최다 오답 '
        f'<b style="color:#DC2626;font-size:1.05rem;">{max_cnt}</b>회</span>'
        f'<span style="font-size:0.82rem;color:#64748B;">최고 취약 '
        f'<b style="color:#1E293B;">{top_w}</b></span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 노트 필터
    note_opts = {"전체": None}
    note_opts.update({n["title"]: n["id"] for n in notes})
    sel_note_title = st.selectbox("노트 선택", list(note_opts.keys()), key="wn_note_sel")
    sel_note_id    = note_opts[sel_note_title]
    if sel_note_id:
        wrongs = get_wrong_notes(student_id, sel_note_id)

    # 취약 분석 (AI)
    if api_config:
        profile = get_weakness_profile(student_id, sel_note_id or 0)
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            if st.button("🔍 취약 분석", use_container_width=True, key="analyze_weak"):
                with st.spinner("틀린 패턴을 현미경으로 들여다보는 중…"):
                    summary = analyze_weakness(
                        student_name=student_name,
                        wrong_words=wrongs,
                        exam_results=[],
                        api_config=api_config,
                    )
                    save_weakness_profile(student_id, sel_note_id or 0, summary)
                    profile = summary
                st.rerun()
        if profile:
            st.markdown(f"""
<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;
     padding:14px;margin-bottom:16px;">
  <div style="font-weight:700;color:#854d0e;margin-bottom:6px;">
    {icon("target", 15, "#854d0e")} 반반쌤의 취약점 분석
  </div>
  <div style="font-size:0.88rem;color:#374151;line-height:1.7;">{profile}</div>
</div>
""", unsafe_allow_html=True)

    # 정렬 (복습 긴급도 기본)
    wrongs = sorted(wrongs, key=lambda x: -_review_urgency(x["wrong_count"], x.get("last_wrong", "")))

    st.markdown(section_md("list", f"오답 단어 ({len(wrongs)}개)"), unsafe_allow_html=True)
    st.caption("색이 진할수록 더 자주 틀린 단어예요. 단어를 골라 자세히 복습해보세요.")

    # ── 칩 클라우드 (시각 overview, 긴급도 색상) ────────────────────
    chips_html = '<div style="display:flex;flex-wrap:wrap;gap:7px;margin:6px 0 14px;">'
    for w in wrongs:
        wc = w["wrong_count"]
        if wc >= 5:   c_bg, c_fg, c_bd = "#FEE2E2", "#991B1B", "#FCA5A5"
        elif wc >= 3: c_bg, c_fg, c_bd = "#FEF3C7", "#92400E", "#FCD34D"
        else:         c_bg, c_fg, c_bd = "#E0F2FE", "#075985", "#7DD3FC"
        due_mark = ('<span style="color:#DC2626;">●</span> '
                    if _needs_review_today(wc, w.get("last_wrong","")) else "")
        chips_html += (
            f'<span style="display:inline-flex;align-items:center;gap:5px;'
            f'background:{c_bg};color:{c_fg};border:1px solid {c_bd};'
            f'border-radius:20px;padding:4px 12px;font-size:0.82rem;font-weight:600;">'
            f'{due_mark}{w["word_en"]}'
            f'<span style="opacity:0.6;font-size:0.72rem;">{wc}회</span></span>'
        )
    chips_html += '</div>'
    st.markdown(chips_html, unsafe_allow_html=True)

    # ── 단어 선택 → 상세 카드 1개 (expander 더미 대신) ──────────────
    word_map = {f'{w["word_en"]} ({w["word_kr"]}) · {w["wrong_count"]}회': w for w in wrongs}
    sel_label = st.selectbox("자세히 복습할 단어 선택", list(word_map.keys()),
                             key="wn_word_sel", help="단어를 입력해 검색할 수 있어요")
    w = word_map[sel_label]
    wc, word_en, word_kr = w["wrong_count"], w["word_en"], w["word_kr"]
    explain  = w.get("ai_explain", "")
    last_w   = w.get("last_wrong", "")
    interval = _review_interval(wc)
    urgent   = _urgency_badge(wc, last_w)

    detail = (
        f'<div style="background:rgba(255,255,255,0.72);backdrop-filter:blur(18px);'
        f'border:1px solid rgba(255,255,255,0.7);border-radius:16px;padding:16px 20px;'
        f'box-shadow:0 6px 24px rgba(31,38,135,0.06);margin-bottom:10px;">'
        f'<div style="font-size:1.2rem;font-weight:800;color:#1E293B;">{word_en}'
        f'<span style="font-size:0.9rem;color:#64748B;font-weight:600;"> · {word_kr}</span></div>'
        f'<div style="font-size:0.76rem;color:#94A3B8;margin-top:4px;">'
        f'{wc}회 오답 · 권장 복습 주기 {interval}일 {urgent}</div>'
    )
    if explain:
        detail += (
            f'<div style="background:#F0FDF4;border-radius:10px;padding:12px;'
            f'font-size:0.88rem;color:#374151;line-height:1.7;margin-top:10px;">'
            f'<div style="font-weight:700;margin-bottom:4px;">'
            f'{icon("zap", 13, "#16a34a")} AI 해설</div>{explain}</div>'
        )
    detail += '</div>'
    st.markdown(detail, unsafe_allow_html=True)

    col_ex, col_ok = st.columns(2)
    if api_config and col_ex.button("💡 해설 생성", key=f"wn_explain_{word_en}",
                                    use_container_width=True):
        with st.spinner(f"'{word_en}' 해설 생성 중…"):
            new_explain = explain_wrong_word(word_en, word_kr, wc, api_config)
            save_ai_explain(student_id, w["note_id"], word_en, new_explain)
        st.rerun()
    if col_ok.button("🧠 완전히 외웠어요!", key=f"wn_ok_{word_en}",
                      use_container_width=True, type="primary"):
        delete_wrong_note(student_id, w["note_id"], word_en)
        st.session_state["celebrate_word"]    = word_en
        st.session_state["celebrate_word_kr"] = word_kr
        st.rerun()

    # 집중 퀴즈
    if wrongs:
        st.divider()
        st.markdown(section_md("target", "오답 단어 집중 퀴즈"), unsafe_allow_html=True)
        st.caption("틀린 단어들로만 퀴즈를 풀어 집중 연습해보세요!")
        if st.button("🚀 집중 퀴즈 시작", type="primary", use_container_width=True):
            wrong_pairs = [(w["word_en"], w["word_kr"]) for w in wrongs]
            note_id_for = wrongs[0]["note_id"] if wrongs else 0
            target_note = next((n for n in notes if n["id"] == note_id_for), None)
            if target_note is None and notes:
                target_note = notes[0]
            if target_note:
                from study_vocab import _init_quiz_state
                temp_note = target_note.copy()
                temp_note["words_data"] = wrong_pairs
                _init_quiz_state(wrong_pairs, "en2kr", student_id, note_id_for)
                st.session_state["study_page"] = "단어학습"
                st.session_state["study_note"] = temp_note
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 탭 2: 문제 오답노트 (문법/내신/기출 통합)
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_LABEL = {
    "grammar":   ("문법 드릴", "#7c3aed", "#faf5ff"),
    "exam":      ("내신 문제", "#0891b2", "#eff6ff"),
    "past":      ("기출 문제", "#059669", "#f0fdf4"),
    "past_exam": ("기출 문제", "#059669", "#f0fdf4"),  # study_upload.py alias
    "essay":     ("서술형 DNA", "#7c3aed", "#f5f3ff"),  # study_essay.py
}
_SOURCE_ICON = {"grammar": "📝", "exam": "📋", "past": "📄", "past_exam": "📄", "essay": "✍️"}


def _render_question_wrongnotes(student_id: int, student_name: str,
                                  api_config: dict | None, notes: list):
    qwns = get_question_wrong_notes(student_id, None)

    # 오늘 복습 필요
    due_today = sum(1 for q in qwns
                    if _needs_review_today(q.get("wrong_count", 1),
                                            q.get("last_wrong", "")))
    if due_today > 0:
        st.markdown(f"""
<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
     padding:10px 14px;margin-bottom:12px;">
  <span style="font-weight:700;color:#1d4ed8;">⏰ 오늘 복습 필요: {due_today}개 문제</span>
  <span style="font-size:0.76rem;color:#6b7280;margin-left:8px;">
    망각 곡선 분석 — 오늘 다시 풀어보세요!
  </span>
</div>
""", unsafe_allow_html=True)

    if not qwns:
        st.markdown(f"""
<div style="text-align:center;padding:40px;background:#f9fafb;border-radius:14px;
     border:2px dashed #e5e7eb;">
  <div>{icon("check-circle", 52, "#16a34a")}</div>
  <div style="font-size:1.1rem;font-weight:700;color:#1f2937;margin-top:8px;">
    문제 오답이 없어요! 🎉
  </div>
  <div style="color:#6b7280;font-size:0.9rem;margin-top:4px;">
    문법 드릴, 내신 문제, 기출 문제를 풀면 오답이 여기에 기록됩니다.
  </div>
</div>
""", unsafe_allow_html=True)
        return

    # 소스 필터
    sources = sorted({q.get("source_type", "exam") for q in qwns})
    src_opts = ["전체"] + [_SOURCE_LABEL.get(s, (s, "#374151", "#f3f4f6"))[0] for s in sources]
    src_map  = {"전체": None}
    for s in sources:
        label = _SOURCE_LABEL.get(s, (s, "", ""))[0]
        src_map[label] = s

    sel_src_lbl = st.selectbox("유형 필터", src_opts, key="qwn_src_sel")
    sel_src     = src_map[sel_src_lbl]
    if sel_src:
        qwns = [q for q in qwns if q.get("source_type") == sel_src]

    # 정렬
    sort_q = st.radio("정렬", ["복습 긴급도 순", "많이 틀린 순", "최근 틀린 순"],
                       horizontal=True, key="qwn_sort")
    if sort_q == "복습 긴급도 순":
        qwns = sorted(qwns, key=lambda x: -_review_urgency(
            x.get("wrong_count", 1), x.get("last_wrong", "")))
    elif sort_q == "많이 틀린 순":
        qwns = sorted(qwns, key=lambda x: -x.get("wrong_count", 1))
    else:
        qwns = sorted(qwns, key=lambda x: x.get("last_wrong", ""), reverse=True)

    # 통계 — 인라인 글래스 한 줄 (metric 박스 제거)
    st.markdown(
        f'<div style="display:flex;gap:22px;align-items:center;'
        f'background:rgba(255,255,255,0.7);backdrop-filter:blur(18px);'
        f'border:1px solid rgba(255,255,255,0.7);border-radius:16px;'
        f'padding:12px 20px;margin-bottom:12px;'
        f'box-shadow:0 6px 24px rgba(31,38,135,0.06);">'
        f'<span style="font-size:0.82rem;color:#64748B;">전체 오답 문제 '
        f'<b style="color:#1E293B;font-size:1.05rem;">{len(qwns)}</b>개</span>'
        f'<span style="font-size:0.82rem;color:#64748B;">오늘 복습 필요 '
        f'<b style="color:#1D4ED8;font-size:1.05rem;">{due_today}</b>개</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(section_md("list", f"오답 문제 ({len(qwns)}개)"), unsafe_allow_html=True)
    st.caption("문제를 골라 자세히 복습해보세요.")

    # ── 문제 선택 → 상세 카드 1개 (expander 더미 대신) ──────────────
    def _q_label(idx, q):
        snap = q.get("question_snapshot") or q.get("question_data") or {}
        src  = q.get("source_type", "exam")
        lbl  = _SOURCE_LABEL.get(src, (src, "", ""))[0]
        wc   = q.get("wrong_count", 1)
        due  = "● " if _needs_review_today(wc, q.get("last_wrong","")) else ""
        qt   = (snap.get("question", "질문 없음") or "질문 없음")[:40]
        return f"{due}[{lbl}] {qt}… · {wc}회"

    q_label_map = {_q_label(i, q): q for i, q in enumerate(qwns)}
    sel_q_lbl = st.selectbox("자세히 복습할 문제 선택", list(q_label_map.keys()),
                             key="qwn_q_sel", help="문제 내용을 입력해 검색할 수 있어요")
    q = q_label_map[sel_q_lbl]

    snap    = q.get("question_snapshot") or q.get("question_data") or {}
    src     = q.get("source_type", "exam")
    label, badge_c, bg_c = _SOURCE_LABEL.get(src, (src, "#374151", "#f3f4f6"))
    wc      = q.get("wrong_count", 1)
    last_w  = q.get("last_wrong", "")
    urgent  = _urgency_badge(wc, last_w)
    q_full   = snap.get("question", "")
    q_answer = snap.get("answer", "")
    user_ans = q.get("user_answer", "")
    ai_exp   = q.get("ai_explain", "")
    opts     = snap.get("options", [])

    # 배지 + 문제 + 보기 (글래스 카드 1개)
    card = (
        f'<div style="background:rgba(255,255,255,0.72);backdrop-filter:blur(18px);'
        f'border:1px solid rgba(255,255,255,0.7);border-left:4px solid {badge_c};'
        f'border-radius:16px;padding:16px 20px;margin-bottom:10px;'
        f'box-shadow:0 6px 24px rgba(31,38,135,0.06);">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">'
        f'<span style="background:{badge_c};color:white;border-radius:8px;'
        f'padding:2px 10px;font-size:0.74rem;font-weight:700;">{label}</span>'
        f'<span style="font-size:0.76rem;color:#94A3B8;">{wc}회 오답 · 복습 주기 {_review_interval(wc)}일</span>'
        f'{urgent}</div>'
    )
    if q_full:
        card += (f'<div style="font-size:0.95rem;color:#1F2937;white-space:pre-line;'
                 f'line-height:1.6;margin-bottom:8px;">{q_full}</div>')
    if opts:
        card += (f'<div style="font-size:0.8rem;color:#94A3B8;margin-bottom:8px;">'
                 + " &nbsp;·&nbsp; ".join(opts) + '</div>')
    ans_color = "#DC2626" if user_ans and user_ans != q_answer else "#374151"
    card += (
        f'<div style="display:flex;gap:18px;font-size:0.84rem;margin-top:4px;">'
        f'<span><b style="color:#DC2626;">내 답</b> '
        f'<span style="color:{ans_color};font-weight:600;">{user_ans or "—"}</span></span>'
        f'<span><b style="color:#16A34A;">정답</b> '
        f'<span style="color:#16A34A;font-weight:600;">{q_answer or "—"}</span></span>'
        f'</div>'
    )
    if snap.get("answer_kr"):
        card += (f'<div style="font-size:0.8rem;color:#64748B;margin-top:6px;">'
                 f'{icon("info",12,"#64748B")} {snap["answer_kr"]}</div>')
    if ai_exp:
        card += (f'<div style="background:#F0FDF4;border-radius:10px;padding:10px;margin-top:10px;'
                 f'font-size:0.86rem;color:#374151;line-height:1.7;">'
                 f'<div style="font-weight:700;margin-bottom:4px;">'
                 f'{icon("zap",13,"#16a34a")} AI 해설</div>{ai_exp}</div>')
    card += '</div>'
    st.markdown(card, unsafe_allow_html=True)

    col_ex2, col_ok2 = st.columns(2)
    if api_config and col_ex2.button("💡 AI 해설", key=f"qwn_explain_{q['id']}",
                                     use_container_width=True):
        with st.spinner("AI 해설 생성 중…"):
            from study_ai import explain_wrong_answer
            new_exp = explain_wrong_answer(snap, user_ans, api_config)
            save_question_wrong_explain(q["id"], new_exp)
        st.rerun()
    if col_ok2.button("✅ 완전히 이해했어요!", key=f"qwn_ok_{q['id']}",
                      use_container_width=True, type="primary"):
        remove_question_wrong(q["id"])
        st.success("오답노트에서 제거했습니다! 계속 파이팅 💪")
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 탭 3: 스마트 복습 큐
# ─────────────────────────────────────────────────────────────────────────────

def _render_smart_review(student_id: int, student_name: str,
                          api_config: dict | None, notes: list):
    """망각곡선 기반 오늘의 복습 큐"""

    # 단어 + 문제 오답 통합
    word_wrongs = get_wrong_notes(student_id, None)
    q_wrongs    = get_question_wrong_notes(student_id, None)

    # 오늘 복습 필요한 것만
    due_words = [w for w in word_wrongs
                 if _needs_review_today(w["wrong_count"], w.get("last_wrong", ""))]
    due_qs    = [q for q in q_wrongs
                 if _needs_review_today(q.get("wrong_count", 1), q.get("last_wrong", ""))]

    total_due = len(due_words) + len(due_qs)

    # 전체 오답 현황 요약
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1px solid #bbf7d0;
     border-radius:12px;padding:16px;margin-bottom:16px;">
  <div style="font-size:0.82rem;font-weight:700;color:#166534;margin-bottom:12px;">
    📊 전체 오답 현황
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
    <div style="text-align:center;background:white;border-radius:8px;padding:10px;">
      <div style="font-size:1.4rem;font-weight:800;color:#7c3aed;">{len(word_wrongs)}</div>
      <div style="font-size:0.72rem;color:#6b7280;">단어 오답</div>
    </div>
    <div style="text-align:center;background:white;border-radius:8px;padding:10px;">
      <div style="font-size:1.4rem;font-weight:800;color:#0891b2;">{len(q_wrongs)}</div>
      <div style="font-size:0.72rem;color:#6b7280;">문제 오답</div>
    </div>
    <div style="text-align:center;background:white;border-radius:8px;padding:10px;">
      <div style="font-size:1.4rem;font-weight:800;color:#dc2626;">{total_due}</div>
      <div style="font-size:0.72rem;color:#6b7280;">오늘 복습</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    if total_due == 0:
        st.markdown(f"""
<div style="text-align:center;padding:40px;background:#f0fdf4;border-radius:14px;
     border:2px solid #bbf7d0;">
  <div style="font-size:3rem;">🎉</div>
  <div style="font-size:1.1rem;font-weight:700;color:#166534;margin-top:10px;">
    오늘 복습 완료!
  </div>
  <div style="color:#6b7280;font-size:0.9rem;margin-top:4px;">
    오늘 복습해야 할 항목이 없어요. 내일 또 열심히 해봐요!
  </div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;
     padding:12px 16px;margin-bottom:16px;">
  <div style="font-weight:700;color:#92400e;font-size:0.9rem;">
    ⏰ 오늘의 스마트 복습 큐 — {total_due}개 항목
  </div>
  <div style="font-size:0.78rem;color:#6b7280;margin-top:2px;">
    에빙하우스 망각곡선 기반 · 지금 복습하면 장기 기억 효율 최대화!
  </div>
</div>
""", unsafe_allow_html=True)

    # 오늘 복습 필요 단어
    if due_words:
        st.markdown(f"**📖 단어 복습 ({len(due_words)}개)**")
        cols = st.columns(min(3, len(due_words)))
        for i, w in enumerate(due_words[:6]):
            wc  = w["wrong_count"]
            col = cols[i % len(cols)]
            col.markdown(f"""
<div style="background:white;border:2px solid #fecaca;border-radius:10px;
     padding:12px;text-align:center;margin-bottom:8px;">
  <div style="font-size:1.1rem;font-weight:800;color:#374151;">{w['word_en']}</div>
  <div style="font-size:0.8rem;color:#6b7280;margin-top:2px;">{w['word_kr']}</div>
  <div style="font-size:0.7rem;color:#dc2626;margin-top:4px;">🔴 {wc}회 오답</div>
</div>
""", unsafe_allow_html=True)
        if len(due_words) > 6:
            st.caption(f"… 외 {len(due_words)-6}개 더")

    # 오늘 복습 필요 문제
    if due_qs:
        st.markdown(f"**❓ 문제 복습 ({len(due_qs)}개)**")
        for q in due_qs[:5]:
            snap  = q.get("question_snapshot") or {}
            src   = q.get("source_type", "exam")
            label, badge_c, _ = _SOURCE_LABEL.get(src, (src, "#374151", "#f3f4f6"))
            q_text = snap.get("question", "")[:70]
            st.markdown(f"""
<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;
     padding:10px 14px;margin-bottom:6px;border-left:3px solid {badge_c};">
  <span style="background:{badge_c};color:white;border-radius:6px;
       padding:1px 7px;font-size:0.68rem;margin-right:6px;">{label}</span>
  <span style="font-size:0.85rem;color:#374151;">{q_text}…</span>
</div>
""", unsafe_allow_html=True)
        if len(due_qs) > 5:
            st.caption(f"… 외 {len(due_qs)-5}개 더")

    # 단어 집중 퀴즈 시작
    if due_words and notes:
        st.divider()
        st.markdown("#### 지금 바로 오늘의 복습 시작!")
        if st.button("🚀 오늘의 단어 집중 퀴즈", type="primary", use_container_width=True):
            wrong_pairs = [(w["word_en"], w["word_kr"]) for w in due_words]
            note_id_for = due_words[0]["note_id"] if due_words else 0
            target_note = next((n for n in notes if n["id"] == note_id_for), None)
            if target_note is None and notes:
                target_note = notes[0]
            if target_note:
                from study_vocab import _init_quiz_state
                temp_note = target_note.copy()
                temp_note["words_data"] = wrong_pairs
                _init_quiz_state(wrong_pairs, "en2kr", student_id, note_id_for)
                st.session_state["study_page"] = "단어학습"
                st.session_state["study_note"] = temp_note
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Public: 오답노트 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_wrong_note(student_id: int | None, student_name: str,
                    api_config: dict | None, notes: list[dict]):
    # 축하 애니메이션
    if "celebrate_word" in st.session_state:
        _cw  = st.session_state.pop("celebrate_word")
        _ckr = st.session_state.pop("celebrate_word_kr", "")
        _render_memorize_celebration(_cw, _ckr)

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#dc2626,#f87171);color:white;
     border-radius:14px;padding:18px 20px;margin-bottom:20px;">
  <div style="font-size:0.85rem;opacity:0.85;display:flex;align-items:center;gap:4px;">
    {icon("alert-circle", 14, "rgba(255,255,255,0.85)")} 오답노트
  </div>
  <div style="font-size:1.4rem;font-weight:800;margin-top:4px;">
    {student_name + "의 " if student_name else ""}오답 학습 센터
  </div>
  <div style="font-size:0.82rem;opacity:0.85;margin-top:4px;">
    단어 · 문법 · 내신 · 기출 전체 오답 통합 관리 + 스마트 복습
  </div>
</div>
""", unsafe_allow_html=True)

    if not student_id:
        st.info("👤 왼쪽 사이드바에서 학생 이름을 선택하면 오답 기록이 저장됩니다.")
        return

    tab_word, tab_question, tab_smart = st.tabs([
        "📖 단어 오답", "❓ 문제 오답 (문법/내신/기출)", "🧠 스마트 복습 큐"
    ])

    with tab_word:
        _render_word_wrongnotes(student_id, student_name, api_config, notes)

    with tab_question:
        _render_question_wrongnotes(student_id, student_name, api_config, notes)

    with tab_smart:
        _render_smart_review(student_id, student_name, api_config, notes)
