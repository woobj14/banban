# study_vocab.py — D.Y. 담당: 단어 학습 모듈
# 플래시카드 (CSS 3D 플립) + 4가지 퀴즈 모드

import random
import streamlit as st
import streamlit.components.v1 as components
from icons import icon, section_md, title_md
from study_db import (
    get_or_create_student, start_quiz_session, end_quiz_session,
    save_quiz_result, record_wrong, record_correct, get_wrong_notes,
    log_study_activity, save_to_question_bank,
)
from study_ai import get_word_info
from sounds import queue_sound, play_pending_sound


# ─────────────────────────────────────────────────────────────────────────────
# 플래시카드 HTML 컴포넌트 생성
# ─────────────────────────────────────────────────────────────────────────────

def _flashcard_html(words: list[tuple], note_title: str) -> str:
    """CSS 3D 플립 플래시카드 — 뒷면에 영영풀이·유의어·반의어 자동 표시 (free API)"""
    words_json = [{"en": e, "kr": k} for e, k in words]
    import json
    words_str = json.dumps(words_json, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f0f4ff;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  user-select: none;
}}
.header {{ font-size: 0.85rem; color: #6b7280; margin-bottom: 12px; text-align: center; }}
.counter {{ font-size: 1.1rem; font-weight: 700; color: #1a4fa0; margin-bottom: 10px; }}
.progress-bar {{
  width: 320px; height: 6px; background: #e5e7eb;
  border-radius: 3px; overflow: hidden; margin-bottom: 14px;
}}
.progress-fill {{
  height: 100%;
  background: linear-gradient(90deg, #6366F1, #4F46E5);
  border-radius: 3px; transition: width 0.3s;
}}
.scene {{
  width: 320px; height: 280px;
  perspective: 900px; cursor: pointer; margin-bottom: 14px;
}}
.card {{
  width: 100%; height: 100%; position: relative;
  transform-style: preserve-3d;
  transition: transform 0.55s cubic-bezier(0.4, 0.2, 0.2, 1);
  border-radius: 18px;
}}
.card.flipped {{ transform: rotateY(180deg); }}
.face {{
  position: absolute; width: 100%; height: 100%;
  backface-visibility: hidden; border-radius: 18px;
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 18px 16px;
  box-shadow: 0 6px 24px rgba(0,0,0,0.14);
  overflow: hidden;
}}
.front {{ background: linear-gradient(135deg, #4F46E5, #6366F1); color: white; }}
.back  {{ background: white; color: #1f2937; transform: rotateY(180deg);
          justify-content: flex-start; align-items: stretch; padding: 14px 16px; }}
.badge {{
  display: inline-block;
  background: rgba(255,255,255,0.22); color: white;
  border-radius: 20px; padding: 2px 10px;
  font-size: 0.72rem; font-weight: 600; margin-bottom: 10px; align-self: center;
}}
.word-en {{
  font-size: 2rem; font-weight: 800; letter-spacing: -1px;
  margin-bottom: 6px; text-align: center;
}}
.phonetic {{
  font-size: 0.82rem; opacity: 0.75; margin-bottom: 4px;
}}
.tap-hint {{ font-size: 0.73rem; opacity: 0.65; margin-top: 10px; }}

/* 뒷면 레이아웃 */
.back-word-kr {{
  font-size: 1.4rem; font-weight: 800; color: #1a4fa0;
  text-align: center; margin-bottom: 10px; padding-bottom: 8px;
  border-bottom: 1.5px solid #e5e7eb;
}}
.section-label {{
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase; color: #9ca3af; margin: 6px 0 3px 0;
}}
.def-text {{
  font-size: 0.78rem; color: #374151; line-height: 1.55;
}}
.def-ko {{
  font-size: 0.74rem; color: #4f46e5; line-height: 1.5;
  margin: 1px 0 4px 10px; padding-left: 8px;
  border-left: 2px solid #c7d2fe;
}}
.example-text {{
  font-size: 0.72rem; color: #6b7280; font-style: italic;
  line-height: 1.4; margin-top: 2px;
}}
.example-ko {{
  font-size: 0.7rem; color: #818cf8; line-height: 1.4;
  margin: 1px 0 2px 10px;
}}
.syn-list, .ant-list {{
  display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px;
}}
.chip {{
  font-size: 0.68rem; padding: 2px 8px; border-radius: 20px;
  font-weight: 600; cursor: pointer;
}}
.chip-syn {{ background: #ede9fe; color: #5b21b6; }}
.chip-ant {{ background: #fff1f2; color: #be123c; }}
.loading {{ font-size: 0.75rem; color: #9ca3af; text-align: center; margin-top: 6px; }}
.tap-back {{ font-size: 0.68rem; color: #c4b5fd; text-align: center; margin-top: 8px; }}

.nav-row {{ display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }}
.btn {{
  border: none; border-radius: 10px; cursor: pointer;
  font-weight: 600; font-size: 0.9rem;
  padding: 10px 20px; transition: all 0.15s;
}}
.btn:active {{ transform: scale(0.96); }}
.btn-prev    {{ background: #e5e7eb; color: #374151; }}
.btn-next    {{ background: #3b82f6; color: white; }}
.btn-shuffle {{ background: #f3f4f6; color: #374151; font-size: 0.8rem; padding: 8px 14px; }}
.btn-speak {{
  background: linear-gradient(135deg, #4F46E5, #818CF8);
  color: white; border: none; border-radius: 20px;
  padding: 7px 20px; font-size: 0.82rem; font-weight: 700;
  cursor: pointer; margin-top: 10px;
  transition: all 0.15s; box-shadow: 0 2px 8px rgba(79,70,229,0.3);
}}
.btn-speak:active {{ transform: scale(0.95); opacity: 0.9; }}
.btn-speak.speaking {{ background: linear-gradient(135deg,#059669,#10B981); }}
</style>
</head>
<body>
<div class="header">📚 {note_title} 단어 플래시카드</div>
<div class="counter" id="counter"></div>
<div class="progress-bar">
  <div class="progress-fill" id="progress"></div>
</div>
<div class="scene" id="scene" onclick="flipCard()">
  <div class="card" id="card">
    <!-- 앞면: 영어 단어 -->
    <div class="face front">
      <div class="badge">영어 → 한국어</div>
      <div class="word-en" id="word-en"></div>
      <div class="phonetic" id="phonetic"></div>
      <button class="btn-speak" id="speak-btn"
              onclick="event.stopPropagation(); speakWord()">🔊 발음 듣기</button>
      <div class="tap-hint">👆 탭하면 뒤집혀요</div>
    </div>
    <!-- 뒷면: 한글 뜻 + 영영풀이 + 유의어/반의어 -->
    <div class="face back">
      <div class="back-word-kr" id="word-kr"></div>
      <div id="dict-content">
        <div class="loading" id="loading-msg">📖 사전 불러오는 중…</div>
      </div>
      <div class="tap-back">👆 탭하면 다시 영어</div>
    </div>
  </div>
</div>
<div class="nav-row">
  <button class="btn btn-prev"    onclick="prevCard()">◀ 이전</button>
  <button class="btn btn-shuffle" onclick="shuffleCards()">🔀 섞기</button>
  <button class="btn btn-next"    onclick="nextCard()">다음 ▶</button>
</div>

<script>
const WORDS = {words_str};
let idx = 0;
let arr = [...WORDS];
let flipped = false;
const dictCache = {{}};  // word → dict data

// ── TTS (Web Speech API) ──────────────────────────────────────
function speakWord() {{
  if (!window.speechSynthesis) return;
  const text = arr[idx].en;
  _speak(text);
}}

function _speak(text) {{
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang  = 'en-US';
  u.rate  = 0.85;
  u.pitch = 1.0;
  // 자연스러운 영어 목소리 우선 선택
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v =>
    (v.name.includes('Google') || v.name.includes('Samantha') || v.name.includes('Alex'))
    && v.lang.startsWith('en')
  ) || voices.find(v => v.lang === 'en-US') || voices.find(v => v.lang.startsWith('en'));
  if (preferred) u.voice = preferred;
  const btn = document.getElementById('speak-btn');
  if (btn) {{ btn.classList.add('speaking'); btn.textContent = '🔊 재생 중…'; }}
  u.onend = () => {{
    if (btn) {{ btn.classList.remove('speaking'); btn.textContent = '🔊 발음 듣기'; }}
  }};
  window.speechSynthesis.speak(u);
}}
// iOS/Safari: 목소리 목록은 비동기 로드
if (window.speechSynthesis.onvoiceschanged !== undefined) {{
  window.speechSynthesis.onvoiceschanged = () => {{}};
}}
// ─────────────────────────────────────────────────────────────

function render() {{
  const w = arr[idx];
  document.getElementById('word-en').textContent = w.en;
  document.getElementById('word-kr').textContent  = w.kr;
  document.getElementById('phonetic').textContent = '';
  document.getElementById('dict-content').innerHTML =
    '<div class="loading" id="loading-msg">📖 사전 불러오는 중…</div>';
  document.getElementById('counter').textContent = (idx+1) + ' / ' + arr.length;
  document.getElementById('progress').style.width = ((idx+1)/arr.length*100) + '%';
  const card = document.getElementById('card');
  card.classList.remove('flipped');
  flipped = false;
  prefetchDict(w.en);
}}

function prefetchDict(word) {{
  const key = word.toLowerCase().trim();
  if (dictCache[key]) return;
  fetch('https://api.dictionaryapi.dev/api/v2/entries/en/' + encodeURIComponent(key))
    .then(r => r.json())
    .then(data => {{ if (Array.isArray(data) && data.length > 0) dictCache[key] = data[0]; }})
    .catch(() => {{ dictCache[key] = null; }});
}}

function renderDictContent(word) {{
  const key = word.toLowerCase().trim();
  const container = document.getElementById('dict-content');
  const data = dictCache[key];

  if (data === undefined) {{
    // 아직 로딩 중 — 잠시 후 재시도
    setTimeout(() => renderDictContent(word), 600);
    return;
  }}
  if (!data) {{
    container.innerHTML = '<div class="loading">📖 사전 정보 없음</div>';
    return;
  }}

  // 발음기호
  const phon = data.phonetics && data.phonetics.find(p => p.text);
  if (phon) document.getElementById('phonetic').textContent = phon.text;

  let html = '';
  let trJobs = [];   // [{{id, text}}] 렌더 후 한국어 해석 비동기 채우기
  let trSeq = 0;
  // 품사별 최대 2개 정의 + 예문
  const meanings = (data.meanings || []).slice(0, 2);
  meanings.forEach(m => {{
    html += `<div class="section-label">[${{m.partOfSpeech}}] 영영 풀이</div>`;
    const defs = (m.definitions || []).slice(0, 1);
    defs.forEach(d => {{
      html += `<div class="def-text">· ${{d.definition}}</div>`;
      const dId = 'trd_' + (trSeq++);
      html += `<div class="def-ko" id="${{dId}}">해석 불러오는 중…</div>`;
      trJobs.push({{id: dId, text: d.definition}});
      if (d.example) {{
        html += `<div class="example-text">ex. ${{d.example}}</div>`;
        const eId = 'trd_' + (trSeq++);
        html += `<div class="example-ko" id="${{eId}}"></div>`;
        trJobs.push({{id: eId, text: d.example, prefix: '뜻: '}});
      }}
    }});

    // 유의어
    const syns = [...new Set([...(m.synonyms||[]), ...(defs.flatMap(d=>d.synonyms||[]))])].slice(0,5);
    if (syns.length) {{
      html += '<div class="section-label">유의어</div><div class="syn-list">';
      syns.forEach(s => {{ html += `<span class="chip chip-syn">${{s}}</span>`; }});
      html += '</div>';
    }}
    // 반의어
    const ants = [...new Set([...(m.antonyms||[]), ...(defs.flatMap(d=>d.antonyms||[]))])].slice(0,5);
    if (ants.length) {{
      html += '<div class="section-label">반의어</div><div class="ant-list">';
      ants.forEach(a => {{ html += `<span class="chip chip-ant">${{a}}</span>`; }});
      html += '</div>';
    }}
  }});

  if (!html) html = '<div class="loading">📖 정의 정보 없음</div>';
  container.innerHTML = html;

  // 영영풀이·예문 → 한국어 해석 비동기 채우기 (중학생용)
  trJobs.forEach(job => translateToKo(job.text, job.id, job.prefix || ''));
}}

// ── 무료 번역(Google gtx 비공식) → 실패 시 MyMemory 폴백 ──
const trCache = {{}};
function translateToKo(text, targetId, prefix) {{
  if (!text) {{ const el0 = document.getElementById(targetId); if (el0) el0.textContent=''; return; }}
  const setTxt = (ko) => {{
    const el = document.getElementById(targetId);
    if (el) {{ el.textContent = ko ? (prefix + ko) : ''; }}
  }};
  if (trCache[text] !== undefined) {{ setTxt(trCache[text]); return; }}

  const gUrl = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=ko&dt=t&q='
               + encodeURIComponent(text);
  fetch(gUrl)
    .then(r => r.json())
    .then(d => {{
      let ko = '';
      if (Array.isArray(d) && Array.isArray(d[0])) {{
        ko = d[0].map(seg => (seg && seg[0]) ? seg[0] : '').join('');
      }}
      if (ko) {{ trCache[text] = ko; setTxt(ko); }}
      else throw new Error('empty');
    }})
    .catch(() => {{
      // 폴백: MyMemory
      fetch('https://api.mymemory.translated.net/get?langpair=en|ko&q=' + encodeURIComponent(text))
        .then(r => r.json())
        .then(d => {{
          const ko = (d && d.responseData && d.responseData.translatedText) || '';
          trCache[text] = ko;
          setTxt(ko);
        }})
        .catch(() => setTxt(''));
    }});
}}

function flipCard() {{
  const card = document.getElementById('card');
  flipped = !flipped;
  if (flipped) {{
    card.classList.add('flipped');
    renderDictContent(arr[idx].en);
  }} else {{
    card.classList.remove('flipped');
  }}
}}

function nextCard() {{ idx = (idx + 1) % arr.length; render(); }}
function prevCard() {{ idx = (idx - 1 + arr.length) % arr.length; render(); }}

function shuffleCards() {{
  for (let i = arr.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }}
  idx = 0;
  render();
}}

// 카드 이동은 버튼으로만. 카드 영역은 '탭=뒤집기'만 (onclick 단일 핸들러).
// 스와이프 핸들러 제거 → 탭 시 touchend+click 이중 발화로 인한 끊김/되돌림 해소.

render();
// 첫 3단어 미리 로드
WORDS.slice(0,3).forEach(w => prefetchDict(w.en));
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 퀴즈 — 상태 관리
# ─────────────────────────────────────────────────────────────────────────────

def _init_quiz_state(words: list[tuple], quiz_type: str, student_id: int | None,
                     note_id: int):
    """퀴즈 세션 초기화"""
    shuffled = words.copy()
    random.shuffle(shuffled)
    session_id = start_quiz_session(student_id, note_id, quiz_type)

    st.session_state["quiz"] = {
        "words":      shuffled,
        "idx":        0,
        "score":      0,
        "wrong":      [],        # (en, kr) 오답 목록
        "correct":    [],        # (en, kr) 정답 목록
        "type":       quiz_type,
        "student_id": student_id,
        "note_id":    note_id,
        "session_id": session_id,
        "answered":   False,
        "last_ok":    None,
        "options":    [],
        "total":      len(shuffled),
        "done":       False,
    }
    _prepare_question()


def _prepare_question():
    """현재 문항 준비 (보기 생성 등)"""
    q = st.session_state["quiz"]
    if q["idx"] >= len(q["words"]):
        q["done"] = True
        end_quiz_session(q["session_id"])
        return

    word_en, word_kr = q["words"][q["idx"]]
    q["answered"] = False
    q["last_ok"]  = None

    if q["type"] in ("en2kr", "kr2en"):
        # 4지선다 보기 생성
        all_words = q["words"]
        wrongs    = [w for w in all_words if w != (word_en, word_kr)]
        random.shuffle(wrongs)
        distractors = wrongs[:3]
        correct     = (word_en, word_kr)
        pool        = distractors + [correct]
        random.shuffle(pool)
        if q["type"] == "en2kr":
            q["options"] = [w[1] for w in pool]  # 한국어 보기
            q["correct_option"] = word_kr
        else:
            q["options"] = [w[0] for w in pool]  # 영어 보기
            q["correct_option"] = word_en


def _save_vocab_to_bank(words: list, note_id: int) -> int:
    """단어들을 '단어' 유형 4지선다(뜻 고르기) 문제로 문제뱅크에 적재.
    뱅크는 question 텍스트로 중복 제거 → 같은 단어는 한 번만 쌓임."""
    if not note_id or len(words) < 4:
        return 0
    bank = []
    pool_kr = [k for _, k in words if k]
    for en, kr in words:
        if not en or not kr:
            continue
        distract = [k for k in pool_kr if k != kr]
        random.shuffle(distract)
        opts = distract[:3] + [kr]
        random.shuffle(opts)
        marks = ["①", "②", "③", "④"]
        numbered = [f"{marks[i]} {o}" for i, o in enumerate(opts)]
        answer   = numbered[opts.index(kr)]
        bank.append({
            "type":       "단어",
            "question":   f"다음 단어의 뜻으로 알맞은 것은?\n{en}",
            "passage":    "",
            "options":    numbered,
            "answer":     answer,
            "answer_kr":  f"{en} = {kr}",
            "difficulty": "easy",
        })
    try:
        return save_to_question_bank(note_id, bank, source_type="vocab")
    except Exception:
        return 0


def _finish_quiz_ui(api_config: dict | None):
    """퀴즈 완료 화면"""
    q   = st.session_state["quiz"]
    sc  = q["score"]
    tot = q["total"]
    pct = int(sc / tot * 100) if tot else 0

    # 단어 문제뱅크 적재 (세션당 1회) — 학생이 문제뱅크에서 단어 문제도 풀 수 있게
    if not q.get("banked") and q.get("note_id"):
        _save_vocab_to_bank(q.get("words", []), q["note_id"])
        q["banked"] = True

    # 완료 팡파레 (처음 진입 시 1회만)
    if not q.get("finish_sound_played"):
        queue_sound("finish")
        play_pending_sound()
        q["finish_sound_played"] = True

    # 점수에 따른 이모지/메시지
    if pct >= 90:
        emoji, msg = "🏆", "완벽해요! 최고입니다!"
    elif pct >= 70:
        emoji, msg = "🌟", "잘 했어요! 조금만 더 연습하면 완벽!"
    elif pct >= 50:
        emoji, msg = "💪", "반은 맞혔어요! 오답 노트를 확인해 보세요."
    else:
        emoji, msg = "📚", "더 열심히 공부해 봐요! 틀린 단어를 반복 학습하세요."

    st.markdown(f"""
<div style="text-align:center;padding:24px;background:white;border-radius:16px;
     box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-bottom:16px;">
  <div style="font-size:3rem;">{emoji}</div>
  <div style="font-size:1.6rem;font-weight:800;color:#1a4fa0;margin:8px 0;">
    {sc} / {tot} ({pct}점)
  </div>
  <div style="color:#6b7280;font-size:0.95rem;">{msg}</div>
</div>
""", unsafe_allow_html=True)

    # 학습 로그 기록
    student_id = q.get("student_id")
    if student_id and not q.get("logged"):
        log_study_activity(student_id, q["note_id"], "vocab", score=sc, total=tot)
        q["logged"] = True

    if q["wrong"]:
        n_wrong = len(q["wrong"])
        st.markdown(section_md("list", f"오답 목록 ({n_wrong}개)"), unsafe_allow_html=True)
        if student_id:
            st.markdown(
                f'<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:8px;'
                f'padding:8px 12px;margin-bottom:10px;font-size:0.82rem;color:#991b1b;">'
                f'{icon("alert-circle",13,"#dc2626")} 틀린 단어 <b>{n_wrong}개</b>가 '
                f'오답노트에 자동으로 기록되었습니다.</div>',
                unsafe_allow_html=True,
            )
        for en, kr in q["wrong"]:
            with st.expander(f"❌ **{en}** — {kr}", expanded=False):
                col_a, col_b = st.columns(2)
                # AI 해설 버튼 (API 있을 때만)
                if api_config and col_a.button(f"💡 AI 해설", key=f"explain_{en}",
                                                use_container_width=True):
                    with st.spinner(f"'{en}' 단어의 비밀을 캐내는 중…"):
                        from study_ai import explain_wrong_word
                        wrong_data = [w for w in get_wrong_notes(student_id or 0, q["note_id"])
                                      if w["word_en"] == en]
                        wc = wrong_data[0]["wrong_count"] if wrong_data else 1
                        explain_txt = explain_wrong_word(en, kr, wc, api_config)
                    st.info(explain_txt)
                col_b.markdown(
                    f'<div style="padding:6px 0;font-size:0.8rem;color:#dc2626;text-align:center;">'
                    f'오답노트 기록됨 ✓</div>',
                    unsafe_allow_html=True,
                )

    # ── 정답 단어 중 추가로 복습하고 싶은 단어 수동 추가 ──────────────
    correct_words = q.get("correct", [])
    if correct_words and student_id:
        with st.expander(
            f"📌 정답 단어 중 오답노트에 추가 ({len(correct_words)}개)", expanded=False
        ):
            st.caption("혹시 찍었거나 헷갈렸던 단어를 오답노트에 추가하세요.")
            for en, kr in correct_words:
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.markdown(f'<span style="font-weight:600;">{en}</span>',
                            unsafe_allow_html=True)
                c2.markdown(kr)
                if c3.button("📌", key=f"manual_wrong_{en}", use_container_width=True,
                             help="오답노트에 추가"):
                    record_wrong(student_id, q["note_id"], en, kr)
                    st.success(f"'{en}' 오답노트에 추가됨!")
                    st.rerun()

    col1, col2 = st.columns(2)
    if col1.button("🔄 다시 풀기", use_container_width=True):
        del st.session_state["quiz"]
        st.rerun()
    if col2.button("🏠 단어학습 홈", use_container_width=True):
        del st.session_state["quiz"]
        st.session_state["study_sub"] = "단어학습"
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Public: 단어학습 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_vocab(note: dict, student_id: int | None, api_config: dict | None):
    """
    단어 학습 메인 화면.
    note: {id, title, words_data (list of (en,kr)), ...}
    """
    words     = note.get("words_data", [])
    note_id   = note["id"]
    note_title = note.get("title", "단어")

    if not words:
        st.warning("이 노트에 단어가 없습니다.")
        return

    # ── 퀴즈 진행 중 ───────────────────────────────────────────────
    if "quiz" in st.session_state:
        _render_quiz(api_config)
        return

    # 통합 헤더는 _study_note_selector가 렌더 → 페이지 자체 헤더 제거

    # 플래시카드
    st.markdown(section_md("flip-horizontal", "플래시카드"), unsafe_allow_html=True)
    st.caption("카드를 탭하면 뒤집혀요. 좌우로 스와이프하면 다음/이전 단어")
    components.html(_flashcard_html(words, note_title), height=420, scrolling=False)

    st.divider()

    # 퀴즈 모드 선택
    st.markdown(section_md("zap", "퀴즈 모드"), unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        st.markdown(f"""
<div style="background:#dbeafe;border-radius:12px;padding:14px;text-align:center;">
  <div style="margin-bottom:4px;">{icon("book-open", 32, "#1a4fa0")}</div>
  <div style="font-weight:700;color:#1a4fa0;">영어 → 한국어</div>
  <div style="font-size:0.78rem;color:#6b7280;">영어 단어를 보고 한국어 뜻 선택</div>
</div>
""", unsafe_allow_html=True)
        if st.button("시작하기", key="q_en2kr", use_container_width=True):
            _init_quiz_state(words, "en2kr", student_id, note_id)
            st.rerun()

    with col2:
        st.markdown(f"""
<div style="background:#dcfce7;border-radius:12px;padding:14px;text-align:center;">
  <div style="margin-bottom:4px;">{icon("layers", 32, "#166534")}</div>
  <div style="font-weight:700;color:#166534;">한국어 → 영어</div>
  <div style="font-size:0.78rem;color:#6b7280;">한국어 뜻을 보고 영어 단어 선택</div>
</div>
""", unsafe_allow_html=True)
        if st.button("시작하기", key="q_kr2en", use_container_width=True):
            _init_quiz_state(words, "kr2en", student_id, note_id)
            st.rerun()

    with col3:
        st.markdown(f"""
<div style="background:#fef9c3;border-radius:12px;padding:14px;text-align:center;">
  <div style="margin-bottom:4px;">{icon("zap", 32, "#854d0e")}</div>
  <div style="font-weight:700;color:#854d0e;">영영 → 영어</div>
  <div style="font-size:0.78rem;color:#6b7280;">영어 정의를 보고 단어 선택 (AI)</div>
</div>
""", unsafe_allow_html=True)
        if api_config:
            if st.button("시작하기", key="q_en2en", use_container_width=True):
                _init_quiz_state(words, "en2en", student_id, note_id)
                st.rerun()
        else:
            st.caption("🔑 API 키 필요")

    with col4:
        st.markdown(f"""
<div style="background:#fce7f3;border-radius:12px;padding:14px;text-align:center;">
  <div style="margin-bottom:4px;">{icon("pencil", 32, "#9d174d")}</div>
  <div style="font-weight:700;color:#9d174d;">문장 빈칸</div>
  <div style="font-size:0.78rem;color:#6b7280;">예문의 빈칸에 단어를 직접 입력</div>
</div>
""", unsafe_allow_html=True)
        if api_config:
            if st.button("시작하기", key="q_sentence", use_container_width=True):
                _init_quiz_state(words, "sentence", student_id, note_id)
                st.rerun()
        else:
            st.caption("🔑 API 키 필요")

    # 오답 노트 미리보기
    if student_id:
        wrongs = get_wrong_notes(student_id, note_id)
        if wrongs:
            st.divider()
            st.markdown(section_md("list", f"오답 노트 ({len(wrongs)}개)"), unsafe_allow_html=True)
            for w in wrongs[:5]:
                col_en, col_kr, col_cnt = st.columns([2, 2, 1])
                col_en.markdown(f'**{w["word_en"]}**')
                col_kr.markdown(w["word_kr"])
                col_cnt.markdown(
                    f'<span style="color:#dc2626;font-weight:700;">{w["wrong_count"]}회</span>',
                    unsafe_allow_html=True
                )
            if len(wrongs) > 5:
                st.caption(f"... 외 {len(wrongs)-5}개 더 → 오답노트 메뉴에서 전체 확인")


def _render_quiz(api_config: dict | None):
    """퀴즈 진행 화면 렌더링"""
    q = st.session_state.get("quiz", {})
    if not q:
        return

    # 사운드 재생 (이전 답안 처리에서 예약된 경우)
    play_pending_sound()

    # 완료 화면
    if q.get("done"):
        _finish_quiz_ui(api_config)
        return

    idx   = q["idx"]
    total = q["total"]
    words = q["words"]
    if idx >= len(words):
        q["done"] = True
        st.rerun()
        return

    word_en, word_kr = words[idx]
    quiz_type        = q["type"]

    # 진행 바
    pct = int(idx / total * 100)
    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
  <span style="font-size:0.85rem;color:#6b7280;">문제 {idx+1} / {total}</span>
  <span style="font-size:0.85rem;font-weight:700;color:#1a4fa0;">점수: {q['score']}</span>
</div>
<div style="background:#e5e7eb;border-radius:4px;height:6px;margin-bottom:16px;">
  <div style="background:#3b82f6;height:100%;width:{pct}%;border-radius:4px;transition:width 0.3s;"></div>
</div>
""", unsafe_allow_html=True)

    # 문제 카드
    if quiz_type == "en2kr":
        q_text    = word_en
        q_label   = "아래 단어의 한국어 뜻을 고르세요"
        q_icon    = icon("book-open", 16, "#9ca3af")
    elif quiz_type == "kr2en":
        q_text    = word_kr
        q_label   = "아래 뜻에 해당하는 영어 단어를 고르세요"
        q_icon    = icon("layers", 16, "#9ca3af")
    elif quiz_type == "en2en":
        q_text    = "AI 영영 정의 로딩 중…"
        q_label   = "다음 영어 정의에 해당하는 단어를 고르세요"
        q_icon    = icon("zap", 16, "#9ca3af")
        if api_config and not q.get("answered"):
            info = get_word_info(word_en, api_config)
            q_text = info.get("definition", word_en)
    else:  # sentence
        q_text    = "AI 예문 로딩 중…"
        q_label   = "다음 예문의 빈칸에 알맞은 단어를 쓰세요"
        q_icon    = icon("pencil", 16, "#9ca3af")
        if api_config and not q.get("answered"):
            info  = get_word_info(word_en, api_config)
            ex    = info.get("example", "")
            # 단어를 ___로 치환
            q_text = ex.replace(word_en, "___") if word_en in ex else f"___: {word_kr}"

    st.markdown(f"""
<div style="background:white;border-radius:14px;padding:20px;
     box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-bottom:16px;">
  <div style="font-size:0.8rem;color:#9ca3af;margin-bottom:8px;">{q_icon} {q_label}</div>
  <div style="font-size:1.5rem;font-weight:800;color:#1f2937;text-align:center;
       padding:12px 0;">{q_text}</div>
</div>
""", unsafe_allow_html=True)

    # 이미 답한 경우
    if q.get("answered"):
        last_ok = q.get("last_ok")
        if last_ok:
            st.success(f"✅ 정답! **{word_en}** = {word_kr}")
        else:
            st.error(f"❌ 오답. 정답: **{word_en}** = {word_kr}")
            if q.get("student_id"):
                st.markdown(
                    f'<div style="background:#fef2f2;border-radius:6px;padding:6px 10px;'
                    f'font-size:0.78rem;color:#991b1b;margin-bottom:4px;">'
                    f'{icon("alert-circle",12,"#dc2626")} 오답노트에 자동 기록됨</div>',
                    unsafe_allow_html=True,
                )

        if st.button("다음 문제 →", type="primary", use_container_width=True):
            q["idx"]     += 1
            q["answered"] = False
            q["last_ok"]  = None
            _prepare_question()
            st.rerun()
        return

    # 답 입력
    if quiz_type in ("en2kr", "kr2en", "en2en"):
        options = q.get("options", [])
        if not options:
            _prepare_question()
            st.rerun()
            return

        for i, opt in enumerate(options):
            btn_label = f"{['①','②','③','④'][i]} {opt}"
            if st.button(btn_label, key=f"opt_{idx}_{i}", use_container_width=True):
                correct_opt = q.get("correct_option", "")
                is_correct  = (opt == correct_opt)
                _handle_answer(is_correct, word_en, word_kr, opt, api_config)

    else:  # sentence — 텍스트 입력
        user_ans = st.text_input(
            "정답 입력", key=f"sent_input_{idx}",
            placeholder="단어를 입력하세요…"
        )
        if st.button("제출", type="primary", use_container_width=True):
            is_correct = user_ans.strip().lower() == word_en.lower()
            _handle_answer(is_correct, word_en, word_kr, user_ans, api_config)


def _handle_answer(is_correct: bool, word_en: str, word_kr: str,
                   user_answer: str, api_config: dict | None):
    """답안 처리 + DB 저장"""
    q = st.session_state["quiz"]
    q["answered"] = True
    q["last_ok"]  = is_correct

    if is_correct:
        q["score"] += 1
        q["correct"].append((word_en, word_kr))
        if q.get("student_id"):
            record_correct(q["student_id"], q["note_id"], word_en)
        queue_sound("correct")
    else:
        q["wrong"].append((word_en, word_kr))
        if q.get("student_id"):
            record_wrong(q["student_id"], q["note_id"], word_en, word_kr)
            # 망각 곡선 복습 스케줄 자동 등록
            try:
                from study_review import auto_schedule_word
                auto_schedule_word(q["student_id"], q["note_id"], word_en, word_kr)
            except Exception:
                pass
        queue_sound("wrong")

    save_quiz_result(
        q["session_id"], word_en, word_kr, user_answer, is_correct
    )
    st.rerun()
