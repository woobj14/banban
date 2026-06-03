# study_grammar.py — 반반쌤 담당: 문법학습 모듈
# AI 문법 포인트 추출 + 선생님 편집 + 4종 드릴 + 문법뱅크 연동

import json
import random
import time
import streamlit as st
import streamlit.components.v1 as components
from icons import icon, section_md, title_md, confirm_delete_btn
from sounds import queue_sound, play_pending_sound
from study_db import (
    get_grammar_points, save_grammar_point, update_grammar_point,
    delete_grammar_point, get_question_bank, count_question_bank,
    save_to_question_bank, add_question_wrong, get_question_wrong_notes,
    log_study_activity, remove_question_wrong,
)


# ─────────────────────────────────────────────────────────────────────────────
# TTS 헬퍼 — Web Speech API (Lucide 아이콘 지침에 따라 icon() 사용 금지, 이모지 사용)
# ─────────────────────────────────────────────────────────────────────────────

def _grammar_tts(text: str, key: str = "g", label: str = "정답 발음 듣기",
                 color: str = "#4F46E5"):
    """문법 TTS 버튼 (드릴 정답 / 예문 공용).
    st.button()은 HTML 미지원 → components.html 사용.
    HTML 내 아이콘은 Lucide SVG 인라인 사용 (이모지 금지).
    """
    safe = text.replace("'", "\\'").replace('"', '\\"').replace("\n", " ")
    volume_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" '
        'viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align:middle;margin-right:5px;">'
        '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
        '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>'
        '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>'
        '</svg>'
    )
    playing_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" '
        'viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" '
        'style="vertical-align:middle;margin-right:5px;">'
        '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
        '<line x1="23" x2="23" y1="9" y2="15"/>'
        '<line x1="19" x2="19" y1="7" y2="17"/>'
        '</svg>'
    )
    components.html(f"""
<script>
function gtts_{key}(){{
  if(!window.speechSynthesis)return;
  window.speechSynthesis.cancel();
  var u=new SpeechSynthesisUtterance('{safe}');
  u.lang='en-US';u.rate=0.85;u.pitch=1.0;
  var vv=window.speechSynthesis.getVoices();
  var v=vv.find(function(x){{return(x.name.indexOf('Google')>-1||x.name.indexOf('Samantha')>-1)&&x.lang.indexOf('en')===0;}})
    ||vv.find(function(x){{return x.lang==='en-US';}});
  if(v)u.voice=v;
  var b=document.getElementById('gttsb_{key}');
  if(b){{b.innerHTML='{playing_svg} 재생 중…';b.style.background='#059669';}}
  u.onend=function(){{if(b){{b.innerHTML='{volume_svg} {label}';b.style.background='{color}';}}}};
  window.speechSynthesis.speak(u);
}}
</script>
<button id="gttsb_{key}" onclick="gtts_{key}()"
  style="display:inline-flex;align-items:center;
         background:{color};color:white;border:none;border-radius:20px;
         padding:6px 14px;font-size:0.78rem;font-weight:700;cursor:pointer;
         margin:4px 0;box-shadow:0 2px 6px rgba(79,70,229,0.25);
         transition:background 0.2s;">
  {volume_svg} {label}
</button>
""", height=44)


# ─────────────────────────────────────────────────────────────────────────────
# AI 문법 포인트 추출
# ─────────────────────────────────────────────────────────────────────────────

def extract_grammar_points_ai(text_data: dict, dialogues: list[dict],
                               api_config: dict) -> list[dict]:
    """본문+대화문 → 문법 포인트 2~3개 추출"""
    passage_lines = []
    if text_data.get("sections"):
        for sec in text_data["sections"]:
            for en, _ in sec.get("sentences", []):
                passage_lines.append(en)
    elif text_data.get("sentences"):
        for en, _ in text_data.get("sentences", []):
            passage_lines.append(en)
    passage_text = "\n".join(passage_lines[:25])

    dlg_text = ""
    for dlg in dialogues[:5]:
        for en, _ in dlg.get("lines", []):
            dlg_text += en + "\n"

    prompt = f"""당신은 대한민국 최고의 영어 선생님 반반쌤입니다.
아래 중학교 영어 교과서 본문과 대화문을 분석해서 핵심 문법 포인트를 추출해주세요.

[본문]
{passage_text}

[대화문]
{dlg_text[:800] if dlg_text.strip() else "(없음)"}

반드시 아래 JSON 형식만 반환 (다른 텍스트 절대 금지):
{{
  "grammar_points": [
    {{
      "point_name": "may + V (허가/추측)",
      "category": "조동사",
      "explanation_kr": "may는 두 가지 뜻이 있어요.\\n① 허가: ~해도 된다 (May I ~? 로 물어볼 때)\\n② 추측: ~일지도 모른다 (평서문에서 사용)",
      "patterns": [
        "May I + V? → ~해도 될까요?",
        "You may + V → ~해도 됩니다",
        "It may + V → ~할지도 몰라요"
      ],
      "textbook_examples": [
        ["May I pull down the blind?", "블라인드를 내려도 될까요?"],
        ["You may talk on the phone quietly.", "조용히 전화 통화는 해도 됩니다."]
      ],
      "tip": "허가 요청은 의문문(May I~?), 추측은 평서문(It may~)으로 구분해요!"
    }}
  ]
}}

규칙:
- 2~3개 핵심 문법 포인트만 추출 (중학생 수준)
- 교과서에 실제 등장하는 예문 우선 사용
- explanation_kr: 3~5줄, 친절한 선생님 말투
- patterns: 핵심 패턴 2~3개
- tip: 기억하기 쉬운 한 줄 팁
- 순수 JSON만 반환"""

    from ocr_extractor import _call_ai_text
    try:
        raw  = _call_ai_text(prompt, api_config)
        raw  = raw.strip()
        import re
        m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        if m: raw = m.group(1)
        s = raw.find("{")
        if s > 0: raw = raw[s:]
        data = json.loads(raw)
        return data.get("grammar_points", [])
    except Exception as e:
        raise RuntimeError(f"문법 포인트 추출 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# AI 문법 드릴 문제 생성
# ─────────────────────────────────────────────────────────────────────────────

_DRILL_TYPES = {
    "빈칸완성":  "Fill-in-the-blank: 빈칸에 알맞은 말을 고르시오",
    "오류찾기":  "Error correction: 틀린 부분을 고쳐 쓰시오",
    "배열하기":  "Word ordering: 주어진 단어를 바르게 배열하시오",
    "우리말→영어": "Translation: 우리말을 영어로 쓰시오",
}


def _make_timer_html(q_idx: int, dur_s: int = 30) -> str:
    """카운트다운 타이머 HTML — components.html(height=38)로 임베드."""
    ms = dur_s * 1000
    return f"""<html><body style="margin:0;padding:2px 0 2px 0;overflow:hidden;background:transparent">
<div style="width:100%;height:7px;background:#e5e7eb;border-radius:4px;overflow:hidden">
  <div id="tb{q_idx}" style="height:100%;width:100%;background:#7c3aed;border-radius:4px"></div>
</div>
<div id="tl{q_idx}" style="font-size:0.68rem;color:#9ca3af;text-align:right;
     margin-top:2px;font-weight:600;font-family:monospace">{dur_s}s ⏱</div>
<script>
!function(){{
  var ms={ms},s=Date.now(),
      b=document.getElementById('tb{q_idx}'),
      l=document.getElementById('tl{q_idx}');
  function f(){{
    var r=Math.max(0,ms-(Date.now()-s)),p=r/ms*100;
    if(!b)return;
    b.style.width=p+'%';
    l.textContent=(r/1000).toFixed(1)+'s ⏱';
    b.style.background=p>60?'#7c3aed':p>30?'#f59e0b':'#ef4444';
    if(r>0)requestAnimationFrame(f);
    else{{b.style.background='#ef4444';l.textContent='⏰ Time up!';}}
  }}
  f();
}}();
</script>
</body></html>"""


def generate_grammar_drills(
    grammar_point: dict,
    api_config: dict,
    n: int = 4,
    existing_questions: list[str] | None = None,
    text_context: str = "",
) -> list[dict]:
    """문법 포인트 → 4종 드릴 문제 생성 (중복 방지 + 교과서 문맥 연계)"""
    pt_name  = grammar_point.get("point_name", "")
    explain  = grammar_point.get("explanation_kr", "")
    patterns = grammar_point.get("patterns", [])
    examples = grammar_point.get("examples", [])

    ex_text  = "\n".join(f"- {e[0]} ({e[1]})" for e in examples if isinstance(e, (list, tuple)) and len(e) >= 2)
    pat_text = "\n".join(f"- {p}" for p in patterns)

    # 중복 방지 블록
    dup_block = ""
    if existing_questions:
        dup_lines = "\n".join(f"- {q[:80]}" for q in existing_questions[:20])
        dup_block = (
            f"\n[이미 출제된 문제 — 동일하거나 유사한 문제는 절대 출제 금지]\n"
            f"{dup_lines}\n"
        )

    # 교과서 본문 컨텍스트 블록
    ctx_block = ""
    if text_context.strip():
        ctx_block = (
            f"\n[교과서 본문 (이 내용과 연결해서 출제 — 실제 문장을 활용하세요)]\n"
            f"{text_context[:600]}\n"
        )

    prompt = f"""당신은 친절한 영어 선생님 반반쌤입니다.
아래 문법 포인트에 대한 중학생용 연습 문제를 {n}개 만들어주세요.
빈칸완성, 오류찾기, 배열하기, 우리말→영어 유형을 골고루 포함하세요.

[문법 포인트] {pt_name}
[설명] {explain[:300]}
[핵심 패턴]
{pat_text}
[교과서 예문]
{ex_text}
{ctx_block}{dup_block}
반드시 아래 JSON 형식만 반환:
{{
  "drills": [
    {{
      "type": "빈칸완성",
      "question": "You ___ sit here. It's fine.",
      "passage": "교과서 본문에서 발췌한 관련 문장 (없으면 빈 문자열)",
      "options": ["① may", "② might", "③ can't", "④ must"],
      "answer": "① may",
      "answer_kr": "허가 표현 may를 씁니다.",
      "hint": "허가를 나타낼 때 may를 써요"
    }},
    {{
      "type": "오류찾기",
      "question": "다음 문장에서 틀린 부분을 찾아 고쳐 쓰시오.\\nMay I going to the movies?",
      "passage": "",
      "options": [],
      "answer": "going → go (may 뒤에는 동사원형)",
      "answer_kr": "조동사 may 뒤에는 동사원형이 옵니다.",
      "hint": "조동사 뒤 동사 형태를 확인하세요"
    }},
    {{
      "type": "배열하기",
      "question": "다음 단어를 올바른 순서로 배열하시오.\\n[ may / I / here / sit ]",
      "passage": "",
      "options": [],
      "answer": "May I sit here?",
      "answer_kr": "May I + 동사원형 순서로 배열합니다.",
      "hint": "허가 요청 의문문은 May I로 시작해요"
    }},
    {{
      "type": "우리말→영어",
      "question": "우리말을 영어로 쓰시오.\\n'여기 앉아도 될까요?'",
      "passage": "",
      "options": [],
      "answer": "May I sit here?",
      "answer_kr": "May I + 동사원형 구조를 사용합니다.",
      "hint": "May I로 시작하는 의문문을 만들어요"
    }}
  ]
}}

규칙:
- 교과서 본문이 있으면 해당 문장을 passage 필드에 넣고 연결된 문제 출제
- 객관식(빈칸완성)은 보기 4개 (①②③④)
- 주관식(오류찾기/배열하기/우리말→영어)은 options를 []로
- 이미 출제된 문제와 같거나 유사하면 반드시 피할 것
- 중학생 수준의 어휘 사용
- 순수 JSON만 반환"""

    from ocr_extractor import _call_ai_text
    try:
        raw  = _call_ai_text(prompt, api_config)
        raw  = raw.strip()
        import re
        m = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        if m: raw = m.group(1)
        s = raw.find("{")
        if s > 0: raw = raw[s:]
        data   = json.loads(raw)
        drills = data.get("drills", [])
        # 유효성 보정 + 중복 제거 (기존 문제 & 자체 중복)
        import re as _re
        def _nq(t: str) -> str:
            return _re.sub(r"\s+", " ",
                           _re.sub(r"[^\w가-힣]", " ", (t or "").lower())).strip()
        seen = {_nq(q) for q in (existing_questions or [])}
        out  = []
        for d in drills:
            q = d.get("question", "")
            if not q:
                continue
            key = _nq(q)
            if key in seen:
                continue
            seen.add(key)
            d.setdefault("type",      "빈칸완성")
            d.setdefault("passage",   "")
            d.setdefault("options",   [])
            d.setdefault("answer",    "")
            d.setdefault("answer_kr", "")
            d.setdefault("hint",      "")
            out.append(d)
        return out
    except Exception as e:
        raise RuntimeError(f"드릴 생성 실패: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
# 문법 포인트 카드 렌더링
# ─────────────────────────────────────────────────────────────────────────────

_CAT_COLORS = {
    "조동사":   ("#4F46E5", "#ede9fe"),
    "시제":     ("#166534", "#dcfce7"),
    "전치사":   ("#92400e", "#fef3c7"),
    "문장구조": ("#6d28d9", "#ede9fe"),
    "기타":     ("#374151", "#f3f4f6"),
}


def _render_grammar_card(gp: dict):
    cat    = gp.get("category", "기타")
    hdr_c, bg_c = _CAT_COLORS.get(cat, _CAT_COLORS["기타"])
    name   = gp.get("point_name", "")
    expl   = gp.get("explanation_kr", "").replace("\n", "<br>")
    patterns = gp.get("patterns", [])
    examples = gp.get("examples", [])
    tip    = gp.get("tip", "")

    pat_html = "".join(
        f'<div style="background:rgba(255,255,255,0.7);border-radius:6px;'
        f'padding:5px 10px;margin:3px 0;font-size:0.83rem;font-family:monospace;">'
        f'{p}</div>' for p in patterns
    )

    valid_examples = [e for e in examples[:4] if isinstance(e, (list, tuple)) and len(e) >= 1]

    ex_html = "".join(
        f'<div style="margin:4px 0;">'
        f'<span style="color:{hdr_c};font-weight:600;">{e[0]}</span><br>'
        f'<span style="color:#6b7280;font-size:0.82rem;">'
        f'{e[1] if len(e) > 1 else ""}</span></div>'
        for e in valid_examples
    )

    st.markdown(f"""
<div style="background:{bg_c};border-radius:14px;padding:18px;margin-bottom:4px;
     border-left:5px solid {hdr_c};">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <span style="font-weight:800;color:{hdr_c};font-size:1.05rem;">{name}</span>
    <span style="background:{hdr_c};color:white;border-radius:20px;
          padding:2px 10px;font-size:0.72rem;">{cat}</span>
  </div>
  <div style="font-size:0.88rem;color:#374151;line-height:1.8;margin-bottom:10px;">{expl}</div>
  <div style="margin-bottom:10px;">
    <div style="font-size:0.78rem;font-weight:700;color:{hdr_c};margin-bottom:4px;">
      {icon("layers",13,hdr_c)} 핵심 패턴
    </div>
    {pat_html}
  </div>
  {'<div style="margin-bottom:6px;"><div style="font-size:0.78rem;font-weight:700;color:' + hdr_c + ';margin-bottom:4px;">' + icon("book-open",13,hdr_c) + ' 교과서 예문</div>' + ex_html + '</div>' if ex_html else ''}
  {'<div style="background:rgba(255,255,255,0.8);border-radius:8px;padding:8px 12px;font-size:0.82rem;color:#374151;">' + icon("zap",13,"#f59e0b") + ' <b>TIP</b> ' + tip + '</div>' if tip else ''}
</div>
""", unsafe_allow_html=True)

    if valid_examples:
        gp_key = str(gp.get("id", name.replace(" ", "_")))
        for i, ex in enumerate(valid_examples):
            en_text = ex[0].strip()
            if en_text:
                _grammar_tts(
                    en_text,
                    key=f"gc_{gp_key}_{i}",
                    label=f"예문 {i+1} 듣기",
                    color=hdr_c,
                )

    st.markdown('<div style="margin-bottom:14px;"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 드릴 진행 상태
# ─────────────────────────────────────────────────────────────────────────────

def _init_drill_state(drills: list[dict], grammar_point_id: int,
                      grammar_point_name: str, student_id: int | None, note_id: int):
    st.session_state["grammar_drill"] = {
        "drills":       drills,
        "idx":          0,
        "score":        0,
        "wrong":        [],
        "answered":     False,
        "last_ok":      None,
        "gp_id":        grammar_point_id,
        "gp_name":      grammar_point_name,
        "student_id":   student_id,
        "note_id":      note_id,
        "done":         False,
        # 콤보 + 반응 시스템
        "combo":        0,
        "max_combo":    0,
        "reaction":     "",
        "ai_feedback":  "",
        "last_q_idx":   -1,
        "q_start_time": None,
    }


def _render_drill(api_config: dict | None):
    """문법 드릴 진행 화면 — 타이머 + 콤보 + 반반쌤 반응"""
    d = st.session_state.get("grammar_drill", {})
    if not d:
        return

    # 사운드 재생 (이전 답안 처리에서 예약된 경우)
    play_pending_sound()

    if d.get("done"):
        _render_drill_result(api_config)
        return

    drills = d["drills"]
    idx    = d["idx"]
    if idx >= len(drills):
        d["done"] = True
        st.rerun()
        return

    q     = drills[idx]
    tot   = len(drills)
    pct   = int(idx / tot * 100)
    combo = d.get("combo", 0)

    # 콤보 배지 HTML
    if combo >= 7:
        combo_badge = (f'<span style="background:#7c3aed;color:white;border-radius:16px;'
                       f'padding:2px 10px;font-size:0.78rem;font-weight:700;margin-left:8px;">'
                       f'💥 {combo}연속!</span>')
    elif combo >= 5:
        combo_badge = (f'<span style="background:#f59e0b;color:white;border-radius:16px;'
                       f'padding:2px 10px;font-size:0.78rem;font-weight:700;margin-left:8px;">'
                       f'⚡ {combo}연속!</span>')
    elif combo >= 3:
        combo_badge = (f'<span style="background:#ef4444;color:white;border-radius:16px;'
                       f'padding:2px 10px;font-size:0.78rem;font-weight:700;margin-left:8px;">'
                       f'🔥 {combo}연속!</span>')
    else:
        combo_badge = ""

    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
  <span style="font-size:0.85rem;color:#6b7280;">
    드릴 {idx+1} / {tot} &nbsp;|&nbsp; {d['gp_name']}
  </span>
  <span style="font-size:0.85rem;font-weight:700;color:#7c3aed;">
    점수: {d['score']}{combo_badge}
  </span>
</div>
<div style="background:#e5e7eb;border-radius:4px;height:6px;margin-bottom:8px;">
  <div style="background:#7c3aed;height:100%;width:{pct}%;border-radius:4px;"></div>
</div>
""", unsafe_allow_html=True)

    # 타이머 (미답변 상태에서만)
    if not d.get("answered"):
        if d.get("last_q_idx") != idx:
            d["q_start_time"] = time.time()
            d["last_q_idx"]   = idx
        components.html(_make_timer_html(idx, dur_s=30), height=38, scrolling=False)

    q_type = q.get("type", "")
    type_color = {
        "빈칸완성":   "#6366F1",
        "오류찾기":   "#dc2626",
        "배열하기":   "#166534",
        "우리말→영어": "#92400e",
    }.get(q_type, "#374151")

    # 교과서 본문 컨텍스트 카드 (있을 때만)
    if q.get("passage"):
        st.markdown(f"""
<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
     padding:10px 14px;margin-bottom:10px;">
  <div style="font-size:0.72rem;font-weight:700;color:#3b82f6;margin-bottom:4px;">
    📖 교과서 본문
  </div>
  <div style="font-size:0.88rem;color:#1e40af;font-style:italic;line-height:1.6;">
    {q['passage']}
  </div>
</div>
""", unsafe_allow_html=True)

    # 힌트 (미답변 상태에서만)
    hint_html = ""
    if q.get("hint") and not d.get("answered"):
        hint_html = (
            f'<div style="background:#f8fafc;border-radius:6px;padding:6px 10px;'
            f'font-size:0.78rem;color:#6b7280;margin-top:8px;">'
            + icon("zap", 12, "#6b7280") + f' {q["hint"]}</div>'
        )

    # 문제 카드
    st.markdown(f"""
<div style="background:white;border-radius:14px;padding:18px;
     box-shadow:0 2px 10px rgba(0,0,0,0.07);margin-bottom:14px;
     border-left:5px solid {type_color};">
  <div style="font-size:0.8rem;font-weight:700;color:{type_color};margin-bottom:8px;">
    {icon("pencil", 14, type_color)} {q_type}
  </div>
  <div style="font-size:0.98rem;font-weight:600;color:#1f2937;white-space:pre-line;">
    {q.get("question", "")}
  </div>
  {hint_html}
</div>
""", unsafe_allow_html=True)

    # ── 답변 후 결과 표시 ─────────────────────────────────────
    if d.get("answered"):
        if d.get("last_ok"):
            st.success("정답!")
        else:
            st.error(f"오답. 정답: **{q.get('answer', '')}**")

        # TTS — 정답 문장 발음 듣기 (영어 텍스트가 있을 때)
        answer_text = q.get("answer", "").strip()
        passage_text = q.get("passage", "").strip()
        tts_text = answer_text if answer_text else passage_text
        if tts_text:
            _grammar_tts(tts_text, f"gr_{idx}")

        # AI 의미 채점 피드백 (주관식)
        if d.get("ai_feedback"):
            st.markdown(
                f'<div style="font-size:0.84rem;color:#4b5563;margin-top:4px;">'
                f'💡 {d["ai_feedback"]}</div>',
                unsafe_allow_html=True,
            )

        if q.get("answer_kr"):
            st.markdown(
                f'<div style="font-size:0.84rem;color:#6b7280;margin-top:4px;">'
                f'{q["answer_kr"]}</div>',
                unsafe_allow_html=True,
            )

        # 반반쌤 반응 말풍선
        reaction = d.get("reaction", "")
        if reaction:
            st.markdown(f"""
<div style="background:#faf5ff;border-left:4px solid #7c3aed;
     border-radius:0 12px 12px 0;padding:10px 14px;margin:10px 0;
     display:flex;align-items:flex-start;gap:10px;">
  <span style="font-size:1.5rem;line-height:1;">👩‍🏫</span>
  <div>
    <div style="font-size:0.7rem;font-weight:700;color:#7c3aed;margin-bottom:2px;">
      반반쌤
    </div>
    <div style="font-size:0.88rem;color:#374151;">{reaction}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # 오답노트 자동 저장 알림 (버튼 → 자동 저장으로 변경)
        if not d.get("last_ok") and d.get("student_id"):
            st.markdown(
                '<div style="font-size:0.78rem;color:#059669;margin:4px 0;">'
                '📌 오답노트에 자동 저장됐어요!</div>',
                unsafe_allow_html=True,
            )

        if st.button("다음 문제", type="primary", use_container_width=True,
                     key=f"drill_next_{idx}"):
            d["idx"]       += 1
            d["answered"]   = False
            d["last_ok"]    = None
            d["reaction"]   = ""
            d["ai_feedback"] = ""
            st.rerun()
        return

    # ── 미답변: 보기 or 주관식 입력 ─────────────────────────
    options = q.get("options", [])
    if options:
        for i, opt in enumerate(options):
            if st.button(opt, key=f"drill_opt_{idx}_{i}", use_container_width=True):
                _handle_drill_answer(opt, q.get("answer", ""), q, api_config)
    else:
        user_ans = st.text_area(
            "답 입력", key=f"drill_text_{idx}", height=70,
            placeholder="정답을 입력하세요… (의미가 맞으면 정답 처리됩니다 🤖)",
        )
        if st.button("제출", type="primary", use_container_width=True,
                     key=f"drill_submit_{idx}"):
            _handle_drill_answer(user_ans, q.get("answer", ""), q, api_config)


def _handle_drill_answer(user_ans: str, correct: str,
                         q: dict, api_config: dict | None):
    """답안 처리 — 객관식 정확 매칭, 주관식 AI 의미 채점 + 콤보 + 반응"""
    from study_ai import check_subjective_answer, get_bansam_reaction
    d = st.session_state["grammar_drill"]

    options = q.get("options", [])

    if options:
        # 객관식: 정확 매칭
        is_ok = user_ans.strip().lower() == correct.strip().lower()
        if not is_ok and "|" in correct:
            is_ok = user_ans.strip().lower() in [
                a.strip().lower() for a in correct.split("|")
            ]
        ai_feedback = ""
    else:
        # 주관식: AI 의미 채점 (API 있을 때만)
        if api_config and user_ans.strip():
            try:
                with st.spinner("반반쌤이 채점 중…"):
                    is_ok, ai_feedback = check_subjective_answer(
                        user_answer=user_ans,
                        correct_answer=correct,
                        question=q.get("question", ""),
                        grammar_point_name=d.get("gp_name", ""),
                        api_config=api_config,
                    )
            except Exception:
                is_ok = user_ans.strip().lower() == correct.strip().lower()
                ai_feedback = ""
        else:
            is_ok = user_ans.strip().lower() == correct.strip().lower()
            if not is_ok and "|" in correct:
                is_ok = user_ans.strip().lower() in [
                    a.strip().lower() for a in correct.split("|")
                ]
            ai_feedback = ""

    # 콤보 업데이트
    if is_ok:
        new_combo      = d.get("combo", 0) + 1
        d["combo"]     = new_combo
        d["max_combo"] = max(d.get("max_combo", 0), new_combo)
        d["score"]    += 1
        queue_sound("correct")
    else:
        new_combo  = 0
        d["combo"] = 0
        d["wrong"].append(d["drills"][d["idx"]])
        queue_sound("wrong")
        # ── 오답 시 자동 오답노트 저장 ──────────────────────────
        sid = d.get("student_id")
        if sid:
            try:
                add_question_wrong(
                    student_id=sid,
                    note_id=d.get("note_id", 0),
                    bank_question_id=None,
                    source_type="grammar",
                    question_snapshot=q,
                    user_answer=user_ans,
                )
            except Exception:
                pass  # 저장 실패 시 조용히 무시 (드릴 흐름 유지)
            # 망각 곡선 복습 스케줄 자동 등록
            try:
                from study_review import auto_schedule_grammar
                auto_schedule_grammar(
                    student_id=sid,
                    note_id=d.get("note_id", 0),
                    gp_id=d.get("gp_id", 0),
                    gp_name=d.get("gp_name", ""),
                )
            except Exception:
                pass

    d["answered"]    = True
    d["last_ok"]     = is_ok
    d["last_user_ans"] = user_ans
    d["ai_feedback"] = ai_feedback
    d["reaction"]    = get_bansam_reaction(is_ok, new_combo)
    st.rerun()


def _render_drill_result(api_config: dict | None):
    d         = st.session_state.get("grammar_drill", {})
    sc        = d.get("score", 0)
    tot       = len(d.get("drills", []))
    pct       = int(sc / tot * 100) if tot else 0
    max_combo = d.get("max_combo", 0)

    # 완료 팡파레 (처음 진입 시 1회만)
    if not d.get("finish_sound_played"):
        queue_sound("finish")
        play_pending_sound()
        d["finish_sound_played"] = True

    if pct >= 90:   emoji, msg = "🏆", "완벽해요!"
    elif pct >= 70: emoji, msg = "🌟", "잘 했어요!"
    elif pct >= 50: emoji, msg = "💪", "절반 이상 맞혔어요!"
    else:           emoji, msg = "📚", "다시 한번 도전해봐요!"

    # 최고 콤보 배지
    if max_combo >= 7:
        combo_line = f'<div style="margin-top:10px;font-size:0.95rem;">💥 최고 콤보 <b>{max_combo}연속</b>! 전설급!</div>'
    elif max_combo >= 5:
        combo_line = f'<div style="margin-top:10px;font-size:0.95rem;">⚡ 최고 콤보 <b>{max_combo}연속</b>! 대단해요!</div>'
    elif max_combo >= 3:
        combo_line = f'<div style="margin-top:10px;font-size:0.95rem;">🔥 최고 콤보 <b>{max_combo}연속</b>! 핫해요~</div>'
    else:
        combo_line = ""

    st.markdown(f"""
<div style="background:#faf5ff;border-radius:16px;padding:24px;text-align:center;
     margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
  <div style="font-size:3rem;">{emoji}</div>
  <div style="font-size:2rem;font-weight:800;color:#6d28d9;margin:8px 0;">
    {sc} / {tot} ({pct}점)
  </div>
  <div style="color:#6b7280;">{msg}</div>
  {combo_line}
</div>
""", unsafe_allow_html=True)

    # 학습 로그 기록
    if d.get("student_id") and not d.get("logged"):
        log_study_activity(d["student_id"], d["note_id"], "grammar",
                           score=sc, total=tot)
        d["logged"] = True

    wrong_list = d.get("wrong", [])
    if wrong_list:
        st.markdown(section_md("list", f"오답 문제 ({len(wrong_list)}개)"),
                    unsafe_allow_html=True)
        for wi, w in enumerate(wrong_list):
            with st.expander(f"[오답] {w.get('type','')} — {w.get('question','')[:40]}…"):
                st.markdown(f"**문제:** {w.get('question','')}")
                st.markdown(f"**정답:** `{w.get('answer','')}`")
                if w.get("answer_kr"):
                    st.caption(w["answer_kr"])
                ans_txt = (w.get("answer") or w.get("passage") or "").strip()
                if ans_txt:
                    _grammar_tts(ans_txt, key=f"wr_{wi}", label="정답 발음 듣기", color="#7C3AED")

    col1, col2 = st.columns(2)
    if col1.button("다시 풀기", use_container_width=True):
        del st.session_state["grammar_drill"]
        st.rerun()
    if col2.button("문법 홈으로", use_container_width=True):
        del st.session_state["grammar_drill"]
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Public: 문법학습 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_grammar(note: dict, student_id: int | None, api_config: dict | None):
    """문법학습 메인 페이지"""
    note_id    = note["id"]
    note_title = note.get("title", "노트")

    # 통합 헤더는 _study_note_selector가 렌더 → 페이지 자체 헤더 제거

    # ── 드릴 진행 중 ─────────────────────────────────────────────
    if "grammar_drill" in st.session_state:
        _render_drill(api_config)
        return

    # ── 문법 포인트 목록 조회 ─────────────────────────────────────
    try:
        gps = get_grammar_points(note_id)
    except Exception as e:
        err_str = str(e)
        if "does not exist" in err_str or "42P01" in err_str:
            st.error(
                "❌ **Supabase 테이블 미설치** — 문법 기능을 사용하려면 먼저 DB를 초기화하세요.\n\n"
                "**해결**: Supabase 대시보드 > SQL Editor 에서 "
                "`supabase_migration_v3.sql` 파일 내용 전체를 붙여넣고 **Run** 클릭"
            )
        else:
            st.error(f"DB 조회 오류: {err_str}")
        return

    # 학습·드릴에는 '활성' 포인트만 사용 (비활성은 포인트 관리에서만 노출)
    active_gps = [g for g in gps if g.get("is_active", True)]

    tab_learn, tab_drill, tab_wrongnote, tab_manage = st.tabs([
        "문법 카드", "드릴 연습", "오답노트", "포인트 관리"
    ])

    # ── 탭1: 문법 카드 ─────────────────────────────────────────────
    with tab_learn:
        if not active_gps:
            _empty_msg = ("'포인트 관리' 탭에서 AI 자동 추출을 먼저 실행해주세요"
                          if not gps else
                          "모든 포인트가 '학습 제외' 상태예요. 포인트 관리에서 켜주세요.")
            st.markdown(f"""
<div style="text-align:center;padding:40px;background:#faf5ff;border-radius:14px;
     border:2px dashed #e9d5ff;">
  <div style="margin-bottom:8px;">{icon("book-open", 52, "#7c3aed")}</div>
  <div style="font-weight:700;color:#6d28d9;font-size:1.1rem;margin-top:8px;">
    학습할 문법 포인트가 없어요
  </div>
  <div style="color:#9ca3af;font-size:0.9rem;margin-top:4px;">
    {_empty_msg}
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            st.caption(f"이 노트의 핵심 문법 포인트 {len(active_gps)}개")
            for gp in active_gps:
                _render_grammar_card(gp)

    # ── 탭2: 드릴 연습 ─────────────────────────────────────────────
    with tab_drill:
        if not api_config:
            st.warning("API 키가 필요합니다.")
        elif not gps:
            st.info("포인트 관리 탭에서 문법 포인트를 먼저 추출해주세요.")
        else:
            # 전체 뱅크 수 (표시용)
            try:
                bank_cnt = count_question_bank(note_id, source_type="grammar")
            except Exception:
                bank_cnt = 0
            if bank_cnt >= 8:
                st.markdown(f"""
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
     padding:10px 14px;margin-bottom:12px;font-size:0.85rem;color:#166534;">
  {icon("check-circle",14,"#16a34a")} 문법 뱅크에 <b>{bank_cnt}개</b> 문제가 있어요.
  새 생성 없이 뱅크에서 연습할 수 있습니다!
</div>
""", unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                sel_gp_name = st.selectbox(
                    "연습할 문법 포인트",
                    ["전체 랜덤"] + [gp["point_name"] for gp in active_gps],
                    key="drill_sel_gp",
                )
            with col2:
                n_drill = st.selectbox("문제 수", [4, 6, 8], index=0,
                                       key="drill_n")

            if st.button("드릴 시작", type="primary", use_container_width=True):
                sel_gp = None
                gp_id  = None
                if sel_gp_name != "전체 랜덤":
                    sel_gp = next((g for g in active_gps if g["point_name"] == sel_gp_name), None)
                    gp_id  = sel_gp["id"] if sel_gp else None

                # ── 뱅크 확인: 선택된 문법 포인트 기준으로만 카운트 ──
                # 다른 포인트 문제가 섞이지 않도록 gp_id 필터 적용
                try:
                    actual_bank_cnt = count_question_bank(
                        note_id, source_type="grammar",
                        grammar_point_id=gp_id,   # None이면 전체 뱅크 카운트
                    )
                except Exception:
                    actual_bank_cnt = 0

                bank_q = get_question_bank(
                    note_id, source_type="grammar",
                    grammar_point_id=gp_id,       # 선택 포인트로 필터링
                    limit=n_drill
                ) if actual_bank_cnt >= n_drill else []

                if bank_q and len(bank_q) >= n_drill:
                    drills = [
                        {
                            "type":      q.get("q_type", "빈칸완성"),
                            "question":  q["question"],
                            "passage":   q.get("passage", ""),
                            "options":   q.get("options", []),
                            "answer":    q["answer"],
                            "answer_kr": q.get("answer_kr", ""),
                            "hint":      "",
                            "bank_id":   q["id"],
                        }
                        for q in bank_q[:n_drill]
                    ]
                    st.info(f"뱅크에서 {len(drills)}개 문제를 가져왔습니다.")
                else:
                    target_gp = sel_gp if sel_gp else (active_gps[0] if active_gps else None)
                    if not target_gp:
                        st.error("학습할 문법 포인트가 없습니다.")
                        st.stop()
                    with st.spinner("문법 함정을 촘촘히 설계하는 중… 도망 못 가요!"):
                        try:
                            # 이미 출제된 문제 수집 (중복 방지)
                            try:
                                all_bank = get_question_bank(
                                    note_id, source_type="grammar", limit=100
                                )
                                existing_q_texts = [q["question"] for q in all_bank]
                            except Exception:
                                existing_q_texts = []

                            # 교과서 본문 컨텍스트 추출
                            _td = note.get("text_data", {})
                            _plines: list[str] = []
                            if _td.get("sections"):
                                for _sec in _td["sections"]:
                                    for _en, _ in _sec.get("sentences", []):
                                        _plines.append(_en)
                            elif _td.get("sentences"):
                                for _en, _ in _td.get("sentences", []):
                                    _plines.append(_en)
                            text_context = "\n".join(_plines[:15])

                            drills = generate_grammar_drills(
                                target_gp, api_config, n_drill,
                                existing_questions=existing_q_texts,
                                text_context=text_context,
                            )
                            # 뱅크에 저장
                            bank_format = [
                                {
                                    "type":      d.get("type", ""),
                                    "question":  d.get("question", ""),
                                    "passage":   d.get("passage", ""),
                                    "options":   d.get("options", []),
                                    "answer":    d.get("answer", ""),
                                    "answer_kr": d.get("answer_kr", ""),
                                    "difficulty": "medium",
                                }
                                for d in drills
                            ]
                            saved = save_to_question_bank(
                                note_id, bank_format,
                                source_type="grammar",
                                grammar_point_id=gp_id,
                            )
                            if saved > 0:
                                st.success(f"{saved}개 문제를 문법 뱅크에 저장했습니다!")
                        except Exception as e:
                            err_str = str(e)
                            if "does not exist" in err_str or "42P01" in err_str:
                                st.error(
                                    "❌ Supabase 테이블이 없습니다.\n"
                                    "supabase_migration_v3.sql 을 Supabase SQL Editor에서 실행하세요."
                                )
                            else:
                                st.error(f"문제 생성 실패: {err_str}")
                            st.stop()

                _init_drill_state(
                    drills=drills,
                    grammar_point_id=gp_id or 0,
                    grammar_point_name=sel_gp_name,
                    student_id=student_id,
                    note_id=note_id,
                )
                st.rerun()

    # ── 탭3: 오답노트 ─────────────────────────────────────────────
    with tab_wrongnote:
        if not student_id:
            st.info("로그인하면 오답노트를 저장하고 볼 수 있어요.")
        else:
            try:
                wrong_items = get_question_wrong_notes(
                    student_id=student_id,
                    note_id=note_id,
                    source_type="grammar",
                )
            except Exception as e:
                st.error(f"오답노트 조회 실패: {e}")
                wrong_items = []

            if not wrong_items:
                st.markdown(f"""
<div style="text-align:center;padding:40px;background:#faf5ff;border-radius:14px;
     border:2px dashed #e9d5ff;">
  <div style="margin-bottom:8px;">{icon("clipboard2-check", 52, "#7c3aed")}</div>
  <div style="font-weight:700;color:#6d28d9;font-size:1.1rem;margin-top:8px;">
    오답노트가 없어요 🎉
  </div>
  <div style="color:#9ca3af;font-size:0.9rem;margin-top:4px;">
    드릴 연습에서 틀린 문제가 여기에 자동으로 저장돼요
  </div>
</div>
""", unsafe_allow_html=True)
            else:
                st.caption(f"총 {len(wrong_items)}개 오답 문제 (틀린 횟수 많은 순)")

                # 유형별 색상
                _type_color = {
                    "빈칸완성":    "#6366F1",
                    "오류찾기":    "#dc2626",
                    "배열하기":    "#166534",
                    "우리말→영어": "#92400e",
                }

                for item in wrong_items:
                    snap     = item.get("question_data") or item.get("question_snapshot") or {}
                    q_type   = snap.get("type", "문법")
                    question = snap.get("question", "(문제 없음)")
                    answer   = snap.get("answer", "")
                    answer_kr = snap.get("answer_kr", "")
                    user_ans = item.get("user_answer", "")
                    wrong_cnt = item.get("wrong_count", 1)
                    t_color  = _type_color.get(q_type, "#374151")

                    with st.expander(
                        f"❌ [{q_type}] {question[:45]}{'…' if len(question)>45 else ''}"
                        f"  ·  틀린 횟수 {wrong_cnt}회",
                        expanded=False,
                    ):
                        st.markdown(f"""
<div style="background:white;border-radius:10px;padding:14px;
     border-left:4px solid {t_color};margin-bottom:8px;">
  <div style="font-size:0.75rem;font-weight:700;color:{t_color};margin-bottom:6px;">
    {q_type}
  </div>
  <div style="font-size:0.95rem;font-weight:600;color:#1f2937;white-space:pre-line;
       margin-bottom:10px;">
    {question}
  </div>
  <div style="display:flex;gap:16px;font-size:0.85rem;flex-wrap:wrap;">
    <div>
      <span style="color:#6b7280;">내 답:</span>
      <span style="color:#dc2626;font-weight:600;margin-left:4px;">{user_ans or "(미입력)"}</span>
    </div>
    <div>
      <span style="color:#6b7280;">정답:</span>
      <span style="color:#16a34a;font-weight:600;margin-left:4px;">{answer}</span>
    </div>
  </div>
  {f'<div style="margin-top:8px;font-size:0.82rem;color:#6b7280;">{answer_kr}</div>' if answer_kr else ''}
</div>
""", unsafe_allow_html=True)

                        col_l, col_r = st.columns([3, 1])
                        with col_r:
                            if st.button(
                                "🗑 삭제", key=f"del_gwn_{item['id']}",
                                use_container_width=True,
                            ):
                                try:
                                    remove_question_wrong(item["id"])
                                    st.success("삭제됐어요!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"삭제 실패: {e}")

    # ── 탭4: 포인트 관리 ───────────────────────────────────────────
    with tab_manage:
        if api_config:
            text_data  = note.get("text_data", {})
            dialogues  = note.get("dialogues_data", [])

            if st.button("AI 자동 추출", type="primary",
                         use_container_width=True, key="grammar_extract"):
                with st.spinner("교과서 속 문법 보석을 캐내는 중… 광부 모드 ON!"):
                    try:
                        pts = extract_grammar_points_ai(text_data, dialogues, api_config)
                        added = 0
                        for pt in pts:
                            save_grammar_point(
                                note_id     = note_id,
                                point_name  = pt.get("point_name", ""),
                                category    = pt.get("category", "기타"),
                                explanation_kr = pt.get("explanation_kr", ""),
                                patterns    = pt.get("patterns", []),
                                examples    = pt.get("textbook_examples", []),
                                tip         = pt.get("tip", ""),
                                ai_generated= True,
                            )
                            added += 1
                        st.success(f"{added}개 문법 포인트 추출 완료!")
                        st.rerun()
                    except Exception as e:
                        err_str = str(e)
                        if "does not exist" in err_str or "42P01" in err_str:
                            st.error(
                                "❌ Supabase 테이블이 없습니다.\n\n"
                                "**해결 방법**: Supabase 대시보드 > SQL Editor 에서 "
                                "`supabase_migration_v3.sql` 내용을 붙여넣고 실행하세요.\n\n"
                                f"상세 오류: {err_str}"
                            )
                        else:
                            st.error(f"추출 실패: {err_str}")
        else:
            st.warning("API 키가 있어야 AI 자동 추출이 가능합니다.")

        st.divider()

        # ── 선생님 직접 입력 (눈에 잘 띄는 카드 UI) ─────────────
        st.markdown(f"""
<div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);
     border:2px solid #C7D2FE;border-radius:14px;padding:16px 18px;
     margin-bottom:4px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
    <span style="font-size:1.2rem;">✏️</span>
    <span style="font-weight:800;font-size:0.95rem;color:#4338CA;">
      선생님 직접 입력
    </span>
    <span style="background:#EEF2FF;color:#6366F1;font-size:0.7rem;
         padding:2px 8px;border-radius:10px;border:1px solid #C7D2FE;">
      AI 없이 바로 추가
    </span>
  </div>
  <div style="font-size:0.8rem;color:#6366F1;">
    문법 포인트를 직접 입력하면 즉시 등록됩니다
  </div>
</div>
""", unsafe_allow_html=True)

        with st.container():
            c1, c2 = st.columns([3, 1])
            new_name = c1.text_input(
                "포인트 이름 *", key="gp_new_name",
                placeholder="예: may + V (허가/추측)  /  현재완료 have + p.p.",
            )
            new_cat = c2.selectbox(
                "카테고리", ["조동사","시제","전치사","문장구조","접속사","수동태","기타"],
                key="gp_new_cat",
            )

            new_expl = st.text_area(
                "한국어 설명", key="gp_new_expl", height=110,
                placeholder=(
                    "예: may는 두 가지 의미가 있어요.\n"
                    "① 허가: ~해도 된다 (May I~? 로 질문)\n"
                    "② 추측: ~일지도 모른다 (평서문에서)\n"
                    "→ 허가는 의문문, 추측은 평서문으로 구분!"
                ),
            )

            c3, c4 = st.columns(2)
            new_patterns_raw = c3.text_area(
                "핵심 패턴 (줄바꿈으로 구분)", key="gp_new_patterns", height=80,
                placeholder="May I + V? → ~해도 될까요?\nYou may + V → ~해도 됩니다",
            )
            new_examples_raw = c4.text_area(
                "교과서 예문 (영어,한국어 한 쌍씩)", key="gp_new_examples", height=80,
                placeholder="May I sit here?,여기 앉아도 될까요?\nIt may rain.,비가 올지도 몰라.",
            )

            new_tip = st.text_input(
                "권쌤 한 줄 팁 💡", key="gp_new_tip",
                placeholder="예: May I~?는 허가 요청, may는 추측 → 문장 타입으로 구분!",
            )

        if st.button(
            "✅ 문법 포인트 추가하기", key="gp_add_btn",
            type="primary", use_container_width=True,
        ):
            if not new_name.strip():
                st.error("포인트 이름을 입력해주세요.")
            else:
                # 패턴 파싱 (줄바꿈 구분)
                patterns = [p.strip() for p in new_patterns_raw.splitlines() if p.strip()]
                # 예문 파싱 (콤마 구분, 두 개씩)
                examples = []
                for line in new_examples_raw.splitlines():
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        examples.append([parts[0].strip(), parts[1].strip()])
                    elif parts[0].strip():
                        examples.append([parts[0].strip(), ""])
                try:
                    save_grammar_point(
                        note_id=note_id,
                        point_name=new_name.strip(),
                        category=new_cat,
                        explanation_kr=new_expl.strip(),
                        patterns=patterns,
                        examples=examples,
                        tip=new_tip.strip(),
                        ai_generated=False,
                    )
                    st.success(f"'{new_name.strip()}' 포인트를 추가했습니다!")
                    # 입력 초기화
                    for k in ["gp_new_name","gp_new_expl","gp_new_patterns",
                              "gp_new_examples","gp_new_tip"]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except Exception as e:
                    err = str(e)
                    if "42501" in err or "does not exist" in err:
                        st.error("Supabase RLS 오류 — supabase_rls_fix.sql 실행 후 재시도")
                    else:
                        st.error(f"추가 실패: {err}")

        # 기존 포인트 편집/삭제
        if gps:
            st.markdown(section_md("list", f"등록된 포인트 ({len(gps)}개)"),
                        unsafe_allow_html=True)
            st.caption("비활성으로 끄면 학생 학습·드릴에서 제외돼요 (삭제하지 않고 보관).")
            for gp in gps:
                ai_badge = ('<span style="background:rgba(99,102,241,0.2);color:#818CF8;'
                            'border-radius:10px;padding:1px 7px;font-size:0.7rem;">AI</span>'
                            if gp.get("ai_generated") else
                            '<span style="background:#dcfce7;color:#166534;'
                            'border-radius:10px;padding:1px 7px;font-size:0.7rem;">직접</span>')
                is_active = gp.get("is_active", True)
                status_badge = ('' if is_active else
                                ' <span style="background:#FEE2E2;color:#B91C1C;'
                                'border-radius:10px;padding:1px 7px;font-size:0.7rem;">학습 제외</span>')
                with st.expander(f"{gp['point_name']} {ai_badge}{status_badge}",
                                 expanded=False):
                    # ── 학습 포함 토글 ────────────────────────────
                    new_active = st.toggle(
                        "학생 학습에 포함", value=is_active,
                        key=f"gp_active_{gp['id']}",
                    )
                    if new_active != is_active:
                        try:
                            update_grammar_point(gp["id"], is_active=new_active)
                            st.rerun()
                        except Exception:
                            st.warning("활성/비활성 컬럼이 없습니다. "
                                       "Supabase에서 supabase_migration_v7.sql을 실행해주세요.")

                    edit_name = st.text_input("이름", value=gp["point_name"],
                                              key=f"gp_edit_name_{gp['id']}")
                    edit_expl = st.text_area("설명", value=gp["explanation_kr"],
                                             key=f"gp_edit_expl_{gp['id']}", height=80)
                    edit_tip  = st.text_input("팁", value=gp.get("tip",""),
                                              key=f"gp_edit_tip_{gp['id']}")
                    c1, c2 = st.columns(2)
                    if c1.button("저장", key=f"gp_save_{gp['id']}",
                                 use_container_width=True):
                        update_grammar_point(gp["id"],
                            point_name=edit_name,
                            explanation_kr=edit_expl,
                            tip=edit_tip,
                        )
                        st.success("저장됨!")
                        st.rerun()
                    with c2:
                        if confirm_delete_btn(
                            "삭제", key=f"gp_del_{gp['id']}",
                            item_name=gp.get("point_name", ""),
                            use_container_width=True,
                        ):
                            delete_grammar_point(gp["id"])
                            st.rerun()
