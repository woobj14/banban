# tts.py — 반반 BanBan 고품질 음성 (Gemini 3.1 Flash TTS · Kore)
# patient tutor 스타일 영어 발음. 같은 텍스트는 캐싱해 1회만 생성.

import os
import struct
import base64

# patient·warm tutor 디렉터 노트 (Kore 음성)
_DIRECTOR = """Read the following based on the director's note.
# Director's note
Style: Patient, warm and encouraging English tutor for a Korean student. Pace: Slow and clear. Accent: American (General).
## Transcript:
{text}"""

_MODEL = "gemini-2.5-flash-preview-tts"   # 2.5 TTS — 3.1 대비 비용 절반


def _gemini_key(api_config: dict | None) -> str:
    """api_config(멀티키) 또는 환경변수에서 Gemini 키 추출."""
    if api_config:
        keys = api_config.get("gemini_keys") or []
        if keys:
            return keys[0]
        if api_config.get("gemini_key"):
            return api_config["gemini_key"]
        if api_config.get("type") == "gemini" and api_config.get("key"):
            return api_config["key"]
    return os.environ.get("GEMINI_API_KEY", "")


def _parse_mime(mime_type: str) -> tuple[int, int]:
    """audio/L16;rate=24000 → (bits_per_sample, rate)."""
    bits, rate = 16, 24000
    for p in mime_type.split(";"):
        p = p.strip()
        if p.lower().startswith("rate="):
            try: rate = int(p.split("=", 1)[1])
            except Exception: pass
        elif p.startswith("audio/L"):
            try: bits = int(p.split("L", 1)[1])
            except Exception: pass
    return bits, rate


def _to_wav(audio: bytes, mime_type: str) -> bytes:
    """raw PCM → WAV (헤더 부착)."""
    bits, rate = _parse_mime(mime_type)
    channels = 1
    bytes_per_sample = bits // 8
    block_align = channels * bytes_per_sample
    byte_rate = rate * block_align
    chunk_size = 36 + len(audio)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
        channels, rate, byte_rate, block_align, bits,
        b"data", len(audio),
    )
    return header + audio


def gemini_tts(text: str, api_config: dict | None = None, voice: str = "Kore") -> bytes:
    """텍스트 → WAV 오디오 bytes (Gemini Kore)."""
    from google import genai
    from google.genai import types

    key = _gemini_key(api_config)
    if not key:
        raise RuntimeError("Gemini API 키가 없습니다.")
    client = genai.Client(api_key=key)

    audio = b""
    mime = "audio/L16;rate=24000"
    for chunk in client.models.generate_content_stream(
        model=_MODEL,
        contents=[types.Content(role="user",
                                parts=[types.Part.from_text(text=_DIRECTOR.format(text=text))])],
        config=types.GenerateContentConfig(
            temperature=1,
            response_modalities=["audio"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))),
        ),
    ):
        if chunk.parts and chunk.parts[0].inline_data and chunk.parts[0].inline_data.data:
            audio += chunk.parts[0].inline_data.data
            mime = chunk.parts[0].inline_data.mime_type or mime
    if not audio:
        raise RuntimeError("TTS 오디오 생성 실패")
    return _to_wav(audio, mime)


def gemini_tts_cached(text: str, api_config: dict | None = None, voice: str = "Kore") -> bytes:
    """캐시 우선 — 있으면 즉시, 없으면 생성 후 캐싱."""
    from study_db import get_tts_cache, save_tts_cache

    text = (text or "").strip()
    if not text:
        raise ValueError("빈 텍스트")

    cached = get_tts_cache(text, voice)
    if cached:
        return base64.b64decode(cached)

    wav = gemini_tts(text, api_config, voice)
    save_tts_cache(text, voice, base64.b64encode(wav).decode("ascii"))
    return wav
