# study_cheatsheet.py — 시험 직전 A4 요약노트 생성
# A.R. 담당 | 글자 8pt, 여백 최소화, 앞/뒷면 양면 인쇄용

from __future__ import annotations
import datetime
import streamlit as st
import streamlit.components.v1 as components
from icons import icon, section_md


# ─────────────────────────────────────────────────────────────────────────────
# HTML 렌더러
# ─────────────────────────────────────────────────────────────────────────────

def _build_sections_body(data: dict, blank_mode: str = "none",
                         sections: list | None = None) -> str:
    """한 단원의 요약 데이터(front/back) → 섹션 HTML(body) 문자열.
    단원 묶기 시 단원별로 이 함수를 호출해 각각의 본문을 만든다.
    """
    front = data.get("front", {})
    back  = data.get("back",  {})
    words        = front.get("words",       []) or data.get("words", [])
    grammar      = front.get("grammar",     []) or data.get("grammar", [])
    sentences    = back.get("sentences",    []) or data.get("sentences", [])
    patterns     = back.get("patterns",     []) or data.get("patterns", [])
    secret_tips  = back.get("secret_tips",  []) or data.get("secret_tips", [])
    exam_keys    = back.get("exam_keys",    []) or data.get("exam_keys", [])
    dlg_summ     = back.get("dialogue_summaries", []) or data.get("dialogue_summaries", [])

    # ── 선택 섹션 게이트 (AI 환각 방지 — 사용자가 끈 섹션은 강제 제외) ──
    if sections is not None:
        _sec = set(sections)
        if "단어"     not in _sec:                       words       = []
        if "문법"     not in _sec:                       grammar     = []
        if "대화문"   not in _sec:                       dlg_summ    = []
        if not ({"대화문", "본문"} & _sec):              sentences   = []
        if not ({"대화문", "본문", "문법"} & _sec):      patterns    = []
        if "비법노트" not in _sec:                       secret_tips = []
        if "기출문제" not in _sec:                       exam_keys   = []

    # ── 빈칸(셀프테스트) 처리 헬퍼 ──────────────────
    def _blank(text: str, hide: bool) -> str:
        if hide and text and text.strip():
            return '<span class="blk"></span>'
        return text

    body = ""

    # ── 단어 영영풀이 (시험에 영영풀이→단어 매칭 출제 대비) ─────
    if words:
        rows = ""
        for i, w in enumerate(words):
            en     = w.get("en", "")
            def_en = w.get("def_en", "") or w.get("definition", "")
            kr     = w.get("kr", "")
            bg = ' style="background:#f5f5f5;"' if i % 2 == 0 else ""
            # 영영풀이는 항상 보이는 '단서' → 빈칸 모드에서도 가리지 않음.
            #   en(단어) 가림 = 영영풀이 보고 단어 떠올리기(실제 시험 유형)
            #   kr 가림      = 단어·영영 보고 뜻 떠올리기
            en_h = _blank(en, blank_mode == "en")
            kr_h = _blank(kr, blank_mode == "kr")
            def_sp = f'<div class="w-def">{def_en}</div>' if def_en else ""
            rows += (f'<div class="word-row"{bg}>'
                     f'<div class="w-head"><span class="w-en">{en_h}</span>'
                     f'<span class="w-kr">{kr_h}</span></div>'
                     f'{def_sp}</div>\n')
        body += (f'<div class="section"><div class="sec-title sc-w">단어 영영풀이 ({len(words)})</div>'
                 f'<div class="word-grid">{rows}</div></div>')

    # ── 문법 ──────────────────────────────────────
    if grammar:
        g_items = ""
        for g in grammar:
            note    = g.get("note", "")
            note_sp = f'<div class="g-note">! {note}</div>' if note else ""
            g_items += (f'<div class="g-item"><div class="g-rule">▸ {g.get("rule","")}</div>'
                        f'<div class="g-ex">{g.get("example","")}</div>{note_sp}</div>')
        body += (f'<div class="section"><div class="sec-title sc-g">문법 포인트 ({len(grammar)})</div>'
                 f'{g_items}</div>')

    # ── 대화문 요약 (시험 직전 상황 상기) ──────────
    if dlg_summ:
        d_items = "".join(
            f'<div class="ds-item"><span class="ds-title">▸ {d.get("title","")}</span> '
            f'{d.get("summary","")}</div>' for d in dlg_summ
        )
        body += (f'<div class="section"><div class="sec-title sc-d">대화문 요약 ({len(dlg_summ)})</div>'
                 f'{d_items}</div>')

    # ── 핵심 문장 ──────────────────────────────────
    if sentences:
        s_rows = ""
        for i, s in enumerate(sentences):
            bg = ' style="background:#f5f5f5;"' if i % 2 == 0 else ""
            en_h = _blank(s.get("en",""), blank_mode == "en")
            kr_h = _blank(s.get("kr",""), blank_mode == "kr")
            s_rows += (f'<div class="sent-row"{bg}><div class="s-en">{en_h}</div>'
                       f'<div class="s-kr">{kr_h}</div></div>')
        body += (f'<div class="section"><div class="sec-title sc-s">핵심 문장 ({len(sentences)})</div>'
                 f'{s_rows}</div>')

    # ── 핵심 패턴 ──────────────────────────────────
    if patterns:
        p_items = ""
        for p in patterns:
            ex = p.get("ex", "")
            ex_span = f' → <em>{ex}</em>' if ex else ""
            p_items += (f'<div class="p-item"><span class="p-pat">{p.get("pattern","")}</span> '
                        f'<span class="p-mng">{p.get("meaning","")}{ex_span}</span></div>')
        body += (f'<div class="section"><div class="sec-title sc-p">핵심 패턴 ({len(patterns)})</div>'
                 f'{p_items}</div>')

    # ── 비법노트 ──────────────────────────────────
    if secret_tips:
        t_items = "".join(
            f'<div class="tip-item"><span class="tip-title">【{t.get("title","")}】</span> '
            f'{t.get("content","")}</div>' for t in secret_tips
        )
        body += (f'<div class="section"><div class="sec-title sc-t">비법노트 요약 ({len(secret_tips)})</div>'
                 f'{t_items}</div>')

    # ── 기출 포인트 ────────────────────────────────
    if exam_keys:
        e_items = "".join(
            f'<div class="e-item"><span class="e-type">[{e.get("type","")}]</span> '
            f'{e.get("content","")}</div>' for e in exam_keys
        )
        body += (f'<div class="section"><div class="sec-title sc-e">기출 핵심 포인트 ({len(exam_keys)})</div>'
                 f'{e_items}</div>')

    if not body:
        body = '<p style="color:#999;font-size:7pt;">선택된 섹션의 내용이 없습니다.</p>'
    return body


def _render_cheatsheet_html(note_title: str, data: dict, date_str: str,
                            blank_mode: str = "none",
                            sections: list | None = None) -> str:
    """JSON 데이터 → 인쇄용 A4 HTML.

    - 단일 단원: data = {"front":..,"back":..} → 한 흐름으로 배치
    - 두 단원 묶기: data = {"units":[{"title":..,"front":..,"back":..}, ...]}
      → 단원별 헤더(📘 단원1 · 제목)로 구분해 각각의 흐름으로 렌더
    - blank_mode: 'none'(모두 보기) | 'en'(영어 가림) | 'kr'(한글 가림)
    """
    units = data.get("units") if isinstance(data, dict) else None
    if units:
        _badges = ["📘", "📗", "📙", "📕"]
        inner = ""
        for i, u in enumerate(units):
            _ut   = u.get("title", "") or f"단원 {i+1}"
            _body = _build_sections_body(u, blank_mode, sections)
            inner += (f'<div class="unit-block">'
                      f'<div class="unit-head">{_badges[i % len(_badges)]} 단원 {i+1} · {_ut}</div>'
                      f'<div class="flow">{_body}</div></div>')
    else:
        inner = f'<div class="flow">{_build_sections_body(data, blank_mode, sections)}</div>'

    blank_badge = ""
    if blank_mode == "en":
        blank_badge = '<span class="bmode">빈칸: 영어</span>'
    elif blank_mode == "kr":
        blank_badge = '<span class="bmode">빈칸: 한글</span>'

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{note_title} — 시험 요약노트</title>
<style>
@page {{ size: A4 portrait; margin: 5mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0;
     -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{
  font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', Arial, sans-serif;
  font-size: 8pt; line-height: 1.32; color: #111; background: white;
}}
/* 단일 시트 — 한 단원 한 바닥, 내용 넘치면 자동 다음 장 */
.sheet {{ width: 200mm; }}
.sheet-header {{
  display: flex; justify-content: space-between; align-items: center;
  border: 1pt solid #111; padding: 1.5mm 3mm; margin-bottom: 2.5mm;
}}
.sheet-header .title {{ font-size: 9pt; font-weight: 900; color: #111; }}
.sheet-header .meta  {{ font-size: 6.5pt; color: #444; }}
.bmode {{ border: 0.6pt solid #111; border-radius: 2px; padding: 0 1.5mm;
          font-size: 6pt; font-weight: 700; margin-left: 2mm; }}

/* 본문 2단 자동 흐름 (넘치면 다음 단/다음 장) */
.flow {{ column-count: 2; column-gap: 5mm; column-rule: 0.4pt solid #d1d5db; }}
.section {{ break-inside: avoid; margin-bottom: 2.2mm; }}

/* 단원 묶기 — 단원별 구분 블록 */
.unit-block {{ margin-bottom: 3mm; }}
.unit-block + .unit-block {{ border-top: 1.2pt dashed #94a3b8; padding-top: 2mm; }}
.unit-head {{
  font-size: 9pt; font-weight: 900; color: #0f172a;
  background: linear-gradient(90deg,#e0e7ff,#f1f5f9);
  border-left: 3pt solid #4F46E5; padding: 1mm 2.5mm; margin-bottom: 1.5mm;
  border-radius: 2px;
}}
@media print {{ .unit-head {{ background: #eef2ff !important; }} }}

/* 섹션 헤더 — 화면은 컬러, 인쇄(흑백)는 테두리로 구분 */
.sec-title {{
  color: white; font-size: 7.5pt; font-weight: 900;
  padding: 0.8mm 2mm; margin-bottom: 1mm; letter-spacing: 0.02em;
}}
.sc-w {{ background:#4F46E5; }} .sc-g {{ background:#7C3AED; }}
.sc-s {{ background:#0891B2; }} .sc-p {{ background:#059669; }}
.sc-t {{ background:#D97706; }} .sc-e {{ background:#DC2626; }}
.sc-d {{ background:#0e7490; }}

.ds-item {{ padding: 0.5mm 1.5mm; border-left: 1.5pt solid #0e7490; margin-bottom: 1mm; break-inside: avoid; font-size: 7pt; color: #374151; }}
.ds-title {{ font-weight: 700; color: #155e75; }}

.word-grid {{ column-count: 2; column-gap: 4mm; }}
.word-row {{ padding: 0.6mm 1.5mm; margin-bottom: 0.8mm; break-inside: avoid;
             border-left: 1.5pt solid #4F46E5; }}
.w-head {{ display: flex; gap: 1.5mm; align-items: baseline; }}
.w-en {{ font-weight: 800; color: #1d4ed8; font-size: 7.5pt; }}
.w-kr {{ color: #374151; font-size: 7pt; }}
.w-def {{ color: #4b5563; font-size: 7pt; margin-top: 0.2mm; line-height: 1.25; }}
.w-def::before {{ content: "def. "; color: #6366f1; font-weight: 700; font-size: 6pt; }}

.g-item {{ padding: 0.5mm 1.5mm; border-left: 1.5pt solid #7C3AED; margin-bottom: 1.4mm; break-inside: avoid; }}
.g-rule {{ font-weight: 700; color: #5b21b6; font-size: 7.5pt; }}
.g-ex   {{ color: #374151; font-size: 7pt; margin-top: 0.3mm; }}
.g-note {{ color: #dc2626; font-size: 6.5pt; margin-top: 0.3mm; }}

.sent-row {{ padding: 0.5mm 1.5mm; margin-bottom: 0.4mm; break-inside: avoid; }}
.s-en {{ font-weight: 600; color: #0c4a6e; font-size: 7.5pt; }}
.s-kr {{ color: #4b5563; font-size: 7pt; margin-top: 0.2mm; }}

.p-item {{ padding: 0.4mm 1.5mm; border-left: 1.5pt solid #059669; margin-bottom: 1mm; break-inside: avoid; }}
.p-pat {{ font-weight: 700; color: #065f46; font-size: 7.5pt; }}
.p-mng {{ color: #374151; font-size: 7pt; }}

.tip-item {{ padding: 0.4mm 1.5mm; border-left: 1.5pt solid #d97706; margin-bottom: 1mm; break-inside: avoid; font-size: 7pt; color: #374151; }}
.tip-title {{ font-weight: 700; color: #92400e; }}

.e-item {{ padding: 0.4mm 1.5mm; border-left: 1.5pt solid #dc2626; margin-bottom: 1mm; break-inside: avoid; font-size: 7pt; color: #374151; }}
.e-type {{ font-weight: 700; color: #991b1b; }}

/* 빈칸(셀프테스트) — 가린 칸 */
.blk {{ display: inline-block; min-width: 14mm; border-bottom: 0.8pt solid #111; }}

.sheet-footer {{
  margin-top: 2.5mm; border-top: 0.4pt solid #888; padding-top: 1mm;
  text-align: center; font-size: 6.5pt; color: #666;
}}

@media screen {{
  body {{ background: #f1f5f9; }}
  .sheet {{ background: white; box-shadow: 0 2px 12px rgba(0,0,0,.15);
            margin: 0 auto; padding: 5mm; max-width: 210mm; }}
}}
/* 흑백 인쇄 대응 — 섹션 헤더를 흰배경+검정테두리로 (색 안 뭉개짐) */
@media print {{
  .sec-title {{ background: white !important; color: #111 !important;
                border: 0.8pt solid #111; border-left-width: 2.5pt; }}
}}
</style>
</head>
<body>
<div class="sheet">
  <div class="sheet-header">
    <span class="title">{note_title} — 시험 요약 {blank_badge}</span>
    <span class="meta">반반 BanBan · {date_str}</span>
  </div>
  {inner}
  <div class="sheet-footer">반반 BanBan · 영어학습 파트너 · 시험 직전 요약노트</div>
</div>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# 단원 묶기 헬퍼 (시험은 보통 두 단원 출제 → 1~2단원 병합 지원)
# ─────────────────────────────────────────────────────────────────────────────

def _load_cheat_bundle(note_id) -> dict | None:
    """단원 1개의 요약노트 재료(단어·대화·본문·문법·비법·기출) 일괄 로드."""
    from library import get_note
    from study_db import get_grammar_points, list_secret_notes, list_past_problems
    note = get_note(note_id)
    if not note:
        return None
    return {
        "id":          note_id,
        "note":        note,
        "words":       note.get("words", []),
        "dialogues":   note.get("dialogues", []),
        "text_data":   note.get("text_data", {}),
        "grammar_pts": get_grammar_points(note_id),
        "secret_nts":  list_secret_notes(note_id),
        "past_probs":  list_past_problems(note_id),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_cheatsheet(student_id, student_name: str, api_cfg: dict, notes: list):
    """시험 직전 요약노트 — 새로 만들기 / 저장된 요약노트 탭."""
    section_md("시험 직전 요약노트", icon("file-text"))
    st.caption("선택한 섹션만 · 한 단원 한 장 · 여백 5mm · 인쇄용 PDF로 변환 가능")

    if not notes:
        st.info("먼저 반반노트 라이브러리에 노트를 추가해주세요.")
        return

    tab_new, tab_saved = st.tabs(["✨ 새로 만들기", "📚 저장된 요약노트"])
    with tab_new:
        _cheatsheet_new(student_id, student_name, api_cfg, notes)
    with tab_saved:
        _cheatsheet_saved(notes)


def _cheatsheet_new(student_id, student_name: str, api_cfg: dict, notes: list):
    """요약노트 새로 만들기 (생성 시 자동 저장)."""

    # ── 교과서 · 단원 선택 (계단식: 학년 → 출판사 → 단원) ──────────
    st.markdown("#### 📂 교과서 · 단원 선택")
    import auth as _auth_cs
    _role   = _auth_cs.current_role()
    _sgrade = _auth_cs.current_grade() if _role == "student" else ""
    _GORDER = ["중1", "중2", "중3", "고1", "고2", "고3"]
    _grades = sorted({n.get("grade", "") for n in notes if n.get("grade")},
                     key=lambda g: _GORDER.index(g) if g in _GORDER else 99)

    cc1, cc2, cc3 = st.columns(3)
    if _sgrade and _sgrade in _grades:
        _sg = _sgrade                                  # 학생은 내 학년 자동
        cc1.caption(f"학년 · {_sgrade}")
    elif _grades:
        _sg = cc1.selectbox("학년", ["전체"] + _grades, key="cs_grade")
    else:
        _sg = "전체"
    _p1 = [n for n in notes if _sg == "전체" or n.get("grade") == _sg]

    _pubs = sorted({n.get("publisher", "") for n in _p1 if n.get("publisher")})
    _sp = (cc2.selectbox("출판사", ["전체"] + _pubs, key="cs_pub") if _pubs else "전체")
    _p2 = [n for n in _p1 if _sp == "전체" or n.get("publisher") == _sp]

    if not _p2:
        st.info("해당 조건의 교과서가 없어요. 위 단계를 바꿔보세요.")
        return
    _ids = [n["id"] for n in _p2]
    def _fu_cs(i):
        _n = next((x for x in _p2 if x["id"] == i), {})
        return f"{_n.get('title','')} [{_n.get('content_type','')}]"
    selected_id = cc3.selectbox("단원 1", _ids, format_func=_fu_cs, key="cs_note_id")

    if not selected_id:
        return

    # ── 두 번째 단원(선택) — 시험은 보통 두 단원을 묶어 출제 ──────
    _ids2 = [i for i in _ids if i != selected_id]
    second_id = None
    if _ids2:
        _sel2 = cc3.selectbox(
            "단원 2 (선택 · 두 단원 묶기)",
            ["(없음)"] + _ids2,
            format_func=lambda i: "(없음)" if i == "(없음)" else _fu_cs(i),
            key="cs_note_id2",
        )
        second_id = None if _sel2 == "(없음)" else _sel2

    selected_ids = [selected_id] + ([second_id] if second_id else [])

    # ── 노트 데이터 로드 (1~2단원) ───────────────────────
    bundles = []
    for _nid in selected_ids:
        _b = _load_cheat_bundle(_nid)
        if _b:
            bundles.append(_b)
    if not bundles:
        st.error("노트를 불러올 수 없습니다.")
        return

    combined_title = " + ".join(b["note"].get("title", "") for b in bundles)

    # ── 포함할 섹션 선택 (두 단원의 합집합) ──────────────────────
    st.markdown("#### ⚙️ 포함할 섹션 선택")

    _sec_order = ["단어", "대화문", "본문", "문법", "비법노트", "기출문제"]
    _avail = set()
    for b in bundles:
        if b["words"]:                                          _avail.add("단어")
        if b["dialogues"]:                                      _avail.add("대화문")
        if b["text_data"] and b["text_data"].get("sentences"):  _avail.add("본문")
        if b["grammar_pts"]:                                    _avail.add("문법")
        if b["secret_nts"]:                                     _avail.add("비법노트")
        if b["past_probs"]:                                     _avail.add("기출문제")
    avail_sections = [s for s in _sec_order if s in _avail]

    if not avail_sections:
        st.warning("선택한 단원에 포함할 수 있는 데이터가 없습니다. 먼저 노트 내용을 추가해주세요.")
        return

    if len(bundles) == 2:
        st.success(f"📎 두 단원 묶기: **{combined_title}** — 단어 영영풀이는 단원당 15개씩, "
                   f"한 장(넘치면 자동 다음 장)으로 정리돼요.")

    col_checks = st.columns(len(avail_sections))
    chosen_sections = []
    for i, sec in enumerate(avail_sections):
        with col_checks[i]:
            sec_icons = {
                "단어": "📚", "대화문": "💬", "본문": "📄",
                "문법": "📝", "비법노트": "💡", "기출문제": "📌"
            }
            if st.checkbox(f"{sec_icons.get(sec,'')} {sec}", value=True, key=f"cs_sec_{sec}"):
                chosen_sections.append(sec)

    if not chosen_sections:
        st.warning("최소 1개 이상의 섹션을 선택해주세요.")
        return

    # ── 데이터 미리보기 (두 단원 합계) ────────────────────────
    with st.expander("📊 포함 데이터 현황", expanded=False):
        _tw   = sum(len(b["words"]) for b in bundles)
        _tg   = sum(len(b["grammar_pts"]) for b in bundles)
        _tdl  = sum(len(d.get("lines", [])) for b in bundles for d in b["dialogues"])
        _ts   = sum(len(b["secret_nts"]) for b in bundles)
        _tsent= sum(len(b["text_data"].get("sentences", [])) if b["text_data"] else 0
                    for b in bundles)
        _tp   = sum(len(b["past_probs"]) for b in bundles)
        cols = st.columns(3)
        with cols[0]:
            st.metric("단어", f"{_tw}개")
            st.metric("문법 포인트", f"{_tg}개")
        with cols[1]:
            st.metric("대화문 줄", f"{_tdl}줄")
            st.metric("비법노트", f"{_ts}개")
        with cols[2]:
            st.metric("본문 문장", f"{_tsent}개")
            st.metric("기출 세트", f"{_tp}개")

    st.divider()

    # ── 출력 모드 (빈칸/셀프테스트 — 기본: 모두 보기) ──
    _bm_label = st.radio(
        "출력 모드",
        ["📖 모두 보기", "✏️ 영어 가림 (셀프테스트)", "✏️ 한글 가림"],
        horizontal=True, key="cs_blank_mode",
        help="시험 직전엔 '모두 보기', 셀프테스트는 가림 모드로. (가림은 출력물에 빈칸으로)",
    )
    blank_mode = {"📖 모두 보기": "none",
                  "✏️ 영어 가림 (셀프테스트)": "en",
                  "✏️ 한글 가림": "kr"}.get(_bm_label, "none")

    # ── 캐시 키 (AI 생성 데이터만 캐시 — 모드는 즉시 재렌더) ──
    data_key = (f"_cs_data_{'_'.join(str(i) for i in selected_ids)}"
                f"_{'_'.join(sorted(chosen_sections))}")

    # ── 생성 버튼 ──────────────────────────────
    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        gen_btn = st.button(
            "🤖 AI 요약노트 생성",
            type="primary",
            use_container_width=True,
            key="cs_gen_btn",
        )
    with col_btn2:
        if st.button("🔄 재생성", use_container_width=True, key="cs_regen_btn"):
            st.session_state.pop(data_key, None)
            st.rerun()

    if gen_btn or data_key in st.session_state:
        if data_key not in st.session_state:
            # AI 사용량 게이팅 (무료 월 N회 / 유료 무제한)
            from plans import can_use_ai, increment_ai_usage, upgrade_banner, ai_usage_bar
            _aiok, _, _ = can_use_ai()
            ai_usage_bar()
            if not _aiok:
                upgrade_banner("student", compact=True)
                st.stop()
            _spin = ("두 단원을 분석해 한 장으로 묶는 중입니다... (단원당 30~60초)"
                     if len(bundles) == 2
                     else "핵심 내용을 분석하고 요약노트를 만들고 있습니다... (30~60초)")
            with st.spinner(_spin):
                try:
                    from study_ai import generate_cheatsheet_data
                    # 단원별로 생성(단어 영영풀이 15개씩 보존) → 한 장으로 병합
                    _parts = []
                    for b in bundles:
                        increment_ai_usage()
                        _parts.append(generate_cheatsheet_data(
                            note_title    = b["note"].get("title", ""),
                            words         = b["words"],
                            dialogues     = b["dialogues"],
                            text_data     = b["text_data"] or {},
                            grammar_points= b["grammar_pts"],
                            secret_notes  = b["secret_nts"],
                            past_problems = b["past_probs"],
                            sections      = chosen_sections,
                            api_config    = api_cfg,
                        ))
                    # 단원이 2개면 단원별 구분 구조로, 1개면 기존 단일 구조로 저장/렌더
                    if len(bundles) >= 2:
                        data = {"units": [
                            {"title": b["note"].get("title", "") or f"단원 {i+1}", **part}
                            for i, (b, part) in enumerate(zip(bundles, _parts))
                        ]}
                    else:
                        data = _parts[0]
                    st.session_state[data_key] = data
                    # ── 자동 저장 (생성 직후 1회) ──────────────
                    try:
                        from study_db import save_cheatsheet
                        import auth as _a
                        _u = _a.current_user()
                        save_cheatsheet(selected_id, combined_title, data,
                                        chosen_sections,
                                        owner_id=_u.id if _u else None)
                        st.session_state[f"{data_key}_saved"] = True
                    except Exception as _se:
                        # 자동 저장 실패는 조용히 넘기지 않고 알림 (원인 진단)
                        _msg = str(_se)
                        if "cheatsheets" in _msg or "does not exist" in _msg or "42P01" in _msg:
                            st.warning("⚠️ 자동 저장 실패 — Supabase에서 "
                                       "`supabase_migration_v14.sql`(cheatsheets 테이블)을 "
                                       "먼저 실행해주세요.")
                        else:
                            st.warning(f"⚠️ 자동 저장 실패: {_msg}")
                except Exception as e:
                    st.error(f"요약노트 생성 실패: {e}")
                    return

        data = st.session_state.get(data_key)
        if not data:
            return
        # 모드 반영해 매번 렌더 (AI 재호출 없음)
        date_str = datetime.date.today().strftime("%Y년 %m월 %d일")
        html = _render_cheatsheet_html(
            note_title = combined_title,
            data       = data,
            date_str   = date_str,
            blank_mode = blank_mode,
            sections   = chosen_sections,
        )

        # ── 다운로드 / 인쇄 버튼 ──────────────
        st.success("✅ 요약노트 생성 완료! 💾 「저장된 요약노트」 탭에 자동 저장됐어요.")

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            note_title_safe = (combined_title or "요약노트").replace(" ","_").replace("+","와")
            st.download_button(
                label="⬇️ HTML 다운로드 (→ 브라우저 인쇄로 PDF 변환)",
                data=html.encode("utf-8"),
                file_name=f"{note_title_safe}_시험요약노트.html",
                mime="text/html",
                use_container_width=True,
                type="primary",
            )
        with dl_col2:
            # 인쇄 버튼 (JS window.print 트리거)
            st.info("💡 HTML 다운로드 후 브라우저에서 열고 **Ctrl+P** (Mac: ⌘P) 를 누르면 PDF로 저장할 수 있습니다.")

        # ── 인쇄 방법 안내 ──────────────────────
        with st.expander("🖨️ 인쇄 방법 안내", expanded=False):
            st.markdown("""
**양면 인쇄 방법:**
1. 위 **HTML 다운로드** 버튼 클릭
2. 다운로드된 `.html` 파일을 브라우저(Chrome/Edge)로 열기
3. **Ctrl+P** (Mac: ⌘P) 를 눌러 인쇄 대화상자 열기
4. **대상**: PDF로 저장 또는 프린터 선택
5. **용지 크기**: A4
6. **여백**: 없음 (None) 또는 최소
7. **양면 인쇄**: 긴 쪽으로 뒤집기 (Flip on long edge) 선택
8. 인쇄 또는 저장

**PDF → 양면 출력 팁:**
- Chrome: '추가 설정' → '양면 인쇄' 체크
- Edge: '기타 설정' → '양면 인쇄' 체크
- macOS: 인쇄 대화상자 하단 '양면' 체크박스
""")

        # ── 미리보기 (단일 시트) ────────────────
        st.markdown("#### 👁️ 미리보기 (실제 인쇄 결과와 다를 수 있어요)")
        components.html(html, height=820, scrolling=True)


# ─────────────────────────────────────────────────────────────────────────────
# 저장된 요약노트 탭 — 탐색 / 보기 / 삭제
# ─────────────────────────────────────────────────────────────────────────────

def _cheatsheet_saved(notes: list):
    """저장된 요약노트 — 교과서별 탐색 + 보기/삭제."""
    from study_db import list_cheatsheets, delete_cheatsheet

    try:
        all_cs = list_cheatsheets()
    except Exception as e:
        st.error(f"저장된 요약노트 조회 오류: {e}")
        return

    if not all_cs:
        st.markdown(
            '<div style="text-align:center;padding:36px 20px;background:#F8FAFB;'
            'border:1px dashed #CBD5E1;border-radius:14px;color:#94A3B8;">'
            '아직 저장된 요약노트가 없어요.<br>'
            '<span style="font-size:0.85rem;">「새로 만들기」 탭에서 생성하면 자동 저장돼요.</span>'
            '</div>', unsafe_allow_html=True,
        )
        return

    # ── 탐색 필터: 교과서(노트) ─────────────────────────────
    note_titles = {n["id"]: n.get("title", "(제목없음)") for n in notes}
    avail_note_ids = sorted({c.get("note_id") for c in all_cs if c.get("note_id")},
                            key=lambda i: note_titles.get(i, ""))
    opts = ["전체"] + avail_note_ids
    f_note = st.selectbox(
        "교과서로 찾기", opts,
        format_func=lambda x: "전체 보기" if x == "전체" else note_titles.get(x, f"노트 #{x}"),
        key="cs_saved_filter",
    )
    cs_list = [c for c in all_cs if f_note == "전체" or c.get("note_id") == f_note]
    st.caption(f"{len(cs_list)}개 / 전체 {len(all_cs)}개")

    # ── 보기 모드 (저장본도 빈칸 모드 선택) ──────────────────
    _bm = st.radio("출력 모드", ["📖 모두 보기", "✏️ 영어 가림", "✏️ 한글 가림"],
                   horizontal=True, key="cs_saved_blank")
    blank_mode = {"📖 모두 보기": "none", "✏️ 영어 가림": "en",
                  "✏️ 한글 가림": "kr"}.get(_bm, "none")

    for c in cs_list:
        cs_id    = c["id"]
        title    = c.get("note_title", "요약노트")
        secs     = c.get("sections", []) or []
        sec_str  = ", ".join(secs) if isinstance(secs, list) else ""
        created  = c.get("created_at", "")[:16]

        with st.expander(f"📝 {title} — {created}  ·  [{sec_str}]"):
            html = _render_cheatsheet_html(
                note_title = title,
                data       = c.get("data", {}) or {},
                date_str   = created,
                blank_mode = blank_mode,
                sections   = secs if isinstance(secs, list) and secs else None,
            )
            components.html(html, height=560, scrolling=True)

            dc1, dc2 = st.columns([3, 1])
            _safe = title.replace(" ", "_")
            dc1.download_button(
                "⬇️ HTML 다운로드 (→ 인쇄/PDF)",
                data=html.encode("utf-8"),
                file_name=f"{_safe}_시험요약노트.html",
                mime="text/html", use_container_width=True,
                key=f"cs_dl_{cs_id}",
            )
            if dc2.button("🗑️ 삭제", key=f"cs_del_{cs_id}", use_container_width=True):
                delete_cheatsheet(cs_id)
                st.rerun()

