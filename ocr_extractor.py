# ocr_extractor.py — S.Y. 담당: 듀얼 AI OCR 모듈
# Anthropic Claude Vision  또는  Google Gemini Vision 자동 선택

import base64
import json
import re
import io

# ─────────────────────────────────────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """LLM 응답 → JSON 파싱 (마크다운 코드블록 처리)"""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if m:
        raw = m.group(1)
    raw = raw.strip()
    # JSON 시작 위치 찾기 (앞에 여분 텍스트가 있을 경우)
    start = raw.find("{")
    if start > 0:
        raw = raw[start:]
    return json.loads(raw)


def _encode_image(image_bytes: bytes) -> tuple[str, str]:
    """이미지 bytes → (base64, mime_type)"""
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    if image_bytes[:4] == b"\x89PNG":
        mime = "image/png"
    elif image_bytes[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    elif image_bytes[:4] == b"RIFF":
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    return b64, mime


# ─────────────────────────────────────────────────────────────────────────────
# AI 백엔드 — Anthropic
# ─────────────────────────────────────────────────────────────────────────────

def _call_anthropic(image_bytes: bytes, prompt: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    b64, mime = _encode_image(image_bytes)
    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": mime, "data": b64}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return resp.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# AI 백엔드 — Google Gemini
# ─────────────────────────────────────────────────────────────────────────────

def _call_gemini(image_bytes: bytes, prompt: str, api_key: str,
                 model: str = "gemini-2.5-flash") -> str:
    from google import genai
    from google.genai import types
    from PIL import Image

    client = genai.Client(api_key=api_key)
    img = Image.open(io.BytesIO(image_bytes))
    resp = client.models.generate_content(
        model=model,
        contents=[prompt, img],
    )
    return resp.text


# ─────────────────────────────────────────────────────────────────────────────
# 공통 디스패처
# ─────────────────────────────────────────────────────────────────────────────

def _call_ai(image_bytes: bytes, prompt: str, api_config: dict) -> str:
    """이미지 + 텍스트 프롬프트 → AI 응답"""
    atype = api_config.get("type", "")
    key   = api_config.get("key", "")
    if not key:
        raise ValueError("API 키가 설정되지 않았습니다.")

    if atype == "anthropic":
        return _call_anthropic(image_bytes, prompt, key)
    elif atype == "gemini":
        return _call_gemini(image_bytes, prompt, key)
    else:
        raise ValueError(f"알 수 없는 API 타입: {atype}")


def _call_ai_text(prompt: str, api_config: dict) -> str:
    """이미지 없이 텍스트 전용 AI 호출"""
    atype = api_config.get("type", "")
    key   = api_config.get("key", "")
    if not key:
        raise ValueError("API 키가 설정되지 않았습니다.")

    if atype == "anthropic":
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model="claude-opus-4-5", max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    elif atype == "gemini":
        from google import genai
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt]
        )
        return resp.text
    else:
        raise ValueError(f"알 수 없는 API 타입: {atype}")


# ─────────────────────────────────────────────────────────────────────────────
# 프롬프트 템플릿
# ─────────────────────────────────────────────────────────────────────────────

_PROMPT_WORDS = """이 영어 교과서 이미지에서 단어 목록을 추출해주세요.

반드시 아래 JSON 형식만 반환하세요 (다른 텍스트 절대 금지):
{
  "words": [
    {"en": "blind", "kr": "눈이 먼"},
    {"en": "amusement park", "kr": "놀이공원"}
  ]
}

규칙:
- 영어 단어/표현: 이미지에서 정확히 추출 (구동사, 숙어 포함)
- 한국어 뜻: 이미지에 있으면 그대로, 없으면 중학교 수준 번역
- 번호·체크박스 제외, 단어와 뜻만 추출
- 이미지 순서대로
- 순수 JSON만 반환"""

_PROMPT_DIALOGUES = """이 영어 교과서 이미지에서 대화문을 모두 추출해주세요.

반드시 아래 JSON 형식만 반환하세요 (다른 텍스트 절대 금지):
{
  "dialogues": [
    {
      "title": "대화문1",
      "lines": [
        {"en": "G: I'm excited about the school festival.", "kr": "G: 나는 학교 축제에 신나요."},
        {"en": "B: Me too.", "kr": "B: 나도요."}
      ]
    }
  ]
}

규칙:
- 대화문 제목: 이미지의 번호/제목 사용
- 영어 대사: 정확히 추출, 화자 표시(B: G: M: W: A: H: 등) 유지
- 한국어: 이미지에 있으면 그대로, 없으면 자연스러운 번역 (화자 표시 유지)
- 대화문 여러 개이면 모두 추출
- Q&A 문제, 주석(❶❷ 등)은 제외
- 순수 JSON만 반환"""

_PROMPT_TEXT = """이 영어 교과서 본문 이미지에서 텍스트를 추출하고 서론/본론/결론으로 단락을 분류해주세요.

반드시 아래 JSON 형식만 반환하세요 (다른 텍스트 절대 금지):
{
  "title_en": "The Power of Small Acts",
  "title_kr": "작은 행동의 힘",
  "sections": [
    {
      "label": "서론",
      "sentences": [
        {"en": "01 Jimin woke up. It was bright and sunny.", "kr": "01 지민이가 잠에서 깼어요. 밖은 밝고 화창했어요."},
        {"en": "02 Mom said, 'Have fun!'", "kr": "02 엄마가 말했어요. '즐겁게 놀렴!'"}
      ]
    },
    {
      "label": "본론",
      "sentences": [
        {"en": "03 Jimin met her friend Sora at the subway station.", "kr": "03 지민이는 지하철역에서 친구 소라를 만났어요."}
      ]
    },
    {
      "label": "결론",
      "sentences": [
        {"en": "25 On the way home, Jimin thought,", "kr": "25 집으로 돌아오는 지하철 안에서 지민이는 생각했어요,"}
      ]
    }
  ]
}

규칙:
- 제목: 영어/한국어 모두 추출 (없으면 번역 생성)
- 서론: 이야기 도입부 / 인물·상황 소개 (처음 약 20~25%)
- 본론: 중심 사건·전개 (중간 약 50~60%)
- 결론: 마무리·교훈·결말 (마지막 약 20~25%)
- 각 섹션에 최소 1개 이상 문장 포함, 내용에 따라 자연스럽게 분류
- 문장 번호(01, 02...)는 섹션에 관계없이 원문 번호 유지
- 한국어: 이미지에 있으면 그대로, 없으면 자연스러운 번역
- 보이는 모든 문장 추출
- 순수 JSON만 반환"""

_PROMPT_META = """이 교과서 이미지에서 교과서 정보를 추출해주세요.

반드시 아래 JSON 형식만 반환:
{
  "grade": "중2",
  "publisher": "NE능률",
  "author": "김기택",
  "chapter": "3",
  "confidence": "high"
}

- grade: 중1/중2/중3/고1/고2/고3 (페이지 하단 등에서 추출)
- publisher: YBM/NE능률/천재교육/동아출판/비상교육/미래엔/지학사/금성출판사 중 하나
- author: 저자명
- chapter: 과 번호 (숫자만)
- confidence: 확실하면 "high", 추정이면 "low"
- 찾을 수 없으면 빈 문자열("")
- 순수 JSON만 반환"""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_words(image_bytes: bytes, api_config: dict) -> list[tuple[str, str]]:
    """단어 이미지 → [(영어, 한국어), ...]"""
    raw  = _call_ai(image_bytes, _PROMPT_WORDS, api_config)
    data = _parse_json(raw)
    return [(w["en"].strip(), w["kr"].strip())
            for w in data.get("words", []) if w.get("en")]


def extract_dialogues(image_bytes: bytes, api_config: dict) -> list[dict]:
    """대화문 이미지 → [{'title': str, 'lines': [(en, kr), ...]}, ...]"""
    raw  = _call_ai(image_bytes, _PROMPT_DIALOGUES, api_config)
    data = _parse_json(raw)
    result = []
    for dlg in data.get("dialogues", []):
        lines = [(l["en"].strip(), l["kr"].strip())
                 for l in dlg.get("lines", []) if l.get("en")]
        if lines:
            result.append({"title": dlg.get("title", "대화문"), "lines": lines})
    return result


def extract_text(image_bytes: bytes, api_config: dict) -> dict:
    """본문 이미지 → {'title_en', 'title_kr', 'sentences', 'sections'(선택)}

    AI가 섹션 형식으로 응답하면 'sections' 키 포함.
    응답이 구 형식(flat sentences)이면 하위 호환 처리.
    """
    raw  = _call_ai(image_bytes, _PROMPT_TEXT, api_config)
    data = _parse_json(raw)

    result = {
        "title_en": data.get("title_en", ""),
        "title_kr": data.get("title_kr", ""),
    }

    raw_sections = data.get("sections", [])
    if raw_sections:
        # 새 섹션 형식
        sections      = []
        all_sentences = []
        for sec in raw_sections:
            sents = [(s["en"].strip(), s["kr"].strip())
                     for s in sec.get("sentences", []) if s.get("en")]
            if sents:
                sections.append({"label": sec.get("label", ""), "sentences": sents})
                all_sentences.extend(sents)
        result["sentences"] = all_sentences
        result["sections"]  = sections
    else:
        # 구 형식 (flat sentences) — 하위 호환
        result["sentences"] = [(s["en"].strip(), s["kr"].strip())
                               for s in data.get("sentences", []) if s.get("en")]

    return result


def detect_metadata(image_bytes: bytes, api_config: dict) -> dict:
    """교과서 정보 자동 인식 (학년, 출판사, 저자, 과)"""
    try:
        raw  = _call_ai(image_bytes, _PROMPT_META, api_config)
        return _parse_json(raw)
    except Exception:
        return {"grade": "", "publisher": "", "author": "", "chapter": "", "confidence": "low"}


def translate_to_pairs(plain_text: str, api_config: dict) -> dict:
    """
    순수 영어 본문 → {'title_en', 'title_kr', 'sentences', 'sections'}
    한글 번역이 없는 영어 텍스트를 스발노트 형식으로 변환하고 서론/본론/결론으로 분류
    """
    prompt = f"""다음 영어 교과서 본문을 분석하고 한국어로 번역한 뒤 서론/본론/결론으로 분류해주세요.

[영어 본문]
{plain_text}

반드시 아래 JSON 형식만 반환하세요 (다른 텍스트 절대 금지):
{{
  "title_en": "School Safety",
  "title_kr": "학교 안전",
  "sections": [
    {{
      "label": "서론",
      "sentences": [
        {{"en": "01 Hello, I'm Safer.", "kr": "01 안녕하세요, 저는 세이퍼예요."}}
      ]
    }},
    {{
      "label": "본론",
      "sentences": [
        {{"en": "02 Many students have fun at school.", "kr": "02 많은 학생들이 학교에서 즐거운 시간을 보내요."}}
      ]
    }},
    {{
      "label": "결론",
      "sentences": [
        {{"en": "10 Stay safe and have fun!", "kr": "10 안전하게 즐겁게 지내세요!"}}
      ]
    }}
  ]
}}

규칙:
- title_en/title_kr: 본문 전체 내용에 맞는 제목 생성
- 각 문장에 01, 02, 03... 순서 번호 부여 (섹션에 관계없이 연속)
- 서론: 이야기 도입부·상황 설정 / 본론: 중심 사건·전개 / 결론: 마무리·교훈·결말
- 자연스러운 중학교 수준 한국어 번역
- 소제목(Time / Causes / Injuries 등)도 문장으로 포함
- 줄바꿈으로 나뉜 긴 문장은 자연스럽게 이어붙이기
- 순수 JSON만 반환"""

    try:
        raw  = _call_ai_text(prompt, api_config)
        data = _parse_json(raw)

        raw_sections = data.get("sections", [])
        if raw_sections:
            sections      = []
            all_sentences = []
            for sec in raw_sections:
                sents = [(s["en"].strip(), s["kr"].strip())
                         for s in sec.get("sentences", []) if s.get("en")]
                if sents:
                    sections.append({"label": sec.get("label", ""), "sentences": sents})
                    all_sentences.extend(sents)
            return {
                "title_en":  data.get("title_en", ""),
                "title_kr":  data.get("title_kr", ""),
                "sentences": all_sentences,
                "sections":  sections,
            }
        else:
            # 구 형식 fallback
            return {
                "title_en":  data.get("title_en", ""),
                "title_kr":  data.get("title_kr", ""),
                "sentences": [(s["en"].strip(), s["kr"].strip())
                              for s in data.get("sentences", []) if s.get("en")],
            }
    except Exception as e:
        raise RuntimeError(f"번역 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# PDF → 이미지 변환 (PyMuPDF)
# ─────────────────────────────────────────────────────────────────────────────

def pdf_to_images(pdf_bytes: bytes, dpi: int = 150) -> list[bytes]:
    """PDF bytes → 페이지별 PNG bytes 리스트.
    dpi=150 은 OCR에 충분하면서 메모리 효율적.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise RuntimeError("PDF 처리 라이브러리가 없습니다. pip install pymupdf 를 실행해 주세요.")

    images: list[bytes] = []
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    mat = fitz.Matrix(dpi / 72, dpi / 72)   # 72dpi 기본 → scale factor
    for page in doc:
        pix  = page.get_pixmap(matrix=mat, alpha=False)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def pdf_page_count(pdf_bytes: bytes) -> int:
    """PDF 총 페이지 수."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        n   = len(doc)
        doc.close()
        return n
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# 텍스트 직접 입력 → 노트 형식 자동 정리
# ─────────────────────────────────────────────────────────────────────────────

_PROMPT_ORGANIZE_WORDS = """아래 텍스트에서 영어 단어/표현과 한국어 뜻을 추출하고 정리해주세요.

입력 텍스트:
{text}

반드시 아래 JSON 형식만 반환하세요:
{{
  "words": [
    {{"en": "blind", "kr": "눈이 먼"}},
    {{"en": "amusement park", "kr": "놀이공원"}}
  ]
}}

규칙:
- 영어와 한국어 뜻이 함께 있으면 그대로 추출
- 영어만 있으면 중학교 수준 한국어 뜻 생성
- 중복 제거, 깔끔하게 정리
- 순수 JSON만 반환"""


_PROMPT_ORGANIZE_DIALOGUES = """아래 텍스트를 대화문 형식으로 정리해주세요.

입력 텍스트:
{text}

반드시 아래 JSON 형식만 반환하세요:
{{
  "dialogues": [
    {{
      "title": "대화문1",
      "lines": [
        {{"en": "G: I'm excited about the school festival.", "kr": "G: 나는 학교 축제에 신나요."}},
        {{"en": "B: Me too!", "kr": "B: 나도요!"}}
      ]
    }}
  ]
}}

규칙:
- 화자 표시(G:, B:, W:, M: 등) 유지
- 한국어 번역이 없으면 자연스럽게 생성
- 대화 흐름에 맞게 분리
- 순수 JSON만 반환"""


_PROMPT_ORGANIZE_TEXT = """아래 텍스트를 영어 지문 형식으로 정리하고 한국어 번역을 추가해주세요.

입력 텍스트:
{text}

반드시 아래 JSON 형식만 반환하세요:
{{
  "title_en": "The Power of Small Acts",
  "title_kr": "작은 행동의 힘",
  "sections": [
    {{
      "label": "서론",
      "sentences": [
        {{"en": "Jimin woke up early.", "kr": "지민이는 일찍 일어났어요."}}
      ]
    }},
    {{
      "label": "본론",
      "sentences": [
        {{"en": "She decided to help others.", "kr": "그녀는 다른 사람을 돕기로 결심했어요."}}
      ]
    }},
    {{
      "label": "결론",
      "sentences": [
        {{"en": "Small acts make a big difference.", "kr": "작은 행동이 큰 변화를 만들어요."}}
      ]
    }}
  ]
}}

규칙:
- 자연스럽게 서론/본론/결론으로 분류
- 한국어 번역은 중학생 수준으로
- 문장 단위로 분리
- 순수 JSON만 반환"""


def organize_text_input(
    raw_text: str,
    content_type: str,   # "단어" | "대화문" | "본문"
    api_config: dict,
) -> dict:
    """사용자 입력 원문 텍스트 → 노트 형식으로 AI 정리.

    Returns:
        content_type=="단어"   → {"words": [(en,kr), ...]}
        content_type=="대화문" → {"dialogues": [...]}
        content_type=="본문"   → {"title_en":..., "title_kr":..., "sections":[...]}
    """
    prompt_map = {
        "단어":   _PROMPT_ORGANIZE_WORDS,
        "대화문": _PROMPT_ORGANIZE_DIALOGUES,
        "본문":   _PROMPT_ORGANIZE_TEXT,
    }
    tmpl = prompt_map.get(content_type, _PROMPT_ORGANIZE_TEXT)
    prompt = tmpl.format(text=raw_text.strip())

    try:
        raw  = _call_ai_text(prompt, api_config)
        data = _parse_json(raw)
    except Exception as e:
        raise RuntimeError(f"텍스트 정리 실패: {e}") from e

    if content_type == "단어":
        words = data.get("words", [])
        return {
            "words": [(w["en"].strip(), w["kr"].strip())
                      for w in words if w.get("en")]
        }
    elif content_type == "대화문":
        dlgs = data.get("dialogues", [])
        result = []
        for d in dlgs:
            lines = []
            for l in d.get("lines", []):
                if isinstance(l, dict):
                    lines.append((l.get("en",""), l.get("kr","")))
                elif isinstance(l, (list, tuple)) and len(l) >= 2:
                    lines.append((l[0], l[1]))
            result.append({"title": d.get("title","대화문"), "lines": lines})
        return {"dialogues": result}
    else:  # 본문
        sections = []
        for sec in data.get("sections", []):
            sents = []
            for s in sec.get("sentences", []):
                if isinstance(s, dict):
                    sents.append((s.get("en",""), s.get("kr","")))
            sections.append({"label": sec.get("label",""), "sentences": sents})
        return {
            "title_en":  data.get("title_en", ""),
            "title_kr":  data.get("title_kr", ""),
            "sections":  sections,
        }
