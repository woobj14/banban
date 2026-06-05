# study_upload.py — S.Y. 담당: 기출문제 업로드
# PDF/이미지 업로드 → AI 추출 → 내신문제 방식 퀴즈 + 오답노트 연동

import streamlit as st
from datetime import date
from icons import icon, section_md, title_md
from study_db import (save_past_problems, list_past_problems, add_question_wrong,
                      update_past_problems, delete_past_problems)
from study_ai import extract_past_problems_from_text


# ─────────────────────────────────────────────────────────────────────────────
# AI 이미지 추출 프롬프트 (밑줄 보존 포함)
# ─────────────────────────────────────────────────────────────────────────────

_IMG_PROMPT = """당신은 대한민국 중학교 영어 시험지 전문 분석가입니다.
이 시험 문제지 이미지를 아주 꼼꼼하게 읽고, 모든 문제를 빠짐없이 추출하세요.

━━━━ 반드시 지켜야 할 추출 규칙 ━━━━

【발문 추출】
- 문제 번호 옆의 한국어 지시문을 question 필드에 완전하게 추출
  예) "다음 글을 읽고 아래 질문에 대한 알맞은 대답이 되도록 빈칸을 완성하시오."
- 조건 표시 (각 빈칸에 한 단어씩, 단어를 변형할 것 등)도 반드시 포함

【지문(passage) 추출】
- 박스·테두리로 묶인 영어 지문은 passage 필드에 완전하게 추출
- 지문 안의 밑줄 친 단어/구절은 <u>해당텍스트</u> 로 표시
- (A)(B)(C) 등 표시도 그대로 보존

【서술형 문제 처리】
- 빈칸(_____)이 있는 문장은 빈칸을 ___ 로 표시하여 그대로 추출
  예) "As the school's ___ ___, Mr. Kim works hard..."
- "→ She ___." 형태의 답 작성란도 sub_questions에 포함
- 소문항 (1), (2) 등이 있으면 sub_questions 배열에 각각 추가
  각 소문항: {"label": "(1)", "question": "What does Ms. Lee do?", "answer_line": "→ She ___."}

【선택지 처리】
- ①②③④⑤ 번호가 있는 선택지는 options 배열에 그대로 보존
- 순서 배열 문제의 (A)(B)(C)는 보기를 options에 넣고 type은 "순서배열"

【밑줄 표시】
- 밑줄 친 단어/구절 → <u>텍스트</u> HTML 태그 사용
  예) "B: I'll do it. And (A)<u>maybe Mingyu will join us, too</u>."

【기타】
- 답이 이미지에 없으면 answer: ""
- 배점이 보이면 points에 숫자로
- 문제 번호(27, 28, 29...)는 반드시 number 필드에

━━━━ JSON 형식 ━━━━
반드시 아래 형식만 반환 (다른 텍스트 절대 금지):
{
  "problems": [
    {
      "number": 27,
      "type": "서술형",
      "passage": "Drum roll, please! The first winner is the facilities manager, Mr. Kim! ...",
      "question": "다음 글을 아래와 같이 요약하고자 할 때, 빈칸에 들어갈 알맞은 말을 각각 찾아 쓰시오. (각 빈칸에 한 단어씩 쓰고 필요시 변형할 것)",
      "answer_template": "As the school's ___ ___, Mr. Kim works hard for a good learning environment by managing ___ ___ and ___ facilities like broken air conditioners.",
      "sub_questions": [],
      "options": [],
      "answer": "",
      "points": 4
    },
    {
      "number": 29,
      "type": "서술형",
      "passage": "The next award goes to ... the leader of the cafeteria staff, Ms. Lee! ...",
      "question": "다음 글을 읽고 아래 질문에 대한 알맞은 대답이 되도록 빈칸을 완성하시오.",
      "answer_template": "",
      "sub_questions": [
        {"label": "(1)", "question": "What does Ms. Lee do after lunchtime?", "answer_line": "→ She ___."},
        {"label": "(2)", "question": "Why is Ms. Lee proud of her job?", "answer_line": "→ Because she ___ to the students."}
      ],
      "options": [],
      "answer": "",
      "points": 4
    },
    {
      "number": 30,
      "type": "순서배열",
      "passage": "Now it's time to announce our final winner. ...",
      "question": "다음 주어진 글에 이어질 순서로 알맞은 것은?",
      "answer_template": "",
      "sub_questions": [],
      "options": ["① (A)-(C)-(B)", "② (B)-(A)-(C)", "③ (B)-(C)-(A)", "④ (C)-(A)-(B)", "⑤ (C)-(B)-(A)"],
      "answer": "",
      "points": 3
    }
  ]
}

type 값: 객관식 / 서술형 / 단답형 / 순서배열 / 빈칸완성 / 어법
순수 JSON만 반환. 이미지의 모든 문제를 빠짐없이 추출."""


def _extract_school(source_name: str) -> str:
    """source_name('… · OO중학교')에서 학교명 부분 추출."""
    if " · " in source_name:
        return source_name.split(" · ", 1)[1].strip()
    return ""


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
        # ── 출처 정보 (구조화 입력 → 통일된 형식으로 저장) ──────────
        st.markdown(
            '<div style="font-size:0.82rem;font-weight:700;color:#0f766e;'
            'margin-bottom:4px;">출처 정보 <span style="font-weight:400;color:#94a3b8;">'
            '— 통일된 형식으로 저장돼 학생이 쉽게 찾아요</span></div>',
            unsafe_allow_html=True,
        )
        _cy        = date.today().year
        _pub_opts  = ["YBM", "NE능률", "천재교육", "동아출판", "비상교육",
                      "미래엔", "지학사", "금성출판사", "기타"]
        _note_pub  = (note or {}).get("publisher", "")
        _pub_idx   = _pub_opts.index(_note_pub) if _note_pub in _pub_opts else 0

        sc1, sc2, sc3, sc4 = st.columns(4)
        src_year = sc1.selectbox("연도", [str(y) for y in range(_cy, _cy - 5, -1)],
                                 key="src_year")
        src_pub  = sc2.selectbox("출판사", _pub_opts, index=_pub_idx, key="src_pub")
        src_sem  = sc3.selectbox("학기", ["1학기", "2학기"], key="src_sem")
        src_exam = sc4.selectbox("시험", ["중간고사", "기말고사", "모의고사", "기타"],
                                 key="src_exam")
        src_school = st.text_input("학교명 (선택)", placeholder="예: OO중학교",
                                   key="src_school")

        source_name = f"{src_year} {src_pub} {src_sem} {src_exam}"
        if src_school.strip():
            source_name += f" · {src_school.strip()}"
        src_meta = {"exam_year": src_year, "publisher": src_pub,
                    "semester": src_sem, "exam_type": src_exam}
        st.caption(f"저장될 출처:  **{source_name}**")

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
                                    "meta":        src_meta,
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
                                    "meta":        src_meta,
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
                    _m = preview_data.get("meta", {})
                    save_past_problems(note_id, src, probs,
                                       exam_year=_m.get("exam_year", ""),
                                       publisher=_m.get("publisher", ""),
                                       semester=_m.get("semester", ""),
                                       exam_type=_m.get("exam_type", ""))
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
        all_saved = list_past_problems(note_id)

        if not all_saved:
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
            # ── 탐색 필터 (연도 / 학기 / 시험) ───────────────────────
            _years = sorted({s.get("exam_year", "") for s in all_saved if s.get("exam_year")},
                            reverse=True)
            fc1, fc2, fc3 = st.columns(3)
            f_year = fc1.selectbox("연도", ["전체"] + _years, key="pp_f_year")
            f_sem  = fc2.selectbox("학기", ["전체", "1학기", "2학기"], key="pp_f_sem")
            f_exam = fc3.selectbox("시험", ["전체", "중간고사", "기말고사", "모의고사", "기타"],
                                   key="pp_f_exam")

            saved = [
                s for s in all_saved
                if (f_year == "전체" or s.get("exam_year") == f_year)
                and (f_sem  == "전체" or s.get("semester")  == f_sem)
                and (f_exam == "전체" or s.get("exam_type") == f_exam)
            ]
            st.caption(f"{len(saved)}개 / 전체 {len(all_saved)}개")

            if not saved:
                st.info("선택한 조건의 기출문제가 없어요. 필터를 바꿔보세요.")

            for s in saved:
                probs   = s.get("problems", [])
                pp_id   = s["id"]
                editing = (st.session_state.get("pp_edit_id") == pp_id)

                with st.expander(
                    f"📋 {s['source_name']} ({len(probs)}문제) — {s['created_at'][:10]}"
                ):
                    # ── 수정 모드: 출처 메타 편집 ────────────────────
                    if editing:
                        st.markdown("**출처 수정**")
                        _py = str(s.get("exam_year", "") or date.today().year)
                        ec1, ec2, ec3, ec4 = st.columns(4)
                        e_year = ec1.text_input("연도", value=_py, key=f"ppe_year_{pp_id}")
                        e_pub  = ec2.text_input("출판사", value=s.get("publisher", ""),
                                                key=f"ppe_pub_{pp_id}")
                        e_sem  = ec3.selectbox("학기", ["1학기", "2학기"],
                                               index=0 if s.get("semester") != "2학기" else 1,
                                               key=f"ppe_sem_{pp_id}")
                        _exam_opts = ["중간고사", "기말고사", "모의고사", "기타"]
                        e_exam = ec4.selectbox("시험", _exam_opts,
                                               index=_exam_opts.index(s.get("exam_type"))
                                               if s.get("exam_type") in _exam_opts else 0,
                                               key=f"ppe_exam_{pp_id}")
                        e_school = st.text_input("학교명 (선택)",
                                                 value=_extract_school(s.get("source_name", "")),
                                                 key=f"ppe_school_{pp_id}")
                        _new_src = f"{e_year} {e_pub} {e_sem} {e_exam}"
                        if e_school.strip():
                            _new_src += f" · {e_school.strip()}"
                        st.caption(f"새 출처: **{_new_src}**")

                        sv1, sv2 = st.columns(2)
                        if sv1.button("저장", type="primary", use_container_width=True,
                                      key=f"ppe_save_{pp_id}"):
                            update_past_problems(pp_id, source_name=_new_src,
                                                 exam_year=e_year.strip(), publisher=e_pub.strip(),
                                                 semester=e_sem, exam_type=e_exam)
                            st.session_state.pop("pp_edit_id", None)
                            st.rerun()
                        if sv2.button("취소", use_container_width=True, key=f"ppe_cancel_{pp_id}"):
                            st.session_state.pop("pp_edit_id", None)
                            st.rerun()
                        continue

                    # ── 문제 목록 요약 (정답 미노출) ─────────────────
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
                    btn_c1, btn_c2, btn_c3 = st.columns([3, 1, 1])

                    if btn_c1.button("🎯 내신문제 방식으로 풀기",
                                     key=f"quiz_past_{pp_id}",
                                     use_container_width=True, type="primary"):
                        st.session_state["past_quiz_state"] = {
                            "problems":     probs,
                            "source_name":  s["source_name"],
                            "answers":      {},
                            "submitted":    False,
                            "note_id":      note_id or 0,
                            "from_preview": False,
                        }
                        st.rerun()

                    if btn_c2.button("✏️ 수정", key=f"edit_past_{pp_id}",
                                     use_container_width=True):
                        st.session_state["pp_edit_id"] = pp_id
                        st.rerun()

                    if btn_c3.button("🗑️ 삭제", key=f"del_past_{pp_id}",
                                     use_container_width=True):
                        delete_past_problems(pp_id)   # Supabase 삭제 (기존 SQLite 버그 수정)
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

        # ── 빈칸 서술 템플릿 (answer_template) ──────────────────────
        if p.get("answer_template"):
            st.markdown(
                f'<div style="background:#F0FDF4;border:1px solid #BBF7D0;'
                f'border-radius:8px;padding:10px 14px;font-size:0.9rem;'
                f'color:#1f2937;line-height:2;margin-bottom:10px;">'
                f'✏️ {p["answer_template"].replace(chr(10),"<br>")}</div>',
                unsafe_allow_html=True,
            )

        options = p.get("options", [])
        sub_qs  = p.get("sub_questions", [])

        if options:
            # ── 객관식 / 순서배열 ─────────────────────────────────
            prev     = answers.get(i)
            prev_idx = None
            if prev:
                for oi, opt in enumerate(options):
                    if opt == prev:
                        prev_idx = oi
                        break
            choice = st.radio(
                f"past_q_{i}", options, index=prev_idx,
                key=f"past_radio_{i}", label_visibility="collapsed",
            )
            if choice:
                answers[i] = choice

        elif sub_qs:
            # ── 소문항 (1)(2) 서술형 ─────────────────────────────
            sub_ans = answers.get(i) if isinstance(answers.get(i), dict) else {}
            for sq in sub_qs:
                lbl = sq.get("label", "")
                sq_q = sq.get("question", "")
                ans_line = sq.get("answer_line", "")
                st.markdown(
                    f'<div style="font-size:0.87rem;font-weight:700;'
                    f'color:#0891B2;margin:8px 0 3px;">{lbl} {sq_q}</div>',
                    unsafe_allow_html=True,
                )
                if ans_line:
                    st.markdown(
                        f'<div style="font-size:0.82rem;color:#64748B;margin-bottom:4px;">'
                        f'{ans_line}</div>', unsafe_allow_html=True,
                    )
                sq_val = sub_ans.get(lbl, "")
                new_val = st.text_input(
                    f"{lbl} 답", value=sq_val,
                    key=f"past_sub_{i}_{lbl}",
                    placeholder="영어로 답을 쓰세요…",
                    label_visibility="collapsed",
                )
                sub_ans[lbl] = new_val
            answers[i] = sub_ans

        else:
            # ── 단순 서술형 / 단답형 ─────────────────────────────
            prev_text = answers.get(i, "")
            if isinstance(prev_text, dict):
                prev_text = ""
            ans_text = st.text_area(
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
