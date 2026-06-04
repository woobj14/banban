# study_essay.py — 반반쌤 담당: 서술형 DNA 엔진
# 우리 앱만의 차별화 서술형 — 노트 DNA 출제 + 내신 조건 + 스캐폴딩 3단계
# + AI 채점/개선 피드백 + 문제 저장(뱅크) + 오답노트 연동
#
# 5가지 특징
#   ① 노트 DNA 문제   — 이 학생의 반반노트(단어/대화문/본문)에서만 출제
#   ② 내신 조건 서술형 — 단어 수 제한·지정 어휘 등 실제 시험 조건 재현
#   ③ 스캐폴딩 3단계   — 빈칸 → 문장완성 → 자유서술, 불안 없이 도전
#   ④ AI 채점 + 개선   — O/X가 아니라 "이렇게 바꾸면 더 좋아요"
#   ⑤ 에빙하우스 연동  — 복습 알림 시 서술형 1문제 (study_review 연동)

import streamlit as st
from icons import icon, section_md
from study_db import (
    save_to_question_bank, get_question_bank, count_question_bank,
    add_question_wrong, log_study_activity,
)
from study_ai import generate_essay_questions, grade_essay_answer, _ESSAY_TYPES
from plans import can_use_ai, increment_ai_usage, upgrade_banner, ai_usage_bar


# ─────────────────────────────────────────────────────────────────────────────
# 유형 메타 (아이콘·색)
# ─────────────────────────────────────────────────────────────────────────────
_ETYPE_META = {
    "영작":     ("vector-pen",    "#7C3AED"),
    "문장완성": ("file-text",     "#6366F1"),
    "요약":     ("align-left",    "#0891B2"),
    "이유설명": ("help-circle",   "#D97706"),
    "빈칸서술": ("edit-3",        "#DC2626"),
}
_DIFF_LABELS = {
    "easy":   ("쉬움 ★",     "#dcfce7", "#166534"),
    "medium": ("보통 ★★",   "#fef9c3", "#854d0e"),
    "hard":   ("어려움 ★★★", "#fee2e2", "#991b1b"),
}
_DIFF_FILTER = {"전체": None, "쉬움": "easy", "보통": "medium", "어려움": "hard"}


def _emeta(t: str):
    return _ETYPE_META.get(t, ("vector-pen", "#7C3AED"))


# ─────────────────────────────────────────────────────────────────────────────
# question_bank ↔ 서술형 dict 변환
#   서술형 전용 필드(constraints/keywords/scaffold/source)는 options(JSONB)에 묶어 저장
# ─────────────────────────────────────────────────────────────────────────────

def _to_bank(q: dict, difficulty: str) -> dict:
    return {
        "type":       q.get("type", "서술형"),
        "question":   q.get("question", ""),
        "passage":    q.get("passage", ""),
        "options": {                       # JSONB: 서술형 메타 보따리
            "constraints": q.get("constraints", ""),
            "keywords":    q.get("keywords", []),
            "scaffold":    q.get("scaffold", {}),
            "source":      q.get("source", ""),
        },
        "answer":     q.get("model_answer", ""),   # 모범답안
        "answer_kr":  q.get("answer_kr", ""),
        "difficulty": difficulty,
    }


def _from_bank(row: dict) -> dict:
    meta = row.get("options") or {}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "type":         row.get("q_type", "서술형"),
        "question":     row.get("question", ""),
        "passage":      row.get("passage", ""),
        "constraints":  meta.get("constraints", ""),
        "keywords":     meta.get("keywords", []),
        "scaffold":     meta.get("scaffold", {}),
        "source":       meta.get("source", ""),
        "model_answer": row.get("answer", ""),
        "answer_kr":    row.get("answer_kr", ""),
        "difficulty":   row.get("difficulty", "medium"),
        "bank_id":      row.get("id"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 문제 카드 렌더 (발문 + 조건 + 지문)
# ─────────────────────────────────────────────────────────────────────────────

def _render_prompt_card(i: int, q: dict):
    t       = q.get("type", "서술형")
    ic, clr = _emeta(t)
    diff    = q.get("difficulty", "medium")
    dlabel, dbg, dfc = _DIFF_LABELS.get(diff, _DIFF_LABELS["medium"])
    src     = q.get("source", "")

    st.markdown(
        f'<div style="background:white;border-radius:16px;padding:20px;'
        f'box-shadow:0 2px 12px rgba(0,0,0,0.07);margin-bottom:14px;'
        f'border-left:5px solid {clr};">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:10px;">'
        f'<span style="font-weight:800;color:#1f2937;font-size:1.05rem;'
        f'display:inline-flex;align-items:center;gap:6px;">'
        f'{icon(ic,16,clr)} 서술형 {i+1}. {t}'
        f'{f" · {src}" if src else ""}</span>'
        f'<span style="background:{dbg};color:{dfc};border-radius:20px;padding:2px 10px;'
        f'font-size:0.74rem;font-weight:700;">{dlabel}</span>'
        f'</div>'
        f'<div style="font-size:1.02rem;color:#1f2937;font-weight:600;line-height:1.7;">'
        f'{q.get("question","").replace(chr(10),"<br>")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 근거 지문
    if q.get("passage"):
        st.markdown(
            f'<div style="background:#F8FAFF;border:1.5px solid #C7D2FE;border-radius:10px;'
            f'padding:12px 16px;font-size:0.95rem;color:#1f2937;line-height:1.8;'
            f'margin:-6px 0 12px;">{icon("book-open",13,"#6366F1")} '
            f'{q["passage"].replace(chr(10),"<br>")}</div>',
            unsafe_allow_html=True,
        )

    # 내신 조건 (특징 ②)
    if q.get("constraints"):
        st.markdown(
            f'<div style="background:#FEF3C7;border:1px solid #FDE68A;border-radius:10px;'
            f'padding:8px 14px;font-size:0.84rem;color:#92400E;margin-bottom:12px;'
            f'display:flex;align-items:center;gap:6px;">'
            f'{icon("alert-circle",14,"#D97706")} <b>조건</b> · {q["constraints"]}</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 스캐폴딩 3단계 (특징 ③)
# ─────────────────────────────────────────────────────────────────────────────

def _render_scaffold(i: int, q: dict):
    sc = q.get("scaffold") or {}
    if not sc.get("step1_blank"):
        return
    with st.expander("어려우면 단계별로 도전해보기 (스캐폴딩)", expanded=False):
        # 1단계: 빈칸
        st.markdown(
            f'<div style="font-size:0.82rem;font-weight:700;color:#16A34A;margin-bottom:4px;">'
            f'{icon("circle",12,"#16A34A")} 1단계 · 빈칸 채우기 (가장 쉬워요)</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:0.95rem;color:#374151;margin-bottom:6px;">'
            f'{sc["step1_blank"]}</div>', unsafe_allow_html=True,
        )
        s1 = st.text_input("1단계 답", key=f"sc1_{i}", label_visibility="collapsed",
                           placeholder="빈칸에 들어갈 말")
        if s1:
            if s1.strip().lower() == str(sc.get("step1_answer", "")).strip().lower():
                st.success(f"맞아요! 정답: {sc.get('step1_answer','')}")
            else:
                st.caption(f"힌트: 정답은 '{sc.get('step1_answer','')}' 입니다.")
        # 2단계: 문장완성 힌트
        if sc.get("step2_hint"):
            st.markdown(
                f'<div style="font-size:0.82rem;font-weight:700;color:#6366F1;'
                f'margin:10px 0 4px;">{icon("circle",12,"#6366F1")} 2단계 · 문장 완성 힌트</div>'
                f'<div style="font-size:0.9rem;color:#475569;background:#EEF2FF;'
                f'border-radius:8px;padding:8px 12px;">{sc["step2_hint"]}</div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            f'<div style="font-size:0.82rem;font-weight:700;color:#DC2626;margin:10px 0 2px;">'
            f'{icon("circle",12,"#DC2626")} 3단계 · 이제 위에서 자유롭게 직접 써보세요!</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 채점 결과 카드 (특징 ④)
# ─────────────────────────────────────────────────────────────────────────────

def _render_grade(res: dict, model_answer: str):
    score  = res.get("score", 0)
    passed = res.get("passed", False)
    color  = "#16A34A" if score >= 70 else "#D97706" if score >= 40 else "#DC2626"
    bg     = "#F0FDF4" if score >= 70 else "#FFFBEB" if score >= 40 else "#FEF2F2"

    # 점수 바
    st.markdown(
        f'<div style="background:{bg};border-radius:14px;padding:16px 18px;margin-bottom:10px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<span style="font-weight:800;color:{color};font-size:1.1rem;">'
        f'{icon("check-circle" if passed else "alert-circle",18,color)} {score}점</span>'
        f'<span style="font-size:0.8rem;color:{color};font-weight:700;">'
        f'{"통과!" if passed else "조금만 더!"}</span></div>'
        f'<div style="background:#E2E8F0;border-radius:5px;height:8px;">'
        f'<div style="background:{color};width:{score}%;height:100%;border-radius:5px;"></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # 키워드 칩 (포함/누락)
    chips = ""
    for k in res.get("matched", []):
        chips += (f'<span style="background:#DCFCE7;color:#166534;border-radius:14px;'
                  f'padding:3px 10px;font-size:0.78rem;font-weight:700;margin:2px;'
                  f'display:inline-block;">{icon("check",11,"#166534")} {k}</span>')
    for k in res.get("missing", []):
        chips += (f'<span style="background:#FEE2E2;color:#991B1B;border-radius:14px;'
                  f'padding:3px 10px;font-size:0.78rem;font-weight:700;margin:2px;'
                  f'display:inline-block;">{icon("x",11,"#991B1B")} {k}</span>')
    if chips:
        st.markdown(f'<div style="margin-bottom:10px;">{chips}</div>', unsafe_allow_html=True)

    # 피드백 / 개선 / 문법
    if res.get("feedback"):
        st.markdown(
            f'<div style="font-size:0.9rem;color:#166534;margin-bottom:6px;'
            f'display:flex;align-items:center;gap:6px;">'
            f'{icon("thumbs-up",14,"#16A34A")} {res["feedback"]}</div>',
            unsafe_allow_html=True,
        )
    if res.get("improve"):
        st.markdown(
            f'<div style="background:#EEF2FF;border-radius:10px;padding:10px 14px;'
            f'font-size:0.9rem;color:#4338CA;line-height:1.6;margin-bottom:6px;'
            f'display:flex;align-items:flex-start;gap:6px;">'
            f'{icon("sparkles",14,"#6366F1")} <span><b>이렇게 바꾸면 더 좋아요</b><br>'
            f'{res["improve"]}</span></div>',
            unsafe_allow_html=True,
        )
    if res.get("grammar"):
        st.markdown(
            f'<div style="font-size:0.84rem;color:#92400E;margin-bottom:6px;'
            f'display:flex;align-items:center;gap:6px;">'
            f'{icon("alert-triangle",13,"#D97706")} {res["grammar"]}</div>',
            unsafe_allow_html=True,
        )
    # 모범답안
    st.markdown(
        f'<div style="background:#F8FAFC;border-radius:10px;padding:10px 14px;'
        f'font-size:0.9rem;color:#334155;border:1px dashed #CBD5E1;">'
        f'{icon("award",13,"#475569")} <b>모범답안</b> · {model_answer}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 풀이 화면 (한 문제씩 진행)
# ─────────────────────────────────────────────────────────────────────────────

def _render_solve(api_config: dict):
    es        = st.session_state["essay_state"]
    questions = es["questions"]
    idx       = es["idx"]
    total     = len(questions)

    # 완료 화면
    if idx >= total:
        _render_done()
        return

    q = questions[idx]

    # 진행 표시
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-bottom:8px;font-size:0.8rem;color:#94A3B8;">'
        f'<span>서술형 진행 {idx+1} / {total}</span>'
        f'<span>통과 {es.get("passed_cnt",0)}개</span></div>'
        f'<div style="background:#E2E8F0;border-radius:5px;height:5px;margin-bottom:14px;">'
        f'<div style="background:#7C3AED;width:{int(idx/total*100)}%;height:100%;'
        f'border-radius:5px;"></div></div>',
        unsafe_allow_html=True,
    )

    _render_prompt_card(idx, q)
    _render_scaffold(idx, q)

    graded = es["results"].get(idx)
    if graded is None:
        ans = st.text_area("내 답안", key=f"essay_ans_{idx}",
                           placeholder="여기에 영어로 직접 써보세요…", height=100)
        c1, c2 = st.columns([1, 1])
        if c1.button("채점하기", type="primary", use_container_width=True,
                     key=f"essay_grade_{idx}"):
            if not ans.strip():
                st.warning("답안을 입력해주세요.")
            else:
                with st.spinner("반반쌤이 답안을 꼼꼼히 채점하는 중…"):
                    res = grade_essay_answer(
                        q.get("question", ""), q.get("model_answer", ""),
                        q.get("keywords", []), ans, api_config,
                        constraints=q.get("constraints", ""),
                    )
                es["results"][idx] = {"res": res, "user_answer": ans}
                if res.get("passed"):
                    es["passed_cnt"] = es.get("passed_cnt", 0) + 1
                else:
                    _save_wrong(es, q, ans)   # 오답노트 연동 (특징 ⑤)
                st.rerun()
        if c2.button("건너뛰기", use_container_width=True, key=f"essay_skip_{idx}"):
            es["results"][idx] = {"res": None, "user_answer": ""}
            st.rerun()
    else:
        res = graded["res"]
        if res:
            _render_grade(res, q.get("model_answer", ""))
        else:
            st.info("이 문제는 건너뛰었어요.")
        is_last = (idx + 1 >= total)
        if st.button("결과 보기" if is_last else "다음 문제",
                     type="primary", use_container_width=True, key=f"essay_next_{idx}"):
            es["idx"] += 1
            st.rerun()


def _save_wrong(es: dict, q: dict, user_answer: str):
    """틀린 서술형 → 오답노트 자동 저장 (source_type='essay')."""
    sid = es.get("student_id")
    if not sid:
        return
    try:
        add_question_wrong(
            student_id=sid,
            note_id=es.get("note_id"),
            bank_question_id=q.get("bank_id"),
            source_type="essay",
            question_snapshot={
                "question":  q.get("question", ""),
                "passage":   q.get("passage", ""),
                "answer":    q.get("model_answer", ""),
                "answer_kr": q.get("answer_kr", ""),
                "type":      q.get("type", "서술형"),
                "constraints": q.get("constraints", ""),
            },
            user_answer=user_answer,
        )
    except Exception:
        pass


def _render_done():
    es    = st.session_state["essay_state"]
    total = len(es["questions"])
    passed = es.get("passed_cnt", 0)
    pct   = int(passed / total * 100) if total else 0
    if pct >= 80:   emoji, msg = "award", "서술형 실력이 탄탄해요!"
    elif pct >= 50: emoji, msg = "trending-up", "잘하고 있어요! 오답을 복습해봐요."
    else:           emoji, msg = "book-open", "괜찮아요. 오답노트에서 다시 도전해요!"

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#F5F3FF,#EEF2FF);'
        f'border:1px solid #C7D2FE;border-radius:18px;padding:26px;text-align:center;'
        f'margin-bottom:16px;">'
        f'<div style="margin-bottom:6px;">{icon(emoji,38,"#7C3AED")}</div>'
        f'<div style="font-size:1.9rem;font-weight:900;color:#1E293B;">{passed} / {total} 통과</div>'
        f'<div style="color:#6366F1;margin-top:4px;">{msg}</div></div>',
        unsafe_allow_html=True,
    )

    # 학습 로그 (특징 ⑤ — 복습/리포트 연동 기반)
    if es.get("student_id") and not es.get("logged"):
        try:
            log_study_activity(es["student_id"], es.get("note_id"), "essay",
                               score=passed, total=total)
        except Exception:
            pass
        es["logged"] = True

    if passed < total:
        st.markdown(
            f'<div style="font-size:0.86rem;color:#059669;margin-bottom:10px;'
            f'display:flex;align-items:center;gap:6px;">'
            f'{icon("check-circle",14,"#059669")} 통과하지 못한 서술형은 '
            f'<b>오답노트</b>에 저장됐어요. 약점 처방전에서 다시 만나요!</div>',
            unsafe_allow_html=True,
        )

    if st.button("새 서술형 도전하기", type="primary", use_container_width=True):
        del st.session_state["essay_state"]
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 새 문제 생성 탭
# ─────────────────────────────────────────────────────────────────────────────

def _start_session(questions: list[dict], student_id, note_id):
    st.session_state["essay_state"] = {
        "questions":   questions,
        "idx":         0,
        "results":     {},
        "passed_cnt":  0,
        "student_id":  student_id,
        "note_id":     note_id,
    }
    st.rerun()


def _tab_generate(note: dict, student_id, note_id: int, api_config: dict):
    words     = note.get("words_data", [])
    dialogues = note.get("dialogues_data", [])
    text_data = note.get("text_data", {})

    _has = {
        "단어":   len(words) > 0,
        "대화문": sum(len(d.get("lines", [])) for d in dialogues) > 0,
        "본문":   len(text_data.get("sentences", [])) > 0,
    }
    if not any(_has.values()):
        st.info("이 노트에는 출제할 자료(단어/대화문/본문)가 없어요.")
        return

    # 특징 소개 배너
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#F5F3FF,#EEF2FF);'
        f'border:1px solid #DDD6FE;border-radius:12px;padding:12px 16px;margin-bottom:14px;'
        f'font-size:0.84rem;color:#5B21B6;line-height:1.7;">'
        f'{icon("vector-pen",14,"#7C3AED")} <b>서술형 DNA</b> — 내가 공부한 이 노트에서만 '
        f'나오는 서술형이에요. 내신 조건·스캐폴딩 단계·AI 첨삭까지 한 번에!</div>',
        unsafe_allow_html=True,
    )

    # 범위 (특징 ①)
    scope_opts = ["전체"] + [k for k in ("단어", "대화문", "본문") if _has[k]]
    scope = st.radio("출제 범위", scope_opts, index=0, horizontal=True,
                     format_func=lambda s: f"{s}", key="essay_scope")

    c1, c2 = st.columns(2)
    difficulty = c1.selectbox("난이도", ["easy", "medium", "hard"],
                              format_func=lambda x: _DIFF_LABELS[x][0], index=1,
                              key="essay_diff")
    n_q = c2.selectbox("문제 수", [2, 3, 5], index=1, key="essay_nq")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    ai_ok, _, _ = can_use_ai()
    ai_usage_bar()
    if not ai_ok:
        upgrade_banner(required="student", compact=True)
        return

    if st.button(f"{scope} 서술형 만들기", type="primary", use_container_width=True):
        with st.spinner("반반쌤이 생각하게 만드는 서술형을 출제하는 중…"):
            try:
                increment_ai_usage()
                try:
                    _existing = [q.get("question", "")
                                 for q in get_question_bank(note_id, source_type="essay",
                                                            limit=10000)]
                except Exception:
                    _existing = []
                questions = generate_essay_questions(
                    text_data=text_data, words=words, dialogues=dialogues,
                    api_config=api_config, n_questions=n_q, scope=scope,
                    difficulty=difficulty, avoid=_existing,
                )
            except Exception as e:
                st.error(f"생성 실패: {e}")
                return
        if not questions:
            st.warning("새 서술형을 만들지 못했어요. 저장된 문제 탭에서 기존 문제를 풀어보세요.")
            return
        # 문제뱅크 자동 저장 (특징 ⑥ — 저장)
        try:
            saved = save_to_question_bank(
                note_id, [_to_bank(q, difficulty) for q in questions],
                source_type="essay",
            )
        except Exception:
            saved = 0
        st.success(f"{len(questions)}개 서술형 생성 완료! (저장 +{saved}개)")
        _start_session(questions, student_id, note_id)


# ─────────────────────────────────────────────────────────────────────────────
# 저장된 문제 탭 (뱅크, AI 비용 0원)
# ─────────────────────────────────────────────────────────────────────────────

def _tab_bank(note: dict, student_id, note_id: int):
    st.markdown(
        f'<div style="font-size:0.85rem;color:#64748B;margin-bottom:10px;">'
        f'{icon("database",14,"#7C3AED")} 지금까지 만든 서술형이 저장돼 있어요. '
        f'<b>새로 만들지 않아도</b> 골라서 다시 풀 수 있어요.</div>',
        unsafe_allow_html=True,
    )
    try:
        rows = get_question_bank(note_id, source_type="essay", limit=10000)
    except Exception as e:
        st.error(f"뱅크 조회 오류: {e}")
        return
    if not rows:
        st.markdown(
            f'<div style="text-align:center;padding:34px 20px;background:#F8FAFB;'
            f'border:1px dashed #CBD5E1;border-radius:14px;color:#94A3B8;">'
            f'{icon("database",32,"#CBD5E1")}<br>'
            f'<div style="margin-top:10px;">아직 저장된 서술형이 없어요.</div>'
            f'<div style="font-size:0.82rem;margin-top:4px;">'
            f'「새 서술형」 탭에서 만들면 여기에 모여요.</div></div>',
            unsafe_allow_html=True,
        )
        return

    diff_label = st.radio("난이도", list(_DIFF_FILTER.keys()), index=0,
                          horizontal=True, key="essay_bank_diff")
    diff_val = _DIFF_FILTER[diff_label]
    pool = [r for r in rows if (diff_val is None or r.get("difficulty") == diff_val)]

    st.markdown(
        f'<div style="font-size:0.82rem;color:#475569;margin:6px 0 10px;">'
        f'<b style="color:#7C3AED;">{len(pool)}</b>개 저장됨 ({diff_label})</div>',
        unsafe_allow_html=True,
    )
    if not pool:
        st.info("이 난이도에는 저장된 서술형이 없어요.")
        return

    n_pick = st.selectbox("풀 문제 수", [3, 5, 10], index=0, key="essay_bank_n")
    if st.button(f"저장된 서술형 풀기 ({min(n_pick,len(pool))}문제)",
                 type="primary", use_container_width=True, key="essay_bank_play"):
        import random
        picked = random.sample(pool, min(n_pick, len(pool)))
        questions = [_from_bank(r) for r in picked]
        _start_session(questions, student_id, note_id)


# ─────────────────────────────────────────────────────────────────────────────
# Public: 서술형 DNA 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_essay(note: dict, student_id, student_name: str, api_config: dict | None):
    """서술형 DNA 메인 화면.
    note: {id, title, words_data, dialogues_data, text_data}
    """
    note_id = note["id"]

    if not api_config:
        st.warning("API 키가 필요합니다. .env에 ANTHROPIC_API_KEY 또는 GEMINI_API_KEY를 설정해주세요.")
        return

    # 진행 중 세션이 있으면 풀이 화면 유지
    if st.session_state.get("essay_state"):
        _render_solve(api_config)
        return

    try:
        _bank_n = count_question_bank(note_id, source_type="essay")
    except Exception:
        _bank_n = 0
    bank_label = f"저장된 문제 ({_bank_n})" if _bank_n else "저장된 문제"

    gen_tab, bank_tab = st.tabs(["새 서술형", bank_label])
    with gen_tab:
        _tab_generate(note, student_id, note_id, api_config)
    with bank_tab:
        _tab_bank(note, student_id, note_id)
