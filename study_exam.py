# study_exam.py — 반반쌤 담당: 내신문제 엔진
# 자동 문제 생성 + 채점 + 오답 해설

import streamlit as st
from icons import icon, section_md, title_md
from study_db import (
    save_exam_set, get_exam_set, save_exam_result,
    record_wrong, record_correct,
    save_to_question_bank, count_question_bank, get_question_bank,
    add_question_wrong, log_study_activity,
)
from study_ai import generate_exam_questions, explain_wrong_answer, generate_ox_questions
from plans    import can_use_ai, increment_ai_usage, upgrade_banner, ai_usage_bar


# ─────────────────────────────────────────────────────────────────────────────
# 채점 유틸 — 보기 번호(인덱스)로 견고하게 채점
#   AI가 answer를 "② met"/"met"/"②"/"2)" 등 제각각 형식으로 주어도
#   같은 보기를 가리키면 정답으로 인정 (정답이 오답 처리되는 버그 방지)
# ─────────────────────────────────────────────────────────────────────────────
import re as _re

_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩"

def _norm_ans(s: str) -> str:
    return _re.sub(r"\s+", " ",
                   _re.sub(r"[^\w가-힣]", " ", (s or "").lower())).strip()

def _strip_marker(s: str) -> str:
    """앞쪽 보기 기호(①, 1), (2), A. 등) 제거 후 본문만."""
    s = (s or "").strip()
    s = _re.sub(r"^\s*[\(\[]?\s*(?:[①②③④⑤⑥⑦⑧⑨⑩]|[1-9][0-9]?|[a-eA-E])\s*[\)\].:、]?\s+",
                "", s)
    return s.strip()

def _marker_to_index(s: str):
    """순수 보기 기호('②','2','(3)','B')만일 때 0-based 인덱스. 아니면 None."""
    s = (s or "").strip()
    if len(s) == 1 and s in _CIRCLED:
        return _CIRCLED.index(s)
    m = _re.fullmatch(r"[\(\[]?\s*([1-9][0-9]?|[a-eA-E])\s*[\)\].:]?", s)
    if m:
        tok = m.group(1)
        return int(tok) - 1 if tok.isdigit() else "abcde".index(tok.lower())
    return None

def _option_index(value: str, options: list) -> int:
    """value(정답 또는 학생 선택)가 가리키는 보기 인덱스(-1=못 찾음)."""
    if not options:
        return -1
    idx = _marker_to_index(value)
    if idx is not None and 0 <= idx < len(options):
        return idx
    nv_strip = _norm_ans(_strip_marker(value))
    nv_full  = _norm_ans(value)
    for i, o in enumerate(options):
        if (_norm_ans(_strip_marker(o)) == nv_strip and nv_strip) \
           or _norm_ans(o) == nv_full:
            return i
    return -1

def is_answer_correct(user_ans: str, correct: str, options: list | None) -> bool:
    """객관식은 보기 인덱스로, 단답은 정규화 텍스트로 채점."""
    options = options or []
    if not options:
        return _norm_ans(_strip_marker(user_ans)) == _norm_ans(_strip_marker(correct)) \
            or _norm_ans(user_ans) == _norm_ans(correct)
    ui = _option_index(user_ans, options)
    ci = _option_index(correct, options)
    if ui >= 0 and ci >= 0:
        return ui == ci
    return _norm_ans(_strip_marker(user_ans)) == _norm_ans(_strip_marker(correct))


# ─────────────────────────────────────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────────────────────────────────────

_DIFF_LABELS = {
    "easy":   ("쉬움 ★", "#dcfce7", "#166534"),
    "medium": ("보통 ★★", "#fef9c3", "#854d0e"),
    "hard":   ("어려움 ★★★", "#fee2e2", "#991b1b"),
}

_TYPE_ICONS = {
    "빈칸":  "pencil",
    "문법":  "check-square",
    "일치":  "check-circle",
    "순서":  "layers",
    "주제":  "sparkles",
    "서술형":"file-text",
}

def _ticon(qtype: str, size: int = 14, color: str = "#374151") -> str:
    """문제 유형 → Lucide SVG 아이콘 문자열"""
    return icon(_TYPE_ICONS.get(qtype, "info"), size, color)


# 대화 화자 접두어 패턴 (G: B: W: M: A: H: 등)
import re as _re
_SPEAKER_RE = _re.compile(r'^([A-Za-z]+)\s*:\s*')
_SPEAKER_COLORS = {
    "G": "#4F46E5", "B": "#0891B2", "W": "#7C3AED",
    "M": "#D97706", "A": "#059669", "H": "#DC2626",
}

def _format_passage(text: str) -> str:
    """지문 텍스트 포맷:
    - 대화문(G:, B: 등)이면 화자마다 줄바꿈 + 색상 강조
    - 일반 지문이면 그대로 반환 (줄바꿈만 <br> 변환)
    """
    if not text:
        return ""
    # 대화문 감지: G: / B: / W: 등 패턴이 있으면
    if _re.search(r'\b[A-Z]\s*:', text):
        # 화자 앞에서 줄바꿈
        lines = _re.split(r'(?<=[.!?])\s+(?=[A-Z]\s*:)', text)
        if len(lines) == 1:
            # 마침표 없이 바로 붙어있는 경우도 처리
            lines = _re.split(r'\s+(?=[A-Z]\s*:)', text)
        parts = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = _SPEAKER_RE.match(line)
            if m:
                sp   = m.group(1).upper()
                rest = line[m.end():]
                color = _SPEAKER_COLORS.get(sp, "#374151")
                parts.append(
                    f'<span style="font-weight:800;color:{color};">{m.group(0).strip()}</span>'
                    f'<span style="color:#1f2937;"> {rest}</span>'
                )
            else:
                parts.append(f'<span style="color:#374151;">{line}</span>')
        return "<br>".join(parts)
    # 일반 지문: \n → <br>
    return text.replace("\n", "<br>")


def _render_question_card(i: int, q: dict, show_answer: bool = False,
                          user_ans: str = ""):
    diff  = q.get("difficulty", "medium")
    dc, fc = _DIFF_LABELS.get(diff, _DIFF_LABELS["medium"])[1:]
    ticon = _ticon(q.get("type", ""), 14, fc)

    st.markdown(f"""
<div style="background:white;border-radius:14px;padding:18px;
     box-shadow:0 2px 10px rgba(0,0,0,0.07);margin-bottom:16px;
     border-left:5px solid {fc};">
  <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
    <span style="font-weight:800;color:#1f2937;font-size:1.05rem;">문제 {i+1}. {ticon} {q.get('type','')}</span>
    <span style="background:{dc};color:{fc};border-radius:20px;padding:2px 10px;
          font-size:0.75rem;font-weight:700;">{_DIFF_LABELS.get(diff, _DIFF_LABELS['medium'])[0]}</span>
  </div>
""", unsafe_allow_html=True)

    # 지문 있으면 표시 (글자 크기 키움 + 대화문 줄바꿈 처리)
    if q.get("passage"):
        passage_html = _format_passage(q["passage"])
        st.markdown(f"""
<div style="background:#F8FAFF;border-radius:10px;padding:14px 18px;
     font-size:1rem;color:#1f2937;margin-bottom:12px;
     border:1.5px solid #C7D2FE;line-height:1.8;">
  {passage_html}
</div>
""", unsafe_allow_html=True)

    # 문제 본문
    q_text = q.get("question", "").replace("\n", "<br>")
    st.markdown(f"""
<div style="font-size:1rem;color:#1f2937;font-weight:600;margin-bottom:12px;
     line-height:1.7;">
  {q_text}
</div>
</div>
""", unsafe_allow_html=True)

    if show_answer:
        is_ok  = is_answer_correct(user_ans, q.get("answer", ""), q.get("options"))
        color  = "#16a34a" if is_ok else "#dc2626"
        bg     = "#f0fdf4" if is_ok else "#fef2f2"
        ans_icon = icon("check-circle", 14, color) if is_ok else icon("x-circle", 14, color)
        st.markdown(f"""
<div style="background:{bg};border-radius:8px;padding:10px 14px;margin-top:6px;">
  <span style="display:inline-flex;align-items:center;gap:5px;font-weight:700;color:{color};">
    {ans_icon} {user_ans or '(미답변)'}
  </span>
  {'&nbsp;&nbsp;→&nbsp;&nbsp;<span style="color:#374151;">정답: ' + q.get("answer","") + '</span>' if not is_ok else ''}
  {('<br><span style="font-size:0.82rem;color:#6b7280;">' + q.get("answer_kr","") + '</span>') if q.get("answer_kr") else ''}
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# O/X (T/F) 이해도 문제 플로우 — 지문 고정 + 묶음 진행
# ─────────────────────────────────────────────────────────────────────────────

def _ox_dialogue_passage(d: dict) -> str:
    """대화문 → 영어 대사 줄 단위 HTML (한글은 정답 노출 방지로 숨김)."""
    out = []
    for ln in d.get("lines", []):
        if isinstance(ln, (list, tuple)) and ln and str(ln[0]).strip():
            out.append(str(ln[0]).strip())
    return "<br>".join(out)


def _ox_section_passage(sents: list) -> str:
    """본문 단락 → 영어 문장 이어붙인 단락 HTML."""
    out = []
    for p in sents:
        if isinstance(p, (list, tuple)) and p and str(p[0]).strip():
            out.append(str(p[0]).strip())
    return " ".join(out)


def _build_ox_groups(questions: list, dialogues: list, text_data: dict) -> list:
    """AI O/X 문제를 노트의 실제 지문별로 그룹핑.

    반환: [{"source", "group", "passage"(HTML), "questions":[...]}...]
    지문 텍스트는 노트 원본(authoritative)에서 가져와 정확성 보장.
    """
    # ① 노트에서 지문 정의를 순서대로 수집
    passages = []  # (source, group_name, passage_html)
    for d in (dialogues or []):
        txt = _ox_dialogue_passage(d)
        if txt:
            passages.append(("대화문", d.get("title", "대화문"), txt))

    secs = text_data.get("sections") or []
    if secs:
        for s in secs:
            txt = _ox_section_passage(s.get("sentences", []))
            if txt:
                passages.append(("본문", s.get("label", "단락"), txt))
    elif text_data.get("sentences"):
        txt = _ox_section_passage(text_data["sentences"])
        if txt:
            passages.append(("본문", "본문", txt))

    groups = [{"source": s, "group": g, "passage": t, "questions": []}
              for (s, g, t) in passages]

    # ② 각 문제를 지문에 배정 (정확/부분/소스 매칭 순)
    def _match(q) -> int:
        qg = (q.get("group") or "").strip()
        qs = (q.get("source") or "").strip()
        for i, (_, pg, _t) in enumerate(passages):
            if qg and qg == pg:
                return i
        for i, (_, pg, _t) in enumerate(passages):
            if qg and (qg in pg or pg in qg):
                return i
        for i, (psrc, _pg, _t) in enumerate(passages):
            if qs and psrc == qs:
                return i
        return 0 if passages else -1

    orphans = []
    for q in questions:
        mi = _match(q)
        if mi >= 0:
            groups[mi]["questions"].append(q)
        else:
            orphans.append(q)

    # ③ 문제 없는 지문 제거 + 미매칭 문제는 첫 그룹에 흡수
    groups = [g for g in groups if g["questions"]]
    if orphans:
        if groups:
            groups[0]["questions"].extend(orphans)
        else:
            groups = [{"source": "본문", "group": "본문",
                       "passage": "", "questions": orphans}]
    return groups


def _render_ox_passage(grp: dict, gidx: int, gtotal: int):
    """현재 지문 카드 (고정 표시)."""
    src   = grp.get("source", "")
    name  = grp.get("group", "")
    psg   = grp.get("passage", "")
    icon_name = "message-circle" if src == "대화문" else "book-open"
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);'
        f'border:1px solid #C7D2FE;border-radius:16px;padding:18px 20px;margin-bottom:14px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:7px;font-size:0.82rem;'
        f'font-weight:800;color:#4338CA;">'
        f'{icon(icon_name,15,"#4338CA")} 지문 {gidx+1} · {src} '
        f'<span style="color:#6366F1;">{name}</span></div>'
        f'<span style="font-size:0.72rem;color:#818CF8;background:white;'
        f'border-radius:20px;padding:2px 10px;font-weight:700;">지문 {gidx+1}/{gtotal}</span>'
        f'</div>'
        f'<div style="font-size:0.98rem;line-height:1.85;color:#1E293B;'
        f'background:rgba(255,255,255,0.6);border-radius:10px;padding:12px 14px;">'
        f'{psg or "(지문 없음 — 진술만 보고 풀어요)"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_ox(note: dict, student_id: int | None, api_config: dict | None):
    note_id   = note["id"]
    dialogues = note.get("dialogues_data", note.get("dialogues", []))
    text_data = note.get("text_data", {})

    ox = st.session_state.get("ox_state")

    # ── 생성 전 ───────────────────────────────────────────────────
    if not ox:
        st.markdown(
            f'<div style="font-size:0.85rem;color:#64748B;margin-bottom:10px;">'
            f'{icon("check-square",14,"#16A34A")} 대화문·본문 내용을 제대로 이해했는지 '
            f'참/거짓으로 확인해요. 대화문당 3문제, 본문 단락별 7문제 이상 출제됩니다.</div>',
            unsafe_allow_html=True,
        )
        if not dialogues and not text_data.get("sections") and not text_data.get("sentences"):
            st.info("이 노트에는 대화문/본문이 없어 O/X 문제를 만들 수 없어요.")
            return
        if st.button("O/X 문제 생성하기", type="primary", use_container_width=True,
                     key="ox_gen_btn"):
            with st.spinner("반반쌤이 이해도 문제를 출제하는 중…"):
                try:
                    qs = generate_ox_questions(text_data, dialogues, api_config)
                except Exception as e:
                    st.error(f"생성 실패: {e}")
                    return
            if not qs:
                st.warning("문제를 생성하지 못했어요. 다시 시도해주세요.")
                return
            groups = _build_ox_groups(qs, dialogues, text_data)
            if not groups:
                st.warning("지문을 구성하지 못했어요. 다시 시도해주세요.")
                return
            st.session_state["ox_state"] = {
                "groups": groups, "gidx": 0, "qidx": 0, "score": 0,
                "answered": False, "last_ok": None,
                "student_id": student_id, "note_id": note_id,
                "wrong": [],
                "total": sum(len(g["questions"]) for g in groups),
            }
            st.rerun()
        return

    groups = ox["groups"]
    gtotal = len(groups)
    gidx   = ox["gidx"]
    total  = ox["total"]

    # ── 완료 화면 ─────────────────────────────────────────────────
    if gidx >= gtotal:
        sc  = ox["score"]
        pct = int(sc / total * 100) if total else 0
        if pct >= 90:   emoji, msg = "award", "완벽한 이해예요!"
        elif pct >= 70: emoji, msg = "trending-up", "잘 이해했어요!"
        else:           emoji, msg = "book-open", "지문을 다시 한번 읽어볼까요?"
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.72);backdrop-filter:blur(18px);'
            f'border:1px solid rgba(255,255,255,0.7);border-radius:18px;padding:24px;'
            f'text-align:center;box-shadow:0 8px 32px rgba(31,38,135,0.08);">'
            f'<div style="margin-bottom:6px;">{icon(emoji,34,"#6366F1")}</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#1E293B;">{sc} / {total}</div>'
            f'<div style="color:#64748B;margin-top:4px;">{msg}</div></div>',
            unsafe_allow_html=True,
        )
        if ox["student_id"]:
            try:
                log_study_activity(ox["student_id"], note_id, "exam",
                                   score=sc, total=total)
            except Exception:
                pass
        if st.button("다시 풀기", use_container_width=True, key="ox_retry"):
            del st.session_state["ox_state"]
            st.rerun()
        return

    # ── 현재 지문 + 문제 ──────────────────────────────────────────
    grp    = groups[gidx]
    qlist  = grp["questions"]
    qidx   = ox["qidx"]
    q      = qlist[qidx]

    # 전체 진행 위치 (앞 그룹들의 문제 수 합 + 현재 그룹 내 위치)
    done_before = sum(len(groups[g]["questions"]) for g in range(gidx))
    overall_pos = done_before + qidx + 1

    # ① 지문 카드 (고정)
    _render_ox_passage(grp, gidx, gtotal)

    # ② 진행 표시 (이 지문 내 + 전체)
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:8px;font-size:0.78rem;color:#94A3B8;">'
        f'<span>이 지문 문제 {qidx+1} / {len(qlist)}</span>'
        f'<span>전체 {overall_pos} / {total}</span></div>',
        unsafe_allow_html=True,
    )

    # ③ 진술문 카드
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.72);backdrop-filter:blur(18px);'
        f'border:1px solid rgba(255,255,255,0.7);border-radius:16px;padding:22px 24px;'
        f'box-shadow:0 6px 24px rgba(31,38,135,0.06);margin-bottom:12px;">'
        f'<div style="font-size:0.74rem;color:#94A3B8;font-weight:700;margin-bottom:6px;">'
        f'위 지문을 읽고, 다음 설명이 맞으면 O, 틀리면 X</div>'
        f'<div style="font-size:1.05rem;font-weight:700;color:#1E293B;line-height:1.5;">'
        f'{q["statement"]}</div></div>',
        unsafe_allow_html=True,
    )

    # ④ 답안 + 진행 (그룹 경계 넘어가기 처리)
    def _advance():
        ox["qidx"]     += 1
        ox["answered"]  = False
        ox["last_ok"]   = None
        if ox["qidx"] >= len(qlist):     # 이 지문 끝 → 다음 지문
            ox["gidx"] += 1
            ox["qidx"]  = 0

    if not ox["answered"]:
        c_o, c_x = st.columns(2)
        picked = None
        if c_o.button("O (맞다)", use_container_width=True, key=f"ox_o_{gidx}_{qidx}"):
            picked = "O"
        if c_x.button("X (틀리다)", use_container_width=True, key=f"ox_x_{gidx}_{qidx}"):
            picked = "X"
        if picked:
            ok = (picked == q["answer"])
            ox["answered"] = True
            ox["last_ok"]  = ok
            if ok:
                ox["score"] += 1
            else:
                ox["wrong"].append(q)
                ox["last_saved"] = None
                if ox["student_id"]:
                    try:
                        add_question_wrong(
                            ox["student_id"], note_id, None, "exam",
                            {"question": q["statement"],
                             "answer": q["answer"],
                             "answer_kr": q.get("explain", ""),
                             "type": "O/X"},
                            picked,
                        )
                        ox["last_saved"] = True
                    except Exception:
                        ox["last_saved"] = False
            st.rerun()
    else:
        if ox["last_ok"]:
            st.success("정답이에요!")
        else:
            st.error(f"아쉬워요. 정답은 **{q['answer']}**")
            _ls = ox.get("last_saved")
            if _ls is True:
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#059669;margin:2px 0 8px;'
                    f'display:flex;align-items:center;gap:5px;">'
                    f'{icon("check-circle",13,"#059669")} 오답노트에 자동 저장됐어요</div>',
                    unsafe_allow_html=True,
                )
            elif _ls is False:
                st.caption("⚠️ 오답노트 저장에 실패했어요. 잠시 후 다시 시도해 주세요.")
            elif not ox.get("student_id"):
                st.caption("로그인하면 이 오답이 오답노트에 저장돼요.")
        if q.get("explain"):
            st.markdown(
                f'<div style="background:#F0FDF4;border-radius:10px;padding:10px 14px;'
                f'font-size:0.86rem;color:#374151;line-height:1.6;margin-bottom:10px;">'
                f'{icon("zap",13,"#16a34a")} {q["explain"]}</div>',
                unsafe_allow_html=True,
            )
        # 다음 버튼: 지문 마지막 문제면 "다음 지문" 라벨
        is_last_in_grp = (qidx + 1 >= len(qlist))
        nxt_label = ("다음 지문으로" if is_last_in_grp and gidx + 1 < gtotal
                     else "결과 보기" if is_last_in_grp else "다음 문제")
        if st.button(nxt_label, type="primary", use_container_width=True,
                     key=f"ox_next_{gidx}_{qidx}"):
            _advance()
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Public: 내신문제 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 문제뱅크 — 누적 문제를 유형별로 골라 풀기 (AI 비용 0원)
# ─────────────────────────────────────────────────────────────────────────────

_QTYPE_META = {
    "단어":   ("bookmark",       "#0891B2", "단어 뜻 고르기"),
    "빈칸":   ("file-text",      "#6366F1", "문맥에 맞는 말 고르기"),
    "문법":   ("check-square",   "#0891B2", "어법상 틀린 부분 찾기"),
    "일치":   ("book-open",      "#16A34A", "내용 일치 / 불일치"),
    "순서":   ("layers",         "#D97706", "문장 순서 배열"),
    "주제":   ("sparkles",       "#7C3AED", "주제·제목 파악"),
    "서술형": ("pencil-square",  "#DC2626", "서술형 단답"),
    "빈칸완성":  ("file-text",   "#6366F1", "빈칸 채우기"),
    "오류찾기":  ("check-square", "#0891B2", "틀린 부분 찾기"),
    "배열하기":  ("layers",      "#D97706", "순서 배열"),
    "우리말→영어": ("pencil-square", "#DC2626", "영작"),
}
_DIFF_FILTER = {"전체": None, "쉬움": "easy", "보통": "medium", "어려움": "hard"}


def _render_question_bank(note: dict, student_id: int | None, api_config: dict | None):
    """누적된 문제뱅크를 유형별로 보여주고, 선택 유형을 바로 풀이."""
    note_id    = note["id"]
    words      = note.get("words_data", [])
    text_data  = note.get("text_data", {})

    st.markdown(
        f'<div style="font-size:0.85rem;color:#64748B;margin-bottom:10px;">'
        f'{icon("database",14,"#6366F1")} 지금까지 생성된 문제가 유형별로 쌓여 있어요. '
        f'<b>새로 만들지 않아도</b> 골라서 바로 풀 수 있어요.</div>',
        unsafe_allow_html=True,
    )

    # ── 전체 뱅크 조회 후 유형별 집계 ─────────────────────────────
    try:
        all_qs = get_question_bank(note_id, limit=10000)
    except Exception as e:
        st.error(f"뱅크 조회 오류: {e}")
        return

    if not all_qs:
        st.markdown(
            f'<div style="text-align:center;padding:36px 20px;background:#F8FAFB;'
            f'border:1px dashed #CBD5E1;border-radius:14px;color:#94A3B8;">'
            f'{icon("database",34,"#CBD5E1")}<br>'
            f'<div style="margin-top:10px;font-size:0.95rem;">아직 쌓인 문제가 없어요.</div>'
            f'<div style="font-size:0.82rem;margin-top:4px;">'
            f'「내신문제」 탭에서 문제를 생성하면 여기에 자동으로 모여요.</div></div>',
            unsafe_allow_html=True,
        )
        return

    # ── 난이도 필터 ───────────────────────────────────────────────
    diff_label = st.radio(
        "난이도", list(_DIFF_FILTER.keys()), index=0, horizontal=True,
        key="bank_diff_filter",
    )
    diff_val = _DIFF_FILTER[diff_label]
    pool = [q for q in all_qs if (diff_val is None or q.get("difficulty") == diff_val)]

    # 유형별 집계
    by_type: dict[str, list] = {}
    for q in pool:
        by_type.setdefault(q.get("q_type") or "기타", []).append(q)

    total = len(pool)
    st.markdown(
        f'<div style="font-size:0.82rem;color:#475569;margin:6px 0 10px;">'
        f'<b style="color:#4F46E5;">{total}</b>개 문제 · {len(by_type)}개 유형 '
        f'({diff_label})</div>',
        unsafe_allow_html=True,
    )

    if total == 0:
        st.info("이 난이도에는 쌓인 문제가 없어요. 다른 난이도를 선택해보세요.")
        return

    # ── 유형별 카드 (2열) → 클릭 시 그 유형 풀이 ──────────────────
    type_order = [t for t in _QTYPE_META if t in by_type] + \
                 [t for t in by_type if t not in _QTYPE_META]

    def _start_bank(qs_subset: list, label: str):
        import random as _r
        _r.shuffle(qs_subset)
        picked = qs_subset[:10]
        questions = [{
            "type":       q.get("q_type", ""),
            "question":   q.get("question", ""),
            "passage":    q.get("passage", ""),
            "options":    q.get("options", []),
            "answer":     q.get("answer", ""),
            "answer_kr":  q.get("answer_kr", ""),
            "difficulty": q.get("difficulty", "medium"),
            "bank_id":    q["id"],
        } for q in picked]
        try:
            exam_set_id = save_exam_set(student_id, note_id,
                                        questions[0].get("difficulty", "medium"),
                                        questions)
        except Exception:
            exam_set_id = None
        st.session_state["exam_state"] = {
            "exam_set_id": exam_set_id, "questions": questions,
            "answers": {}, "submitted": False, "idx": 0,
            "student_id": student_id, "note_id": note_id,
            "words": words, "sentences": text_data.get("sentences", []),
            "from_bank": True, "bank_label": label,
        }
        st.rerun()

    cols = st.columns(2)
    for i, t in enumerate(type_order):
        cnt = len(by_type[t])
        ic, color, desc = _QTYPE_META.get(t, ("file-text", "#64748B", ""))
        with cols[i % 2]:
            st.markdown(
                f'<div style="background:white;border:1px solid #ECEEF3;border-radius:14px;'
                f'padding:14px 16px;margin-bottom:4px;box-shadow:0 2px 8px rgba(31,38,135,0.05);">'
                f'<div style="display:flex;align-items:center;justify-content:space-between;">'
                f'<div style="display:flex;align-items:center;gap:8px;">'
                f'<span style="display:inline-flex;width:32px;height:32px;border-radius:9px;'
                f'align-items:center;justify-content:center;background:{color}18;">'
                f'{icon(ic,17,color)}</span>'
                f'<div><div style="font-weight:800;font-size:0.95rem;color:#1E293B;">{t}</div>'
                f'<div style="font-size:0.72rem;color:#94A3B8;">{desc}</div></div></div>'
                f'<div style="font-size:1.1rem;font-weight:900;color:{color};">{cnt}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if st.button(f"{t} 풀기 ({min(cnt,10)}문제)", key=f"bank_play_{t}",
                         use_container_width=True):
                _start_bank(list(by_type[t]), f"{t} · {diff_label}")

    # ── 전체 랜덤 풀기 ────────────────────────────────────────────
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button(f"전체 랜덤 10문제 풀기 ({diff_label})", type="primary",
                 use_container_width=True, key="bank_play_all"):
        _start_bank(list(pool), f"전체 랜덤 · {diff_label}")


def page_exam(note: dict, student_id: int | None, api_config: dict | None):
    """
    내신문제 메인 화면.
    note: {id, title, words_data, dialogues_data, text_data}
    """
    note_id    = note["id"]
    note_title = note.get("title", "노트")

    # 통합 헤더는 _study_note_selector가 렌더 → 페이지 자체 헤더 제거

    if not api_config:
        st.warning("API 키가 필요합니다. .env 파일에 ANTHROPIC_API_KEY 또는 GEMINI_API_KEY를 설정해주세요.")
        return

    # ── 문제 유형 선택: 내신문제 / O/X 이해도 ──────────────────────
    # 진행 중인 세션이 있으면 해당 모드 유지
    if st.session_state.get("exam_state"):
        _render_exam(st.session_state["exam_state"], api_config)
        return
    if st.session_state.get("ox_state"):
        _render_ox(note, student_id, api_config)
        return

    # 뱅크 누적 수 → 탭 라벨에 표시
    try:
        _bank_n = count_question_bank(note_id)
    except Exception:
        _bank_n = 0
    bank_label = f"문제뱅크 ({_bank_n})" if _bank_n else "문제뱅크"

    ex_tab, ox_tab, bank_tab = st.tabs(["내신문제", "O/X 이해도", bank_label])
    with ex_tab:
        _page_exam_main(note, student_id, api_config)
    with ox_tab:
        _render_ox(note, student_id, api_config)
    with bank_tab:
        _render_question_bank(note, student_id, api_config)


def _page_exam_main(note: dict, student_id: int | None, api_config: dict | None):
    """내신문제(객관식/서술형) 생성·풀이 — 기존 플로우."""
    note_id    = note["id"]
    note_title = note.get("title", "노트")

    # ── 문제 생성 설정 ─────────────────────────────────────────────
    st.markdown(section_md("sliders", "시험 설정"), unsafe_allow_html=True)

    # 내신뱅크 현황 표시
    try:
        bank_cnt = count_question_bank(note_id, source_type="exam")
    except Exception:
        bank_cnt = 0
    if bank_cnt > 0:
        _bank_bg  = "#f0fdf4" if bank_cnt >= 20 else "#f0f9ff"
        _bank_clr = "#166534" if bank_cnt >= 20 else "#0369a1"
        _bank_bc  = "#bbf7d0" if bank_cnt >= 20 else "#bae6fd"
        st.markdown(f"""
<div style="background:{_bank_bg};border:1px solid {_bank_bc};border-radius:10px;
     padding:10px 14px;margin-bottom:12px;font-size:0.85rem;color:{_bank_clr};">
  {icon("database",14,_bank_clr)} 내신뱅크에 이 노트의 문제 <b>{bank_cnt}개</b>가 누적되어 있습니다.
  {"&nbsp; 뱅크에서 바로 풀 수 있어요!" if bank_cnt >= 20 else ""}
</div>
""", unsafe_allow_html=True)

    # 학습 자료 확인 (범위 선택보다 먼저 — 가용 범위 판단용)
    words     = note.get("words_data", [])
    dialogues = note.get("dialogues_data", [])
    text_data = note.get("text_data", {})

    _has = {
        "단어":   len(words) > 0,
        "대화문": sum(len(d.get("lines", [])) for d in dialogues) > 0,
        "본문":   len(text_data.get("sentences", [])) > 0,
    }

    # ── 시험 범위 선택 (단어/대화문/본문/전체) ────────────────────
    scope_opts = ["전체"] + [k for k in ("단어", "대화문", "본문") if _has[k]]
    scope_icons = {"전체": "layers", "단어": "file-text",
                   "대화문": "message-circle", "본문": "book-open"}
    scope = st.radio(
        "시험 범위",
        scope_opts,
        index=0,
        horizontal=True,
        format_func=lambda s: f"{s} 테스트",
        key="exam_scope",
    )
    st.caption({
        "전체":   "단어·대화문·본문을 골고루 출제해요.",
        "단어":   "단어의 의미·용법·어휘력 중심으로 출제해요.",
        "대화문": "대화의 맥락·의도·세부 내용 이해 중심으로 출제해요.",
        "본문":   "본문 내용 일치·주제·문법 중심으로 출제해요.",
    }.get(scope, ""))

    col1, col2 = st.columns(2)
    difficulty = col1.selectbox(
        "난이도",
        options=["easy", "medium", "hard"],
        format_func=lambda x: _DIFF_LABELS[x][0],
        index=1,
        key="exam_diff",
    )
    n_q = col2.selectbox("문제 수", [3, 5, 7, 10], index=1, key="exam_nq")

    col_w, col_d, col_t = st.columns(3)
    col_w.metric("단어", f"{len(words)}개")
    col_d.metric("대화문", f"{sum(len(d.get('lines',[])) for d in dialogues)}줄")
    col_t.metric("본문", f"{len(text_data.get('sentences',[]))}문장")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if bank_cnt >= 20:
        gen_col, bank_col = st.columns([2, 1])
    else:
        gen_col = st.container()
        bank_col = None

    with gen_col:
        # ── AI 사용 가능 여부 체크 ────────────────────────────────
        ai_ok, ai_used, ai_limit = can_use_ai()
        ai_usage_bar()
        if not ai_ok:
            upgrade_banner(required="student", compact=True)
        elif st.button(f"{scope} 테스트 문제 생성하기", type="primary", use_container_width=True):
            with st.spinner("반반쌤이 심혈을 기울여 문제를 출제하는 중… 집중집중!"):
                try:
                    increment_ai_usage()
                    # 기존 뱅크 문제 → 중복 회피 목록
                    try:
                        _existing = [q.get("question", "")
                                     for q in get_question_bank(note_id, limit=10000)]
                    except Exception:
                        _existing = []
                    questions = generate_exam_questions(
                        text_data=text_data,
                        words=words,
                        dialogues=dialogues,
                        difficulty=difficulty,
                        api_config=api_config,
                        n_questions=n_q,
                        scope=scope,
                        avoid=_existing,
                    )
                    if not questions:
                        st.warning("새로운 문제를 만들지 못했어요(이미 충분히 출제됨). "
                                   "문제뱅크 탭에서 기존 문제를 풀어보세요.")
                        st.stop()
                    # ── 내신뱅크 자동 저장 ──────────────────────────
                    bank_fmt = [
                        {
                            "type":      q.get("type", ""),
                            "question":  q.get("question", ""),
                            "passage":   q.get("passage", ""),
                            "options":   q.get("options", []),
                            "answer":    q.get("answer", ""),
                            "answer_kr": q.get("answer_kr", ""),
                            "difficulty": difficulty,
                        }
                        for q in questions
                    ]
                    _saved = save_to_question_bank(note_id, bank_fmt, source_type="exam")
                    exam_set_id = save_exam_set(student_id, note_id, difficulty, questions)
                    st.session_state["exam_state"] = {
                        "exam_set_id": exam_set_id,
                        "questions":   questions,
                        "answers":     {},
                        "submitted":   False,
                        "idx":         0,
                        "student_id":  student_id,
                        "note_id":     note_id,
                        "words":       words,
                        "sentences":   text_data.get("sentences", []),
                    }
                    st.success(f"{len(questions)}개 문제 생성 완료! (뱅크 +{_saved}개 저장)")
                    st.rerun()
                except Exception as e:
                    err_str = str(e)
                    if "42501" in err_str or "does not exist" in err_str:
                        st.error(
                            "Supabase 테이블/권한 오류\n\n"
                            "**해결**: Supabase SQL Editor에서 `supabase_rls_fix.sql` 실행"
                        )
                    else:
                        st.error(f"문제 생성 실패: {err_str}")

    if bank_cnt >= 20:
        with bank_col:
            if st.button("뱅크에서 풀기", use_container_width=True):
                bank_qs = get_question_bank(note_id, source_type="exam", limit=n_q)
                if bank_qs:
                    questions = [
                        {
                            "type":      q.get("q_type", ""),
                            "question":  q.get("question", ""),
                            "passage":   q.get("passage", ""),
                            "options":   q.get("options", []),
                            "answer":    q.get("answer", ""),
                            "answer_kr": q.get("answer_kr", ""),
                            "difficulty": q.get("difficulty", "medium"),
                            "bank_id":   q["id"],
                        }
                        for q in bank_qs
                    ]
                    exam_set_id = save_exam_set(student_id, note_id, difficulty, questions)
                    st.session_state["exam_state"] = {
                        "exam_set_id": exam_set_id,
                        "questions":   questions,
                        "answers":     {},
                        "submitted":   False,
                        "idx":         0,
                        "student_id":  student_id,
                        "note_id":     note_id,
                        "words":       words,
                        "sentences":   text_data.get("sentences", []),
                        "from_bank":   True,
                    }
                    st.info(f"뱅크에서 {len(questions)}개 문제를 가져왔습니다.")
                    st.rerun()


def _render_exam(exam_state: dict, api_config: dict | None):
    """시험 화면 렌더링"""
    questions = exam_state["questions"]
    answers   = exam_state["answers"]
    submitted = exam_state.get("submitted", False)

    if not questions:
        st.error("문제가 없습니다.")
        if st.button("돌아가기"):
            del st.session_state["exam_state"]
            st.rerun()
        return

    if submitted:
        _render_result(exam_state, api_config)
        return

    # 문제 목록 (스크롤 방식)
    st.markdown(section_md("pencil", "문제 풀기"), unsafe_allow_html=True)
    st.caption("모든 문제에 답한 후 제출 버튼을 눌러주세요.")

    for i, q in enumerate(questions):
        diff  = q.get("difficulty", "medium")
        dc, fc = _DIFF_LABELS.get(diff, _DIFF_LABELS["medium"])[1:]
        ticon = _ticon(q.get("type", ""), 14, fc)

        with st.container():
            st.markdown(f"""
<div style="background:white;border-radius:14px;padding:16px;
     box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:12px;
     border-left:4px solid {fc};">
  <div style="font-weight:800;color:#1f2937;margin-bottom:8px;
       display:flex;align-items:center;gap:6px;">
    {ticon} 문제 {i+1} &nbsp;
    <span style="background:{dc};color:{fc};border-radius:20px;padding:1px 8px;
          font-size:0.72rem;">{_DIFF_LABELS.get(diff, _DIFF_LABELS['medium'])[0]}</span>
  </div>
""", unsafe_allow_html=True)

            if q.get("passage"):
                passage_html = _format_passage(q["passage"])
                st.markdown(f"""
<div style="background:#F8FAFF;border-radius:10px;padding:14px 18px;
     font-size:1rem;color:#1f2937;margin-bottom:12px;
     border:1.5px solid #C7D2FE;line-height:1.8;">
  {passage_html}
</div>
""", unsafe_allow_html=True)

            q_text = q.get("question", "")
            st.markdown(f'<div style="font-size:1rem;font-weight:600;margin-bottom:10px;color:#1f2937;line-height:1.7;">{q_text.replace(chr(10), "<br>")}</div></div>', unsafe_allow_html=True)

            options = q.get("options", [])
            if options:
                # 객관식
                prev = answers.get(i, None)
                prev_idx = None
                if prev and options:
                    for oi, opt in enumerate(options):
                        if opt == prev or f"{['①','②','③','④'][oi]} {opt}".strip() == prev.strip():
                            prev_idx = oi
                            break

                choice = st.radio(
                    f"q{i}", options,
                    index=prev_idx,
                    key=f"exam_q_{i}",
                    label_visibility="collapsed",
                )
                if choice:
                    answers[i] = choice
            else:
                # 서술형 / 단답형
                prev_text = answers.get(i, "")
                ans_text  = st.text_area(
                    f"q{i}", value=prev_text, key=f"exam_q_{i}",
                    placeholder="답을 입력하세요…",
                    label_visibility="collapsed", height=80,
                )
                if ans_text:
                    answers[i] = ans_text

    answered_count = len([v for v in answers.values() if v])
    total          = len(questions)

    st.markdown(f"""
<div style="background:#f0f4ff;border-radius:10px;padding:12px;text-align:center;
     margin:16px 0;font-size:0.9rem;color:#374151;">
  <span style="display:inline-flex;align-items:center;gap:6px;">
    {icon("bar-chart-2", 14, "#374151")} {answered_count} / {total} 문항 답변 완료
  </span>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    if col1.button("처음부터", use_container_width=True):
        del st.session_state["exam_state"]
        st.rerun()

    submit_ready = answered_count >= total
    if col2.button(
        "제출하기" if submit_ready else f"{total-answered_count}개 미답",
        type="primary", use_container_width=True,
        disabled=not submit_ready,
    ):
        exam_state["submitted"] = True
        exam_state["answers"]   = answers
        st.rerun()


def _render_result(exam_state: dict, api_config: dict | None):
    """채점 결과 화면"""
    questions  = exam_state["questions"]
    answers    = exam_state["answers"]
    student_id = exam_state.get("student_id")
    note_id    = exam_state.get("note_id")

    # 채점
    score = 0
    for i, q in enumerate(questions):
        user_ans = answers.get(i, "")
        correct  = q.get("answer", "").strip()
        q_type   = q.get("type", "")
        if q_type == "서술형":
            # 서술형은 AI 채점 (나중에 구현), 일단 부분점수 없이 제출만
            pass
        else:
            if is_answer_correct(user_ans, q.get("answer", ""), q.get("options")):
                score += 1

    total = len(questions)
    pct   = int(score / total * 100) if total else 0

    # 채점 결과 DB 저장
    if not exam_state.get("result_saved"):
        saved_wrong: dict[int, bool] = {}   # 문항별 오답노트 저장 성공 여부(정직한 표시용)
        save_err: str | None = None
        try:
            save_exam_result(
                exam_state["exam_set_id"], student_id,
                {str(k): v for k, v in answers.items()},
                score, total, ""
            )
        except Exception as e:
            save_err = str(e)
        # 오답 단어 기록 + 문제 오답노트 자동 저장
        if student_id:
            for i, q in enumerate(questions):
                user_ans = answers.get(i, "")
                correct  = q.get("answer", "").strip()
                if q.get("type") != "서술형" and not is_answer_correct(
                        user_ans, q.get("answer", ""), q.get("options")):
                    # 지문에서 단어 찾기 (간단한 매칭)
                    try:
                        passage = q.get("passage", "") + " " + q.get("question", "")
                        for en, kr in exam_state.get("words", []):
                            if en.lower() in passage.lower():
                                record_wrong(student_id, note_id, en, kr)
                                break
                    except Exception:
                        pass
                    # 오답 문제 자동 오답노트 저장 — 성공/실패를 기록(삼키지 않음)
                    try:
                        add_question_wrong(
                            student_id=student_id,
                            note_id=note_id,
                            bank_question_id=q.get("bank_id"),
                            source_type="exam",
                            question_snapshot=q,
                            user_answer=user_ans,
                        )
                        saved_wrong[i] = True
                    except Exception as e:
                        saved_wrong[i] = False
                        save_err = save_err or str(e)
                    # 문장 복습 스케줄 자동 등록
                    try:
                        from study_review import auto_schedule_sentence
                        passage = q.get("passage", "").strip()
                        if passage and len(passage) > 5:
                            note_sents = exam_state.get("sentences", [])
                            kr_text = ""
                            for en_s, kr_s in note_sents:
                                if en_s.strip() and (
                                    en_s.strip() in passage or
                                    passage[:40].strip() in en_s
                                ):
                                    kr_text = kr_s
                                    break
                            sent_idx = abs(hash(passage[:50])) % 1000000
                            auto_schedule_sentence(
                                student_id, note_id, sent_idx, passage, kr_text
                            )
                    except Exception:
                        pass
        exam_state["wrong_saved"] = saved_wrong
        exam_state["save_err"]    = save_err
        exam_state["result_saved"] = True

    # 점수 표시
    if pct >= 90:   result_icon, msg, bg = icon("award",     52, "#16a34a"), "최우수! 만점에 가깝습니다!", "#f0fdf4"
    elif pct >= 70: result_icon, msg, bg = icon("star",      52, "#ca8a04"), "우수! 훌륭해요!",           "#fffbeb"
    elif pct >= 50: result_icon, msg, bg = icon("zap",       52, "#ea580c"), "보통. 오답을 다시 확인해 봐요.", "#fff7ed"
    else:           result_icon, msg, bg = icon("book-open", 52, "#dc2626"), "아직 공부가 필요해요. 파이팅!", "#fef2f2"

    st.markdown(f"""
<div style="background:{bg};border-radius:16px;padding:24px;text-align:center;
     margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
  <div style="display:flex;justify-content:center;margin-bottom:6px;">{result_icon}</div>
  <div style="font-size:2rem;font-weight:800;color:#818CF8;margin:8px 0;">
    {score} / {total} ({pct}점)
  </div>
  <div style="color:#6b7280;font-size:0.95rem;">{msg}</div>
</div>
""", unsafe_allow_html=True)

    # 문항별 채점 결과
    st.markdown(section_md("list", "문항별 결과"), unsafe_allow_html=True)
    for i, q in enumerate(questions):
        user_ans = answers.get(i, "")
        correct  = q.get("answer", "").strip()
        q_type   = q.get("type", "")

        is_ok    = (q_type == "서술형") or is_answer_correct(
            user_ans, q.get("answer", ""), q.get("options"))
        color    = "#16a34a" if is_ok else "#dc2626"
        bg_c     = "#f0fdf4" if is_ok else "#fef2f2"
        mark     = "정답" if is_ok else "오답"

        with st.expander(f"[{mark}] 문제 {i+1}. {q_type}", expanded=not is_ok):
            if q.get("passage"):
                passage_html = _format_passage(q["passage"])
                st.markdown(
                    f'<div style="background:#F8FAFF;border-radius:8px;padding:12px 16px;'
                    f'font-size:1rem;color:#1f2937;margin-bottom:8px;'
                    f'border:1.5px solid #C7D2FE;line-height:1.8;">{passage_html}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(f'<div style="font-size:1rem;font-weight:600;line-height:1.7;">{q.get("question","").replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
            st.markdown(f"""
<div style="background:{bg_c};border-radius:8px;padding:10px;margin-top:6px;">
  <b style="color:{color};">내 답: {user_ans or "(미답)"}</b>
  {f'<br><b style="color:#16a34a;">정답: {correct}</b>' if not is_ok else ''}
  {f'<br><span style="color:#6b7280;font-size:0.82rem;">{q.get("answer_kr","")}</span>' if q.get("answer_kr") else ''}
</div>
""", unsafe_allow_html=True)

            # AI 해설 버튼 + 자동 오답노트 안내 (오답일 때)
            if not is_ok and q_type != "서술형":
                # AI 해설 — 세션에 저장해 버튼/리런 후에도 유지
                _ex_key = f"exam_explain_{note_id}_{i}"
                if api_config and st.button("AI 해설 보기",
                                             key=f"res_explain_{i}",
                                             use_container_width=True):
                    with st.spinner("이 오답, 왜 틀렸는지 낱낱이 파헤치는 중…"):
                        st.session_state[_ex_key] = explain_wrong_answer(q, user_ans, api_config)
                if st.session_state.get(_ex_key):
                    st.info(st.session_state[_ex_key])

                # 오답노트 저장 — 실제 결과를 정직하게 표시
                _ws = exam_state.get("wrong_saved", {})
                if not student_id:
                    st.caption("로그인하면 이 오답이 오답노트에 자동 저장돼요.")
                elif _ws.get(i):
                    st.markdown(
                        f'<div style="font-size:0.78rem;color:#059669;margin:4px 0;'
                        f'display:flex;align-items:center;gap:5px;">'
                        f'{icon("check-circle",13,"#059669")} 오답노트에 자동 저장됐어요</div>',
                        unsafe_allow_html=True,
                    )
                elif _ws.get(i) is False:
                    st.caption("⚠️ 오답노트 저장에 실패했어요. 잠시 후 다시 시도해 주세요.")

    col1, col2 = st.columns(2)
    if col1.button("다시 풀기", use_container_width=True):
        # 새 문제 생성 (동일 설정)
        del st.session_state["exam_state"]
        st.rerun()
    if col2.button("내신문제 홈", use_container_width=True):
        del st.session_state["exam_state"]
        st.rerun()
