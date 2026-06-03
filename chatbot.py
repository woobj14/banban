# chatbot.py — 반쌤 AI 영어 튜터 채팅 페이지
# 반반 BanBan | 페르소나: 반쌤 (따뜻한 AI 영어 선생님)

import os
import streamlit as st
from icons import icon, section_md

# ─────────────────────────────────────────────────────────────────────────────
# 반쌤 시스템 프롬프트
# ─────────────────────────────────────────────────────────────────────────────

BANSAM_SYSTEM = """당신은 '반쌤'입니다. 반반 BanBan 영어 학습 플랫폼의 AI 영어 선생님입니다.

[성격 & 말투]
- 따뜻하고 인내심 있는 선생님처럼 말합니다.
- 학생이 틀렸을 때도 "괜찮아요, 많이들 어려워하는 부분이에요 😊"처럼 격려합니다.
- 어려운 문법도 쉬운 예문 위주로 설명합니다.
- 친근하지만 정중한 존댓말을 씁니다. 반말은 절대 사용하지 않습니다.
- 이모지는 가끔 자연스럽게 사용합니다 (과도하게 남발하지 않음).
- 학원 선생님 같은 친근한 분위기를 유지합니다.

[역할]
- 영어 문법 질문 답변 (예문 2~3개와 함께 명확하게 설명)
- 단어 의미·발음·사용법 설명
- 영어 작문 교정 및 피드백
- 학습 방법 조언 및 동기부여
- 내신·수능 영어 시험 준비 도움
- 오답 원인 분석 및 반복 실수 예방 조언

[답변 스타일]
- 설명 후 "혹시 더 궁금한 점 있으면 물어보세요 😊" 같은 열린 마무리를 합니다.
- 복잡한 개념은 단계별로 나눠서 설명합니다.
- 예문은 실생활에서 자주 쓰이는 자연스러운 문장을 사용합니다.
- 영어와 한국어를 자연스럽게 섞어 사용합니다.

[금지 사항]
- 영어 학습과 직접 관련 없는 주제(수학, 과학, 다른 과목 등)는 "저는 영어 학습만 도와드릴 수 있어요 😊"라고 안내합니다.
- 숙제 전체를 그냥 다 해주지 않고, 방향과 힌트를 제시합니다.
- 학생이 직접 생각하고 풀 수 있도록 유도합니다.

[첫 인사 예시]
"안녕하세요! 저는 반쌤이에요 😊 영어 공부하다가 모르는 게 생기면 언제든 물어보세요. 문법이든 단어든 작문이든 다 괜찮아요!"
"""

BANSAM_GREETING = (
    "안녕하세요! 저는 반쌤이에요 😊\n\n"
    "영어 공부하다가 모르는 게 생기면 언제든 물어보세요.\n"
    "문법, 단어, 작문, 시험 준비 — 다 괜찮아요!\n\n"
    "어떤 부분이 궁금하신가요?"
)


# ─────────────────────────────────────────────────────────────────────────────
# API 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def _get_api_type() -> str | None:
    """사용 가능한 API 종류 반환 ('anthropic' | 'gemini' | None)"""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return None


def _call_anthropic(messages: list[dict], system: str) -> str:
    """Anthropic Claude API 호출"""
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        return f"[반쌤 오류] API 연결에 문제가 생겼어요. 잠시 후 다시 시도해주세요. ({e})"


def _call_gemini(messages: list[dict], system: str) -> str:
    """Google Gemini API 호출 (신버전 google-genai SDK 사용)"""
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

        # system + 이전 대화 + 마지막 사용자 메시지를 하나의 프롬프트로 합치기
        # (Gemini는 system_instruction을 GenerateContentConfig으로 전달)
        history_text = ""
        for m in messages[:-1]:
            role_label = "학생" if m["role"] == "user" else "반쌤"
            history_text += f"\n{role_label}: {m['content']}"

        last_user_msg = messages[-1]["content"] if messages else ""

        full_prompt = history_text + f"\n학생: {last_user_msg}" if history_text else last_user_msg

        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[full_prompt],
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=1500,
            ),
        )
        return resp.text
    except Exception as e:
        return f"[반쌤 오류] API 연결에 문제가 생겼어요. 잠시 후 다시 시도해주세요. ({e})"


def get_bansam_reply(messages: list[dict]) -> str:
    """현재 설정된 API로 반쌤 응답 생성"""
    api = _get_api_type()
    if api == "anthropic":
        return _call_anthropic(messages, BANSAM_SYSTEM)
    if api == "gemini":
        return _call_gemini(messages, BANSAM_SYSTEM)
    return (
        "현재 AI 연결이 설정되지 않았어요.\n"
        ".env 파일에 ANTHROPIC_API_KEY 또는 GEMINI_API_KEY를 추가해주세요."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 채팅 페이지 렌더링
# ─────────────────────────────────────────────────────────────────────────────

def render_chatbot():
    """반쌤 AI 튜터 채팅 메인 렌더러"""

    # ── 페이지 헤더 ──────────────────────────────────────────────────
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#4F46E5,#7C3AED);
     color:white;border-radius:14px;padding:18px 22px;margin-bottom:20px;">
  <div style="font-size:0.82rem;opacity:0.85;">
    {icon("message-circle", 14, "rgba(255,255,255,0.85)")} AI 튜터
  </div>
  <div style="font-size:1.45rem;font-weight:900;margin-top:3px;letter-spacing:-0.5px;">
    반쌤에게 질문하기
  </div>
  <div style="font-size:0.82rem;opacity:0.8;margin-top:5px;">
    영어 문법 · 단어 · 작문 · 시험 준비 — 언제든 물어보세요
  </div>
</div>
""", unsafe_allow_html=True)

    api_type = _get_api_type()

    # API 미설정 경고
    if not api_type:
        st.markdown(f"""
<div style="background:rgba(245,158,11,0.12);border:1px solid rgba(245,158,11,0.3);
     border-radius:12px;padding:14px 16px;margin-bottom:16px;">
  <div style="color:#FCD34D;font-weight:700;font-size:0.88rem;margin-bottom:6px;">
    {icon("alert-circle", 15, "#F59E0B")} AI 연결 미설정
  </div>
  <div style="color:#FDE68A;font-size:0.82rem;line-height:1.8;">
    .env 파일에 <b>ANTHROPIC_API_KEY</b> 또는 <b>GEMINI_API_KEY</b>를 추가하면 반쌤이 활성화됩니다.
  </div>
</div>
""", unsafe_allow_html=True)
        return

    # ── 채팅 히스토리 초기화 ──────────────────────────────────────────
    if "bansam_messages" not in st.session_state:
        st.session_state["bansam_messages"] = [
            {"role": "assistant", "content": BANSAM_GREETING}
        ]

    # ── 유용한 질문 예시 버튼 ──────────────────────────────────────────
    if len(st.session_state["bansam_messages"]) == 1:
        st.markdown(f"""
<div style="font-size:0.78rem;color:#64748B;font-weight:600;margin-bottom:8px;">
  {icon("zap", 11, "#818CF8")} 이런 질문을 해보세요
</div>
""", unsafe_allow_html=True)
        example_qs = [
            "can과 could의 차이는?",
            "가정법 if문 쉽게 설명해줘요",
            "이 문장 문법 맞나요 확인해주세요",
            "단어 암기 잘하는 방법 알려주세요",
        ]
        cols = st.columns(2)
        for i, q in enumerate(example_qs):
            if cols[i % 2].button(q, key=f"example_q_{i}", use_container_width=True):
                st.session_state["bansam_messages"].append({"role": "user", "content": q})
                with st.spinner("반쌤이 답변을 쓰고 있어요..."):
                    reply = get_bansam_reply(
                        [m for m in st.session_state["bansam_messages"]
                         if m["role"] != "assistant" or m["content"] != BANSAM_GREETING]
                    )
                st.session_state["bansam_messages"].append({"role": "assistant", "content": reply})
                st.rerun()

        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

    # ── 채팅 메시지 표시 ──────────────────────────────────────────────
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["bansam_messages"]:
            if msg["role"] == "assistant":
                with st.chat_message("assistant", avatar="🧑‍🏫"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("user", avatar="🙋"):
                    st.markdown(msg["content"])

    # ── 입력창 ────────────────────────────────────────────────────────
    user_input = st.chat_input(
        "반쌤에게 영어 질문 입력… (예: 관계대명사 who와 which 차이가 뭐예요?)"
    )

    if user_input and user_input.strip():
        # 사용자 메시지 추가
        st.session_state["bansam_messages"].append(
            {"role": "user", "content": user_input.strip()}
        )

        # API 전송용 메시지 (greeting 제외한 실제 대화 내용)
        api_messages = [
            m for m in st.session_state["bansam_messages"]
            if not (m["role"] == "assistant" and m["content"] == BANSAM_GREETING)
        ]

        # 반쌤 응답 생성 (스트리밍 없이 한 번에)
        with st.spinner("반쌤이 답변을 쓰고 있어요..."):
            reply = get_bansam_reply(api_messages)

        st.session_state["bansam_messages"].append(
            {"role": "assistant", "content": reply}
        )
        st.rerun()

    # ── 대화 초기화 버튼 ──────────────────────────────────────────────
    if len(st.session_state["bansam_messages"]) > 1:
        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
        _, reset_col = st.columns([5, 1])
        with reset_col:
            if st.button("대화 초기화", key="bansam_reset", use_container_width=True):
                st.session_state["bansam_messages"] = [
                    {"role": "assistant", "content": BANSAM_GREETING}
                ]
                st.rerun()
