# study_ai.py — S.Y. 담당: 학습 AI 헬퍼 모듈
# 단어 정의 생성, 내신문제 생성, 오답 해설, 비법노트 인포그래픽

import json
import re
from study_db import get_word_cache, save_word_cache


# ─────────────────────────────────────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict | list:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if m:
        raw = m.group(1)
    raw = raw.strip()
    start = raw.find("{")
    if start < 0:
        start = raw.find("[")
    if start > 0:
        raw = raw[start:]
    return json.loads(raw)


def _call_text(prompt: str, api_config: dict) -> str:
    """텍스트 전용 AI 호출 — 3단 폴백 체인.

    호출 순서:
      1) Gemini 키1 (GEMINI_API_KEY)       — 기본, 저렴·빠름
      2) Gemini 키2 (GEMINI_API_KEY_2)     — 키1 429/실패 시
      3) Claude Haiku (ANTHROPIC_API_KEY)  — Gemini 전부 실패 시
    """
    from google import genai as _genai

    # 키 목록 구성 (새 멀티키 + 구형 단일키 하위 호환)
    gemini_keys   = api_config.get("gemini_keys") or []
    anthropic_key = api_config.get("anthropic_key", "").strip()

    if not gemini_keys:
        # 구형 단일키 방식 호환
        atype = api_config.get("type", "")
        key   = api_config.get("key", "").strip()
        gk    = api_config.get("gemini_key", "").strip()
        if gk:   gemini_keys = [gk]
        elif atype == "gemini" and key:   gemini_keys = [key]
        elif atype == "anthropic" and key: anthropic_key = anthropic_key or key

    last_err = None

    # ── Gemini 키 순서대로 시도 ─────────────────────────────────────
    for idx, gkey in enumerate(gemini_keys, 1):
        try:
            client = _genai.Client(api_key=gkey)
            resp   = client.models.generate_content(
                model="gemini-2.5-flash", contents=[prompt]
            )
            return resp.text
        except Exception as e:
            last_err = e
            remaining_gemini = len(gemini_keys) - idx
            if remaining_gemini > 0:
                # 다음 Gemini 키로 재시도
                continue
            # Gemini 키 소진 → Claude 폴백
            if anthropic_key:
                try:
                    import streamlit as st
                    st.toast("⚡ Gemini 한도 → Claude Haiku 전환", icon="🔄")
                except Exception:
                    pass

    # ── Claude Haiku 폴백 ────────────────────────────────────────────
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            resp   = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=8192,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        except Exception as e:
            last_err = e

    raise ValueError(f"모든 AI 키 실패: {last_err}")


# ─────────────────────────────────────────────────────────────────────────────
# 단어 영영사전 정의 + 예문 (캐시 포함)
# ─────────────────────────────────────────────────────────────────────────────

def get_word_info(word_en: str, api_config: dict) -> dict:
    """영어 단어 → {definition: str, example: str}  (DB 캐시 우선)"""
    cached = get_word_cache(word_en)
    if cached and cached.get("definition"):
        return {"definition": cached["definition"], "example": cached["example"]}

    prompt = f"""You are an English teacher for Korean middle school students.
For the word/phrase "{word_en}", provide:
1. A simple English definition (one sentence, max 15 words, suitable for Korean middle school)
2. One example sentence (simple, under 15 words)

Return ONLY JSON:
{{"definition": "...", "example": "..."}}"""

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        defn = data.get("definition", "")
        exmp = data.get("example", "")
        save_word_cache(word_en, defn, exmp)
        return {"definition": defn, "example": exmp}
    except Exception as e:
        return {"definition": f"(조회 실패: {e})", "example": ""}


# ─────────────────────────────────────────────────────────────────────────────
# 내신 문제 생성 — 반반쌤 페르소나
# ─────────────────────────────────────────────────────────────────────────────

_EXAM_TYPES = {
    "빈칸": "Fill in the blank (choose from options)",
    "문법": "Grammar error correction (find the wrong word/phrase)",
    "일치": "True/False about passage content",
    "순서": "Sentence ordering (arrange scrambled sentences)",
    "주제": "Main topic / title selection",
    "서술형": "Short answer (Korean explanation in 1-2 sentences)",
}

_DIFFICULTY_DESC = {
    "easy":   "쉬운 난이도 (중1 수준, 직접적인 정보 찾기)",
    "medium": "중간 난이도 (중2 수준, 추론 필요)",
    "hard":   "어려운 난이도 (중3 수준, 심화 응용)",
}


def generate_exam_questions(
    text_data: dict,
    words: list[tuple],
    dialogues: list[dict],
    difficulty: str,
    api_config: dict,
    n_questions: int = 5,
    scope: str = "전체",
    avoid: list[str] | None = None,
) -> list[dict]:
    """
    반반쌤 페르소나로 내신 문제 생성.

    scope: "단어" | "대화문" | "본문" | "전체"
           선택된 범위의 자료만 사용해 집중 출제.
    avoid: 이미 출제된 문제 텍스트 목록 → 중복 회피.

    Returns list of:
    {
      "type": "빈칸"|"문법"|"일치"|"순서"|"주제"|"서술형",
      "question": str,         # 문제 본문
      "passage": str,          # 관련 지문 (있으면)
      "options": list[str],    # 보기 (객관식만, 없으면 [])
      "answer": str,           # 정답
      "answer_kr": str,        # 정답 한국어 설명
      "difficulty": str,
    }
    """
    use_word = scope in ("단어", "전체")
    use_dlg  = scope in ("대화문", "전체")
    use_text = scope in ("본문", "전체")

    # 본문 요약 구성
    passage_lines = []
    if text_data.get("sections"):
        for sec in text_data["sections"]:
            for en, kr in sec.get("sentences", []):
                passage_lines.append(f"{en}")
    elif text_data.get("sentences"):
        for en, kr in text_data.get("sentences", []):
            passage_lines.append(en)
    passage_text = "\n".join(passage_lines[:30]) if use_text else ""

    word_list = "\n".join(f"- {en}: {kr}" for en, kr in words[:30]) if use_word else ""
    dlg_text  = ""
    if use_dlg:
        for dlg in dialogues[:3]:
            dlg_text += f"\n[{dlg['title']}]\n"
            for en, kr in dlg.get("lines", [])[:6]:
                dlg_text += f"  {en}\n"

    diff_desc = _DIFFICULTY_DESC.get(difficulty, _DIFFICULTY_DESC["medium"])

    # 범위별 출제 지침
    _SCOPE_GUIDE = {
        "단어":   "단어의 의미·용법·어휘력을 평가하는 문제 위주로 출제 (빈칸, 어휘 의미, 영영뜻 매칭 등).",
        "대화문": "대화문의 맥락·의도·세부 내용 이해를 평가하는 문제 위주로 출제 (빈칸, 응답 고르기, 대화 일치).",
        "본문":   "본문의 내용 일치·주제·문법·문장 순서를 평가하는 문제 위주로 출제.",
        "전체":   "단어·대화문·본문을 골고루 활용해 다양한 유형으로 출제.",
    }
    scope_guide = _SCOPE_GUIDE.get(scope, _SCOPE_GUIDE["전체"])

    # 이미 출제된 문제 → 회피 목록 (최근 40개만, 프롬프트 비대화 방지)
    avoid = avoid or []
    avoid_block = ""
    if avoid:
        sample = [a for a in avoid if a][-40:]
        avoid_block = (
            "\n[이미 출제된 문제 — 절대 중복 금지]\n"
            + "\n".join(f"- {a[:80]}" for a in sample)
            + "\n위 문제들과 똑같거나 거의 비슷한 문제는 만들지 말고, 새로운 문제를 출제하세요.\n"
        )

    prompt = f"""당신은 대한민국 최고의 영어 선생님 반반쌤입니다.
친절하고 꼼꼼하게 학생들이 내신에서 높은 점수를 받을 수 있도록 문제를 출제합니다.
{avoid_block}

[학습 자료]
== 본문 ==
{passage_text if passage_text.strip() else "(이번 시험 범위 아님)"}

== 단어 ==
{word_list if word_list.strip() else "(이번 시험 범위 아님)"}

== 대화문 ==
{dlg_text if dlg_text.strip() else "(이번 시험 범위 아님)"}

[출제 조건]
- 시험 범위: {scope} 테스트 — {scope_guide}
- 난이도: {diff_desc}
- 문제 수: {n_questions}개
- 문제 유형 (범위에 맞게 다양하게): {', '.join(_EXAM_TYPES.keys())}
- 객관식은 보기 4개 (①②③④)
- 서술형은 한국어로 답 작성
- 반드시 위 '시험 범위'에 해당하는 자료만 사용해 출제 (다른 범위 자료 사용 금지)
- 실제 내신 시험 형식에 맞게 출제
- ★중요1★ 독해형 문제(일치/주제/순서)는 반드시 'passage' 필드에
  그 문제가 근거한 실제 본문/대화문 문장을 그대로 넣으세요.
  '윗글', '다음 글'이라고 하면서 passage를 비워두면 절대 안 됩니다.
- ★중요2★ 빈칸 문제는 빈칸(______)이 들어간 지문을 'question' 안에 직접 넣고,
  'passage' 필드는 반드시 비워두세요(""). passage에 정답이 든 원문을 넣으면
  학생이 지문만 보고 답을 알아버립니다. 절대 금지.

반드시 아래 JSON 형식만 반환 (다른 텍스트 절대 금지):
{{
  "questions": [
    {{
      "type": "빈칸",
      "question": "다음 빈칸에 알맞은 것을 고르시오.\\nJimin _____ her friend at the subway station.",
      "passage": "Jimin met her friend, Sora, at the subway station.",
      "options": ["① met", "② meets", "③ meet", "④ meeting"],
      "answer": "① met",
      "answer_kr": "과거시제 만나다 → met",
      "difficulty": "{difficulty}"
    }}
  ]
}}"""

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        qs   = data.get("questions", [])
        # 유효성 검사 + 중복 제거 (회피 목록 & 자체 중복)
        seen = {_norm_q(a) for a in avoid}
        valid = []
        for q in qs:
            if q.get("question") and q.get("answer"):
                key = _norm_q(q["question"])
                if key in seen:        # 기존/방금 생성분과 중복 → 스킵
                    continue
                seen.add(key)
                q.setdefault("type", "빈칸")
                q.setdefault("passage", "")
                q.setdefault("options", [])
                q.setdefault("answer_kr", "")
                q.setdefault("difficulty", difficulty)
                valid.append(q)

        # ── 지문 보정 ──────────────────────────────────────────────
        # ① 빈칸형: 문제에 이미 빈칸 지문이 들어있으면 별도 passage 제거
        #    (정답이 든 원문 전체가 지문으로 노출되어 답이 보이는 버그 방지)
        # ② 독해형(일치/주제/순서): passage 비면 노트 실제 본문/대화문 주입
        default_passage = passage_text.strip() if use_text else ""
        if not default_passage and use_dlg and dlg_text.strip():
            default_passage = dlg_text.strip()
        _ref = ("윗글", "다음 글", "글의", "지문",
                "다음을 읽", "본문", "according to", "the passage")
        _reading_types = ("일치", "주제", "순서")
        for q in valid:
            qtype  = q.get("type", "")
            qt_raw = q.get("question") or ""
            if "빈칸" in qtype:
                # 문제 본문에 빈칸(___)이 있으면 자기완결적 → 지문 박스 제거
                if "___" in qt_raw:
                    q["passage"] = ""
                continue
            if not (q.get("passage") or "").strip():
                qt = qt_raw.lower()
                needs = (qtype in _reading_types
                         or any(m.lower() in qt for m in _ref))
                if needs and default_passage:
                    q["passage"] = default_passage
        return valid
    except Exception as e:
        raise RuntimeError(f"문제 생성 실패: {e}") from e


def _norm_q(text: str) -> str:
    """문제 텍스트 정규화 — 공백·기호 차이 무시하고 중복 판정."""
    import re
    return re.sub(r"\s+", " ", re.sub(r"[^\w가-힣]", " ", (text or "").lower())).strip()


# ─────────────────────────────────────────────────────────────────────────────
# O/X (T/F) 이해도 문제 — 대화문당 3개, 본문 단락별 7개 이상
# ─────────────────────────────────────────────────────────────────────────────

def generate_ox_questions(text_data: dict, dialogues: list[dict],
                          api_config: dict) -> list[dict]:
    """대화문·본문 이해도 확인용 O/X 문제 생성.

    Returns list of:
    {
      "source": "대화문"|"본문",
      "group":  str,        # 대화문 제목 또는 단락 라벨
      "statement": str,     # 한국어 진술문
      "answer": "O"|"X",
      "explain": str,       # 한국어 해설
    }
    """
    if not api_config:
        return []

    # 대화문 블록
    dlg_blocks = []
    for d in (dialogues or []):
        title = d.get("title", "대화문")
        ens   = [ln[0] for ln in d.get("lines", [])
                 if isinstance(ln, (list, tuple)) and ln]
        if ens:
            dlg_blocks.append(f"[{title}]\n" + "\n".join(ens[:20]))

    # 본문 단락 블록
    sec_blocks = []
    for s in (text_data.get("sections") or []):
        label = s.get("label", "단락")
        ens   = [p[0] for p in s.get("sentences", [])
                 if isinstance(p, (list, tuple)) and p]
        if ens:
            sec_blocks.append(f"[{label}]\n" + " ".join(ens[:40]))
    # sections 없으면 sentences 전체를 한 단락으로
    if not sec_blocks and text_data.get("sentences"):
        ens = [p[0] for p in text_data["sentences"]
               if isinstance(p, (list, tuple)) and p]
        if ens:
            sec_blocks.append("[본문]\n" + " ".join(ens[:40]))

    if not dlg_blocks and not sec_blocks:
        return []

    prompt = f"""당신은 한국 중학생을 가르치는 영어 선생님 반반쌤입니다.
아래 대화문과 본문 내용에 대한 이해도를 확인하는 O/X(참/거짓) 문제를 만들어주세요.

[대화문]
{chr(10).join(dlg_blocks) if dlg_blocks else "(없음)"}

[본문 단락]
{chr(10).join(sec_blocks) if sec_blocks else "(없음)"}

출제 규칙:
- 대화문: 각 대화문당 정확히 3문제
- 본문: 각 단락당 7문제 이상
- 진술문은 한국어로, 내용 사실 확인형 (지문 근거로 참/거짓 명확)
- 절반 정도는 참(O), 절반은 거짓(X)으로 균형
- 거짓 문제는 지문과 그럴듯하게 다른 내용으로 (단순 부정 X)
- 해설은 한국어 1문장, 왜 O/X인지 지문 근거 제시

반드시 아래 JSON만 반환:
{{"questions": [
  {{"source": "대화문", "group": "대화문제목", "statement": "민수는 주말에 도서관에 갈 계획이다.", "answer": "O", "explain": "민수가 주말에 도서관에 간다고 말함."}},
  {{"source": "본문", "group": "단락라벨", "statement": "...", "answer": "X", "explain": "..."}}
]}}"""

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        out  = []
        _seen = set()
        for q in data.get("questions", []):
            ans = str(q.get("answer", "")).strip().upper()
            ans = "O" if ans in ("O", "참", "TRUE", "T") else "X" if ans in ("X", "거짓", "FALSE", "F") else ""
            _k = _norm_q(q.get("statement", ""))
            if _k in _seen:        # 동일 진술문 중복 제거
                continue
            if q.get("statement") and ans:
                _seen.add(_k)
                out.append({
                    "source":    q.get("source", "본문"),
                    "group":     q.get("group", ""),
                    "statement": q["statement"],
                    "answer":    ans,
                    "explain":   q.get("explain", ""),
                })
        return out
    except Exception as e:
        raise RuntimeError(f"O/X 문제 생성 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# 오답 해설
# ─────────────────────────────────────────────────────────────────────────────

def explain_wrong_answer(
    question: dict,
    user_answer: str,
    api_config: dict,
) -> str:
    """오답에 대한 친절한 AI 해설 반환 (한국어)"""
    prompt = f"""당신은 친절한 영어 선생님 반반쌤입니다.
학생이 아래 문제를 틀렸습니다. 왜 틀렸는지, 정답이 무엇인지 중학생이 이해하기 쉽게 한국어로 설명해주세요.
3-4문장으로 간결하게.

[문제]
{question.get('question', '')}

[지문]
{question.get('passage', '')}

[학생 답]: {user_answer}
[정답]: {question.get('answer', '')}
[정답 설명]: {question.get('answer_kr', '')}

친절하고 격려하는 말투로 설명해주세요. 마지막에 응원 한마디 추가."""

    try:
        return _call_text(prompt, api_config)
    except Exception as e:
        return f"(해설 생성 실패: {e})"


def explain_wrong_word(
    word_en: str,
    word_kr: str,
    wrong_count: int,
    api_config: dict,
) -> str:
    """오답 단어에 대한 친절한 해설 (한국어)"""
    prompt = f"""당신은 친절한 영어 선생님 반반쌤입니다.
학생이 '{word_en}({word_kr})' 단어를 {wrong_count}번 틀렸습니다.
이 단어를 확실히 외울 수 있도록 도와주세요.

다음을 포함해서 3-5문장으로 설명해주세요:
1. 단어의 의미와 품사
2. 외우기 좋은 연상 팁 or 어원
3. 예문 1개 (영어 + 한국어)
4. 응원 한마디

한국어로 작성, 중학생 눈높이."""

    try:
        return _call_text(prompt, api_config)
    except Exception as e:
        return f"(해설 생성 실패: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# 취약 분석 요약
# ─────────────────────────────────────────────────────────────────────────────

def analyze_weakness(
    student_name: str,
    wrong_words: list[dict],
    exam_results: list[dict],
    api_config: dict,
) -> str:
    """학생의 취약점 분석 및 학습 권장 사항 (한국어)"""
    words_summary = "\n".join(
        f"- {w['word_en']}({w['word_kr']}): {w['wrong_count']}회 오답"
        for w in wrong_words[:15]
    )

    prompt = f"""당신은 친절한 영어 선생님 반반쌤입니다.
학생 '{student_name}'의 학습 데이터를 분석해서 맞춤형 피드백을 작성해주세요.

[오답 단어 (상위 15개)]
{words_summary if words_summary else "아직 오답 데이터 없음"}

분석 내용:
1. 취약한 영역 (예: 동사변형, 숙어, 형용사 등)
2. 가장 집중 학습이 필요한 단어 TOP 3
3. 학습 권장 방법 (구체적으로)
4. 응원 메시지

한국어로 작성, 250자 이내, 친절한 선생님 말투."""

    try:
        return _call_text(prompt, api_config)
    except Exception as e:
        return f"(분석 실패: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# 비법노트 — AI 인포그래픽 HTML 생성
# ─────────────────────────────────────────────────────────────────────────────

def generate_secret_note_html(
    teacher_input: str,
    title: str,
    api_config: dict,
    style: str = "카드형",
) -> str:
    """반반쌤 × 반반 디자인팀 콜라보 프리미엄 인포그래픽 생성"""

    STYLE_GUIDE = {
        "카드형": """
[디자인 컨셉 — 프리미엄 학습 카드]
- 배경: 연한 그라데이션 (예: #EEF2FF → #F5F3FF)
- 헤더: 강렬한 인디고/보라 그라데이션 배너 (#4F46E5 → #7C3AED), 흰색 제목
- 카드들: 흰색 배경, 왼쪽 4px 컬러 border (포인트마다 색상 다르게)
  예: 조동사=#4F46E5, 예문=#0891B2, 팁=#D97706, 주의=#EF4444
- 각 카드 상단에 대형 이모지(2rem) + 굵은 제목(1.1rem, 진한 색)
- 핵심 표현은 <span> 으로 강조 (배경색, 둥근 모서리)
- 하단 푸터: "반반쌤 × 반반 BanBan 비법노트" 소인
- 그림자 효과: box-shadow 0 4px 16px rgba(79,70,229,0.12)
""",
        "만화 대화형": """
[디자인 컨셉 — 캐릭터 대화 학습 만화]
중요: 이 스타일은 반반쌤👩‍🏫 과 학생(지우)🙋‍♂️ 두 캐릭터가 대화하며 내용을 설명하는 형식입니다.

레이아웃 규칙:
- 배경: 밝은 크림 (#FFFBEB) + 가벼운 도트 패턴 또는 그라데이션
- 헤더: 만화 타이틀 스타일 (두꺼운 테두리, 별표 장식, 형광색 강조)
- 전체를 대화 씬으로 구성 (최소 6~8개 대화 교환)

캐릭터 스타일:
1. 반반쌤 👩‍🏫 (왼쪽 배치)
   - 아바타: 원형 배지 (#7C3AED 배경, 흰색 👩‍🏫 이모지, 그림자)
   - 말풍선: 흰색 배경, 보라색 테두리(#7C3AED 2px), 왼쪽 꼬리
   - 이름표: "반반쌤" 보라색 레이블
   - 선생님답게 설명하고, 예문을 제시하며, 팁을 알려줌

2. 학생 지우 🙋‍♂️ (오른쪽 배치)
   - 아바타: 원형 배지 (#F59E0B 배경, 흰색 🙋‍♂️ 이모지, 그림자)
   - 말풍선: 연한 노란 배경 (#FFFBEB), 앰버 테두리(#F59E0B 2px), 오른쪽 꼬리
   - 이름표: "지우" 앰버색 레이블
   - 학생답게 질문하고, 이해한 것 확인하고, 실수하다 고쳐가는 대화

대화 흐름 구조 (반드시 포함):
1. 학생: 오늘 뭐 배워요? (호기심)
2. 선생님: [핵심 개념 소개 + 예문]
3. 학생: [이해 확인 질문 또는 실수]
4. 선생님: [교정 또는 추가 설명 + 2번째 예문]
5. 학생: [다른 상황 적용 시도]
6. 선생님: [칭찬 + 심화 팁]
7. 학생: [정리/요약]
8. 선생님: [암기 팁 + 마무리]

시각 요소:
- 대화 사이에 "학습 포인트 박스" 삽입 (배경#EDE9FE, 보라 테두리): 핵심 규칙 정리
- 효과음 텍스트 (예: "딩동댕!", "바로 그거야!", "잠깐!") — CSS로 팡파레 스타일
- 말풍선 꼬리: CSS border trick 또는 clip-path
- 각 캐릭터 row: display:flex, align-items:flex-start, gap:10px
- 선생님 row: flex-direction:row / 학생 row: flex-direction:row-reverse

하단 푸터: "반반쌤 비법노트 | 반반 BanBan" 보라색 배지
""",
        "웹툰형": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[디자인 컨셉 — 세련된 한국 만화/웹툰 스타일 비법노트]
목표: 전문 만화책처럼 아름답고 세련된 패널 구도.
     캐릭터는 SVG 인라인으로 만화 감성의 얼굴을 직접 그림.
     말풍선은 항상 캐릭터 그림 영역과 완전히 분리 — 절대 겹치지 않음.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

══════════════════════════════
[핵심 레이아웃 철칙 — 위반 금지]
══════════════════════════════
① 각 패널 내부는 반드시 두 존으로 나뉜다:
   [말풍선 존 (상단 60%)] ← 오직 말풍선/효과음/텍스트만
   [캐릭터 존 (하단 40%)] ← 오직 SVG 캐릭터 그림만
② 캐릭터 SVG와 말풍선은 absolute position을 절대 섞지 않는다.
   → 말풍선은 flex/block 흐름으로 위에, 캐릭터는 아래에 배치.
③ 패널 구조 예시 (매 패널 반드시 이 HTML 패턴 사용):
   <div class="panel">
     <div class="bubble-zone">
       <!-- 말풍선들만 이곳에 -->
     </div>
     <div class="char-zone">
       <!-- SVG 캐릭터들만 이곳에 -->
     </div>
   </div>
④ 말풍선 꼬리는 항상 아래를 향해 캐릭터를 가리킨다 (::after 삼각형).
⑤ 효과음(폰트 크기 1.5rem 이상)도 bubble-zone 안에만 배치.

══════════════════════════════
[SVG 캐릭터 정의 — 4인 고정 등장인물]
══════════════════════════════
각 캐릭터는 inline SVG (viewBox="0 0 100 130" width="90" height="117")로 표현.
아래 SVG를 캐릭터마다 정확히 복사해서 사용한다.

▣ 반반쌤 (여교사 — 긴 흑발, 단정한 인상)
<svg viewBox="0 0 100 130" width="90" height="117" xmlns="http://www.w3.org/2000/svg">
  <!-- 긴 머리 뒷결 -->
  <path d="M20,38 C14,65 12,100 18,125 C25,128 32,127 36,122" fill="#1C1C1C"/>
  <path d="M80,38 C86,65 88,100 82,125 C75,128 68,127 64,122" fill="#1C1C1C"/>
  <!-- 얼굴 -->
  <ellipse cx="50" cy="56" rx="26" ry="30" fill="#FDDCB5" stroke="#2a1a0e" stroke-width="1.3"/>
  <!-- 앞머리/탑 -->
  <path d="M24,42 C26,18 38,10 50,9 C62,10 74,18 76,42 C70,28 58,22 50,21 C42,22 30,28 24,42Z" fill="#1C1C1C"/>
  <!-- 앞머리 -->
  <path d="M24,42 C27,34 34,30 32,42" fill="#1C1C1C"/>
  <path d="M76,42 C73,34 66,30 68,42" fill="#1C1C1C"/>
  <!-- 왼쪽 눈 -->
  <ellipse cx="37" cy="53" rx="8" ry="9.5" fill="white" stroke="#1a1a1a" stroke-width="1.4"/>
  <ellipse cx="37" cy="54" rx="5.5" ry="6.5" fill="#2a1208"/>
  <ellipse cx="37" cy="54" rx="3" ry="3.5" fill="#5a2810"/>
  <circle cx="35.5" cy="51.5" r="1.8" fill="white"/>
  <!-- 오른쪽 눈 -->
  <ellipse cx="63" cy="53" rx="8" ry="9.5" fill="white" stroke="#1a1a1a" stroke-width="1.4"/>
  <ellipse cx="63" cy="54" rx="5.5" ry="6.5" fill="#2a1208"/>
  <ellipse cx="63" cy="54" rx="3" ry="3.5" fill="#5a2810"/>
  <circle cx="61.5" cy="51.5" r="1.8" fill="white"/>
  <!-- 눈썹 -->
  <path d="M29,41 C33,38 38,37.5 44,39.5" stroke="#2a1a0e" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M56,39.5 C62,37.5 67,38 71,41" stroke="#2a1a0e" stroke-width="2" fill="none" stroke-linecap="round"/>
  <!-- 코 -->
  <path d="M47,66 C49,70 51,70 53,66" stroke="#c8906a" stroke-width="1.2" fill="none"/>
  <!-- 입 (차분한 미소) -->
  <path d="M41,77 C46,82 54,82 59,77" stroke="#c05050" stroke-width="1.8" fill="none" stroke-linecap="round"/>
  <!-- 속눈썹 -->
  <path d="M29,53 C27,50 26,47 27.5,45" stroke="#1a1a1a" stroke-width="1.1" fill="none"/>
  <path d="M45,52 C47,49 48,46 46.5,44" stroke="#1a1a1a" stroke-width="1.1" fill="none"/>
  <!-- 목·옷 -->
  <rect x="44" y="84" width="12" height="14" fill="#FDDCB5" rx="2"/>
  <path d="M30,98 C36,88 44,95 50,93 C56,95 64,88 70,98 C72,118 72,130 50,130 C28,130 28,118 30,98Z" fill="#f0f0f0" stroke="#ccc" stroke-width="1"/>
  <path d="M50,93 L50,115" stroke="#bbb" stroke-width="1" fill="none"/>
  <!-- 이름표 -->
  <rect x="30" y="118" width="40" height="10" rx="5" fill="#7C3AED"/>
  <text x="50" y="126" text-anchor="middle" fill="white" font-size="7" font-family="sans-serif" font-weight="bold">반반쌤</text>
</svg>

▣ 이반이 (남학생 — 짧은 흑발, 졸린 눈)
<svg viewBox="0 0 100 130" width="90" height="117" xmlns="http://www.w3.org/2000/svg">
  <!-- 머리카락 -->
  <path d="M22,40 C20,20 34,9 50,8 C66,9 80,20 78,40 C72,25 60,19 50,18 C40,19 28,25 22,40Z" fill="#1a1a1a"/>
  <path d="M22,40 C20,34 18,38 20,46" fill="#1a1a1a"/>
  <path d="M78,40 C80,34 82,38 80,46" fill="#1a1a1a"/>
  <!-- 얼굴 -->
  <ellipse cx="50" cy="57" rx="27" ry="30" fill="#FDE8C8" stroke="#2a1a0e" stroke-width="1.3"/>
  <!-- 졸린 눈 (반만 감긴) -->
  <ellipse cx="37" cy="54" rx="8.5" ry="6" fill="white" stroke="#1a1a1a" stroke-width="1.4"/>
  <path d="M28.5,54 Q37,48 45.5,54" fill="#1a1a1a"/>
  <ellipse cx="63" cy="54" rx="8.5" ry="6" fill="white" stroke="#1a1a1a" stroke-width="1.4"/>
  <path d="M54.5,54 Q63,48 71.5,54" fill="#1a1a1a"/>
  <!-- 눈썹 (느슨하게) -->
  <path d="M29,43 C33,41 39,41 44,43" stroke="#2a1a0e" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M56,43 C61,41 67,41 71,43" stroke="#2a1a0e" stroke-width="2" fill="none" stroke-linecap="round"/>
  <!-- 코 -->
  <path d="M47,67 C49,71 51,71 53,67" stroke="#c8906a" stroke-width="1.2" fill="none"/>
  <!-- 입 (약간 벌린) -->
  <path d="M42,78 C46,83 54,83 58,78" stroke="#c05050" stroke-width="1.8" fill="none" stroke-linecap="round"/>
  <!-- 목·교복 -->
  <rect x="44" y="85" width="12" height="14" fill="#FDE8C8" rx="2"/>
  <path d="M28,100 C34,90 44,96 50,94 C56,96 66,90 72,100 C75,120 75,130 50,130 C25,130 25,120 28,100Z" fill="#3B82F6" stroke="#2563EB" stroke-width="1"/>
  <path d="M50,94 L50,116" stroke="#93C5FD" stroke-width="1" fill="none"/>
  <!-- 이름표 -->
  <rect x="30" y="118" width="40" height="10" rx="5" fill="#2563EB"/>
  <text x="50" y="126" text-anchor="middle" fill="white" font-size="7" font-family="sans-serif" font-weight="bold">이반이</text>
</svg>

▣ 강지유 (여학생 — 갈색 단발, 동그란 안경)
<svg viewBox="0 0 100 130" width="90" height="117" xmlns="http://www.w3.org/2000/svg">
  <!-- 단발 머리 -->
  <path d="M22,42 C19,22 32,10 50,9 C68,10 81,22 78,42 C78,65 76,78 75,82 C68,86 55,86 50,85 C45,86 32,86 25,82 C24,78 22,65 22,42Z" fill="#8B4513"/>
  <!-- 얼굴 -->
  <ellipse cx="50" cy="54" rx="25" ry="28" fill="#FDDCB5" stroke="#2a1a0e" stroke-width="1.3"/>
  <!-- 안경 -->
  <circle cx="36" cy="53" r="9" fill="none" stroke="#333" stroke-width="2"/>
  <circle cx="64" cy="53" r="9" fill="none" stroke="#333" stroke-width="2"/>
  <line x1="45" y1="53" x2="55" y2="53" stroke="#333" stroke-width="2"/>
  <line x1="27" y1="53" x2="22" y2="50" stroke="#333" stroke-width="1.5"/>
  <line x1="73" y1="53" x2="78" y2="50" stroke="#333" stroke-width="1.5"/>
  <!-- 눈 (안경 안) -->
  <ellipse cx="36" cy="53" rx="5.5" ry="6" fill="#2a1208"/>
  <ellipse cx="36" cy="53" rx="3" ry="3.2" fill="#5a3010"/>
  <circle cx="34.5" cy="51" r="1.5" fill="white"/>
  <ellipse cx="64" cy="53" rx="5.5" ry="6" fill="#2a1208"/>
  <ellipse cx="64" cy="53" rx="3" ry="3.2" fill="#5a3010"/>
  <circle cx="62.5" cy="51" r="1.5" fill="white"/>
  <!-- 눈썹 -->
  <path d="M28,41 C32,38 38,38 43,40" stroke="#5a3010" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M57,40 C62,38 68,38 72,41" stroke="#5a3010" stroke-width="2" fill="none" stroke-linecap="round"/>
  <!-- 코 -->
  <path d="M47,65 C49,69 51,69 53,65" stroke="#c8906a" stroke-width="1.2" fill="none"/>
  <!-- 입 (자신감 있는 미소) -->
  <path d="M40,75 C45,80 55,80 60,75" stroke="#c05050" stroke-width="1.8" fill="none" stroke-linecap="round"/>
  <!-- 목·교복 -->
  <rect x="44" y="82" width="12" height="14" fill="#FDDCB5" rx="2"/>
  <path d="M28,97 C34,87 44,93 50,91 C56,93 66,87 72,97 C75,117 75,130 50,130 C25,130 25,117 28,97Z" fill="#EC4899" stroke="#DB2777" stroke-width="1"/>
  <!-- 이름표 -->
  <rect x="30" y="118" width="40" height="10" rx="5" fill="#DB2777"/>
  <text x="50" y="126" text-anchor="middle" fill="white" font-size="7" font-family="sans-serif" font-weight="bold">강지유</text>
</svg>

▣ 박동현 (남학생 — 곱슬 흑발, 자신감)
<svg viewBox="0 0 100 130" width="90" height="117" xmlns="http://www.w3.org/2000/svg">
  <!-- 곱슬머리 덩어리 -->
  <circle cx="30" cy="28" r="11" fill="#1a1a1a"/>
  <circle cx="42" cy="22" r="12" fill="#1a1a1a"/>
  <circle cx="55" cy="20" r="13" fill="#1a1a1a"/>
  <circle cx="67" cy="23" r="11" fill="#1a1a1a"/>
  <circle cx="75" cy="32" r="10" fill="#1a1a1a"/>
  <circle cx="25" cy="38" r="9" fill="#1a1a1a"/>
  <circle cx="50" cy="18" r="9" fill="#1a1a1a"/>
  <!-- 얼굴 -->
  <ellipse cx="50" cy="60" rx="28" ry="32" fill="#FDDCB5" stroke="#2a1a0e" stroke-width="1.3"/>
  <!-- 웃는 눈 (반달) -->
  <path d="M29,55 Q37,49 45,55" stroke="#1a1a1a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M55,55 Q63,49 71,55" stroke="#1a1a1a" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <!-- 눈썹 (올라간) -->
  <path d="M28,46 C33,43 39,43 44,46" stroke="#2a1a0e" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M56,46 C61,43 67,43 72,46" stroke="#2a1a0e" stroke-width="2" fill="none" stroke-linecap="round"/>
  <!-- 코 -->
  <path d="M47,70 C49,74 51,74 53,70" stroke="#c8906a" stroke-width="1.2" fill="none"/>
  <!-- 자신감 넘치는 큰 미소 -->
  <path d="M37,82 C44,92 56,92 63,82" stroke="#c05050" stroke-width="2" fill="none" stroke-linecap="round"/>
  <!-- 치아 -->
  <path d="M39,83 C44,90 56,90 61,83" fill="white" stroke="#ddd" stroke-width="0.8"/>
  <!-- 볼 홍조 -->
  <ellipse cx="26" cy="76" rx="7" ry="4" fill="#FFB3A0" opacity="0.5"/>
  <ellipse cx="74" cy="76" rx="7" ry="4" fill="#FFB3A0" opacity="0.5"/>
  <!-- 목·교복 -->
  <rect x="44" y="90" width="12" height="13" fill="#FDDCB5" rx="2"/>
  <path d="M26,103 C33,92 44,99 50,97 C56,99 67,92 74,103 C78,122 78,130 50,130 C22,130 22,122 26,103Z" fill="#10B981" stroke="#059669" stroke-width="1"/>
  <!-- 이름표 -->
  <rect x="30" y="118" width="40" height="10" rx="5" fill="#059669"/>
  <text x="50" y="126" text-anchor="middle" fill="white" font-size="7" font-family="sans-serif" font-weight="bold">박동현</text>
</svg>

══════════════════════════════
[전체 CSS 기본 설정]
══════════════════════════════
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  background: #f0f0f0;
  max-width: 480px;
  margin: 0 auto;
}
.wrap { background: white; padding: 0; }

/* ── 패널 기본 ── */
.panel {
  border: 2.5px solid #111;
  margin-bottom: 6px;
  background: white;
  overflow: hidden;
  position: relative;
}
.panel-header {
  background: linear-gradient(135deg, #1a1a1a, #2d2d2d);
  padding: 16px;
  text-align: center;
}

/* ── 말풍선 존 (상단) ── */
.bubble-zone {
  padding: 14px 16px 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: inherit;
}
.bubble-row {
  display: flex;
  align-items: flex-end;
  gap: 6px;
}
.bubble-row.right { flex-direction: row-reverse; }

/* ── 말풍선 스타일 ── */
.bubble {
  background: white;
  border: 2px solid #222;
  border-radius: 18px;
  padding: 9px 14px;
  font-size: 0.9rem;
  line-height: 1.55;
  max-width: 75%;
  position: relative;
  word-break: keep-all;
  box-shadow: 2px 2px 0 #ccc;
}
/* 말풍선 꼬리 — 아래 방향 */
.bubble::after {
  content: '';
  position: absolute;
  bottom: -11px;
  left: 18px;
  border: 6px solid transparent;
  border-top-color: #222;
}
.bubble::before {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 19px;
  border: 5px solid transparent;
  border-top-color: white;
  z-index: 1;
}
.bubble.right::after { left: auto; right: 18px; }
.bubble.right::before { left: auto; right: 19px; }

/* 캐릭터 별 말풍선 테두리 색상 */
.bubble.teacher { border-color: #7C3AED; box-shadow: 2px 2px 0 #c4b5fd; }
.bubble.teacher::after { border-top-color: #7C3AED; }
.bubble.s1 { border-color: #2563EB; box-shadow: 2px 2px 0 #bfdbfe; }
.bubble.s1::after { border-top-color: #2563EB; }
.bubble.s2 { border-color: #DB2777; box-shadow: 2px 2px 0 #fbcfe8; }
.bubble.s2::after { border-top-color: #DB2777; }
.bubble.s3 { border-color: #059669; box-shadow: 2px 2px 0 #a7f3d0; }
.bubble.s3::after { border-top-color: #059669; }

/* ── 효과음 ── */
.sfx {
  font-size: 1.6rem;
  font-weight: 900;
  letter-spacing: -1px;
  color: #ff2d2d;
  display: inline-block;
  text-shadow: 2px 2px 0 #000;
  transform: rotate(-4deg);
  margin: 4px 0;
}
.sfx.blue { color: #2563EB; }
.sfx.green { color: #059669; }
.sfx.purple { color: #7C3AED; }

/* ── 캐릭터 존 (하단) ── */
.char-zone {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 4px;
  padding: 4px 10px 0;
  border-top: 1.5px solid #e5e7eb;
  background: linear-gradient(to bottom, #fafafa, white);
  min-height: 110px;
}
.char-zone svg { display: block; flex-shrink: 0; }

/* ── 배경 효과선 (집중선) ── */
.focus-lines {
  background: repeating-conic-gradient(
    from 0deg at 50% 110%,
    #fffbe6 0deg, #fffbe6 2deg, transparent 2deg, transparent 8deg
  );
}
.focus-lines-blue {
  background: repeating-conic-gradient(
    from 0deg at 50% 110%,
    #eff6ff 0deg, #eff6ff 2deg, transparent 2deg, transparent 8deg
  );
}

/* ── 학습 내용 박스 ── */
.study-box {
  margin: 8px 12px;
  padding: 12px 14px;
  border-left: 4px solid #4F46E5;
  background: #EEF2FF;
  border-radius: 0 10px 10px 0;
  font-size: 0.88rem;
  line-height: 1.6;
}
.study-box .eng {
  font-weight: 700;
  color: #1e40af;
  font-size: 0.95rem;
}
.study-box .kor {
  color: #4b5563;
  font-size: 0.82rem;
  margin-top: 2px;
}
.highlight { background: linear-gradient(transparent 55%, #fef08a 55%); }
.exam-box {
  border: 2px solid #dc2626;
  background: #fff5f5;
  border-radius: 8px;
  padding: 8px 12px;
  margin: 6px 12px;
  font-size: 0.82rem;
  color: #991b1b;
}

/* ── 핵심 설명 패널 (와이드) ── */
.key-panel { background: white; border: 2.5px solid #111; margin-bottom: 6px; }
.key-panel-header {
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  padding: 10px 16px;
  color: white;
  font-weight: 800;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
}
.key-inner { padding: 10px 14px 14px; }

/* ── CTA 박스 ── */
.cta-box {
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  border-radius: 12px;
  margin: 10px;
  padding: 14px;
  text-align: center;
  color: white;
}
.cta-box .cta-title { font-weight: 800; font-size: 0.9rem; margin-bottom: 8px; }
.cta-buttons { display: flex; gap: 6px; justify-content: center; flex-wrap: wrap; }
.cta-btn {
  background: rgba(255,255,255,0.18);
  border: 1px solid rgba(255,255,255,0.4);
  border-radius: 20px;
  padding: 5px 12px;
  font-size: 0.8rem;
  color: white;
  font-weight: 700;
}
.cta-sub { font-size: 0.72rem; opacity: 0.85; margin-top: 6px; }

/* ── 내레이터 박스 ── */
.narrator {
  background: #1a1a1a;
  color: white;
  border-radius: 8px;
  padding: 10px 14px;
  margin: 6px 12px;
  font-size: 0.8rem;
  line-height: 1.6;
  font-style: italic;
}

/* ── 푸터 ── */
.footer {
  text-align: center;
  padding: 10px;
  font-size: 0.72rem;
  color: #9ca3af;
  border-top: 1px solid #e5e7eb;
}
</style>

══════════════════════════════
[6패널 스토리 구조 — 이 순서로 HTML 작성]
══════════════════════════════

★ 패널 0 — 타이틀 헤더:
<div class="panel">
  <div class="panel-header">
    <div style="color:#fde68a;font-size:0.72rem;font-weight:700;letter-spacing:2px;">반반쌤 비법노트 에피소드</div>
    <div style="color:white;font-size:1.6rem;font-weight:900;margin:6px 0;">[오늘의 학습 제목 — 크고 임팩트 있게]</div>
    <div style="color:#a5b4fc;font-size:0.78rem;">반반쌤과 함께 완전 정복!</div>
  </div>
</div>

★ 패널 1 — 이반이 멘붕 (배경: focus-lines):
bubble-zone: 이반이 말풍선 (혼란스러운 불평)
char-zone: 이반이 SVG + 땀방울 💧 텍스트

★ 패널 2 — 박동현 자신감 등장 (배경: focus-lines-blue):
bubble-zone: 동현 말풍선 (틀린 자신감) + 이반이 말풍선 (기대)
sfx: "짜잔~!" (green)
char-zone: 이반이 SVG + 동현 SVG

★ 패널 3 — 반반쌤 등장:
bubble-zone: sfx "휴~" (purple) + 반반쌤 말풍선 + 동현 말풍선 (당황)
char-zone: 반반쌤 SVG + 동현 SVG + 이반이 SVG

★ 패널 4 — 핵심 학습 내용 (key-panel 클래스 사용):
구조:
  <div class="key-panel">
    <div class="key-panel-header">⚡ 오늘의 핵심 포인트!</div>
    <div class="key-inner">
      반반쌤 SVG (작게, float left 느낌)
      study-box (핵심 규칙 + 예문 + highlight 강조 + exam-box)
    </div>
  </div>
이 패널에는 bubble-zone 없이 학습 내용 직접 카드로 표시.

★ 패널 5 — 이반이 파인만 요약:
bubble-zone: 이반이 말풍선 (자기 말로 요약) + 반반쌤 말풍선 (칭찬 👍)
narrator: "지금 이반이랑 같이 이해된 거... 너도 느끼지? 👀 이미 머릿속에 들어온 거야."
char-zone: 이반이 SVG + 반반쌤 SVG

★ 패널 6 — 강지유 CTA:
bubble-zone: 지유 말풍선 + 이반이 말풍선
char-zone: 강지유 SVG + 이반이 SVG
cta-box: 반반 앱 연결 (3개 버튼: 🎓 반반 학습 / 📝 문법 학습 / 🔤 단어 학습)

footer: "반반쌤 비법노트 | 반반 BanBan 🎓"

══════════════════════════════
[전체 제작 규칙]
══════════════════════════════
1. 완전한 HTML5 (<!DOCTYPE html> 포함), <style> 태그 포함
2. 외부 파일·외부 URL·JavaScript 절대 금지
3. max-width: 480px, 모바일 최적화
4. 캐릭터는 위 SVG 코드를 그대로 사용 (임의 수정 금지)
5. ★ 말풍선은 bubble-zone 안에만, SVG는 char-zone 안에만 — 절대 겹치지 않음
6. 각 말풍선에 .bubble + 캐릭터 클래스 (teacher/s1/s2/s3) 적용
7. 효과음은 .sfx 클래스로 bubble-zone 내에 배치
8. 학습 내용(제목/content)에 맞게 스토리 자연스럽게 각색
9. 패널5 하단에 narrator 박스 반드시 포함
10. 패널6 하단에 cta-box 반드시 포함
""",
        "전략표": """
[디자인 컨셉 — 수능/내신 전략 매트릭스]
- 배경: 순백 (#FFFFFF)
- 헤더: 짙은 네이비 배경 (#1E293B), 흰색 큰 제목 + 부제목
- 핵심 전략 표: 좌측 진한 인디고 컬럼 헤더, 교차 줄 배경 (#F8FAFC / #FFFFFF)
- 중요도 배지: 🔴고난도 🟡보통 🟢기본 뱃지 (인라인 컬러 칩)
- 오른쪽 사이드바 스타일: "한 줄 요약" 컬럼 (배경 #EFF6FF)
- 실수 주의 박스: 빨간 왼쪽 테두리 + 연한 빨간 배경, ⚠️ 아이콘
- 암기 공식 박스: 진한 인디고 배경, 흰색 수식 폰트 스타일
- 푸터: "반반쌤 출제 예상 전략 | 반반 BanBan"
""",
        "마인드맵": """
[디자인 컨셉 — 비주얼 마인드맵 / 개념도]
- 배경: 연한 하늘색 (#F0F9FF)
- 중앙 핵심 노드: 큰 원형 배지 (#4F46E5, 흰색 텍스트), 2rem 텍스트
- 1차 가지들: 중앙에서 방사형으로 뻗는 컬러 화살표 → flexbox 시뮬레이션
  각 가지 색상: 인디고, 청록, 앰버, 로즈, 에메랄드
- 2차 노드들: 해당 색상의 연한 배경 카드, 둥근 모서리
- 연결선: CSS border로 시뮬레이션 (JS 없이)
- 예문들: 이탤릭 스타일, 한/영 병렬 배치
- 전체 레이아웃: CSS Grid 또는 Flexbox로 마인드맵 느낌 표현
- 푸터: 반반쌤 비법노트 배지
""",
    }

    style_desc = STYLE_GUIDE.get(style, STYLE_GUIDE["카드형"])

    prompt = f"""당신은 반반 BanBan 교육 플랫폼의 최고 크리에이티브 팀입니다.
두 전문가가 협업합니다:

👩‍🏫 반반쌤 (교육 콘텐츠 전문가)
- 중학교 영어 일타강사, 15년 경력
- 학생이 쉽게 기억할 수 있는 핵심 포인트 선별
- 재미있는 예문, 암기 팁, 혼동 포인트 짚어주기
- 학생을 배려한 친절한 설명 스타일

🎨 반반 디자인팀 수석 인포그래픽 디자이너
- 교육 시각자료 전문 디자이너
- 학생 눈을 사로잡는 레이아웃 구성
- 색상 심리학을 활용한 기억력 강화 디자인
- 어디서도 못 보는 독창적인 비법노트 제작

━━━━━━━━━━━━━━━━━━━━━━━━━━
[반반쌤이 정리한 학습 내용]
제목: {title}
내용:
{teacher_input}
━━━━━━━━━━━━━━━━━━━━━━━━━━

[디자인 스타일]
{style_desc}

━━━━━━━━━━━━━━━━━━━━━━━━━━
[제작 필수 요구사항]
1. 완전한 HTML5 문서 (<!DOCTYPE html> 포함)
2. 인라인 CSS + <style> 태그 내 CSS 혼용 가능 (외부 파일 금지)
3. 시스템 기본 폰트 사용 (웹폰트 URL 금지) — 단, font-weight, font-style, letter-spacing 적극 활용
4. JavaScript 절대 금지 (순수 HTML+CSS만)
5. 이미지/SVG 외부 URL 금지 (인라인 SVG는 허용)
6. max-width: 520px, 모바일 친화적 레이아웃
7. 한국어/영어 혼합 — 중학생 눈높이
8. 내용을 창의적으로 시각화 (단순 나열 금지)
9. 반드시 반반쌤만의 핵심 암기 팁을 1개 이상 포함
10. 학생이 처음 보는 순간 "와!" 소리가 나올 만큼 임팩트 있게
━━━━━━━━━━━━━━━━━━━━━━━━━━

HTML 코드만 반환하세요. 설명 텍스트, 마크다운 코드블록 없이 <!DOCTYPE html>로 바로 시작."""

    try:
        raw = _call_text(prompt, api_config)
        # HTML 코드블록 제거
        m = re.search(r"```(?:html)?\s*([\s\S]+?)\s*```", raw)
        if m:
            return m.group(1).strip()
        raw = raw.strip()
        # DOCTYPE 앞 불필요한 텍스트 제거
        idx = raw.lower().find("<!doctype")
        if idx > 0:
            raw = raw[idx:]
        elif raw.lower().find("<html") >= 0:
            raw = raw[raw.lower().find("<html"):]
        return raw
    except Exception as e:
        raise RuntimeError(f"인포그래픽 생성 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# 비법노트 자동 분석 — 노트에서 문법/어휘/표현 추출
# ─────────────────────────────────────────────────────────────────────────────

def analyze_note_for_secrets(note: dict, api_config: dict) -> list[dict]:
    """
    반반노트 내용 → 핵심 문법 / 어휘 / 표현 아이템 자동 추출
    Returns list of:
    {
      type: "grammar"|"vocab"|"expression",
      icon: str,
      title: str,
      description: str,
      examples: list[str],
      tip: str,
      importance: int (1-5)
    }
    """
    words     = note.get("words_data", note.get("words", []))[:25]
    dialogues = note.get("dialogues_data", note.get("dialogues", []))
    text_data = note.get("text_data", {})
    title     = note.get("title", "반반노트")

    # ── 콘텐츠 요약 ────────────────────────────────────────────────
    word_text = "\n".join(
        f"- {w[0]}: {w[1]}" for w in words
        if isinstance(w, (list, tuple)) and len(w) >= 2
    )

    dlg_lines: list[str] = []
    for dlg in dialogues[:3]:
        for line in dlg.get("lines", [])[:6]:
            if isinstance(line, (list, tuple)) and len(line) >= 2:
                dlg_lines.append(f"  {line[0]}")
    dlg_text = "\n".join(dlg_lines)

    sent_lines: list[str] = []
    if text_data.get("sections"):
        for sec in text_data["sections"]:
            for pair in sec.get("sentences", [])[:6]:
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    sent_lines.append(f"  {pair[0]}")
    elif text_data.get("sentences"):
        for pair in text_data.get("sentences", [])[:15]:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                sent_lines.append(f"  {pair[0]}")
    sent_text = "\n".join(sent_lines[:18])

    prompt = f"""당신은 한국 중학교 영어 내신 전문 교육 분석가입니다.
아래 반반노트 학습 자료를 분석해서, 학생들이 내신 시험에서 반드시 알아야 할
핵심 아이템들을 추출해 주세요.

[노트 제목] {title}

[단어 목록]
{word_text if word_text else "(없음)"}

[대화문]
{dlg_text if dlg_text else "(없음)"}

[본문]
{sent_text if sent_text else "(없음)"}

━━━━━━━━━━━━━━━━━━━━━━━━━━
[추출 지침]
1. grammar (문법 포인트) — 이 자료에 등장하는 핵심 문법 2-4개
   예: 현재완료, 수동태, 가정법, 관계대명사 등
2. vocab (핵심 어휘) — 내신에 꼭 나올 단어/숙어 3-5개
   예: 중요 단어, 혼동 주의 단어쌍, 빈출 숙어
3. expression (핵심 표현) — 외워야 할 구문/관용표현 2-3개
   예: 본문의 중요 구문, 자주 출제되는 표현 패턴

[중요도 기준] (한국 중학교 내신 시험 패턴 기준)
5 = 반드시 출제 예상 🔴
4 = 높은 출제 가능성 🟠
3 = 보통 중요도 🟡
2 = 참고용 🟢
1 = 선택 학습 ⚪

반드시 아래 JSON 배열만 반환 (다른 텍스트 없이):
[
  {{
    "type": "grammar",
    "icon": "📝",
    "title": "현재완료 시제",
    "description": "have/has + p.p. 형태, 과거부터 현재까지 지속·완료·경험 표현",
    "examples": ["I have studied English for 3 years.", "She has just finished."],
    "tip": "for(기간) / since(시점)와 함께 자주 출제",
    "importance": 5
  }},
  {{
    "type": "vocab",
    "icon": "📚",
    "title": "volunteer",
    "description": "동사: 자원봉사하다 / 명사: 자원봉사자",
    "examples": ["She volunteers at a local shelter every weekend."],
    "tip": "volunteer for ~에 자원하다 — 전치사 for 주의",
    "importance": 4
  }},
  {{
    "type": "expression",
    "icon": "💬",
    "title": "used to + 동사원형",
    "description": "과거의 습관이나 상태 (~하곤 했다, ~였었다)",
    "examples": ["I used to play soccer after school.", "There used to be a park here."],
    "tip": "be used to + 동명사(~에 익숙하다)와 혼동 주의!",
    "importance": 5
  }}
]"""

    try:
        raw   = _call_text(prompt, api_config)
        items = _parse_json(raw)
        if not isinstance(items, list):
            items = []
        # importance 범위 보정
        for item in items:
            item["importance"] = max(1, min(5, int(item.get("importance", 3))))
        # 중요도 내림차순 정렬
        items.sort(key=lambda x: x.get("importance", 3), reverse=True)
        return items
    except Exception as e:
        raise RuntimeError(f"자동 분석 실패: {e}") from e


def generate_secret_note_from_items(
    items: list[dict],
    style: str,
    api_config: dict,
    note_title: str,
) -> str:
    """선택된 아이템 목록 → 비법노트 HTML 생성"""
    lines: list[str] = []

    grammar_items    = [i for i in items if i.get("type") == "grammar"]
    vocab_items      = [i for i in items if i.get("type") == "vocab"]
    expr_items       = [i for i in items if i.get("type") == "expression"]

    def _stars(n: int) -> str:
        return "★" * n + "☆" * (5 - n)

    if grammar_items:
        lines.append("■ 핵심 문법 포인트")
        for item in grammar_items:
            lines.append(f"\n[{item['title']}] 중요도 {_stars(item.get('importance',3))}")
            lines.append(f"  설명: {item['description']}")
            if item.get("examples"):
                lines.append("  예문: " + " / ".join(item["examples"][:2]))
            if item.get("tip"):
                lines.append(f"  💡 암기 팁: {item['tip']}")

    if vocab_items:
        lines.append("\n■ 핵심 어휘")
        for item in vocab_items:
            lines.append(f"\n[{item['title']}] {_stars(item.get('importance',3))}")
            lines.append(f"  {item['description']}")
            if item.get("examples"):
                lines.append(f"  예문: {item['examples'][0]}")
            if item.get("tip"):
                lines.append(f"  💡 {item['tip']}")

    if expr_items:
        lines.append("\n■ 핵심 표현 · 구문")
        for item in expr_items:
            lines.append(f"\n[{item['title']}] {_stars(item.get('importance',3))}")
            lines.append(f"  {item['description']}")
            if item.get("examples"):
                lines.append(f"  예문: {item['examples'][0]}")
            if item.get("tip"):
                lines.append(f"  💡 {item['tip']}")

    teacher_input = "\n".join(lines)
    auto_title    = f"{note_title} — AI 핵심 비법노트"

    return generate_secret_note_html(
        teacher_input=teacher_input,
        title=auto_title,
        api_config=api_config,
        style=style,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 기출문제 OCR 추출
# ─────────────────────────────────────────────────────────────────────────────

def extract_past_problems_from_text(text: str, api_config: dict) -> list[dict]:
    """기출문제 텍스트 → 구조화된 문제 목록 (서술형·소문항·빈칸 완전 지원)"""
    prompt = f"""당신은 대한민국 중학교 영어 시험지 전문 분석가입니다.
아래 시험 기출문제 텍스트를 분석해서 모든 문제를 구조화하세요.

[기출문제 텍스트]
{text[:8000]}

━━━━ 추출 규칙 ━━━━

【발문】문제 번호 옆 한국어 지시문 전체를 question에 포함 (조건 포함)

【지문(passage)】박스/테두리 안 영어 지문 → passage 필드에 완전히 추출
  - 밑줄 친 부분 → <u>텍스트</u> 태그

【서술형·빈칸】
  - 빈칸(_____) 있는 문장 → ___ 로 표시해 answer_template에 추출
  - 소문항 (1)(2) → sub_questions 배열에 각각 {"label","question","answer_line"}

【선택지】①②③④⑤ → options 배열에 그대로

반드시 아래 JSON 형식만 반환 (다른 텍스트 절대 금지):
{{
  "problems": [
    {{
      "number": 1,
      "type": "객관식",
      "passage": "지문 (없으면 빈 문자열). <u>밑줄</u> 포함 가능",
      "question": "한국어 발문 전체 (조건 포함)",
      "answer_template": "빈칸 있는 문장 (___ 표시). 없으면 빈 문자열",
      "sub_questions": [],
      "options": ["① 보기1", "② 보기2", "③ 보기3", "④ 보기4"],
      "answer": "② 보기2",
      "points": 3
    }},
    {{
      "number": 2,
      "type": "서술형",
      "passage": "Ms. Lee prepares fresh and delicious meals...",
      "question": "다음 글을 읽고 아래 질문에 대한 알맞은 대답이 되도록 빈칸을 완성하시오.",
      "answer_template": "",
      "sub_questions": [
        {{"label": "(1)", "question": "What does Ms. Lee do after lunchtime?", "answer_line": "→ She ___."}},
        {{"label": "(2)", "question": "Why is Ms. Lee proud of her job?", "answer_line": "→ Because she ___ to the students."}}
      ],
      "options": [],
      "answer": "",
      "points": 4
    }}
  ]
}}

type 값: 객관식 / 서술형 / 단답형 / 순서배열 / 빈칸완성 / 어법
답이 없으면 answer: ""  |  순수 JSON만 반환  |  모든 문제 빠짐없이"""

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        return data.get("problems", [])
    except Exception as e:
        raise RuntimeError(f"기출문제 추출 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# 문법 드릴 — AI 의미 채점 + 반반쌤 즉각 반응
# ─────────────────────────────────────────────────────────────────────────────

import random as _rnd

_CORRECT_REACTIONS = [
    "🎯 딩동댕! 바로 그거에요!",
    "✨ 완벽해요! 이 패턴 완전 마스터했군요!",
    "🌟 오~ 잘 알고 있네요! 역시 우리 학생!",
    "💫 정확해요! 확실히 이해하고 있군요!",
    "👏 잘했어요! 이 문법 자신감 있게 쓸 수 있겠어요!",
    "🎊 맞아요! 이렇게 척척 맞추니 선생님도 기분 좋아요!",
]

_WRONG_REACTIONS = [
    "💪 아쉬워요! 이 부분 한 번 더 확인해봐요.",
    "📚 괜찮아요! 실수에서 배우는 거예요. 다시 도전!",
    "🔍 조금만 더 생각해봐요. 분명히 할 수 있어요!",
    "⚡ 이 부분이 함정이에요! 핵심 패턴 다시 체크!",
    "🌸 틀렸지만 괜찮아요! 이게 진짜 실력이 느는 순간이에요.",
]


def get_bansam_reaction(is_correct: bool, combo: int) -> str:
    """반반쌤 즉각 반응 (템플릿 기반, AI 없음 — 빠름).

    combo: 현재 연속 정답 수 (오답이면 이미 0으로 초기화된 상태로 전달)
    """
    if is_correct:
        if combo >= 7:
            return "💥 7연속 정답!! 완전 영어 천재잖아요? 권쌤도 놀랐어요!"
        elif combo >= 5:
            return "⚡ 5연속 정답! 완전 타오르고 있네요! 이 기세 절대 꺾이지 마요~"
        elif combo >= 3:
            return "🔥 3연속 정답! 완전 핫하네요! 멈출 수가 없어요~"
        else:
            return _rnd.choice(_CORRECT_REACTIONS)
    else:
        return _rnd.choice(_WRONG_REACTIONS)


def check_subjective_answer(
    user_answer: str,
    correct_answer: str,
    question: str,
    grammar_point_name: str,
    api_config: dict,
) -> tuple[bool, str]:
    """주관식 답안 AI 의미 채점.

    표현이 달라도 핵심 개념이 맞으면 정답 처리.
    예: 정답 "going → go"  →  학생 "going을 go로 바꿔야 한다"  →  정답 ✅

    Returns:
        (is_correct: bool, feedback: str)
    """
    if not user_answer.strip():
        return False, "답을 입력해주세요."

    # 빠른 정확 매칭 먼저 (AI 호출 절약)
    ua = user_answer.strip().lower()
    ca = correct_answer.strip().lower()
    if ua == ca:
        return True, ""
    if "|" in correct_answer:
        if ua in [a.strip().lower() for a in correct_answer.split("|")]:
            return True, ""

    prompt = f"""영어 문법 문제 주관식 채점을 해주세요.

문법 포인트: {grammar_point_name}
문제: {question}
모범 답안: {correct_answer}
학생 답안: {user_answer}

채점 기준:
- 핵심 문법 개념이 올바르면 표현 방식이 달라도 정답 처리
- "going → go"  ==  "going을 go로 바꿔야 한다"  →  정답
- "is → be"  ==  "is를 be동사로 적어야 된다"  →  정답
- "May I sit here?"  ==  "may i sit here?"  →  대소문자 무관, 정답
- 핵심 단어나 변형이 누락되면 오답

반드시 아래 JSON만 반환 (다른 텍스트 금지):
{{"correct": true, "feedback": "피드백 1문장 (정답이면 짧게 칭찬, 오답이면 힌트)"}}"""

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        return bool(data.get("correct", False)), data.get("feedback", "")
    except Exception:
        # Fallback: 포함 관계 체크
        if len(ca) > 3 and (ca in ua or ua in ca):
            return True, ""
        return False, f"정답: {correct_answer}"


# ─────────────────────────────────────────────────────────────────────────────
# 선생님 AI 학습 방향 추천
# ─────────────────────────────────────────────────────────────────────────────

def generate_learning_recommendations(
    student_name: str,
    profile: dict,
    api_config: dict,
) -> str:
    """선생님용 학생 맞춤 AI 학습 방향 추천 리포트 (마크다운 반환).

    profile 키:
        module_stats: {activity: {sessions, avg_score, last_score}}
        word_wrong_count: int
        question_wrong_count: int
        weak_words: list[str]
        weak_q_topics: list[str]
        streak: int
        total_sessions: int
        recent_activity_days: int  # 지난 7일 중 활동한 날 수
    """
    mod_map = {
        "word_quiz":  "단어 퀴즈",
        "grammar":    "문법 드릴",
        "exam":       "내신 문제",
        "past":       "기출 문제",
    }

    # 모듈 통계 요약
    mod_lines = []
    for act, stat in profile.get("module_stats", {}).items():
        label     = mod_map.get(act, act)
        sessions  = stat.get("sessions", 0)
        avg       = stat.get("avg_score")
        last      = stat.get("last_score")
        avg_txt   = f"평균 {avg:.0f}점" if avg is not None else "점수 없음"
        last_txt  = f"최근 {last:.0f}점" if last is not None else ""
        mod_lines.append(f"- {label}: {sessions}회, {avg_txt} {last_txt}")

    weak_words = profile.get("weak_words", [])[:5]
    weak_topics = profile.get("weak_q_topics", [])[:5]

    prompt = f"""당신은 대한민국 최고의 영어 교육 컨설턴트 반반쌤입니다.
아래 학생 데이터를 분석하여 담당 선생님에게 제출할 **맞춤 학습 방향 추천 리포트**를 작성하세요.

[학생 정보]
이름: {student_name}
연속 학습일: {profile.get("streak", 0)}일
총 학습 세션: {profile.get("total_sessions", 0)}회
최근 7일 활동일: {profile.get("recent_activity_days", 0)}일

[모듈별 성과]
{chr(10).join(mod_lines) if mod_lines else "기록 없음"}

[취약 단어 Top 5]
{", ".join(weak_words) if weak_words else "없음"}

[취약 문제 유형]
{", ".join(weak_topics) if weak_topics else "없음"}

[단어 오답 수] {profile.get("word_wrong_count", 0)}개
[문제 오답 수] {profile.get("question_wrong_count", 0)}개

━━━━━━━━━━━━━━━━━━━━━━━━━━
아래 마크다운 형식으로 **구체적이고 실행 가능한** 리포트를 작성하세요:

## 📊 종합 평가
(2~3문장, 이 학생의 현재 수준과 학습 패턴 요약)

## 🔴 즉시 개선 필요
(가장 시급한 취약 영역 2~3가지, 구체적 수치 포함)

## 🟢 잘하고 있는 것
(강점 1~2가지, 격려 포함)

## 📅 이번 주 학습 추천
(선생님이 학생에게 바로 적용할 수 있는 구체적 액션 3가지, 번호 매기기)

## 💡 반반쌤의 한 마디
(학생에게 전할 맞춤 응원 메시지, 따뜻하고 구체적으로)

한국어로 작성, 선생님이 보기 좋은 전문적 말투."""

    try:
        return _call_text(prompt, api_config)
    except Exception as e:
        return f"(추천 생성 실패: {e})"


# ─────────────────────────────────────────────────────────────────────────────
# 약점 처방전 — AI 분석 + HTML 처방전 카드 생성
# ─────────────────────────────────────────────────────────────────────────────

def generate_weakness_prescription(
    student_name: str,
    profile: dict,
    wrong_words: list[dict],
    wrong_questions: list[dict],
    api_config: dict,
) -> str:
    """학생 오답 데이터 → 약점 처방전 HTML 카드 반환.

    wrong_words: [{word_en, word_kr, wrong_count}, ...]
    wrong_questions: [{question_snapshot:{gp_name,question_text,correct_answer}, wrong_count, source_type}, ...]
    """
    word_lines = "\n".join(
        f"  - {w.get('word_en','')} ({w.get('word_kr','')}) — {w.get('wrong_count',1)}회 틀림"
        for w in wrong_words[:10]
    ) or "  없음"

    q_lines = []
    for q in wrong_questions[:8]:
        snap = q.get("question_snapshot") or {}
        gp   = snap.get("gp_name", snap.get("type", q.get("source_type", "")))
        txt  = snap.get("question_text", "")[:60]
        cnt  = q.get("wrong_count", 1)
        q_lines.append(f"  - [{gp}] {txt}... ({cnt}회 틀림)")
    q_block = "\n".join(q_lines) or "  없음"

    mod_map = {"word_quiz":"단어 퀴즈","grammar":"문법 드릴","exam":"내신 문제","past":"기출 문제","note_read":"반반노트"}
    mod_lines = []
    for act, stat in profile.get("module_stats", {}).items():
        avg = stat.get("avg_score")
        mod_lines.append(f"  - {mod_map.get(act,act)}: {stat.get('sessions',0)}회"
                         + (f", 평균 {avg:.0f}점" if avg is not None else ""))

    prompt = f"""당신은 반반 BanBan 플랫폼의 반반쌤입니다. 아래 학생 데이터를 분석하여
**약점 처방전** HTML 카드를 만드세요. 마치 의사가 처방전을 주듯, 학생이 꼭 해야 할 것을 명확하게 알려주세요.

[학생] {student_name}  |  연속학습 {profile.get('streak',0)}일  |  총 {profile.get('total_sessions',0)}회 학습

[모듈별 현황]
{chr(10).join(mod_lines) if mod_lines else '  기록없음'}

[틀린 단어 Top 10]
{word_lines}

[틀린 문제 유형]
{q_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
위 데이터를 바탕으로 아래 형식의 **완전한 HTML5** 처방전 카드를 만드세요:

디자인 요구사항:
- max-width: 520px, 모바일 최적화
- 배경: 흰색 카드, 상단 헤더: linear-gradient(135deg, #DC2626, #7C3AED)
- 헤더에: 💊 약점 처방전 | 학생이름 | 날짜 (큰 흰 텍스트)
- 섹션 1: 🔴 긴급 처방 (가장 시급한 취약점 2~3가지, 빨간 테두리 카드)
  - 각 항목: 취약점 이름 + "이렇게 공부하세요" 구체적 방법 1~2줄
- 섹션 2: 📚 이번 주 집중 단어 (틀린 단어 중 Top 5, 단어+뜻+암기팁 인라인)
- 섹션 3: 📝 반복 실수 패턴 (문제 유형별 실수 원인 분석)
- 섹션 4: 🗓 7일 처방 플랜 (요일별 할 것, 테이블 형식, 인디고 배경 헤더)
- 하단 서명: "반반쌤 처방전 | 반반 BanBan 🎓 | 오늘 날짜" (작은 텍스트)
- JavaScript 금지, 외부 URL 금지, 인라인 CSS + <style> 태그

HTML만 반환 (<!DOCTYPE html>로 시작)."""

    try:
        raw = _call_text(prompt, api_config)
        m = re.search(r"```(?:html)?\s*([\s\S]+?)\s*```", raw)
        if m:
            return m.group(1).strip()
        raw = raw.strip()
        idx = raw.lower().find("<!doctype")
        if idx > 0:
            raw = raw[idx:]
        elif raw.lower().find("<html") >= 0:
            raw = raw[raw.lower().find("<html"):]
        return raw
    except Exception as e:
        raise RuntimeError(f"약점 처방전 생성 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# 학부모 주간 리포트 — HTML 리포트 생성
# ─────────────────────────────────────────────────────────────────────────────

def generate_parent_weekly_report(
    student_name: str,
    profile: dict,
    week_logs: list[dict],
    api_config: dict,
) -> str:
    """학부모용 주간 학습 리포트 HTML 생성."""
    # 주간 통계 계산
    total_sessions = len(week_logs)
    study_days = len({r.get("created_at","")[:10] for r in week_logs if r.get("created_at")})
    activities = {}
    for r in week_logs:
        act = r.get("activity","")
        activities[act] = activities.get(act, 0) + 1

    mod_map = {"word_quiz":"단어 퀴즈","grammar":"문법 드릴","exam":"내신 문제",
               "past":"기출 문제","note_read":"반반노트 학습"}
    act_lines = "\n".join(
        f"  - {mod_map.get(k,k)}: {v}회"
        for k,v in sorted(activities.items(), key=lambda x:-x[1])
    ) or "  학습 기록 없음"

    scores = [r for r in week_logs if r.get("score") is not None and r.get("total")]
    avg_score = (sum(r["score"]/r["total"]*100 for r in scores)/len(scores)) if scores else None

    prompt = f"""당신은 반반 BanBan 플랫폼의 반반쌤입니다.
학부모님께 보낼 **주간 학습 리포트 HTML**을 만드세요. 따뜻하고 신뢰감 있는 톤으로.

[학생] {student_name}
[이번 주 학습 요약]
  - 학습한 날: {study_days}일 / 7일
  - 총 학습 횟수: {total_sessions}회
  - 평균 정답률: {f"{avg_score:.0f}%" if avg_score else "측정 중"}
  - 연속 학습일: {profile.get('streak',0)}일

[활동별 횟수]
{act_lines}

[취약 단어] {", ".join(profile.get('weak_words',[])[:5]) or "없음"}
[취약 유형] {", ".join(profile.get('weak_q_topics',[])[:3]) or "없음"}

━━━━━━━━━━━━━━━━━━━━━━━━━━
아래 형식의 완전한 HTML5 주간 리포트를 만드세요:

디자인:
- max-width: 560px, 이메일 친화적 레이아웃
- 헤더: linear-gradient(135deg, #4F46E5, #7C3AED), 흰 텍스트
  "반반 BanBan 주간 학습 리포트 📚" + 학생이름 + 기간
- 상단 KPI 3개 (가로 배열): 학습일수 / 총 세션 / 정답률 (각각 원형 시각화 느낌)
- 학습 활동 막대 차트 (CSS div width로 표현, 인디고 계열)
- 이번 주 칭찬 포인트 (초록 배경 카드): 잘한 것 2가지
- 다음 주 집중 포인트 (주황 배경 카드): 개선 필요 2가지
- 반반쌤의 코멘트 (따뜻한 말, 보라색 왼쪽 테두리 인용)
- 푸터: "반반 BanBan 🎓 | 영어학습 파트너"
- JavaScript 금지, 외부 URL 금지

HTML만 반환 (<!DOCTYPE html>로 시작)."""

    try:
        raw = _call_text(prompt, api_config)
        m = re.search(r"```(?:html)?\s*([\s\S]+?)\s*```", raw)
        if m:
            return m.group(1).strip()
        raw = raw.strip()
        idx = raw.lower().find("<!doctype")
        if idx > 0:
            raw = raw[idx:]
        elif raw.lower().find("<html") >= 0:
            raw = raw[raw.lower().find("<html"):]
        return raw
    except Exception as e:
        raise RuntimeError(f"주간 리포트 생성 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# 시험 직전 요약노트 생성
# ─────────────────────────────────────────────────────────────────────────────

def generate_cheatsheet_data(
    note_title: str,
    words: list,
    dialogues: list,
    text_data: dict,
    grammar_points: list,
    secret_notes: list,
    past_problems: list,
    sections: list[str],
    api_config: dict,
) -> dict:
    """노트 데이터 → 시험 직전 요약노트용 JSON 구조 반환.

    반환 형태:
    {
      "front": {
        "words":   [{"en":..,"kr":..,"tip":..}, ...],   # 최대 60개
        "grammar": [{"rule":..,"example":..,"note":..}, ...],  # 최대 10개
      },
      "back": {
        "sentences":  [{"en":..,"kr":..}, ...],  # 최대 25개
        "patterns":   [{"pattern":..,"meaning":..,"ex":..}, ...],  # 최대 10개
        "secret_tips":[{"title":..,"content":..}, ...],  # 최대 6개
        "exam_keys":  [{"type":..,"content":..}, ...]   # 최대 8개
      }
    }
    """
    # ── 데이터 직렬화 ──────────────────────────────
    words_text = ""
    if "단어" in sections and words:
        word_lines = [f"{w[0]}={w[1]}" for w in words[:80] if len(w) >= 2]
        words_text = "단어목록:\n" + "\n".join(word_lines)

    dlg_text = ""
    if "대화문" in sections and dialogues:
        for d in dialogues[:3]:
            dlg_text += f"[{d.get('title','')}]\n"
            for ln in d.get("lines", [])[:30]:
                if len(ln) >= 2:
                    dlg_text += f"  {ln[0]} / {ln[1]}\n"

    text_text = ""
    if "본문" in sections and text_data:
        sents = text_data.get("sentences", [])
        text_text = f"[{text_data.get('title_en','')}]\n"
        text_text += "\n".join(f"{s[0]} / {s[1]}" for s in sents[:30] if len(s) >= 2)

    grammar_text = ""
    if "문법" in sections and grammar_points:
        for gp in grammar_points[:12]:
            grammar_text += (
                f"■ {gp.get('point_name','')} [{gp.get('category','')}]\n"
                f"  설명: {gp.get('explanation','')[:120]}\n"
                f"  예: {gp.get('example_sentence','')[:80]}\n"
            )

    secret_text = ""
    if "비법노트" in sections and secret_notes:
        for sn in secret_notes[:8]:
            raw_html = sn.get("html_content", "")
            # strip HTML tags
            clean = re.sub(r"<[^>]+>", " ", raw_html)
            clean = re.sub(r"\s{2,}", " ", clean).strip()[:300]
            secret_text += f"[{sn.get('title','')}] {clean}\n"

    exam_text = ""
    if "기출문제" in sections and past_problems:
        for pp in past_problems[:5]:
            for q in pp.get("problems", [])[:6]:
                q_txt = q.get("question","")[:80]
                ans   = q.get("answer","")[:40]
                exam_text += f"Q: {q_txt} → A: {ans}\n"

    prompt = f"""당신은 영어 시험 전문 선생님입니다.
아래 학습 자료를 분석하여 **시험 직전 A4 요약노트**에 담을 핵심 내용만 추출하세요.
출력은 반드시 아래 JSON 형식만 반환하세요 (코드블록 없이).

[노트 제목] {note_title}
[포함 섹션] {', '.join(sections)}

{words_text}

{dlg_text}

{text_text}

{grammar_text}

{secret_text}

{exam_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━
반환 JSON 형식:
{{
  "front": {{
    "words": [{{"en":"단어","kr":"뜻","tip":"암기팁(선택)"}}],
    "grammar": [{{"rule":"문법규칙명","example":"예문 (한국어 해석)","note":"핵심 주의사항"}}]
  }},
  "back": {{
    "sentences": [{{"en":"핵심 문장","kr":"해석"}}],
    "patterns": [{{"pattern":"핵심 표현/패턴","meaning":"의미","ex":"예시"}}],
    "secret_tips": [{{"title":"비법 제목","content":"내용 요약"}}],
    "exam_keys": [{{"type":"문제유형","content":"핵심 포인트"}}]
  }}
}}

규칙:
- words: 시험에 꼭 나올 것만, 최대 60개. tip은 혼동되거나 중요한 것만
- grammar: 핵심 문법만, 최대 10개. example은 영어문장 (한국어해석) 형식
- sentences: 대화문/본문에서 핵심 문장, 최대 25개
- patterns: 자주 출제되는 표현 패턴, 최대 10개
- secret_tips: 비법노트 핵심 요약, 최대 6개
- exam_keys: 기출 핵심 포인트, 최대 8개
- 해당 섹션 자료가 없으면 빈 배열 []로 반환
- JSON만 반환, 다른 텍스트 없음"""

    raw = _call_text(prompt, api_config)
    raw = raw.strip()
    # strip code fences
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if m:
        raw = m.group(1).strip()
    # find first {
    idx = raw.find("{")
    if idx > 0:
        raw = raw[idx:]
    try:
        return json.loads(raw)
    except Exception:
        return {"front": {"words": [], "grammar": []},
                "back":  {"sentences": [], "patterns": [], "secret_tips": [], "exam_keys": []}}


# ─────────────────────────────────────────────────────────────────────────────
# 반반노트 이해 보조장치 — 대화문 키포인트 + 본문 단락 요약 (Gemini 1회 호출)
# ─────────────────────────────────────────────────────────────────────────────

def _line_en(ln):
    """대화문/본문 라인에서 영어 텍스트 추출 (tuple/list/dict 모두 지원)."""
    if isinstance(ln, (list, tuple)) and ln:
        return str(ln[0])
    if isinstance(ln, dict):
        return str(ln.get("en", ln.get("english", "")))
    return str(ln) if ln else ""


def generate_comprehension_aids(dialogues: list, sections: list,
                                api_config: dict) -> dict:
    """대화문별 키포인트 + 본문 단락별 요약을 한 번의 호출로 생성.

    인덱스(번호) 기반 매칭 — 제목 echo 실패에 강건함.

    Returns:
        {
          "dialogue_points": { 0: "핵심 1줄", 1: ... },   # 대화문 순서 인덱스
          "section_summaries": { 0: "요점 1~2문장", ... }  # 단락 순서 인덱스
        }
    """
    if not api_config:
        return {"dialogue_points": {}, "section_summaries": {}}

    # 번호 기반 블록 구성
    dlg_blocks = []
    for i, d in enumerate(dialogues or []):
        ens = [_line_en(ln) for ln in d.get("lines", [])]
        ens = [e for e in ens if e]
        title = d.get("title", f"대화문{i+1}")
        if ens:
            dlg_blocks.append(f"#{i} [{title}]\n" + "\n".join(ens[:20]))

    sec_blocks = []
    for i, s in enumerate(sections or []):
        ens = [_line_en(p) for p in s.get("sentences", [])]
        ens = [e for e in ens if e]
        label = s.get("label", f"단락{i+1}")
        if ens:
            sec_blocks.append(f"#{i} [{label}]\n" + " ".join(ens[:30]))

    if not dlg_blocks and not sec_blocks:
        return {"dialogue_points": {}, "section_summaries": {}}

    prompt = f"""너는 한국 중학생을 가르치는 영어 선생님이야.
아래 대화문과 본문 단락을 읽고, 학생이 '무슨 내용인지' 빠르게 이해하도록 도와줘.
각 항목은 #번호로 구분돼 있어. 반드시 그 번호를 키로 사용해.

[대화문 목록]
{chr(10).join(dlg_blocks) if dlg_blocks else "(없음)"}

[본문 단락 목록]
{chr(10).join(sec_blocks) if sec_blocks else "(없음)"}

규칙:
- 대화문마다: 누가 누구에게 무엇을 하는지 한국어 핵심 1문장 (예: "민수가 지나에게 주말 계획을 물어봄")
- 본문 단락마다: 그 단락의 요점 한국어 1~2문장
- 쉽고 명확하게, 중학생 눈높이로
- 위 #번호를 그대로 키(문자열)로 사용

반드시 아래 JSON만 반환:
{{"dialogue_points": {{"0": "핵심 1줄", "1": "..."}},
  "section_summaries": {{"0": "요점 1~2문장", "1": "..."}}}}"""

    def _to_int_keyed(d):
        out = {}
        if isinstance(d, dict):
            for k, v in d.items():
                try:
                    out[int(str(k).lstrip("#").strip())] = v
                except (ValueError, TypeError):
                    continue
        return out

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        return {
            "dialogue_points":   _to_int_keyed(data.get("dialogue_points", {})),
            "section_summaries": _to_int_keyed(data.get("section_summaries", {})),
        }
    except Exception:
        return {"dialogue_points": {}, "section_summaries": {}}


# ─────────────────────────────────────────────────────────────────────────────
# 서술형 DNA — 노트 기반 내신형 서술형 문제 생성 + AI 채점
# ─────────────────────────────────────────────────────────────────────────────

# 서술형 유형: 노트 3섹션(단어/대화문/본문)에 매핑되는 출제 의도
_ESSAY_TYPES = {
    "영작":     "주어진 우리말을 영어 문장으로 옮겨 쓰는 조건 영작 (지정 단어 사용·어순)",
    "문장완성": "일부가 빈 영어 문장을 문맥에 맞게 완성 (스캐폴딩 중간 단계에 적합)",
    "요약":     "본문/대화문의 핵심을 한두 문장으로 요약 (영어 또는 우리말)",
    "이유설명": "본문 내용에 대해 '왜?'를 영어로 서술 (근거 문장 인용 권장)",
    "빈칸서술": "핵심 표현을 빈칸으로 두고 의미에 맞는 표현을 직접 서술",
}


def generate_essay_questions(
    text_data: dict,
    words: list[tuple],
    dialogues: list[dict],
    api_config: dict,
    n_questions: int = 3,
    scope: str = "전체",
    difficulty: str = "medium",
    avoid: list[str] | None = None,
) -> list[dict]:
    """반반쌤 서술형 DNA 문제 생성.

    우리 앱만의 5가지 특징을 모두 반영:
      ① 노트 DNA   — scope 범위의 노트 자료에서만 출제
      ② 내신 조건  — 단어 수 제한·지정 어휘 등 실제 내신 조건 부여
      ③ 스캐폴딩    — 각 문제에 3단계(빈칸→문장완성→자유서술)
      ④ AI 채점용   — 모범답안 + 핵심 키워드(채점 루브릭) 동봉
      ⑤ (복습 연동은 호출부에서 처리)

    Returns list of:
    {
      "type": "영작"|"문장완성"|"요약"|"이유설명"|"빈칸서술",
      "source": "단어"|"대화문"|"본문",
      "question": str,            # 서술형 발문 (한국어 지시문)
      "passage": str,             # 근거 지문 (있으면)
      "constraints": str,         # 내신 조건 (예: "given 단어 포함, 8단어 이내")
      "model_answer": str,        # 모범답안
      "keywords": list[str],      # 채점 핵심 키워드 (루브릭)
      "scaffold": {               # 스캐폴딩 3단계
          "step1_blank": str,     # 빈칸형 (가장 쉬움)
          "step1_answer": str,
          "step2_hint": str,      # 문장완성 힌트
      },
      "answer_kr": str,           # 한국어 해설
      "difficulty": str,
    }
    """
    use_word = scope in ("단어", "전체")
    use_dlg  = scope in ("대화문", "전체")
    use_text = scope in ("본문", "전체")

    passage_lines = []
    if text_data.get("sections"):
        for sec in text_data["sections"]:
            for en, kr in sec.get("sentences", []):
                passage_lines.append(f"{en}  ({kr})")
    elif text_data.get("sentences"):
        for en, kr in text_data.get("sentences", []):
            passage_lines.append(f"{en}  ({kr})")
    passage_text = "\n".join(passage_lines[:25]) if use_text else ""

    word_list = "\n".join(f"- {en}: {kr}" for en, kr in words[:30]) if use_word else ""
    dlg_text  = ""
    if use_dlg:
        for dlg in dialogues[:3]:
            dlg_text += f"\n[{dlg.get('title','대화문')}]\n"
            for en, kr in dlg.get("lines", [])[:8]:
                dlg_text += f"  {en}  ({kr})\n"

    diff_desc = _DIFFICULTY_DESC.get(difficulty, _DIFFICULTY_DESC["medium"])

    _SCOPE_GUIDE = {
        "단어":   "지정 단어를 활용한 조건 영작·문장완성 위주로 출제.",
        "대화문": "대화 상황을 설명하거나 빈 대사를 서술하는 문제 위주로 출제.",
        "본문":   "본문 요약·이유 설명·핵심 표현 서술 위주로 출제.",
        "전체":   "단어·대화문·본문을 골고루 활용해 다양한 서술형으로 출제.",
    }
    scope_guide = _SCOPE_GUIDE.get(scope, _SCOPE_GUIDE["전체"])

    avoid = avoid or []
    avoid_block = ""
    if avoid:
        sample = [a for a in avoid if a][-30:]
        avoid_block = (
            "\n[이미 출제된 서술형 — 중복 금지]\n"
            + "\n".join(f"- {a[:80]}" for a in sample)
            + "\n위와 똑같거나 거의 비슷한 문제는 만들지 마세요.\n"
        )

    prompt = f"""당신은 대한민국 최고의 영어 선생님 반반쌤입니다.
내신 서술형 비중이 급증하는 흐름에 맞춰, 학생이 '외우지 말고 생각하게' 만드는
서술형 문제를 출제합니다. 아래 학습 자료(이 학생이 실제로 공부한 반반노트)에서만 출제하세요.
{avoid_block}

[학습 자료]
== 본문 ==
{passage_text if passage_text.strip() else "(이번 범위 아님)"}

== 단어 ==
{word_list if word_list.strip() else "(이번 범위 아님)"}

== 대화문 ==
{dlg_text if dlg_text.strip() else "(이번 범위 아님)"}

[출제 조건 — 반드시 지킬 것]
- 범위: {scope} — {scope_guide}
- 난이도: {diff_desc}
- 문제 수: {n_questions}개
- 서술형 유형(다양하게): {', '.join(_ESSAY_TYPES.keys())}
- ★실제 내신 서술형 조건을 반드시 부여★ (예: "주어진 단어를 모두 사용", "8단어 이내로",
  "현재완료 시제로", "두 문장으로"). 이 조건을 'constraints' 필드에 한국어로 명시.
- ★스캐폴딩 3단계★: 같은 핵심을 묻되 난이도를 3단계로 —
  step1_blank(빈칸 1개만 채우는 가장 쉬운 형태) → step2_hint(문장완성 힌트) → 자유서술(question 본문).
  서술형이 무서운 학생도 step1부터 도전해 성취감을 얻게 합니다.
- ★채점용★: 'model_answer'(모범답안)와 'keywords'(채점 시 반드시 들어가야 할 핵심 표현 2~4개)를 제공.
- 'passage'에는 그 문제가 근거한 실제 노트 문장을 그대로 넣으세요(없으면 "").

반드시 아래 JSON만 반환 (다른 텍스트 금지):
{{
  "questions": [
    {{
      "type": "영작",
      "source": "본문",
      "question": "다음 우리말을 주어진 조건에 맞게 영어로 쓰시오: '지민이는 지하철역에서 친구를 만났다.'",
      "passage": "Jimin met her friend, Sora, at the subway station.",
      "constraints": "given 단어(meet, subway station)를 모두 사용 · 과거시제 · 한 문장",
      "model_answer": "Jimin met her friend at the subway station.",
      "keywords": ["met", "subway station"],
      "scaffold": {{
        "step1_blank": "Jimin _____ her friend at the subway station. (meet의 알맞은 형태)",
        "step1_answer": "met",
        "step2_hint": "주어(Jimin) + 동사(met) + 목적어(her friend) + 장소 순서로 배열해 보세요."
      }},
      "answer_kr": "meet의 과거형 met, 장소 표현 at the subway station이 핵심입니다.",
      "difficulty": "{difficulty}"
    }}
  ]
}}"""

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        qs   = data.get("questions", [])
        seen = {_norm_q(a) for a in avoid}
        valid = []
        for q in qs:
            if q.get("question") and q.get("model_answer"):
                key = _norm_q(q["question"])
                if key in seen:
                    continue
                seen.add(key)
                q.setdefault("difficulty", difficulty)
                q.setdefault("keywords", [])
                q.setdefault("scaffold", {})
                q.setdefault("constraints", "")
                valid.append(q)
        return valid
    except Exception:
        return []


def grade_essay_answer(
    question: str,
    model_answer: str,
    keywords: list[str],
    user_answer: str,
    api_config: dict,
    constraints: str = "",
) -> dict:
    """서술형 답안 AI 채점 — 부분점수 + 개선 피드백.

    단순 O/X가 아니라 "이렇게 바꾸면 더 좋아요"를 돌려주는 게 핵심 차별점.

    Returns:
    {
      "score": int,          # 0~100 (의미 일치도 기반 부분점수)
      "passed": bool,        # 70점 이상이면 통과
      "matched": list[str],  # 포함된 핵심 키워드
      "missing": list[str],  # 빠진 핵심 키워드
      "feedback": str,       # 잘한 점 1문장 (격려)
      "improve": str,        # 개선 제안 1문장 ("이렇게 바꾸면 더 좋아요")
      "grammar": str,        # 문법 지적 (있으면, 없으면 "")
    }
    """
    if not user_answer.strip():
        return {"score": 0, "passed": False, "matched": [], "missing": keywords,
                "feedback": "", "improve": "답을 입력해주세요.", "grammar": ""}

    kw_line = ", ".join(keywords) if keywords else "(지정 없음)"
    prompt = f"""당신은 따뜻하지만 꼼꼼한 영어 선생님 반반쌤입니다.
중학생의 영어 서술형 답안을 채점합니다. 정답/오답만 알려주지 말고,
'어떻게 하면 더 잘 쓸 수 있는지'를 반드시 알려주세요.

[문제] {question}
[출제 조건] {constraints or "(없음)"}
[모범답안] {model_answer}
[채점 핵심 키워드] {kw_line}
[학생 답안] {user_answer}

채점 기준:
- 핵심 의미가 맞으면 표현이 모범답안과 달라도 인정 (의미 일치도 중심)
- 핵심 키워드/표현이 들어갔는지 확인 → matched/missing 으로 구분
- 출제 조건(단어 수·지정 어휘·시제 등) 충족 여부 반영
- score: 의미 일치도 + 조건 충족 + 문법을 종합한 0~100 부분점수
- 70점 이상이면 passed=true
- feedback: 학생이 잘한 점 1문장 (격려 톤)
- improve: 더 나은 답안을 위한 구체적 제안 1문장 (예: "meet을 과거형 met으로 바꾸면 완벽해요")
- grammar: 문법 오류가 있으면 짧게 지적, 없으면 ""

반드시 아래 JSON만 반환 (다른 텍스트 금지):
{{"score": 85, "passed": true, "matched": ["met"], "missing": ["subway station"],
  "feedback": "장소 표현을 정확히 썼어요!", "improve": "meet을 과거형 met으로 바꾸면 완벽해요.",
  "grammar": "시제(과거)에 주의하세요."}}"""

    try:
        raw  = _call_text(prompt, api_config)
        data = _parse_json(raw)
        score  = int(data.get("score", 0))
        return {
            "score":    max(0, min(100, score)),
            "passed":   bool(data.get("passed", score >= 70)),
            "matched":  data.get("matched", []),
            "missing":  data.get("missing", []),
            "feedback": data.get("feedback", ""),
            "improve":  data.get("improve", ""),
            "grammar":  data.get("grammar", ""),
        }
    except Exception:
        # Fallback: 키워드 포함 여부로 단순 채점
        ua = user_answer.lower()
        matched = [k for k in keywords if k.lower() in ua]
        missing = [k for k in keywords if k.lower() not in ua]
        score   = int(len(matched) / len(keywords) * 100) if keywords else 50
        return {
            "score": score, "passed": score >= 70,
            "matched": matched, "missing": missing,
            "feedback": "", "improve": f"모범답안: {model_answer}", "grammar": "",
        }
