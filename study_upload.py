# study_upload.py — S.Y. 담당: 기출문제 업로드
# PDF/이미지 업로드 → AI 추출 → 내신문제 방식 퀴즈 + 오답노트 연동

import streamlit as st
from datetime import date
from icons import icon, section_md, title_md
from study_db import save_past_problems, list_past_problems, add_question_wrong
from study_ai import extract_past_problems_from_text


# ─────────────────────────────────────────────────────────────────────────────
# AI 이미지 추출 프롬프트 (밑줄 보존 포함)
# ─────────────────────────────────────────────────────────────────────────────

_IMG_PROMPT = """이 시험 문제지 이미지에서 문제와 답을 추출하세요.

⚠️ 중요 규칙:
- 밑줄이 그어진 단어·구절은 반드시 <u>해당 텍스트</u> 형태로 표시 (HTML 태그)
  예: "She <u>have</u> gone to school."
- 번호로 표시된 선택지(①②③④⑤)는 보기 배열에 그대로 보존
- 답은 정확한 선택지 번호+텍스트로 작성 (예: "② have gone")
- 답이 이미지에 없으면 answer는 ""
- 지문(passage)이 있으면 반드시 passage 필드에 분리

반드시 아래 JSON 형식만 반환 (다른 텍스트 절대 금지):
{
  "problems": [
    {
      "number": 1,
      "type": "객관식",
      "passage": "지문이 있을 경우 여기에 (없으면 빈 문자열). 밑줄 포함 시 <u>텍스트</u> 사용",
      "question": "문제 내용. 밑줄 부분은 <u>텍스트</u> 형태로 표시",
      "options": ["① 보기1", "② 보기2", "③ 보기3", "④ 보기4"],
      "answer": "② 보기2",
      "points": 3
    }
  ]
}
- type: 객관식 / 서술형 / 단답형
- 순수 JSON만 반환"""


# ─────────────────────────────────────────────────────────────────────────────
# Public: 기출문제 업로드 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_upload(note: dict | None, api_config: dict | None,
                student_id: int | None = None):
    """
    기출문제 업로드 메인 화면.
    note: {id, title} 또는 None
    """
    note_id    = note["id"] if note else None
    note_title = note["title"] if note else "전체"

    # 통합 헤더는 _study_note_selector가 렌더 → 안내만 표시
    st.caption("시험 기출문제를 업로드하면 AI가 분석하고 내신문제 방식으로 풀 수 있어요")

    # 저작권 공지
    st.markdown(f"""
<div style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;
     padding:12px 16px;margin-bottom:16px;font-size:0.83rem;color:#92400e;">
  {icon("alert-circle", 14, "#92400e")} <b>저작권 안내</b>: 업로드하는 기출문제의 저작권은 해당 출판사 및 제작 기관에 있습니다.
  개인 학습 목적으로만 사용하고, 무단 배포나 상업적 이용을 금지합니다.
</div>
""", unsafe_allow_html=True)

    if not api_config:
        st.warning("🔑 API 키가 필요합니다.")
        return

    # 기출 퀴즈 진행 중이면 우선 표시
    if st.session_state.get("past_quiz_state"):
        _render_past_quiz(student_id)
        return

    tab_upload, tab_saved = st.tabs(["📤 업로드", "📚 저장된 기출문제"])

    # ── 탭 1: 업로드 ──────────────────────────────────────────────
    with tab_upload:
        source_name = st.text_input(
            "출처", key="upload_source",
            placeholder="예: 2024년 1학기 중간고사, OO중학교 기출",
        )

        upload_method = st.radio(
            "입력 방법", ["📸 이미지 업로드", "📄 PDF 업로드", "📝 텍스트 직접 입력"],
            horizontal=True, key="upload_method",
        )

        if upload_method in ("📸 이미지 업로드", "📄 PDF 업로드"):
            is_pdf = upload_method == "📄 PDF 업로드"
            if is_pdf:
                uploaded_single = st.file_uploader(
                    "기출문제 PDF",
                    type=["pdf"],
                    accept_multiple_files=False,
                    key="upload_files_pdf",
                )
                uploaded = []
                if uploaded_single:
                    from ocr_extractor import pdf_to_images, pdf_page_count
                    pdf_bytes   = uploaded_single.read()
                    total_pages = pdf_page_count(pdf_bytes)
                    st.markdown(f"**총 {total_pages}페이지**")
                    c1, c2 = st.columns(2)
                    ps = c1.number_input("시작 페이지", 1, max(total_pages,1), 1, key="up_ps")
                    pe = c2.number_input("끝 페이지",  1, max(total_pages,1), min(total_pages,10), key="up_pe")
                    # PDF → 이미지 변환 (버튼 클릭 시)
                    if st.button("PDF 페이지 준비", key="pdf_prep_btn"):
                        imgs = pdf_to_images(pdf_bytes)
                        st.session_state["upload_pdf_imgs"] = imgs[ps-1:pe]
                        st.success(f"✅ {len(st.session_state['upload_pdf_imgs'])}페이지 준비됨")
                # 변환된 이미지를 uploaded 리스트처럼 사용
                pdf_imgs = st.session_state.get("upload_pdf_imgs", [])
                analyze_ready = len(pdf_imgs) > 0
            else:
                uploaded = st.file_uploader(
                    "기출문제 이미지 (JPG · PNG · WEBP)",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key="upload_files",
                )
                if uploaded:
                    for f in uploaded:
                        st.image(f.read(), caption=f.name, use_container_width=True)
                        f.seek(0)
                pdf_imgs = []
                analyze_ready = bool(uploaded)

            if analyze_ready or (not is_pdf and uploaded):
                if st.button("🔍 AI 분석하기", type="primary",
                             use_container_width=True, key="upload_analyze"):
                    with st.spinner("기출문제를 낱낱이 해부 중… 밑줄 하나도 안 놓쳐요!"):
                        try:
                            from ocr_extractor import _call_ai, _encode_image
                            import json, re

                            all_problems = []
                            # 이미지 소스 결정 (PDF 변환 이미지 or 직접 업로드)
                            if is_pdf:
                                img_list = pdf_imgs  # already bytes
                            else:
                                img_list = [f.read() for f in uploaded]

                            for img_bytes in img_list:
                                raw = _call_ai(img_bytes, _IMG_PROMPT, api_config)
                                raw = raw.strip()
                                m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
                                if m:
                                    raw = m.group(1)
                                try:
                                    data = json.loads(raw)
                                    all_problems.extend(data.get("problems", []))
                                except Exception:
                                    pass

                            if all_problems:
                                st.session_state["upload_preview"] = {
                                    "problems":    all_problems,
                                    "source_name": source_name.strip(),
                                }
                                st.session_state.pop("upload_pdf_imgs", None)
                                st.rerun()
                            else:
                                st.warning("문제를 추출하지 못했습니다. 파일을 확인해 주세요.")
                        except Exception as e:
                            st.error(f"분석 실패: {e}")

        else:  # 텍스트 직접 입력
            text_input = st.text_area(
                "기출문제 텍스트 붙여넣기", key="upload_text",
                height=250,
                placeholder="시험 문제를 복사해서 붙여넣으세요...",
            )
            if text_input.strip():
                if st.button("🔍 AI 분석하기", type="primary",
                             use_container_width=True, key="upload_text_analyze"):
                    with st.spinner("AI가 기출문제를 꼼꼼히 읽는 중… 잠깐만요!"):
                        try:
                            extracted = extract_past_problems_from_text(
                                text_input, api_config
                            )
                            if extracted:
                                st.session_state["upload_preview"] = {
                                    "problems":    extracted,
                                    "source_name": source_name.strip(),
                                }
                                st.rerun()
                            else:
                                st.warning("문제를 추출하지 못했습니다.")
                        except Exception as e:
                            st.error(f"분석 실패: {e}")

        # ── 추출 완료 액션 카드 ────────────────────────────────────
        preview_data = st.session_state.get("upload_preview")
        if preview_data:
            probs   = preview_data["problems"]
            src     = preview_data.get("source_name") or f"기출문제 {date.today()}"
            n       = len(probs)

            # ── 추출 즉시 자동 저장 (최초 1회) — 데이터 유실 방지 ──
            if not preview_data.get("auto_saved") and note_id:
                try:
                    save_past_problems(note_id, src, probs)
                    preview_data["auto_saved"] = True
                except Exception:
                    pass
            saved = preview_data.get("auto_saved", False)

            st.markdown("---")
            _sub = ("💾 자동 저장됐어요 — 「저장된 기출문제」 탭에서 언제든 다시 풀 수 있어요"
                    if saved else
                    "⚠️ 노트를 선택하면 자동 저장돼요. 지금은 바로 풀기만 가능해요")
            st.markdown(f"""
<div style="background:#f0fdfa;border:2px solid #5eead4;border-radius:14px;
     padding:22px;text-align:center;margin:8px 0 18px 0;">
  <div style="margin-bottom:6px;">{icon("check-circle", 32, "#0d9488")}</div>
  <div style="font-size:1.25rem;font-weight:800;color:#0f766e;">
    {n}개 문제 추출 완료!
  </div>
  <div style="color:#6b7280;font-size:0.85rem;margin-top:4px;">{_sub}</div>
</div>
""", unsafe_allow_html=True)

            act_col1, act_col2 = st.columns([4, 1])

            # 바로 풀기 → quiz state로 이동 (이미 저장됐으니 안심)
            if act_col1.button("🎯 바로 풀기", type="primary",
                               use_container_width=True, key="preview_quiz"):
                st.session_state["past_quiz_state"] = {
                    "problems":     probs,
                    "source_name":  src,
                    "answers":      {},
                    "submitted":    False,
                    "note_id":      note_id or 0,
                    "from_preview": not saved,   # 저장 안 됐을 때만 결과 화면 저장 옵션
                }
                del st.session_state["upload_preview"]
                st.rerun()

            # 닫기 (이미 저장됐으므로 데이터 안전)
            if act_col2.button("닫기", use_container_width=True, key="preview_cancel"):
                del st.session_state["upload_preview"]
                st.rerun()

    # ── 탭 2: 저장된 기출문제 ─────────────────────────────────────
    with tab_saved:
        saved = list_past_problems(note_id)
        if not saved:
            st.markdown(f"""
<div style="text-align:center;padding:40px;background:#f0fdfa;border-radius:14px;
     border:2px dashed #99f6e4;margin:20px 0;">
  <div style="margin-bottom:8px;">{icon("cloud-upload", 52, "#0d9488")}</div>
  <div style="font-size:1.1rem;font-weight:700;color:#0f766e;margin-top:8px;">
    저장된 기출문제가 없어요
  </div>
  <div style="color:#9ca3af;font-size:0.9rem;margin-top:4px;">
    업로드 탭에서 기출문제를 분석하고 저장해 보세요!
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            for s in saved:
                probs = s.get("problems", [])
                with st.expander(
                    f"📋 {s['source_name']} ({len(probs)}문제) — {s['created_at'][:10]}"
                ):
                    # 문제 목록 요약 (정답 미노출)
                    for i, p in enumerate(probs[:3]):
                        number = p.get("number", i + 1)
                        ptype  = p.get("type", "")
                        q_text = p.get("question", "")[:60]
                        st.markdown(
                            f'<div style="font-size:0.83rem;color:#374151;padding:3px 0;">'
                            f'{icon("pencil",12,"#6b7280")} {number}. {q_text}{"…" if len(p.get("question","")) > 60 else ""}'
                            f' <span style="font-size:0.75rem;color:#9ca3af;">({ptype})</span></div>',
                            unsafe_allow_html=True,
                        )
                    if len(probs) > 3:
                        st.caption(f"… 외 {len(probs) - 3}문제")

                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                    btn_c1, btn_c2 = st.columns([3, 1])

                    if btn_c1.button(
                        "🎯 내신문제 방식으로 풀기",
                        key=f"quiz_past_{s['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        st.session_state["past_quiz_state"] = {
                            "problems":     probs,
                            "source_name":  s["source_name"],
                            "answers":      {},
                            "submitted":    False,
                            "note_id":      note_id or 0,
                            "from_preview": False,
                        }
                        st.rerun()

                    if btn_c2.button("🗑️ 삭제", key=f"del_past_{s['id']}",
                                     use_container_width=True):
                        from study_db import DB_PATH
                        import sqlite3
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute("DELETE FROM past_problems WHERE id = ?", (s["id"],))
                        conn.commit()
                        conn.close()
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 내신문제 방식 기출 퀴즈 렌더링
# ─────────────────────────────────────────────────────────────────────────────

def _render_past_quiz(student_id: int | None):
    """기출문제 퀴즈 — 내신문제 시스템 방식 (정답 숨김 + 채점 + 오답노트)"""
    state = st.session_state.get("past_quiz_state", {})
    if not state:
        return

    problems  = state["problems"]
    answers   = state["answers"]
    submitted = state.get("submitted", False)
    src_name  = state.get("source_name", "기출문제")

    if submitted:
        _render_past_quiz_result(state, student_id)
        return

    # ── 진행 중 화면 ───────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0f766e,#14b8a6);color:white;
     border-radius:14px;padding:14px 18px;margin-bottom:16px;">
  <div style="font-size:0.82rem;opacity:0.85;">
    {icon("file-text", 13, "rgba(255,255,255,0.85)")} 기출 퀴즈
  </div>
  <div style="font-size:1.2rem;font-weight:800;">{src_name}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown(section_md("pencil", "문제 풀기"), unsafe_allow_html=True)
    st.caption("모든 문제에 답한 후 제출 버튼을 눌러주세요. 정답은 제출 후 공개됩니다.")

    for i, p in enumerate(problems):
        ptype  = p.get("type", "")
        number = p.get("number", i + 1)
        color  = "#0f766e"

        st.markdown(f"""
<div style="background:white;border-radius:12px;padding:16px;
     box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:14px;
     border-left:4px solid {color};">
  <div style="font-weight:800;color:#1f2937;margin-bottom:8px;">
    문제 {number} &nbsp;
    <span style="background:#ccfbf1;color:#0f766e;border-radius:12px;
          padding:1px 8px;font-size:0.72rem;">{ptype}</span>
  </div>
""", unsafe_allow_html=True)

        # 지문 (밑줄 HTML 지원 + 대화문은 화자별 줄바꿈·색상)
        if p.get("passage"):
            from study_exam import _format_passage
            passage_html = _format_passage(p["passage"])
            st.markdown(f"""
<div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:7px;
     padding:10px 14px;font-size:0.83rem;color:#374151;font-style:italic;
     margin-bottom:10px;line-height:1.9;">{passage_html}</div>
""", unsafe_allow_html=True)

        # 문제 본문 (밑줄 HTML 지원)
        q_html = p.get("question", "").replace("\n", "<br>")
        st.markdown(
            f'<div style="font-size:0.93rem;font-weight:500;color:#1f2937;'
            f'margin-bottom:12px;line-height:1.7;">{q_html}</div></div>',
            unsafe_allow_html=True,
        )

        options = p.get("options", [])
        if options:
            prev     = answers.get(i)
            prev_idx = None
            if prev:
                for oi, opt in enumerate(options):
                    if opt == prev:
                        prev_idx = oi
                        break

            choice = st.radio(
                f"past_q_{i}", options, index=prev_idx,
                key=f"past_radio_{i}",
                label_visibility="collapsed",
            )
            if choice:
                answers[i] = choice
        else:
            # 서술형 / 단답형
            prev_text = answers.get(i, "")
            ans_text  = st.text_area(
                f"past_text_{i}", value=prev_text,
                key=f"past_textarea_{i}",
                placeholder="답을 입력하세요…",
                label_visibility="collapsed", height=70,
            )
            if ans_text:
                answers[i] = ans_text

    # 답변 현황
    answered_cnt = len([v for v in answers.values() if v])
    total_cnt    = len(problems)
    st.markdown(f"""
<div style="background:#f0fdfa;border-radius:10px;padding:12px;text-align:center;
     margin:14px 0;font-size:0.9rem;color:#374151;">
  {icon("bar-chart-2", 14, "#0f766e")} {answered_cnt} / {total_cnt} 문항 답변 완료
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    if col1.button("🗑️ 처음부터", use_container_width=True):
        del st.session_state["past_quiz_state"]
        st.rerun()

    submit_ready = (answered_cnt >= total_cnt)
    if col2.button(
        "✅ 제출하기" if submit_ready else f"⚠️ {total_cnt - answered_cnt}개 미답",
        type="primary", use_container_width=True,
        disabled=not submit_ready,
    ):
        state["submitted"] = True
        state["answers"]   = answers
        st.rerun()


def _render_past_quiz_result(state: dict, student_id: int | None):
    """기출 퀴즈 채점 결과 화면 + 오답노트 연동"""
    problems     = state["problems"]
    answers      = state["answers"]
    src_name     = state.get("source_name", "기출문제")
    note_id      = state.get("note_id", 0)
    from_preview = state.get("from_preview", False)

    # 채점 (정답 있는 문제만)
    scorable = [p for p in problems if p.get("answer")]
    score    = sum(
        1 for i, p in enumerate(problems)
        if p.get("answer") and
           answers.get(i, "").strip() == p["answer"].strip()
    )
    total = len(scorable)
    pct   = int(score / total * 100) if total else 0

    # 오답 문제 자동 오답노트 저장 (최초 1회)
    if not state.get("wrongnote_saved") and student_id:
        for i, p in enumerate(problems):
            user_ans = answers.get(i, "")
            correct  = p.get("answer", "").strip()
            if correct and user_ans.strip() != correct:
                try:
                    add_question_wrong(
                        student_id=student_id,
                        note_id=note_id,
                        bank_question_id=None,
                        source_type="past_exam",
                        question_snapshot=p,
                        user_answer=user_ans,
                    )
                except Exception:
                    pass
                # 문장 복습 스케줄 자동 등록
                try:
                    from study_review import auto_schedule_sentence
                    passage = p.get("passage", "").strip()
                    if passage and len(passage) > 5:
                        sent_idx = abs(hash(passage[:50])) % 1000000
                        auto_schedule_sentence(
                            student_id, note_id, sent_idx, passage, ""
                        )
                except Exception:
                    pass
        state["wrongnote_saved"] = True

    if pct >= 90:
        result_icon = icon("award", 52, "#15803d")
        msg, bg = "최우수! 만점에 가깝습니다!", "#f0fdf4"
    elif pct >= 70:
        result_icon = icon("sparkles", 52, "#ca8a04")
        msg, bg = "우수! 훌륭해요!", "#fffbeb"
    elif pct >= 50:
        result_icon = icon("zap", 52, "#ea580c")
        msg, bg = "절반 이상 맞혔어요. 오답을 다시 확인해 보세요.", "#fff7ed"
    else:
        result_icon = icon("book-open", 52, "#dc2626")
        msg, bg = "오답노트를 꼼꼼히 복습해 봐요!", "#fef2f2"

    st.markdown(f"""
<div style="background:{bg};border-radius:16px;padding:24px;text-align:center;
     margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
  <div style="margin-bottom:8px;">{result_icon}</div>
  <div style="font-size:2rem;font-weight:800;color:#0f766e;margin:8px 0;">
    {score} / {total} ({pct}점)
  </div>
  <div style="color:#6b7280;font-size:0.95rem;">{src_name}</div>
  <div style="color:#6b7280;font-size:0.9rem;margin-top:4px;">{msg}</div>
</div>
""", unsafe_allow_html=True)

    # ── 문항별 채점 결과 ───────────────────────────────────────────
    st.markdown(section_md("list", "문항별 결과"), unsafe_allow_html=True)

    for i, p in enumerate(problems):
        user_ans = answers.get(i, "")
        correct  = p.get("answer", "").strip()
        ptype    = p.get("type", "")
        number   = p.get("number", i + 1)

        if not correct:
            is_ok = None
            color, bg_c, mark = "#6b7280", "#f9fafb", "—"
        else:
            is_ok = (user_ans.strip() == correct)
            if is_ok:
                color, bg_c, mark = "#16a34a", "#f0fdf4", "✅"
            else:
                color, bg_c, mark = "#dc2626", "#fef2f2", "❌"

        with st.expander(
            f"{mark} 문제 {number}. {ptype}"
            + (" (정답 미제공)" if is_ok is None else ""),
            expanded=(is_ok is False),
        ):
            # 지문
            if p.get("passage"):
                st.markdown(f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:7px;
     padding:8px 12px;font-size:0.82rem;color:#374151;font-style:italic;
     margin-bottom:8px;line-height:1.8;">{p['passage']}</div>
""", unsafe_allow_html=True)

            # 문제
            st.markdown(
                f'<div style="font-weight:600;margin-bottom:8px;line-height:1.7;">'
                f'{p.get("question","").replace(chr(10),"<br>")}</div>',
                unsafe_allow_html=True,
            )

            # 선택지 (정답/오답 강조)
            for opt in p.get("options", []):
                is_correct_opt = (opt.strip() == correct)
                is_user_opt    = (opt.strip() == user_ans.strip())
                opt_style = ""
                if is_correct_opt:
                    opt_style = "background:#dcfce7;color:#166534;font-weight:700;border-radius:4px;padding:2px 6px;"
                elif is_user_opt and not is_ok:
                    opt_style = "background:#fee2e2;color:#991b1b;font-weight:700;border-radius:4px;padding:2px 6px;"
                st.markdown(
                    f'<div style="padding:3px 0 3px 14px;font-size:0.87rem;">'
                    f'<span style="{opt_style}">{opt}</span></div>',
                    unsafe_allow_html=True,
                )

            # 내 답 / 정답 비교
            st.markdown(f"""
<div style="background:{bg_c};border-radius:8px;padding:10px 14px;margin-top:8px;">
  <b style="color:{color};">내 답: {user_ans or "(미답)"}</b>
  {f'<br><b style="color:#16a34a;display:inline-flex;align-items:center;gap:4px;">{icon("check-circle", 13, "#16a34a")} 정답: {correct}</b>' if is_ok is False and correct else ''}
</div>
""", unsafe_allow_html=True)

            # 자동 오답노트 저장 알림
            if is_ok is False and student_id:
                st.markdown(
                    '<div style="font-size:0.78rem;color:#059669;margin:4px 0;">'
                    '📌 오답노트에 자동 저장됐어요!</div>',
                    unsafe_allow_html=True,
                )

    # ── 미저장 문제 세트 저장 옵션 ─────────────────────────────────
    if from_preview and note_id:
        st.markdown("---")
        st.markdown(section_md("database", "이 문제 세트 저장하기"), unsafe_allow_html=True)
        st.caption("저장하면 '저장된 기출문제' 탭에서 언제든지 다시 풀 수 있어요.")
        save_src_val = st.text_input(
            "출처 이름", value=src_name, key="result_save_source"
        )
        save_btn_col, _ = st.columns([2, 3])
        if save_btn_col.button("💾 저장하기", key="result_save_btn",
                               use_container_width=True, type="primary"):
            if not save_src_val.strip():
                st.error("출처를 입력해주세요.")
            else:
                try:
                    save_past_problems(note_id, save_src_val.strip(), problems)
                    st.success("✅ 저장 완료!")
                    state["from_preview"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"저장 실패: {e}")

    # ── 하단 버튼 ──────────────────────────────────────────────────
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    if col1.button("🔄 다시 풀기", use_container_width=True):
        st.session_state["past_quiz_state"] = {
            **state,
            "answers":   {},
            "submitted": False,
        }
        st.rerun()
    if col2.button("🏠 기출문제 홈", use_container_width=True):
        del st.session_state["past_quiz_state"]
        st.rerun()
