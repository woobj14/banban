# sounds.py — 반반 BanBan 사운드 이펙트
# Web Audio API로 외부 파일 없이 브라우저에서 직접 소리 합성

import streamlit as st
import streamlit.components.v1 as components

# ─────────────────────────────────────────────────────────────────────────────
# 사운드 JavaScript (Web Audio API — 파일 없이 합성음)
# ─────────────────────────────────────────────────────────────────────────────

# 정답 사운드: C5→E5→G5 밝은 아르페지오 + 반짝 고음
_CORRECT_HTML = """<!DOCTYPE html><html><body style="margin:0">
<script>
(function() {
  try {
    var AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    var ctx = new AudioCtx();

    function note(freq, startT, dur, vol, type) {
      var osc  = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = type || 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0, startT);
      gain.gain.linearRampToValueAtTime(vol, startT + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.001, startT + dur);
      osc.start(startT);
      osc.stop(startT + dur + 0.01);
    }

    var t = ctx.currentTime;
    // 밝은 아르페지오 C5 E5 G5
    note(523.25, t,        0.30, 0.22);
    note(659.25, t + 0.11, 0.28, 0.22);
    note(783.99, t + 0.22, 0.30, 0.22);
    // 반짝 C6
    note(1046.5, t + 0.33, 0.22, 0.14);
    // 부드러운 화음 받침 (E4)
    note(329.63, t,        0.50, 0.08, 'triangle');
  } catch(e) {}
})();
</script></body></html>"""

# 오답 사운드: 낮은 하강 버저 × 2
_WRONG_HTML = """<!DOCTYPE html><html><body style="margin:0">
<script>
(function() {
  try {
    var AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    var ctx = new AudioCtx();

    function buzz(startT) {
      var osc  = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(260, startT);
      osc.frequency.exponentialRampToValueAtTime(110, startT + 0.22);
      gain.gain.setValueAtTime(0.18, startT);
      gain.gain.exponentialRampToValueAtTime(0.001, startT + 0.25);
      osc.start(startT);
      osc.stop(startT + 0.26);
    }

    var t = ctx.currentTime;
    buzz(t);
    buzz(t + 0.20);   // 짧은 두 번째 버저
  } catch(e) {}
})();
</script></body></html>"""

# 완료 팡파레 (드릴 종료 / 퀴즈 완료)
_FINISH_HTML = """<!DOCTYPE html><html><body style="margin:0">
<script>
(function() {
  try {
    var AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    var ctx = new AudioCtx();

    function note(freq, startT, dur, vol) {
      var osc  = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0, startT);
      gain.gain.linearRampToValueAtTime(vol, startT + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, startT + dur);
      osc.start(startT);
      osc.stop(startT + dur + 0.01);
    }

    var t = ctx.currentTime;
    // 짧은 팡파레: C E G C(high)
    note(523.25, t,        0.20, 0.20);
    note(659.25, t + 0.10, 0.20, 0.20);
    note(783.99, t + 0.20, 0.20, 0.20);
    note(1046.5, t + 0.30, 0.45, 0.22);
    // 하모니 받침
    note(261.63, t,        0.50, 0.10);
    note(392.00, t + 0.10, 0.45, 0.08);
  } catch(e) {}
})();
</script></body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def queue_sound(result: str):
    """답안 처리 직후 호출 — session_state에 재생 예약.
    result: 'correct' | 'wrong' | 'finish'
    """
    st.session_state["_sound_pending"] = result


def play_pending_sound():
    """렌더 함수 상단에서 호출 — 예약된 사운드 재생 후 플래그 해제."""
    pending = st.session_state.pop("_sound_pending", None)
    if pending == "correct":
        components.html(_CORRECT_HTML, height=0, scrolling=False)
    elif pending == "wrong":
        components.html(_WRONG_HTML,   height=0, scrolling=False)
    elif pending == "finish":
        components.html(_FINISH_HTML,  height=0, scrolling=False)
