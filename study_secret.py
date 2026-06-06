# study_secret.py — 반반쌤 × 반반 디자인팀 콜라보 비법노트
# 어디서도 못 만드는 프리미엄 인포그래픽 — 추후 유료 전환 예정

import streamlit as st
import streamlit.components.v1 as components
from icons import icon, section_md, confirm_delete_btn
from study_db import save_secret_note, list_secret_notes
from study_ai import (generate_secret_note_html,
                       analyze_note_for_secrets,
                       generate_secret_note_from_items)


# ─────────────────────────────────────────────────────────────────────────────
# 스타일 메타 정보
# ─────────────────────────────────────────────────────────────────────────────

_STYLES = {
    "만화 대화형": ("🗨️", "#7C3AED", "#F5F3FF",
                  "반반쌤👩‍🏫 × 학생🙋 캐릭터 대화 · 만화보듯 재미있게 학습 ⭐NEW"),
    "카드형":     ("🃏", "#4F46E5", "#EEF2FF",
                  "핵심 내용을 색상 카드로 시각화 · 프리미엄 학습 자료"),
    "웹툰형":     ("🎨", "#D97706", "#FFFBEB",
                  "만화 패널 스타일 · 임팩트 있는 비법 정리"),
    "전략표":     ("📊", "#0891B2", "#F0F9FF",
                  "수능/내신 대비 전략 매트릭스 · 시험 직전 최강 무기"),
    "마인드맵":   ("🌐", "#059669", "#ECFDF5",
                  "개념 연결 비주얼맵 · 복잡한 내용을 한눈에"),
}

_TEMPLATES = {
    "직접 입력": "",
    "🔤 조동사 / 시제 정리": (
        "아래 문법을 정리해줘:\n"
        "- 형태: (예시 문장)\n"
        "- 의미: \n"
        "- 혼동 주의: \n"
        "- 시험 출제 포인트: \n"
    ),
    "📚 본문 핵심 표현": (
        "본문에서 꼭 외워야 할 표현들:\n"
        "1. 표현: 뜻 / 예문\n"
        "2. 표현: 뜻 / 예문\n"
        "시험에 자주 나오는 포인트:\n"
    ),
    "📝 단어 집중 암기": (
        "이번 단원 필수 단어:\n"
        "단어 - 뜻 - 예문\n"
        "헷갈리는 단어 비교:\n"
        "암기 팁:\n"
    ),
    "🎯 내신 대비 전략": (
        "출제 예상 문법:\n"
        "출제 예상 어휘:\n"
        "자주 나오는 문제 유형:\n"
        "실수 주의 포인트:\n"
        "반반쌤 예상 문제:\n"
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _style_card(key: str, selected: bool) -> str:
    """스타일 선택 카드 렌더링용 HTML"""
    emoji, color, bg, desc = _STYLES[key]
    border = f"3px solid {color}" if selected else "2px solid #E2E8F0"
    shadow = f"0 0 0 3px {color}30" if selected else "none"
    badge  = (
        f'<div style="background:{color};color:white;font-size:0.65rem;'
        f'padding:2px 7px;border-radius:20px;font-weight:700;display:inline-block;'
        f'margin-bottom:6px;">{"✓ 선택됨" if selected else key}</div>'
    )
    return f"""
<div style="background:{bg};border:{border};border-radius:12px;padding:12px 14px;
     cursor:pointer;box-shadow:{shadow};transition:all 0.2s;">
  {badge}
  <div style="font-size:1.6rem;margin:4px 0;">{emoji}</div>
  <div style="font-weight:700;font-size:0.92rem;color:#1E293B;">{key}</div>
  <div style="font-size:0.75rem;color:#64748B;margin-top:3px;line-height:1.4;">{desc}</div>
</div>
"""


def _delete_secret_note(note_id_sb: int):
    """Supabase에서 비법노트 삭제"""
    from supabase_client import get_supabase
    try:
        get_supabase().table("secret_notes").delete().eq("id", note_id_sb).execute()
    except Exception as e:
        st.error(f"삭제 실패: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Public: 비법노트 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_secret_note(note: dict | None, api_config: dict | None):
    note_id    = note["id"] if note else None
    note_title = note["title"] if note else "전체"

    # ── 헤더 ─────────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#4F46E5 0%,#7C3AED 50%,#A855F7 100%);
     color:white;border-radius:16px;padding:20px 24px;margin-bottom:20px;
     box-shadow:0 8px 32px rgba(79,70,229,0.25);">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <span style="font-size:1.5rem;">✨</span>
    <div>
      <div style="font-size:0.78rem;opacity:0.85;letter-spacing:0.5px;">
        반반쌤 👩‍🏫 × 학생 🙋 캐릭터 대화형 비법노트
      </div>
      <div style="font-size:1.5rem;font-weight:900;letter-spacing:-0.5px;">
        비법노트 ✨
      </div>
    </div>
    <div style="margin-left:auto;text-align:right;">
      <div style="background:rgba(255,255,255,0.2);border-radius:20px;
           padding:4px 12px;font-size:0.72rem;font-weight:700;">
        💎 PREMIUM
      </div>
    </div>
  </div>
  <div style="font-size:0.82rem;opacity:0.85;margin-top:2px;">
    어디서도 못 보는 인포그래픽 · 학생 머릿속에 새기는 비법 자료
  </div>
</div>
""", unsafe_allow_html=True)

    if not api_config:
        st.warning("🔑 AI API 키가 필요합니다.")
        return

    tab_create, tab_auto, tab_saved = st.tabs([
        "✨ 새로 만들기",
        "🤖 자동 비법 만들기",
        "📁 저장된 비법노트",
    ])

    # ══════════════════════════════════════════════════════════════
    # 탭 1: 새로 만들기
    # ══════════════════════════════════════════════════════════════
    with tab_create:

        # ── 스타일 선택 ──────────────────────────────────────────
        st.markdown(f"""
<div style="font-size:0.82rem;font-weight:700;color:#4F46E5;
     letter-spacing:0.3px;margin-bottom:8px;">
  🎨 인포그래픽 스타일 선택
</div>
""", unsafe_allow_html=True)

        style_keys = list(_STYLES.keys())
        if "secret_style" not in st.session_state:
            st.session_state["secret_style"] = "만화 대화형"

        # 5열 스타일 선택 버튼 (만화 대화형 NEW 강조)
        s_cols = st.columns(len(style_keys))
        for i, sk in enumerate(style_keys):
            with s_cols[i]:
                emoji = _STYLES[sk][0]
                is_sel = st.session_state["secret_style"] == sk
                btn_style = (
                    "background:#4F46E5;color:white;border:none;"
                    if is_sel else
                    "background:#F8FAFC;color:#334155;border:1.5px solid #E2E8F0;"
                )
                if st.button(
                    f"{emoji} {sk}",
                    key=f"style_btn_{sk}",
                    use_container_width=True,
                ):
                    st.session_state["secret_style"] = sk
                    st.rerun()

        # 선택된 스타일 설명
        sel_style = st.session_state["secret_style"]
        _, sel_color, sel_bg, sel_desc = _STYLES[sel_style]
        st.markdown(f"""
<div style="background:{sel_bg};border-left:4px solid {sel_color};
     border-radius:0 10px 10px 0;padding:10px 14px;margin:8px 0 16px 0;
     font-size:0.82rem;color:#334155;">
  <b style="color:{sel_color};">{sel_style}</b> — {sel_desc}
</div>
""", unsafe_allow_html=True)

        # ── 템플릿 선택 ──────────────────────────────────────────
        st.markdown(f"""
<div style="font-size:0.82rem;font-weight:700;color:#4F46E5;
     letter-spacing:0.3px;margin-bottom:6px;">
  📌 내용 템플릿 (선택)
</div>
""", unsafe_allow_html=True)

        tmpl_key = st.selectbox(
            "템플릿", list(_TEMPLATES.keys()),
            key="secret_tmpl", label_visibility="collapsed",
        )
        if tmpl_key != "직접 입력":
            if st.button("📋 템플릿 불러오기", key="tmpl_load"):
                st.session_state["secret_content"] = _TEMPLATES[tmpl_key]
                st.rerun()

        # ── 제목 + 내용 입력 ─────────────────────────────────────
        st.markdown(f"""
<div style="font-size:0.82rem;font-weight:700;color:#4F46E5;
     letter-spacing:0.3px;margin:14px 0 6px 0;">
  📝 반반쌤 학습 내용 입력
</div>
""", unsafe_allow_html=True)

        title_input = st.text_input(
            "비법노트 제목", key="secret_title",
            placeholder="예: 조동사 may 완벽 정리 · 본문 핵심 표현 모음",
            label_visibility="collapsed",
        )
        st.caption("📌 제목을 입력하세요 (예: 조동사 may 완벽 정리)")

        content_input = st.text_area(
            "정리할 내용", key="secret_content",
            height=220,
            placeholder=(
                "반반쌤이 선별한 핵심 내용을 여기에 정리하세요.\n\n"
                "예시:\n"
                "■ may + 동사원형\n"
                "  ① 허가: ~해도 된다 → You may sit here.\n"
                "  ② 추측: ~일지도 모른다 → It may rain.\n\n"
                "■ 혼동 주의!\n"
                "  can vs may 차이: can은 능력, may는 허가(정중)\n\n"
                "■ 권쌤 암기 팁: 'May I~?'는 허가 요청 = 허락 요청 의문문"
            ),
            label_visibility="collapsed",
        )
        st.caption("✏️ 문법 규칙, 예문, 단어 정리, 암기 팁 등 자유롭게 입력")

        # ── 생성 버튼 ────────────────────────────────────────────
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        _gen_label = {
            "만화 대화형": "🗨️ 반반쌤 × 학생 캐릭터 대화 비법노트 생성",
        }.get(sel_style, "✨ 반반쌤 비법노트 생성")

        if st.button(
            _gen_label,
            type="primary", use_container_width=True, key="secret_gen_btn"
        ):
            if not title_input.strip():
                st.error("❌ 제목을 입력해주세요.")
            elif not content_input.strip():
                st.error("❌ 정리할 내용을 입력해주세요.")
            else:
                from plans import can_use_ai, increment_ai_usage, upgrade_banner
                _aiok, _, _ = can_use_ai()
                if not _aiok:
                    upgrade_banner("student", compact=True)
                    st.stop()
                increment_ai_usage()
                _spin_msg = {
                    "만화 대화형": "👩‍🏫 반반쌤과 학생이 대화를 나누는 중… 🙋‍♂️",
                }.get(sel_style, f"'{sel_style}' 스타일 비법노트를 제작하는 중… 🎨")
                with st.spinner(_spin_msg):
                    try:
                        html = generate_secret_note_html(
                            teacher_input=content_input,
                            title=title_input,
                            api_config=api_config,
                            style=sel_style,
                        )
                        st.session_state["secret_preview_html"]  = html
                        st.session_state["secret_preview_title"] = title_input
                        st.session_state["secret_note_id"]       = note_id
                        st.session_state["secret_preview_style"] = sel_style
                    except Exception as e:
                        err = str(e)
                        if "does not exist" in err or "42501" in err:
                            st.error(
                                "❌ Supabase 테이블 문제입니다.\n"
                                "supabase_rls_fix.sql 을 Supabase SQL Editor에서 실행하세요."
                            )
                        else:
                            st.error(f"생성 실패: {err}")

        # ── 미리보기 ─────────────────────────────────────────────
        if st.session_state.get("secret_preview_html"):
            prev_style = st.session_state.get("secret_preview_style", "카드형")
            prev_emoji = _STYLES.get(prev_style, ("✨",))[0]
            st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px 0;">
  <div style="width:3px;height:20px;background:#4F46E5;border-radius:2px;"></div>
  <div style="font-weight:700;color:#1E293B;font-size:1rem;">
    {prev_emoji} 미리보기 — {st.session_state['secret_preview_title']}
  </div>
  <div style="background:#EEF2FF;color:#4F46E5;font-size:0.7rem;
       padding:2px 8px;border-radius:10px;font-weight:600;">{prev_style}</div>
</div>
""", unsafe_allow_html=True)

            components.html(
                st.session_state["secret_preview_html"],
                height=650, scrolling=True,
            )

            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                if st.button("💾 저장하기", type="primary", use_container_width=True):
                    try:
                        save_secret_note(
                            note_id=st.session_state.get("secret_note_id") or 0,
                            title=st.session_state["secret_preview_title"],
                            html_content=st.session_state["secret_preview_html"],
                        )
                        st.success("✅ 비법노트 저장 완료!")
                        for k in ["secret_preview_html", "secret_preview_title",
                                  "secret_preview_style"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                    except Exception as e:
                        err = str(e)
                        if "42501" in err or "does not exist" in err:
                            st.error(
                                "❌ Supabase RLS 오류 — supabase_rls_fix.sql 실행 후 재시도"
                            )
                        else:
                            st.error(f"저장 실패: {err}")
            with col2:
                if st.button("🔄 다른 스타일로 재생성", use_container_width=True):
                    for k in ["secret_preview_html", "secret_preview_title",
                              "secret_preview_style"]:
                        st.session_state.pop(k, None)
                    st.rerun()
            with col3:
                if st.button("🗑️ 취소", use_container_width=True):
                    for k in ["secret_preview_html", "secret_preview_title",
                              "secret_preview_style"]:
                        st.session_state.pop(k, None)
                    st.rerun()

    # ══════════════════════════════════════════════════════════════
    # 탭 2: 🤖 자동 비법 만들기
    # ══════════════════════════════════════════════════════════════
    with tab_auto:
        if not note:
            st.info("왼쪽 사이드바에서 노트를 선택하면 자동으로 분석합니다.")
        else:
            _auto_items_key    = f"auto_items_{note_id}"
            _auto_sel_key      = f"auto_sel_{note_id}"
            _auto_prev_key     = "auto_preview_html"
            _auto_ptitle_key   = "auto_preview_title"
            _auto_pstyle_key   = "auto_preview_style"

            # ── 분석 결과 헤더 ──────────────────────────────────
            st.markdown(f"""
<div style="background:linear-gradient(135deg,#F5F3FF,#EDE9FE);
     border:1.5px solid #C4B5FD;border-radius:14px;
     padding:14px 18px;margin-bottom:16px;">
  <div style="font-size:1rem;font-weight:800;color:#5B21B6;margin-bottom:4px;">
    🤖 AI 핵심 포인트 자동 분석
  </div>
  <div style="font-size:0.82rem;color:#7C3AED;line-height:1.6;">
    반반노트 <b>"{note_title}"</b>의 본문·대화문·단어를 AI가 분석해<br>
    내신에 꼭 나올 <b>문법 / 어휘 / 표현</b> 아이템을 뽑아드려요.<br>
    원하는 항목만 체크하고 스타일 선택 → 비법노트 자동 완성!
  </div>
</div>
""", unsafe_allow_html=True)

            # ── 분석 시작 버튼 ───────────────────────────────────
            col_analyze, col_reset = st.columns([3, 1])
            with col_analyze:
                if st.button("🔍 AI 핵심 포인트 분석하기",
                             use_container_width=True, type="primary",
                             key="auto_analyze_btn"):
                    with st.spinner("🤖 반반쌤 AI가 노트를 분석하는 중… (10-20초)"):
                        try:
                            items = analyze_note_for_secrets(note, api_config)
                            st.session_state[_auto_items_key] = items
                            st.session_state[_auto_sel_key]   = set(range(len(items)))
                            # 미리보기 초기화
                            for k in [_auto_prev_key, _auto_ptitle_key, _auto_pstyle_key]:
                                st.session_state.pop(k, None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"분석 실패: {e}")

            with col_reset:
                if st.button("🔄 재분석", use_container_width=True,
                             key="auto_reanalyze_btn"):
                    for k in [_auto_items_key, _auto_sel_key,
                              _auto_prev_key, _auto_ptitle_key, _auto_pstyle_key]:
                        st.session_state.pop(k, None)
                    st.rerun()

            # ── 아이템 목록 ──────────────────────────────────────
            items: list = st.session_state.get(_auto_items_key, [])
            if not items:
                st.markdown("""
<div style="text-align:center;padding:30px;color:#9CA3AF;font-size:0.88rem;">
  위 버튼을 눌러 분석을 시작하세요 👆
</div>
""", unsafe_allow_html=True)
            else:
                sel_set: set = st.session_state.get(_auto_sel_key, set(range(len(items))))

                _TYPE_META = {
                    "grammar":    ("📝 문법",    "#7C3AED", "#F5F3FF"),
                    "vocab":      ("📚 어휘",    "#0891B2", "#F0F9FF"),
                    "expression": ("💬 표현",    "#059669", "#ECFDF5"),
                }
                _IMP_COLOR = {5: "#DC2626", 4: "#D97706", 3: "#4F46E5",
                              2: "#059669", 1: "#9CA3AF"}

                # 전체 선택 / 해제
                c1, c2, c3 = st.columns([2, 2, 2])
                with c1:
                    if st.button("☑️ 전체 선택", use_container_width=True,
                                 key="auto_sel_all"):
                        st.session_state[_auto_sel_key] = set(range(len(items)))
                        st.rerun()
                with c2:
                    if st.button("☐ 전체 해제", use_container_width=True,
                                 key="auto_desel_all"):
                        st.session_state[_auto_sel_key] = set()
                        st.rerun()
                with c3:
                    st.markdown(
                        f'<div style="padding:8px;text-align:center;font-size:0.8rem;'
                        f'color:#4F46E5;font-weight:700;">'
                        f'{len(sel_set)}/{len(items)}개 선택됨</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown("<div style='margin-bottom:8px;'></div>",
                            unsafe_allow_html=True)

                # 아이템 카드 렌더링
                for idx, item in enumerate(items):
                    type_key  = item.get("type", "grammar")
                    type_label, type_color, type_bg = _TYPE_META.get(
                        type_key, ("📝 문법", "#7C3AED", "#F5F3FF"))
                    imp       = item.get("importance", 3)
                    imp_color = _IMP_COLOR.get(imp, "#4F46E5")
                    imp_stars = "★" * imp + "☆" * (5 - imp)
                    imp_label = {5:"반드시출제",4:"출제가능",3:"보통",
                                 2:"참고",1:"선택"}.get(imp, "")
                    is_checked = idx in sel_set

                    border = f"2px solid {type_color}" if is_checked else "1.5px solid #E5E7EB"
                    alpha  = "1" if is_checked else "0.5"

                    st.markdown(f"""
<div style="background:white;border:{border};border-radius:12px;
     padding:12px 14px;margin-bottom:8px;opacity:{alpha};
     transition:all 0.2s;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
    <span style="background:{type_bg};color:{type_color};
      font-size:0.68rem;font-weight:700;padding:2px 8px;
      border-radius:20px;">{type_label}</span>
    <span style="background:{imp_color}22;color:{imp_color};
      font-size:0.68rem;font-weight:700;padding:2px 8px;
      border-radius:20px;">{imp_stars} {imp_label}</span>
  </div>
  <div style="font-size:0.95rem;font-weight:800;color:#1E293B;
       margin-bottom:3px;">{item.get('icon','')} {item.get('title','')}</div>
  <div style="font-size:0.8rem;color:#475569;margin-bottom:4px;">
    {item.get('description','')}</div>
  {f'<div style="font-size:0.75rem;color:#64748B;font-style:italic;">예: {item["examples"][0]}</div>' if item.get("examples") else ""}
  {f'<div style="font-size:0.72rem;color:{type_color};margin-top:4px;">💡 {item["tip"]}</div>' if item.get("tip") else ""}
</div>
""", unsafe_allow_html=True)

                    checked = st.checkbox(
                        f"선택: {item.get('title','')}",
                        value=is_checked,
                        key=f"auto_chk_{note_id}_{idx}",
                        label_visibility="collapsed",
                    )
                    if checked != is_checked:
                        new_sel = set(sel_set)
                        if checked:
                            new_sel.add(idx)
                        else:
                            new_sel.discard(idx)
                        st.session_state[_auto_sel_key] = new_sel
                        st.rerun()

                # ── 스타일 선택 + 생성 ───────────────────────────
                st.markdown("---")
                st.markdown("""
<div style="font-size:0.85rem;font-weight:700;color:#4F46E5;margin-bottom:8px;">
  🎨 인포그래픽 스타일 선택
</div>
""", unsafe_allow_html=True)

                if "auto_style" not in st.session_state:
                    st.session_state["auto_style"] = "만화 대화형"

                style_keys = list(_STYLES.keys())
                sa_cols = st.columns(len(style_keys))
                for i, sk in enumerate(style_keys):
                    with sa_cols[i]:
                        emoji  = _STYLES[sk][0]
                        is_sel = st.session_state["auto_style"] == sk
                        if st.button(f"{emoji} {sk}",
                                     key=f"auto_style_btn_{sk}",
                                     use_container_width=True,
                                     type="primary" if is_sel else "secondary"):
                            st.session_state["auto_style"] = sk
                            st.rerun()

                sel_auto_style = st.session_state["auto_style"]
                _, ac, ab, ad  = _STYLES[sel_auto_style]
                st.markdown(f"""
<div style="background:{ab};border-left:4px solid {ac};
     border-radius:0 10px 10px 0;padding:8px 14px;margin:6px 0 14px;
     font-size:0.8rem;color:#334155;">
  <b style="color:{ac};">{sel_auto_style}</b> — {ad}
</div>
""", unsafe_allow_html=True)

                selected_items = [items[i] for i in sorted(sel_set) if i < len(items)]

                if st.button(
                    f"✨ 선택한 {len(selected_items)}개 항목으로 비법노트 생성",
                    type="primary", use_container_width=True,
                    key="auto_gen_btn",
                    disabled=(len(selected_items) == 0),
                ):
                    if not selected_items:
                        st.warning("최소 1개 이상 항목을 선택하세요.")
                    else:
                        _spin = {
                            "만화 대화형": "👩‍🏫 반반쌤 × 학생 캐릭터가 대화를 나누는 중…",
                        }.get(sel_auto_style,
                              f"'{sel_auto_style}' 스타일로 비법노트 제작 중…")
                        with st.spinner(_spin):
                            try:
                                html = generate_secret_note_from_items(
                                    items=selected_items,
                                    style=sel_auto_style,
                                    api_config=api_config,
                                    note_title=note_title,
                                )
                                st.session_state[_auto_prev_key]   = html
                                st.session_state[_auto_ptitle_key] = (
                                    f"{note_title} — AI 핵심 비법노트")
                                st.session_state[_auto_pstyle_key] = sel_auto_style
                            except Exception as e:
                                st.error(f"생성 실패: {e}")

                # ── 미리보기 + 저장 ──────────────────────────────
                if st.session_state.get(_auto_prev_key):
                    prev_style = st.session_state.get(_auto_pstyle_key, "카드형")
                    prev_emoji = _STYLES.get(prev_style, ("✨",))[0]
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px;">
  <div style="width:3px;height:20px;background:#7C3AED;border-radius:2px;"></div>
  <div style="font-weight:700;color:#1E293B;font-size:1rem;">
    {prev_emoji} 미리보기 — {st.session_state.get(_auto_ptitle_key,'')}
  </div>
  <div style="background:#F5F3FF;color:#7C3AED;font-size:0.7rem;
       padding:2px 8px;border-radius:10px;font-weight:600;">{prev_style}</div>
</div>
""", unsafe_allow_html=True)

                    import streamlit.components.v1 as _comp
                    _comp.html(st.session_state[_auto_prev_key],
                               height=650, scrolling=True)

                    sv1, sv2, sv3 = st.columns([2, 2, 1])
                    with sv1:
                        if st.button("💾 비법노트에 저장",
                                     type="primary", use_container_width=True,
                                     key="auto_save_btn"):
                            try:
                                from study_db import save_secret_note as _ssn
                                _ssn(
                                    note_id=note_id or 0,
                                    title=st.session_state[_auto_ptitle_key],
                                    html_content=st.session_state[_auto_prev_key],
                                )
                                # grammar_points 테이블에도 저장 (분석 결과 보존)
                                if note_id:
                                    from study_db import save_grammar_point
                                    for itm in selected_items:
                                        if itm.get("type") == "grammar":
                                            try:
                                                save_grammar_point(
                                                    note_id=note_id,
                                                    point_name=itm["title"],
                                                    category="grammar",
                                                    explanation_kr=itm.get("description",""),
                                                    patterns=[],
                                                    examples=itm.get("examples", []),
                                                    tip=itm.get("tip",""),
                                                    ai_generated=True,
                                                )
                                            except Exception:
                                                pass
                                st.success("✅ 비법노트 저장 완료!")
                                for k in [_auto_prev_key, _auto_ptitle_key, _auto_pstyle_key]:
                                    st.session_state.pop(k, None)
                                st.rerun()
                            except Exception as e:
                                err = str(e)
                                if "42501" in err or "does not exist" in err:
                                    st.error("❌ Supabase RLS 오류 — supabase_rls_fix.sql 실행")
                                else:
                                    st.error(f"저장 실패: {err}")
                    with sv2:
                        if st.button("🔄 다른 스타일로 재생성",
                                     use_container_width=True, key="auto_regen_btn"):
                            for k in [_auto_prev_key, _auto_ptitle_key, _auto_pstyle_key]:
                                st.session_state.pop(k, None)
                            st.rerun()
                    with sv3:
                        if st.button("🗑️ 취소", use_container_width=True,
                                     key="auto_cancel_btn"):
                            for k in [_auto_prev_key, _auto_ptitle_key, _auto_pstyle_key]:
                                st.session_state.pop(k, None)
                            st.rerun()

    # ══════════════════════════════════════════════════════════════
    # 탭 3: 저장된 비법노트
    # ══════════════════════════════════════════════════════════════
    with tab_saved:
        try:
            saved = list_secret_notes(note_id)
        except Exception as e:
            err = str(e)
            if "42501" in err or "does not exist" in err:
                st.error(
                    "❌ Supabase RLS/테이블 오류 — supabase_rls_fix.sql 을 실행하세요."
                )
            else:
                st.error(f"불러오기 실패: {err}")
            saved = []

        if not saved:
            st.markdown(f"""
<div style="text-align:center;padding:48px 20px;background:#FAFAFE;
     border-radius:16px;border:2px dashed #C7D2FE;margin:20px 0;">
  <div style="font-size:3rem;margin-bottom:12px;">✨</div>
  <div style="font-size:1.1rem;font-weight:800;color:#7C3AED;">
    아직 저장된 비법노트가 없어요
  </div>
  <div style="color:#94A3B8;font-size:0.85rem;margin-top:6px;">
    '새로 만들기' 탭에서 <b>만화 대화형</b>으로 재미있는 비법노트를 만들어보세요!
  </div>
  <div style="margin-top:14px;font-size:1.8rem;">🗨️ 👩‍🏫 💬 🙋</div>
  <div style="margin-top:16px;font-size:2rem;">🎨 📊 🃏 🌐</div>
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
<div style="font-size:0.82rem;color:#64748B;margin-bottom:12px;">
  총 <b style="color:#4F46E5;">{len(saved)}</b>개의 비법노트
  — 클릭해서 펼쳐보세요
</div>
""", unsafe_allow_html=True)

            for s in saved:
                created = s.get("created_at", "")[:10]
                title_s = s.get("title", "제목 없음")

                with st.expander(f"✨  {title_s}  ·  {created}", expanded=False):
                    components.html(s["html_content"], height=600, scrolling=True)

                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.caption(f"저장일: {created}")
                    with c2:
                        if confirm_delete_btn(
                            "삭제", key=f"del_secret_{s['id']}",
                            item_name=title_s,
                            use_container_width=True,
                        ):
                            _delete_secret_note(s["id"])
                            st.rerun()
