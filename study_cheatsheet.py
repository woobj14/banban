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

def _render_cheatsheet_html(note_title: str, data: dict, date_str: str) -> str:
    """JSON 데이터 → 인쇄용 A4 HTML (앞면 + 뒷면)."""

    front = data.get("front", {})
    back  = data.get("back",  {})

    words        = front.get("words",        [])
    grammar      = front.get("grammar",      [])
    sentences    = back.get("sentences",     [])
    patterns     = back.get("patterns",      [])
    secret_tips  = back.get("secret_tips",   [])
    exam_keys    = back.get("exam_keys",     [])

    # ── 앞면 콘텐츠 HTML ────────────────────────────
    front_html = ""

    if words:
        rows = ""
        for i, w in enumerate(words):
            en  = w.get("en", "")
            kr  = w.get("kr", "")
            tip = w.get("tip", "")
            tip_span = f'<span class="tip"> ★{tip}</span>' if tip else ""
            bg = ' style="background:#f8f7ff;"' if i % 2 == 0 else ""
            rows += f'<div class="word-row"{bg}><span class="w-en">{en}</span><span class="w-kr">{kr}{tip_span}</span></div>\n'
        front_html += f"""
<div class="section">
  <div class="sec-title" style="background:#4F46E5;">📚 핵심 단어 ({len(words)}개)</div>
  <div class="word-grid">{rows}</div>
</div>"""

    if grammar:
        g_items = ""
        for g in grammar:
            rule    = g.get("rule",    "")
            example = g.get("example", "")
            note    = g.get("note",    "")
            note_sp = f'<div class="g-note">⚡ {note}</div>' if note else ""
            g_items += f"""
<div class="g-item">
  <div class="g-rule">▸ {rule}</div>
  <div class="g-ex">{example}</div>
  {note_sp}
</div>"""
        front_html += f"""
<div class="section">
  <div class="sec-title" style="background:#7C3AED;">📝 문법 포인트 ({len(grammar)}개)</div>
  {g_items}
</div>"""

    # ── 뒷면 콘텐츠 HTML ────────────────────────────
    back_html = ""

    if sentences:
        s_rows = ""
        for i, s in enumerate(sentences):
            bg = ' style="background:#f0fdf4;"' if i % 2 == 0 else ""
            s_rows += (
                f'<div class="sent-row"{bg}>'
                f'<div class="s-en">{s.get("en","")}</div>'
                f'<div class="s-kr">{s.get("kr","")}</div>'
                f'</div>\n'
            )
        back_html += f"""
<div class="section">
  <div class="sec-title" style="background:#0891B2;">💬 핵심 문장 ({len(sentences)}개)</div>
  {s_rows}
</div>"""

    if patterns:
        p_items = ""
        for p in patterns:
            pat = p.get("pattern", "")
            mng = p.get("meaning", "")
            ex  = p.get("ex", "")
            ex_span = f' → <em>{ex}</em>' if ex else ""
            p_items += f'<div class="p-item"><span class="p-pat">{pat}</span> <span class="p-mng">{mng}{ex_span}</span></div>\n'
        back_html += f"""
<div class="section">
  <div class="sec-title" style="background:#059669;">🔑 핵심 패턴 ({len(patterns)}개)</div>
  {p_items}
</div>"""

    if secret_tips:
        st_items = ""
        for t in secret_tips:
            st_items += (
                f'<div class="tip-item">'
                f'<span class="tip-title">【{t.get("title","")}】</span> '
                f'{t.get("content","")}'
                f'</div>\n'
            )
        back_html += f"""
<div class="section">
  <div class="sec-title" style="background:#D97706;">💡 비법노트 요약 ({len(secret_tips)}개)</div>
  {st_items}
</div>"""

    if exam_keys:
        e_items = ""
        for e in exam_keys:
            e_items += (
                f'<div class="e-item">'
                f'<span class="e-type">[{e.get("type","")}]</span> '
                f'{e.get("content","")}'
                f'</div>\n'
            )
        back_html += f"""
<div class="section">
  <div class="sec-title" style="background:#DC2626;">📌 기출 핵심 포인트 ({len(exam_keys)}개)</div>
  {e_items}
</div>"""

    # ── 빈 섹션 처리 ──────────────────────────
    if not front_html:
        front_html = '<p style="color:#999;font-size:7pt;">선택된 섹션의 내용이 없습니다.</p>'
    if not back_html:
        back_html = '<p style="color:#999;font-size:7pt;">선택된 섹션의 내용이 없습니다.</p>'

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{note_title} — 시험 요약노트</title>
<style>
/* ── 인쇄/페이지 설정 ─────────────────────── */
@page {{
  size: A4 portrait;
  margin: 8mm 8mm 8mm 8mm;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', Arial, sans-serif;
  font-size: 8pt;
  line-height: 1.35;
  color: #111;
  background: white;
}}

/* ── 페이지 컨테이너 ─────────────────────── */
.page {{
  width: 194mm;
  min-height: 281mm;
  page-break-after: always;
  overflow: hidden;
}}
.page:last-child {{ page-break-after: auto; }}

/* ── 페이지 헤더 ─────────────────────────── */
.page-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e1b4b;
  color: white;
  padding: 1.5mm 3mm;
  font-size: 7.5pt;
  font-weight: bold;
  margin-bottom: 2.5mm;
}}
.page-header .side-label {{
  background: white;
  color: #1e1b4b;
  font-size: 6.5pt;
  font-weight: 900;
  padding: 0.3mm 2mm;
  border-radius: 2px;
  margin-left: 2mm;
}}

/* ── 2단 레이아웃 ─────────────────────────── */
.two-col {{
  column-count: 2;
  column-gap: 4mm;
  column-rule: 0.4pt solid #d1d5db;
}}

/* ── 섹션 ────────────────────────────────── */
.section {{
  break-inside: avoid;
  margin-bottom: 2.5mm;
}}
.sec-title {{
  color: white;
  font-size: 7.5pt;
  font-weight: 900;
  padding: 0.8mm 2mm;
  margin-bottom: 1mm;
  letter-spacing: 0.02em;
}}

/* ── 단어 그리드 ─────────────────────────── */
.word-grid {{
  column-count: 3;
  column-gap: 2mm;
  column-rule: 0.3pt dashed #e5e7eb;
}}
.word-row {{
  display: flex;
  gap: 1mm;
  padding: 0.4mm 1.5mm;
  break-inside: avoid;
}}
.w-en {{
  font-weight: 700;
  color: #1d4ed8;
  min-width: 18mm;
  flex-shrink: 0;
  font-size: 7.5pt;
}}
.w-kr {{ color: #374151; font-size: 7.5pt; }}
.tip  {{ color: #9333ea; font-size: 6.5pt; }}

/* ── 문법 ────────────────────────────────── */
.g-item {{
  padding: 0.5mm 1.5mm;
  border-left: 1.5pt solid #7C3AED;
  margin-bottom: 1.5mm;
  break-inside: avoid;
}}
.g-rule {{ font-weight: 700; color: #5b21b6; font-size: 7.5pt; }}
.g-ex   {{ color: #374151; font-size: 7pt; margin-top: 0.3mm; }}
.g-note {{ color: #dc2626; font-size: 6.5pt; margin-top: 0.3mm; }}

/* ── 핵심 문장 ───────────────────────────── */
.sent-row {{
  padding: 0.5mm 1.5mm;
  margin-bottom: 0.5mm;
  break-inside: avoid;
}}
.s-en {{ font-weight: 600; color: #0c4a6e; font-size: 7.5pt; }}
.s-kr {{ color: #4b5563; font-size: 7pt; margin-top: 0.2mm; }}

/* ── 핵심 패턴 ───────────────────────────── */
.p-item {{
  padding: 0.4mm 1.5mm;
  border-left: 1.5pt solid #059669;
  margin-bottom: 1mm;
  break-inside: avoid;
}}
.p-pat {{ font-weight: 700; color: #065f46; font-size: 7.5pt; }}
.p-mng {{ color: #374151; font-size: 7pt; }}

/* ── 비법노트 ────────────────────────────── */
.tip-item {{
  padding: 0.4mm 1.5mm;
  border-left: 1.5pt solid #d97706;
  margin-bottom: 1mm;
  break-inside: avoid;
  font-size: 7pt;
  color: #374151;
}}
.tip-title {{ font-weight: 700; color: #92400e; }}

/* ── 기출 포인트 ─────────────────────────── */
.e-item {{
  padding: 0.4mm 1.5mm;
  border-left: 1.5pt solid #dc2626;
  margin-bottom: 1mm;
  break-inside: avoid;
  font-size: 7pt;
  color: #374151;
}}
.e-type {{ font-weight: 700; color: #991b1b; }}

/* ── 푸터 ────────────────────────────────── */
.page-footer {{
  margin-top: 2mm;
  border-top: 0.4pt solid #d1d5db;
  padding-top: 1mm;
  text-align: center;
  font-size: 6.5pt;
  color: #9ca3af;
}}

/* ── 화면 미리보기 전용 ───────────────────── */
@media screen {{
  body {{ background: #f1f5f9; }}
  .page {{
    background: white;
    box-shadow: 0 2px 12px rgba(0,0,0,.15);
    margin: 0 auto 8mm auto;
    padding: 8mm;
  }}
}}
@media print {{
  .page {{
    padding: 0;
    box-shadow: none;
    background: white;
  }}
  body {{ background: white; }}
}}
</style>
</head>
<body>

<!-- ════════════════════════════════════════════
     앞면 (Front)
     ════════════════════════════════════════════ -->
<div class="page">
  <div class="page-header">
    <span>📖 {note_title}<span class="side-label">앞 면</span></span>
    <span style="font-size:6.5pt;font-weight:400;">반반 BanBan 시험직전 요약노트 &nbsp;|&nbsp; {date_str}</span>
  </div>
  <div class="two-col">
    {front_html}
  </div>
  <div class="page-footer">반반 BanBan 🎓 영어학습 파트너 &nbsp;|&nbsp; 이 요약노트는 AI가 생성했습니다 — 앞면</div>
</div>

<!-- ════════════════════════════════════════════
     뒷면 (Back)
     ════════════════════════════════════════════ -->
<div class="page">
  <div class="page-header" style="background:#0c4a6e;">
    <span>✏️ {note_title}<span class="side-label" style="color:#0c4a6e;">뒷 면</span></span>
    <span style="font-size:6.5pt;font-weight:400;">반반 BanBan 시험직전 요약노트 &nbsp;|&nbsp; {date_str}</span>
  </div>
  <div class="two-col">
    {back_html}
  </div>
  <div class="page-footer">반반 BanBan 🎓 영어학습 파트너 &nbsp;|&nbsp; 이 요약노트는 AI가 생성했습니다 — 뒷면</div>
</div>

</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_cheatsheet(student_id, student_name: str, api_cfg: dict, notes: list):
    """시험 직전 A4 요약노트 생성 페이지."""

    section_md("시험 직전 요약노트", icon("file-text"))
    st.caption("A4 양면 · 8pt · 여백 최소화 · 인쇄용 PDF로 변환 가능")

    if not notes:
        st.info("먼저 반반노트 라이브러리에 노트를 추가해주세요.")
        return

    # ── 노트 선택 ──────────────────────────────
    st.markdown("#### 📂 노트 선택")
    note_options = {n["id"]: f"{n.get('title','(제목없음)')} [{n.get('content_type','')}]" for n in notes}
    selected_id = st.selectbox(
        "요약노트를 만들 노트를 선택하세요",
        options=list(note_options.keys()),
        format_func=lambda x: note_options[x],
        key="cs_note_id",
    )

    if not selected_id:
        return

    # ── 노트 데이터 로드 ───────────────────────
    from library import get_note
    from study_db import get_grammar_points, list_secret_notes, list_past_problems

    note = get_note(selected_id)
    if not note:
        st.error("노트를 불러올 수 없습니다.")
        return

    words      = note.get("words",     [])
    dialogues  = note.get("dialogues", [])
    text_data  = note.get("text_data", {})
    ct         = note.get("content_type", "")

    grammar_pts  = get_grammar_points(selected_id)
    secret_nts   = list_secret_notes(selected_id)
    past_probs   = list_past_problems(selected_id)

    # ── 포함할 섹션 선택 ──────────────────────
    st.markdown("#### ⚙️ 포함할 섹션 선택")

    avail_sections = []
    if words:      avail_sections.append("단어")
    if dialogues:  avail_sections.append("대화문")
    if text_data and text_data.get("sentences"): avail_sections.append("본문")
    if grammar_pts: avail_sections.append("문법")
    if secret_nts:  avail_sections.append("비법노트")
    if past_probs:  avail_sections.append("기출문제")

    if not avail_sections:
        st.warning("이 노트에는 포함할 수 있는 데이터가 없습니다. 먼저 노트 내용을 추가해주세요.")
        return

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

    # ── 데이터 미리보기 ────────────────────────
    with st.expander("📊 포함 데이터 현황", expanded=False):
        cols = st.columns(3)
        with cols[0]:
            st.metric("단어", f"{len(words)}개")
            st.metric("문법 포인트", f"{len(grammar_pts)}개")
        with cols[1]:
            dlg_lines = sum(len(d.get("lines",[])) for d in dialogues)
            st.metric("대화문 줄", f"{dlg_lines}줄")
            st.metric("비법노트", f"{len(secret_nts)}개")
        with cols[2]:
            sents = len(text_data.get("sentences",[])) if text_data else 0
            st.metric("본문 문장", f"{sents}개")
            st.metric("기출 세트", f"{len(past_probs)}개")

    st.divider()

    # ── 캐시 키 ───────────────────────────────
    cache_key = f"_cs_html_{selected_id}_{'_'.join(sorted(chosen_sections))}"

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
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()

    if gen_btn or cache_key in st.session_state:
        if cache_key not in st.session_state:
            with st.spinner("AI가 핵심 내용을 분석하고 요약노트를 만들고 있습니다... (30~60초)"):
                try:
                    from study_ai import generate_cheatsheet_data
                    data = generate_cheatsheet_data(
                        note_title    = note.get("title", ""),
                        words         = words,
                        dialogues     = dialogues,
                        text_data     = text_data or {},
                        grammar_points= grammar_pts,
                        secret_notes  = secret_nts,
                        past_problems = past_probs,
                        sections      = chosen_sections,
                        api_config    = api_cfg,
                    )
                    date_str = datetime.date.today().strftime("%Y년 %m월 %d일")
                    html = _render_cheatsheet_html(
                        note_title = note.get("title",""),
                        data       = data,
                        date_str   = date_str,
                    )
                    st.session_state[cache_key] = html
                except Exception as e:
                    st.error(f"요약노트 생성 실패: {e}")
                    return

        html = st.session_state.get(cache_key, "")
        if not html:
            return

        # ── 다운로드 / 인쇄 버튼 ──────────────
        st.success("✅ 요약노트 생성 완료!")

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            note_title_safe = note.get("title","요약노트").replace(" ","_")
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

        # ── 미리보기 ────────────────────────────
        st.markdown("#### 👁️ 미리보기 (실제 인쇄 결과와 다를 수 있습니다)")

        # 탭으로 앞면/뒷면 분리 미리보기
        tab_front, tab_back, tab_full = st.tabs(["앞면 미리보기", "뒷면 미리보기", "전체 미리보기"])

        # 앞면만 추출하는 미니 HTML
        def _page_preview(html_full: str, page_idx: int) -> str:
            """풀 HTML에서 특정 페이지만 추출해서 스크롤 가능한 미리보기 생성."""
            import re
            # style 추출
            style_m = re.search(r"<style>([\s\S]*?)</style>", html_full)
            style_css = style_m.group(1) if style_m else ""
            # page div 추출
            pages = re.findall(r'(<div class="page">[\s\S]*?</div>\s*\n\s*</div>)', html_full)
            if not pages:
                pages = re.split(r'(?=<div class="page")', html_full)
                pages = [p for p in pages if 'class="page"' in p]
            page_html = pages[page_idx] if page_idx < len(pages) else ""
            return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
{style_css}
@media screen {{
  body {{ background: #f1f5f9; padding: 4px; }}
  .page {{
    background: white;
    box-shadow: 0 1px 8px rgba(0,0,0,.12);
    transform: scale(0.52);
    transform-origin: top left;
    width: 194mm;
    margin: 0;
  }}
  .page-wrapper {{
    width: calc(194mm * 0.52);
    overflow: hidden;
    height: calc(297mm * 0.52);
  }}
}}
</style>
</head><body>
<div class="page-wrapper">{page_html}</div>
</body></html>"""

        with tab_front:
            prev_front = _page_preview(html, 0)
            components.html(prev_front, height=820, scrolling=True)

        with tab_back:
            prev_back = _page_preview(html, 1)
            components.html(prev_back, height=820, scrolling=True)

        with tab_full:
            # 전체 A4 2페이지 미리보기 (작게 스케일)
            full_preview = html.replace(
                "</style>",
                """
@media screen {
  body { background: #e2e8f0; padding: 10px; }
  .page {
    background: white;
    box-shadow: 0 2px 10px rgba(0,0,0,.15);
    transform: scale(0.48);
    transform-origin: top left;
    width: 194mm;
    margin-bottom: calc(-297mm * 0.52 + 10px);
    display: block;
  }
}
</style>"""
            )
            components.html(full_preview, height=680, scrolling=True)

        # ── 통계 ──────────────────────────────
        import json as _json
        if cache_key in st.session_state:
            # 간단한 통계 표시는 생략 (HTML만 저장)
            pass
