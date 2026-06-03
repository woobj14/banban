# study_note_reader.py — 반반 학습 페이지 v2
# 3가지 모드 (st.radio 방식), 학습 로그, 진도바, 에빙하우스 복습 알림

import time
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
from icons import icon


# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_MODES = {
    "both": ("양쪽 보기",  "#4F46E5", "영어·한글 동시 확인"),
    "en":   ("영어 → 한글", "#0891B2", "한글 가림 · 탭하면 확인"),
    "kr":   ("한글 → 영어", "#059669", "영어 가림 · 탭하면 확인"),
}

# 에빙하우스 복습 권장 간격 (일)
_REVIEW_DAYS = [1, 3, 7, 14, 30]


# ─────────────────────────────────────────────────────────────────────────────
# DB 헬퍼 (import 오류 시 조용히 무시)
# ─────────────────────────────────────────────────────────────────────────────

def _log_activity(student_id, note_id, activity, score=None, total=None,
                  duration_sec=0, details=None):
    if not student_id:
        return
    try:
        from study_db import log_study_activity
        log_study_activity(student_id, note_id, activity,
                           score=score, total=total,
                           duration_sec=duration_sec, details=details or {})
    except Exception:
        pass


def _get_last_study_date(student_id, note_id) -> datetime | None:
    """이 노트의 마지막 학습 일시"""
    if not student_id:
        return None
    try:
        from study_db import get_study_logs
        logs = get_study_logs(student_id, days=90)
        note_logs = [
            l for l in logs
            if l.get("note_id") == note_id
            and l.get("activity") in ("note_read", "note_read_start")
        ]
        if not note_logs:
            return None
        latest = max(note_logs, key=lambda x: x.get("created_at", ""))
        raw = latest.get("created_at", "")
        return datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 에빙하우스 복습 상태 계산
# ─────────────────────────────────────────────────────────────────────────────

def _ebbinghaus_badge(last_dt: datetime | None) -> str:
    """에빙하우스 망각 곡선 기반 복습 urgency 뱃지 HTML 반환"""
    if last_dt is None:
        return ""  # 첫 학습 — 뱃지 없음

    # timezone-aware 비교
    now = datetime.now(tz=last_dt.tzinfo)
    days_ago = (now - last_dt).days

    # 마지막 학습 이후 몇 번째 복습 간격에 해당하는지 파악
    if days_ago == 0:
        return (
            '<span style="background:#DCFCE7;color:#166534;border-radius:20px;'
            'padding:2px 10px;font-size:0.72rem;font-weight:700;'
            'display:inline-flex;align-items:center;gap:4px;">'
            + icon("check-circle", 12, "#166534") + '오늘 학습함</span>'
        )
    elif days_ago <= 1:
        label, bg, fg, ic = "1일차 복습 권장", "#DBEAFE", "#1E40AF", "calendar"
    elif days_ago <= 3:
        label, bg, fg, ic = f"{days_ago}일째 · 복습 시기!", "#FEF9C3", "#854D0E", "clock"
    elif days_ago <= 7:
        label, bg, fg, ic = f"{days_ago}일째 · 복습 필요", "#FED7AA", "#7C2D12", "alert-triangle"
    elif days_ago <= 14:
        label, bg, fg, ic = f"{days_ago}일째 · 망각 위험", "#FEE2E2", "#991B1B", "alert-circle"
    else:
        label, bg, fg, ic = f"{days_ago}일째 · 즉시 복습하세요!", "#FEE2E2", "#7F1D1D", "alert-circle"

    return (
        f'<span style="background:{bg};color:{fg};border-radius:20px;'
        f'padding:2px 10px;font-size:0.72rem;font-weight:700;'
        f'display:inline-flex;align-items:center;gap:4px;">'
        + icon(ic, 12, fg) + f'{label}</span>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 진도바
# ─────────────────────────────────────────────────────────────────────────────

def _progress_bar_html(done: int, total: int, color: str = "#4F46E5") -> str:
    pct = int(done / total * 100) if total else 0
    return f"""
<div style="margin:10px 0 6px 0;">
  <div style="display:flex;justify-content:space-between;
       font-size:0.72rem;color:#6B7280;margin-bottom:4px;">
    <span>학습 진도</span>
    <span style="font-weight:700;color:{color};">{done}/{total} 섹션 완료</span>
  </div>
  <div style="background:#E5E7EB;border-radius:999px;height:7px;overflow:hidden;">
    <div style="background:{color};width:{pct}%;height:100%;
         border-radius:999px;transition:width 0.4s ease;"></div>
  </div>
</div>"""


# ─────────────────────────────────────────────────────────────────────────────
# 단어 학습 HTML
# ─────────────────────────────────────────────────────────────────────────────

def _word_study_html(words: list, mode: str, note_id: int = 0) -> str:
    import json
    words_json = json.dumps([{"en": e, "kr": k} for e, k in words], ensure_ascii=False)

    if mode == "both":
        blur_kr, blur_en = "0px", "0px"
    elif mode == "en":
        blur_kr, blur_en = "6px", "0px"
    else:
        blur_kr, blur_en = "0px", "6px"

    hint_txt = "탭하면 보여요" if mode != "both" else ""

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;
  background:#f8fafc;padding:12px;min-height:100vh;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:10px;}}
.card{{background:white;border-radius:12px;padding:14px 10px;text-align:center;
  box-shadow:0 2px 8px rgba(0,0,0,0.07);cursor:pointer;
  transition:transform .15s,box-shadow .15s;border:1.5px solid #e5e7eb;
  user-select:none;-webkit-tap-highlight-color:transparent;}}
.card:active{{transform:scale(.97);}}
.card:hover{{box-shadow:0 4px 14px rgba(0,0,0,.12);border-color:#c7d2fe;}}
.badge{{font-size:.6rem;background:#EEF2FF;color:#4F46E5;border-radius:20px;
  padding:1px 7px;margin-bottom:5px;display:inline-block;font-weight:700;}}
.en{{font-size:1rem;font-weight:700;color:#1e40af;margin-bottom:6px;
  transition:filter .3s;filter:blur({blur_en});}}
.kr{{font-size:.88rem;color:#374151;transition:filter .3s;filter:blur({blur_kr});}}
.card.rev-en .en{{filter:blur(0)!important;}}
.card.rev-kr .kr{{filter:blur(0)!important;}}
.hint{{font-size:.62rem;color:#9ca3af;margin-top:5px;}}
.counter{{text-align:right;font-size:.72rem;color:#9ca3af;margin-bottom:8px;}}
</style></head><body>
<div class="counter" id="cnt"></div>
<div class="grid" id="grid"></div>
<script>
/* note_id={note_id} mode={mode} — unique key for cache busting */
const W={words_json};
const MODE="{mode}";
const grid=document.getElementById('grid');
document.getElementById('cnt').textContent=W.length+'개 단어';
W.forEach((w,i)=>{{
  const d=document.createElement('div');
  d.className='card';
  d.innerHTML=`<div class="badge">단어 ${{i+1}}</div>
    <div class="en">${{w.en}}</div>
    <div class="kr">${{w.kr}}</div>
    <div class="hint">{hint_txt}</div>`;
  d.addEventListener('click',()=>{{
    if(MODE==='en') d.classList.toggle('rev-kr');
    else if(MODE==='kr') d.classList.toggle('rev-en');
  }});
  grid.appendChild(d);
}});
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 대화문 학습 HTML
# ─────────────────────────────────────────────────────────────────────────────

import re as _dlg_re
_DLG_SPEAKER_RE = _dlg_re.compile(r'^([A-Za-z])\s*:\s*')

def _dlg_side(en_text: str, speaker_map: dict) -> tuple[str, str]:
    """화자 텍스트에서 speaker letter 추출 → 고정 left/right 결정.
    같은 화자는 항상 같은 쪽(left/right)에 배치."""
    m = _DLG_SPEAKER_RE.match(en_text)
    sp = m.group(1).upper() if m else ""
    if sp not in speaker_map:
        # 첫 등장 화자 → left, 두번째 → right, 세번째 → left ...
        speaker_map[sp] = "left" if len(speaker_map) % 2 == 0 else "right"
    return sp, speaker_map[sp]


def _get_comprehension_aids(note_id: int, dialogues: list, sections: list,
                            api_config: dict | None) -> dict:
    """이해 보조장치(키포인트/요약)를 노트당 1회 생성해 세션 캐시.
    비용 통제: note_id별 1회만 Gemini 호출. 단, 실패(빈 결과)는 캐시하지 않고
    최대 2회까지 재시도해서 transient 실패를 자가복구."""
    empty = {"dialogue_points": {}, "section_summaries": {}}
    cache_key = f"nr_aids_{note_id}"
    try_key   = f"nr_aids_try_{note_id}"

    cached = st.session_state.get(cache_key)
    if cached is not None:
        return cached

    # 내용/API 없음 → 호출 불필요, 빈 결과 확정 캐시
    if not api_config or (not dialogues and not sections):
        st.session_state[cache_key] = empty
        return empty

    tries = st.session_state.get(try_key, 0)
    if tries >= 2:  # 재시도 한도 — 비용 폭주 방지
        st.session_state[cache_key] = empty
        return empty

    try:
        from study_ai import generate_comprehension_aids
        aids = generate_comprehension_aids(dialogues, sections, api_config)
    except Exception:
        aids = dict(empty)

    has_any = bool(aids.get("dialogue_points") or aids.get("section_summaries"))
    if has_any:
        st.session_state[cache_key] = aids   # 성공 → 확정 캐시
    else:
        st.session_state[try_key] = tries + 1  # 실패 → 재시도 카운트만
    return aids


def _render_keypoint(text: str, label: str = "핵심"):
    """대화문/단락 아래 글래스 키포인트 셀."""
    if not text:
        return
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.72);backdrop-filter:blur(16px);'
        f'border:1px solid rgba(99,102,241,0.18);border-left:3px solid #6366F1;'
        f'border-radius:12px;padding:10px 14px;margin:6px 0 14px;'
        f'box-shadow:0 4px 16px rgba(31,38,135,0.05);'
        f'display:flex;align-items:flex-start;gap:7px;">'
        f'{icon("sparkles", 14, "#6366F1")}'
        f'<div><span style="font-size:0.7rem;font-weight:700;color:#6366F1;'
        f'letter-spacing:0.3px;">{label}</span>'
        f'<div style="font-size:0.85rem;color:#374151;line-height:1.55;'
        f'margin-top:2px;">{text}</div></div></div>',
        unsafe_allow_html=True,
    )


def _dialogue_study_html(dialogues: list, mode: str, note_id: int = 0) -> str:
    import json
    lines_data = []
    speaker_map: dict[str, str] = {}
    for dlg in dialogues:
        title = dlg.get("title", "대화문")
        for line in dlg.get("lines", []):
            if isinstance(line, (list, tuple)) and len(line) >= 2:
                sp, side = _dlg_side(line[0], speaker_map)
                lines_data.append({
                    "en": line[0], "kr": line[1],
                    "side": side, "title": title,
                    "speaker": sp,
                })

    if not lines_data:
        return "<html><body><p style='color:#9ca3af;padding:20px;'>대화문이 없습니다.</p></body></html>"

    blur_kr = "6px" if mode == "en" else "0px"
    blur_en = "6px" if mode == "kr" else "0px"
    lines_json = json.dumps(lines_data, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#f8fafc;padding:14px;}}
.sec-title{{font-size:.72rem;font-weight:700;color:#6b7280;letter-spacing:.1em;
  text-transform:uppercase;margin:12px 0 8px;padding:4px 0;
  border-bottom:1px solid #e5e7eb;}}
.row{{display:flex;margin-bottom:14px;align-items:flex-end;}}
.row.left{{justify-content:flex-start;}}
.row.right{{justify-content:flex-end;}}
.avatar{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-size:1.1rem;flex-shrink:0;font-weight:800;
  font-size:.82rem;}}
.av-a{{background:#DBEAFE;color:#1D4ED8;margin-right:8px;}}
.av-b{{background:#FCE7F3;color:#9D174D;margin-left:8px;}}
.bubble{{max-width:76%;padding:10px 14px;border-radius:18px;cursor:pointer;
  user-select:none;-webkit-tap-highlight-color:transparent;
  transition:transform .1s;}}
.bubble:active{{transform:scale(.98);}}
.left .bubble{{background:white;border:1.5px solid #e5e7eb;
  border-bottom-left-radius:4px;box-shadow:0 2px 6px rgba(0,0,0,.07);}}
.right .bubble{{background:linear-gradient(135deg,#6366f1,#4f46e5);
  border-bottom-right-radius:4px;box-shadow:0 2px 8px rgba(79,70,229,.25);}}
.sp-label{{font-size:.68rem;font-weight:700;letter-spacing:.04em;
  margin-bottom:3px;opacity:.65;}}
.left .sp-label{{color:#4F46E5;}}
.right .sp-label{{color:rgba(255,255,255,.75);}}
.en{{font-size:.92rem;font-weight:600;line-height:1.6;
  transition:filter .3s;filter:blur({blur_en});}}
.right .en{{color:white;}}
.kr{{font-size:.82rem;margin-top:5px;line-height:1.5;
  transition:filter .3s;filter:blur({blur_kr});}}
.left .kr{{color:#64748B;}}
.right .kr{{color:rgba(255,255,255,.8);}}
.bubble.rev .en,.bubble.rev .kr{{filter:blur(0)!important;}}
.hint{{font-size:.6rem;color:#a78bfa;margin-top:3px;}}
.right .hint{{color:rgba(255,255,255,.45);text-align:right;}}
</style></head><body>
<script>
/* note_id={note_id} mode={mode} */
const LINES={lines_json};
const MODE="{mode}";
// 화자 이모지/이니셜 매핑
const SP_EMOJI={{"G":"G","B":"B","W":"W","M":"M","A":"A","H":"H"}};
let cur='';
LINES.forEach((l)=>{{
  if(l.title!==cur){{
    const t=document.createElement('div');
    t.className='sec-title';t.textContent=l.title;
    document.body.appendChild(t);cur=l.title;
  }}
  const isR=(l.side==='right');
  const row=document.createElement('div');
  row.className='row '+l.side;
  const av=document.createElement('div');
  av.className='avatar '+(isR?'av-b':'av-a');
  av.textContent=l.speaker||( isR?'B':'G');
  const bub=document.createElement('div');
  bub.className='bubble';
  // 화자 레이블 + 영어 + 한국어 각각 줄 분리
  const spLabel=l.speaker?`<div class="sp-label">${{l.speaker}}:</div>`:'';
  // G:, B: 접두어를 en/kr 텍스트에서 제거
  const enClean=l.en.replace(/^[A-Za-z]+\\s*:\\s*/,'');
  const krClean=l.kr.replace(/^[A-Za-z]+\\s*:\\s*/,'');
  bub.innerHTML=`${{spLabel}}<div class="en">${{enClean}}</div>
    <div class="kr">${{krClean}}</div>
    ${{MODE!=='both'?'<div class="hint">탭하면 보여요</div>':''}}`;
  bub.addEventListener('click',()=>{{if(MODE!=='both')bub.classList.toggle('rev');}});
  if(isR){{row.appendChild(bub);row.appendChild(av);}}
  else{{row.appendChild(av);row.appendChild(bub);}}
  document.body.appendChild(row);
}});
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 본문 학습 HTML
# ─────────────────────────────────────────────────────────────────────────────

def _text_study_html(text_data: dict, mode: str, note_id: int = 0) -> str:
    import json
    sentences = []
    if text_data.get("sections"):
        for sec in text_data["sections"]:
            for pair in sec.get("sentences", []):
                if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                    sentences.append({"en": pair[0], "kr": pair[1],
                                      "sec": sec.get("title", "본문")})
    elif text_data.get("sentences"):
        for pair in text_data["sentences"]:
            if isinstance(pair, (list, tuple)) and len(pair) >= 2:
                sentences.append({"en": pair[0], "kr": pair[1], "sec": "본문"})

    if not sentences:
        return "<html><body><p style='color:#9ca3af;padding:20px;'>본문이 없습니다.</p></body></html>"

    blur_kr = "6px" if mode == "en" else "0px"
    blur_en = "6px" if mode == "kr" else "0px"
    sents_json = json.dumps(sentences, ensure_ascii=False)
    hint_bar = ('<div class="hint-bar">문장을 탭하면 가려진 내용이 보여요</div>'
                if mode != "both" else "")

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:#f8fafc;padding:14px;}}
.sec-title{{font-size:.72rem;font-weight:700;color:#7c3aed;letter-spacing:.1em;
  text-transform:uppercase;margin:14px 0 8px;padding:5px 10px;
  background:#faf5ff;border-radius:8px;border-left:3px solid #7c3aed;}}
.sent{{background:white;border-radius:10px;padding:12px 14px;margin-bottom:8px;
  cursor:pointer;border:1.5px solid #e5e7eb;
  box-shadow:0 1px 4px rgba(0,0,0,.05);
  transition:box-shadow .15s,border-color .15s;
  user-select:none;-webkit-tap-highlight-color:transparent;}}
.sent:hover{{box-shadow:0 3px 10px rgba(0,0,0,.1);border-color:#c4b5fd;}}
.sent:active{{transform:scale(.99);}}
.num{{font-size:.6rem;color:#a78bfa;font-weight:700;margin-bottom:3px;}}
.en{{font-size:.9rem;font-weight:600;color:#1e3a8a;line-height:1.6;
  transition:filter .3s;filter:blur({blur_en});}}
.kr{{font-size:.82rem;color:#6b7280;margin-top:4px;line-height:1.5;
  transition:filter .3s;filter:blur({blur_kr});}}
.sent.rev .en,.sent.rev .kr{{filter:blur(0)!important;}}
.hint-bar{{font-size:.68rem;color:#9ca3af;text-align:center;
  padding:8px;margin-bottom:10px;background:#f1f5f9;border-radius:8px;}}
</style></head><body>
{hint_bar}
<script>
/* note_id={note_id} mode={mode} */
const SENTS={sents_json};
const MODE="{mode}";
let cur='';
SENTS.forEach((s,i)=>{{
  if(s.sec!==cur){{
    const t=document.createElement('div');
    t.className='sec-title';t.textContent=s.sec;
    document.body.appendChild(t);cur=s.sec;
  }}
  const d=document.createElement('div');
  d.className='sent';
  d.innerHTML=`<div class="num">문장 ${{i+1}}</div>
    <div class="en">${{s.en}}</div>
    <div class="kr">${{s.kr}}</div>`;
  d.addEventListener('click',()=>{{if(MODE!=='both')d.classList.toggle('rev');}});
  document.body.appendChild(d);
}});
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# 메인 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_note_reader(note: dict, student_id: int | None, api_config: dict | None = None):
    """반반 학습 페이지 — 모드 선택, 진도 추적, 학습 로그, 에빙하우스 복습 알림"""
    if not note:
        st.warning("노트를 불러올 수 없습니다.")
        return

    note_id   = note.get("id", 0)
    title     = note.get("title", "반반노트")
    words     = note.get("words_data", note.get("words", []))
    dialogues = note.get("dialogues_data", note.get("dialogues", []))
    text_data = note.get("text_data", {})

    # 단어 리스트 정규화
    word_list: list[tuple[str, str]] = [
        (str(w[0]), str(w[1]))
        for w in words
        if isinstance(w, (list, tuple)) and len(w) >= 2
    ]

    # 사용 가능한 섹션 목록
    has_text = bool(text_data.get("sections") or text_data.get("sentences"))
    avail_sections: list[str] = []
    if word_list:  avail_sections.append("단어")
    if dialogues:  avail_sections.append("대화문")
    if has_text:   avail_sections.append("본문")
    total_sections = len(avail_sections)

    if not avail_sections:
        st.info("학습할 내용이 없습니다. 노트에 단어, 대화문, 본문을 추가해 주세요.")
        return

    # ── 세션 상태 초기화 ────────────────────────────────────────────
    prog_key    = f"nr_done_{note_id}"
    start_key   = f"nr_started_{note_id}"
    ts_key      = f"nr_ts_{note_id}"
    ebbkey      = f"nr_ebb_{note_id}"

    if prog_key not in st.session_state:
        st.session_state[prog_key] = set()

    # 학습 시작 로그 (세션당 1회)
    if not st.session_state.get(start_key):
        st.session_state[start_key] = True
        st.session_state[ts_key]    = time.time()
        _log_activity(student_id, note_id, "note_read_start",
                      details={"title": title})

    # 에빙하우스 날짜 (세션당 1회 조회)
    if ebbkey not in st.session_state:
        st.session_state[ebbkey] = _get_last_study_date(student_id, note_id)

    done_set: set = st.session_state[prog_key]
    done_count = len(done_set)

    # ── 에빙하우스 뱃지 ─────────────────────────────────────────────
    ebb_html = _ebbinghaus_badge(st.session_state[ebbkey])

    # ── 헤더 ────────────────────────────────────────────────────────
    word_cnt  = len(word_list)
    dlg_lines = sum(len(d.get("lines", [])) for d in dialogues)
    sent_cnt  = (sum(len(s.get("sentences", [])) for s in text_data.get("sections", []))
                 or len(text_data.get("sentences", [])))

    # 통합 헤더는 _study_note_selector가 렌더 → 여기선 복습 뱃지만 표시
    if ebb_html:
        st.markdown(
            f'<div style="margin:2px 0 14px;">{ebb_html}</div>',
            unsafe_allow_html=True,
        )

    # ── 진도바 ──────────────────────────────────────────────────────
    st.markdown(
        _progress_bar_html(done_count, total_sections),
        unsafe_allow_html=True,
    )

    # ── 학습 모드 선택 (st.radio) ───────────────────────────────────
    # CSS로 radio를 카드형 버튼처럼 스타일링
    st.markdown("""
<style>
div[data-testid="stRadio"] > label {
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    color: #374151 !important;
    margin-bottom: 6px !important;
}
div[data-testid="stRadio"] div[role="radiogroup"] {
    gap: 8px !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] {
    background: #F8FAFC !important;
    border: 2px solid #E5E7EB !important;
    border-radius: 12px !important;
    padding: 10px 14px !important;
    flex: 1 !important;
    cursor: pointer !important;
    transition: border-color 0.15s, background 0.15s !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
    background: #EEF2FF !important;
    border-color: #4F46E5 !important;
}
div[data-testid="stRadio"] span[data-testid="stMarkdownContainer"] p {
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
}
</style>
""", unsafe_allow_html=True)

    mode = st.radio(
        "학습 모드",
        options=list(_MODES.keys()),
        format_func=lambda k: _MODES[k][0],
        horizontal=True,
        key=f"nr_mode_{note_id}",
    )
    _, mode_color, mode_desc = _MODES[mode]

    # 모드 안내 배너
    if mode != "both":
        hidden = "한글" if mode == "en" else "영어"
        st.markdown(f"""
<div style="background:#FFF9C4;border:1.5px solid #F59E0B;border-radius:10px;
     padding:9px 14px;margin:6px 0 14px;font-size:0.82rem;color:#78350F;
     display:flex;align-items:flex-start;gap:6px;">
  {icon("sparkles", 14, "#B45309")}
  <span><b>{hidden}이 가려집니다.</b>
  각 항목을 <b>탭/클릭</b>하면 잠깐 확인할 수 있어요!
  스스로 먼저 떠올려보고 확인하면 학습 효과 2배!</span>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)

    # ── 이해 보조장치 (대화문 키포인트 / 단락 요약) — 노트당 1회 생성 ──
    _need_gen = (f"nr_aids_{note_id}" not in st.session_state
                 and api_config and (dialogues or text_data.get("sections")))
    if _need_gen:
        with st.spinner("반반쌤이 핵심 정리를 준비하는 중…"):
            _aids = _get_comprehension_aids(
                note_id, dialogues, text_data.get("sections", []), api_config
            )
    else:
        _aids = _get_comprehension_aids(
            note_id, dialogues, text_data.get("sections", []), api_config
        )
    _dlg_points = _aids.get("dialogue_points", {})
    _sec_sums   = _aids.get("section_summaries", {})

    # ── 섹션 탭 ─────────────────────────────────────────────────────
    tab_labels = []
    if word_list:  tab_labels.append("단어")
    if dialogues:  tab_labels.append("대화문")
    if has_text:   tab_labels.append("본문")

    tab_objs = st.tabs(tab_labels)

    for tab_label, tab_obj in zip(tab_labels, tab_objs):
        sec_name = tab_label  # "단어" / "대화문" / "본문"
        is_done  = sec_name in done_set

        with tab_obj:

            # ── 완료 상태 표시 ──────────────────────────────────────
            done_col, _ = st.columns([3, 1])
            with done_col:
                if is_done:
                    st.markdown(
                        '<div style="background:#DCFCE7;border:1.5px solid #86EFAC;'
                        'border-radius:8px;padding:6px 12px;font-size:0.78rem;'
                        'color:#166534;margin-bottom:10px;'
                        'display:flex;align-items:center;gap:5px;">'
                        + icon("check-circle", 13, "#166534") + '이 섹션 완료!</div>',
                        unsafe_allow_html=True,
                    )

            # ── 단어 탭 ─────────────────────────────────────────────
            if tab_label == "단어":
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#6b7280;margin-bottom:8px;">'
                    f'총 <b style="color:#4F46E5;">{len(word_list)}</b>개 단어 &nbsp;—&nbsp;'
                    f'{"한글을 가렸어요. 탭하면 확인!" if mode=="en" else "영어를 가렸어요. 탭하면 확인!" if mode=="kr" else "영어·한글 동시 확인"}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                components.html(
                    _word_study_html(word_list, mode, note_id),
                    height=max(300, (len(word_list) // 3 + 1) * 130),
                    scrolling=True,
                )

                if mode != "both":
                    with st.expander("✏️ 쓰기 연습 (선택)", expanded=False):
                        st.caption("단어를 직접 써보며 연습하세요!")
                        for en, kr in word_list[:10]:
                            prompt = kr if mode == "kr" else en
                            answer = en if mode == "kr" else kr
                            c1, c2 = st.columns([2, 3])
                            with c1:
                                st.markdown(
                                    f'<div style="padding:8px;font-weight:700;'
                                    f'font-size:0.9rem;color:#1e40af;">{prompt}</div>',
                                    unsafe_allow_html=True,
                                )
                            with c2:
                                inp = st.text_input(
                                    f"write_{note_id}_{en}",
                                    label_visibility="collapsed",
                                    placeholder="여기에 입력…",
                                    key=f"write_{note_id}_{mode}_{en}",
                                )
                                if inp.strip():
                                    ok = inp.strip().lower() == answer.strip().lower()
                                    if ok:
                                        st.success(f"✅ {answer}")
                                    else:
                                        st.error(f"❌ 정답: {answer}")

            # ── 대화문 탭 ───────────────────────────────────────────
            elif tab_label == "대화문":
                total_lines = sum(len(d.get("lines", [])) for d in dialogues)
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#6b7280;margin-bottom:8px;">'
                    f'총 <b style="color:#4F46E5;">{total_lines}</b>줄 &nbsp;—&nbsp;'
                    f'{"한글을 가렸어요. 탭하면 확인!" if mode=="en" else "영어를 가렸어요. 탭하면 확인!" if mode=="kr" else "대화 흐름을 따라 읽어보세요!"}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                components.html(
                    _dialogue_study_html(dialogues, mode, note_id),
                    height=max(300, total_lines * 82),
                    scrolling=True,
                )

                # 대화문별 키포인트 (각 대화문 아래 핵심 1줄) — 인덱스 매칭
                if _dlg_points:
                    for di, d in enumerate(dialogues):
                        kp = _dlg_points.get(di)
                        if kp:
                            dtitle = d.get("title", f"대화문{di+1}")
                            st.markdown(
                                f'<div style="font-size:0.74rem;font-weight:700;'
                                f'color:#94A3B8;margin:4px 0 0;">{dtitle}</div>',
                                unsafe_allow_html=True,
                            )
                            _render_keypoint(kp, "이 대화의 핵심")

            # ── 본문 탭 ─────────────────────────────────────────────
            elif tab_label == "본문":
                sent_cnt_local = (
                    sum(len(s.get("sentences", [])) for s in text_data.get("sections", []))
                    or len(text_data.get("sentences", []))
                )
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#6b7280;margin-bottom:8px;">'
                    f'총 <b style="color:#7C3AED;">{sent_cnt_local}</b>개 문장 &nbsp;—&nbsp;'
                    f'{"한글 해석을 가렸어요. 탭하면 확인!" if mode=="en" else "영어를 가렸어요. 탭하면 확인!" if mode=="kr" else "영어·한글 대조하며 학습!"}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                components.html(
                    _text_study_html(text_data, mode, note_id),
                    height=max(400, sent_cnt_local * 92),
                    scrolling=True,
                )

                # 단락별 요약 (각 단락 요점 1~2문장) — 인덱스 매칭
                if _sec_sums:
                    for si, s in enumerate(text_data.get("sections", [])):
                        summ = _sec_sums.get(si)
                        if summ:
                            slabel = s.get("label", f"단락{si+1}")
                            st.markdown(
                                f'<div style="font-size:0.74rem;font-weight:700;'
                                f'color:#94A3B8;margin:4px 0 0;">{slabel}</div>',
                                unsafe_allow_html=True,
                            )
                            _render_keypoint(summ, "단락 요점")

            # ── 섹션 완료 버튼 ──────────────────────────────────────
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            if not is_done:
                if st.button(
                    f"✅ '{sec_name}' 섹션 완료!",
                    key=f"done_{note_id}_{sec_name}",
                    use_container_width=True,
                    type="primary",
                ):
                    done_set.add(sec_name)
                    st.session_state[prog_key] = done_set
                    _log_activity(student_id, note_id, "section_complete",
                                  details={"section": sec_name, "mode": mode})
                    st.rerun()
            else:
                if st.button(
                    "↩️ 다시 학습하기",
                    key=f"redo_{note_id}_{sec_name}",
                    use_container_width=True,
                ):
                    done_set.discard(sec_name)
                    st.session_state[prog_key] = done_set
                    st.rerun()

    # ── 전체 완료 ────────────────────────────────────────────────────
    st.markdown("---")
    all_done = (done_count == total_sections)

    if all_done:
        duration = int(time.time() - st.session_state.get(ts_key, time.time()))
        _log_activity(
            student_id, note_id, "note_read",
            score=total_sections, total=total_sections,
            duration_sec=duration,
            details={"title": title, "mode": mode, "completed": True},
        )
        # 에빙하우스 캐시 갱신
        st.session_state[ebbkey] = datetime.now().astimezone()

        st.markdown(f"""
<div style="background:linear-gradient(135deg,#059669,#0891B2);
     color:white;border-radius:16px;padding:22px 24px;
     text-align:center;box-shadow:0 8px 28px rgba(5,150,105,0.3);">
  <div style="margin-bottom:8px;">{icon("party-popper", 32, "white")}</div>
  <div style="font-size:1.2rem;font-weight:900;margin-bottom:4px;">학습 완료!</div>
  <div style="font-size:0.85rem;opacity:0.9;">
    총 {duration//60}분 {duration%60}초 동안 학습했어요.<br>
    다음 복습 권장일: <b>{(datetime.now() + timedelta(days=1)).strftime("%m월 %d일")}</b>
    (에빙하우스 간격 기준)
  </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    # ── 하단 이동 버튼 ───────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🎯 단어 퀴즈", use_container_width=True,
                     type="primary" if all_done else "secondary"):
            st.session_state["study_page"] = "단어학습"
            st.rerun()
    with c2:
        if st.button("📋 내신문제", use_container_width=True):
            st.session_state["study_page"] = "내신문제"
            st.rerun()
    with c3:
        if st.button("📊 내 학습현황", use_container_width=True):
            st.session_state["study_page"] = "내 학습현황"
            st.session_state["page"] = "__dashboard__"
            st.rerun()
