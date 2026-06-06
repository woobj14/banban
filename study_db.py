# study_db.py — 반반 BanBan 학습 데이터베이스
# SQLite → Supabase PostgreSQL 전환
# 함수 시그니처 동일 유지 — 나머지 모든 파일 수정 불필요

import json
import random
from datetime import datetime, timedelta
from supabase_client import get_supabase

# 하위 호환: SQLite 경로 (마이그레이션 기간 중 참조용)
from pathlib import Path
DB_PATH = Path(__file__).parent / "data" / "study.db"


# ─────────────────────────────────────────────────────────────────────────────
# 초기화 (Supabase 테이블은 supabase_migration.sql로 생성 — 여기선 no-op)
# ─────────────────────────────────────────────────────────────────────────────

def init_db():
    """Supabase 전환 후 no-op. 테이블은 supabase_migration.sql 참조."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# 학생 관리
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_student(name: str, grade: str = "") -> int:
    """이름으로 학생 조회 또는 생성 → student_id(int) 반환.
    Supabase 환경에서는 profiles.student_id를 사용합니다.
    이 함수는 auth.py를 통해 로그인한 사용자의 student_id를 반환합니다."""
    import streamlit as st
    # 로그인된 사용자의 student_id 반환
    sid = st.session_state.get("sb_student_id")
    if sid:
        return int(sid)
    # 비로그인 fallback (개발/테스트용)
    return 0


def list_students() -> list[dict]:
    """모든 학생 프로필 목록"""
    sb = get_supabase()
    result = sb.table("profiles").select("student_id,name,grade,email,created_at") \
                .eq("role", "student").eq("is_active", True) \
                .order("name").execute()
    rows = result.data or []
    # 기존 코드 호환: id → student_id (integer)
    return [
        {
            "id":         r["student_id"],
            "name":       r.get("name", ""),
            "grade":      r.get("grade", ""),
            "email":      r.get("email", ""),
            "created_at": r.get("created_at", ""),
        }
        for r in rows
    ]


def delete_student(student_id: int):
    """학생 비활성화 (soft delete)"""
    sb = get_supabase()
    sb.table("profiles").update({"is_active": False}) \
      .eq("student_id", student_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 단어 오답노트
# ─────────────────────────────────────────────────────────────────────────────

def record_wrong(student_id: int, note_id: int, word_en: str, word_kr: str):
    """오답 기록 (카운터 원자적 증가)"""
    sb = get_supabase()
    sb.rpc("increment_wrong_count", {
        "p_student_id": student_id,
        "p_note_id":    note_id,
        "p_word_en":    word_en,
        "p_word_kr":    word_kr,
    }).execute()


def record_correct(student_id: int, note_id: int, word_en: str):
    """정답 기록 (카운터 감소, 0 이하 시 삭제)"""
    sb = get_supabase()
    sb.rpc("decrement_wrong_count", {
        "p_student_id": student_id,
        "p_note_id":    note_id,
        "p_word_en":    word_en,
    }).execute()


def get_wrong_notes(student_id: int, note_id: int | None = None) -> list[dict]:
    sb = get_supabase()
    q  = sb.table("wrong_notes").select("*").eq("student_id", student_id)
    if note_id:
        q = q.eq("note_id", note_id)
    result = q.order("wrong_count", desc=True).order("last_wrong", desc=True).execute()
    return result.data or []


def save_ai_explain(student_id: int, note_id: int, word_en: str, explain: str):
    sb = get_supabase()
    sb.table("wrong_notes").update({"ai_explain": explain}) \
      .eq("student_id", student_id) \
      .eq("note_id", note_id) \
      .eq("word_en", word_en).execute()


def delete_wrong_note(student_id: int, note_id: int, word_en: str):
    sb = get_supabase()
    sb.table("wrong_notes") \
      .delete() \
      .eq("student_id", student_id) \
      .eq("note_id", note_id) \
      .eq("word_en", word_en).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 단어 AI 캐시
# ─────────────────────────────────────────────────────────────────────────────

def get_word_cache(word_en: str) -> dict | None:
    sb = get_supabase()
    result = sb.table("word_cache").select("*").eq("word_en", word_en).execute()
    rows = result.data
    return rows[0] if rows else None


def save_word_cache(word_en: str, definition: str, example: str):
    sb = get_supabase()
    sb.table("word_cache").upsert(
        {"word_en": word_en, "definition": definition, "example": example},
        on_conflict="word_en",
    ).execute()


# ── TTS 오디오 캐시 (Gemini Kore 음성) ────────────────────────────

def get_tts_cache(text: str, voice: str = "Kore") -> str | None:
    """캐시된 오디오(base64) 반환, 없으면 None."""
    try:
        sb = get_supabase()
        r = sb.table("tts_cache").select("audio_b64") \
              .eq("text", text).eq("voice", voice).limit(1).execute()
        return r.data[0]["audio_b64"] if r.data else None
    except Exception:
        return None


def save_tts_cache(text: str, voice: str, audio_b64: str):
    try:
        get_supabase().table("tts_cache").upsert(
            {"text": text, "voice": voice, "audio_b64": audio_b64},
            on_conflict="text,voice",
        ).execute()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 퀴즈 세션
# ─────────────────────────────────────────────────────────────────────────────

def start_quiz_session(student_id: int | None, note_id: int, quiz_type: str) -> int:
    sb = get_supabase()
    result = sb.table("quiz_sessions").insert({
        "student_id": student_id or 0,   # None → 0 (비로그인 개발 환경)
        "note_id":    note_id,
        "quiz_type":  quiz_type,
    }).execute()
    return result.data[0]["id"]


def end_quiz_session(session_id: int):
    sb = get_supabase()
    sb.table("quiz_sessions").update({"ended_at": datetime.now().isoformat()}) \
      .eq("id", session_id).execute()


def save_quiz_result(session_id: int, word_en: str, word_kr: str,
                     user_answer: str, is_correct: bool):
    sb = get_supabase()
    sb.table("quiz_results").insert({
        "session_id":  session_id,
        "word_en":     word_en,
        "word_kr":     word_kr,
        "user_answer": user_answer,
        "is_correct":  is_correct,
    }).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 내신문제 세트
# ─────────────────────────────────────────────────────────────────────────────

def save_exam_set(student_id: int | None, note_id: int,
                  difficulty: str, questions: list) -> int:
    sb = get_supabase()
    result = sb.table("exam_sets").insert({
        "student_id": student_id or 0,   # None → 0
        "note_id":    note_id,
        "difficulty": difficulty,
        "questions":  questions,   # JSONB — list 직접 전달
    }).execute()
    return result.data[0]["id"]


def get_exam_set(exam_set_id: int) -> dict | None:
    sb = get_supabase()
    result = sb.table("exam_sets").select("*").eq("id", exam_set_id).execute()
    rows = result.data
    return rows[0] if rows else None


def save_exam_result(exam_set_id: int, student_id: int | None,
                     answers: dict, score: int, total: int, feedback: str) -> int:
    sb = get_supabase()
    result = sb.table("exam_results").insert({
        "exam_set_id": exam_set_id,
        "student_id":  student_id or 0,   # None → 0
        "answers":     answers,    # JSONB
        "score":       score,
        "total":       total,
        "feedback":    feedback,
    }).execute()
    return result.data[0]["id"]


# ─────────────────────────────────────────────────────────────────────────────
# 비법노트
# ─────────────────────────────────────────────────────────────────────────────

def save_secret_note(note_id: int, title: str, html_content: str) -> int:
    sb = get_supabase()
    result = sb.table("secret_notes").insert({
        "note_id":      note_id,
        "title":        title,
        "html_content": html_content,
    }).execute()
    return result.data[0]["id"]


def list_secret_notes(note_id: int | None = None) -> list[dict]:
    sb = get_supabase()
    q  = sb.table("secret_notes").select("*")
    if note_id:
        q = q.eq("note_id", note_id)
    result = q.order("created_at", desc=True).execute()
    return result.data or []


# ─────────────────────────────────────────────────────────────────────────────
# 시험 요약노트 (cheatsheets)
# ─────────────────────────────────────────────────────────────────────────────

def save_cheatsheet(note_id: int, note_title: str, data: dict,
                    sections: list, owner_id: str | None = None) -> int:
    sb = get_supabase()
    result = sb.table("cheatsheets").insert({
        "note_id":    note_id,
        "note_title": note_title,
        "data":       data,        # JSONB
        "sections":   sections,    # JSONB
        "owner_id":   owner_id,
    }).execute()
    return result.data[0]["id"]


def list_cheatsheets(note_id: int | None = None) -> list[dict]:
    sb = get_supabase()
    q  = sb.table("cheatsheets").select("*")
    if note_id:
        q = q.eq("note_id", note_id)
    result = q.order("created_at", desc=True).execute()
    return result.data or []


def delete_cheatsheet(cs_id: int):
    get_supabase().table("cheatsheets").delete().eq("id", cs_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 기출문제
# ─────────────────────────────────────────────────────────────────────────────

def save_past_problems(note_id: int, source_name: str, problems: list,
                       exam_year: str = "", publisher: str = "",
                       semester: str = "", exam_type: str = "") -> int:
    sb = get_supabase()
    result = sb.table("past_problems").insert({
        "note_id":     note_id,
        "source_name": source_name,
        "problems":    problems,   # JSONB
        "exam_year":   exam_year,
        "publisher":   publisher,
        "semester":    semester,
        "exam_type":   exam_type,
    }).execute()
    return result.data[0]["id"]


def list_past_problems(note_id: int | None = None,
                       exam_year: str = "", semester: str = "",
                       exam_type: str = "") -> list[dict]:
    sb = get_supabase()
    q  = sb.table("past_problems").select("*")
    if note_id:    q = q.eq("note_id",   note_id)
    if exam_year:  q = q.eq("exam_year", exam_year)
    if semester:   q = q.eq("semester",  semester)
    if exam_type:  q = q.eq("exam_type", exam_type)
    result = q.order("created_at", desc=True).execute()
    return result.data or []


def update_past_problems(pp_id: int, **kwargs):
    """저장된 기출의 출처·메타 수정 (source_name/exam_year/publisher/semester/exam_type)."""
    allowed = {"source_name", "exam_year", "publisher", "semester", "exam_type"}
    payload = {k: v for k, v in kwargs.items() if k in allowed}
    if not payload:
        return
    get_supabase().table("past_problems").update(payload).eq("id", pp_id).execute()


def delete_past_problems(pp_id: int):
    """저장된 기출 삭제 (Supabase) — 기존 SQLite 삭제 버그 대체."""
    get_supabase().table("past_problems").delete().eq("id", pp_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 취약 분석
# ─────────────────────────────────────────────────────────────────────────────

def save_weakness_profile(student_id: int, note_id: int, summary: str):
    sb = get_supabase()
    sb.rpc("upsert_weakness_profile", {
        "p_student_id": student_id,
        "p_note_id":    note_id,
        "p_summary":    summary,
    }).execute()


def get_weakness_profile(student_id: int, note_id: int) -> str:
    sb = get_supabase()
    result = sb.table("weakness_profile").select("summary") \
               .eq("student_id", student_id).eq("note_id", note_id).execute()
    rows = result.data
    return rows[0]["summary"] if rows else ""


# ─────────────────────────────────────────────────────────────────────────────
# 통합 문제뱅크
# ─────────────────────────────────────────────────────────────────────────────

def save_to_question_bank(note_id: int, questions: list[dict],
                          source_type: str = "ai",
                          grammar_point_id: int | None = None) -> int:
    """문제 목록을 뱅크에 저장 → 새로 저장된 수 반환"""
    sb    = get_supabase()
    saved = 0
    for q in questions:
        # 동일 question 텍스트 중복 방지
        dup = sb.table("question_bank").select("id") \
                .eq("note_id", note_id) \
                .eq("question", q.get("question", "")).execute()
        if dup.data:
            continue
        sb.table("question_bank").insert({
            "note_id":          note_id,
            "source_type":      source_type,
            "grammar_point_id": grammar_point_id,
            "q_type":           q.get("type", q.get("q_type", "")),
            "difficulty":       q.get("difficulty", "medium"),
            "question":         q.get("question", ""),
            "passage":          q.get("passage", ""),
            "options":          q.get("options", []),   # JSONB
            "answer":           q.get("answer", ""),
            "answer_kr":        q.get("answer_kr", ""),
        }).execute()
        saved += 1
    return saved


def get_question_bank(note_id: int, source_type: str | None = None,
                      difficulty: str | None = None,
                      q_type: str | None = None,
                      grammar_point_id: int | None = None,
                      limit: int = 50) -> list[dict]:
    """뱅크에서 문제 조회 (랜덤 순서)
    grammar_point_id 지정 시 해당 포인트 문제만 반환.
    """
    sb = get_supabase()
    q  = sb.table("question_bank").select("*").eq("note_id", note_id)
    if source_type:      q = q.eq("source_type",      source_type)
    if difficulty:       q = q.eq("difficulty",        difficulty)
    if q_type:           q = q.eq("q_type",            q_type)
    if grammar_point_id: q = q.eq("grammar_point_id", grammar_point_id)
    result = q.execute()
    rows   = result.data or []
    # Python에서 랜덤 셔플 후 limit 적용
    random.shuffle(rows)
    rows = rows[:limit]
    # options는 JSONB라 이미 list 형태 — 하위 호환을 위해 options 키 보장
    for r in rows:
        if "options" not in r:
            r["options"] = []
    return rows


def count_question_bank(note_id: int, source_type: str | None = None,
                        grammar_point_id: int | None = None) -> int:
    """뱅크 문제 수 카운트.
    grammar_point_id 지정 시 해당 포인트 문제만 카운트.
    """
    sb = get_supabase()
    q  = sb.table("question_bank").select("*", count="exact").eq("note_id", note_id)
    if source_type:
        q = q.eq("source_type", source_type)
    if grammar_point_id:
        q = q.eq("grammar_point_id", grammar_point_id)
    result = q.execute()
    return result.count or 0


def increment_used_count(bank_question_id: int):
    sb = get_supabase()
    # 현재값 조회 후 +1 (Supabase는 .increment() 미지원)
    result = sb.table("question_bank").select("used_count").eq("id", bank_question_id).execute()
    if result.data:
        cur = result.data[0].get("used_count", 0)
        sb.table("question_bank").update({"used_count": cur + 1}) \
          .eq("id", bank_question_id).execute()


def delete_bank_question(bank_question_id: int):
    sb = get_supabase()
    sb.table("question_bank").delete().eq("id", bank_question_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 문법 포인트
# ─────────────────────────────────────────────────────────────────────────────

def save_grammar_point(note_id: int, point_name: str, category: str,
                       explanation_kr: str, patterns: list, examples: list,
                       tip: str, ai_generated: bool = True) -> int:
    sb = get_supabase()
    result = sb.table("grammar_points").insert({
        "note_id":        note_id,
        "point_name":     point_name,
        "category":       category,
        "explanation_kr": explanation_kr,
        "patterns":       patterns,   # JSONB
        "examples":       examples,   # JSONB
        "tip":            tip,
        "ai_generated":   ai_generated,
    }).execute()
    return result.data[0]["id"]


def update_grammar_point(gid: int, **kwargs):
    """선생님 직접 편집"""
    sb  = get_supabase()
    upd = {}
    for k, v in kwargs.items():
        if k in ("point_name", "category", "explanation_kr", "tip", "is_active"):
            upd[k] = v
        elif k == "patterns":
            upd["patterns"] = v   # JSONB: list 직접
        elif k == "examples":
            upd["examples"] = v   # JSONB: list 직접
    if upd:
        sb.table("grammar_points").update(upd).eq("id", gid).execute()


def get_grammar_points(note_id: int) -> list[dict]:
    sb = get_supabase()
    result = sb.table("grammar_points").select("*") \
               .eq("note_id", note_id).order("id").execute()
    rows = result.data or []
    # 하위 호환: patterns/examples/is_active 키 보장
    for r in rows:
        r.setdefault("patterns", [])
        r.setdefault("examples", [])
        if r.get("is_active") is None:   # 컬럼 미존재/NULL → 활성 간주
            r["is_active"] = True
        # 기존 코드가 patterns_json/textbook_examples_json 을 쓰는 곳 호환
        r["patterns_json"]           = r["patterns"]
        r["textbook_examples_json"]  = r["examples"]
    return rows


def delete_grammar_point(gid: int):
    sb = get_supabase()
    sb.table("grammar_points").delete().eq("id", gid).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 문제 오답노트 (내신 + 문법 + 기출 통합)
# ─────────────────────────────────────────────────────────────────────────────

def add_question_wrong(student_id: int, note_id: int,
                       bank_question_id: int | None,
                       source_type: str, question_snapshot: dict,
                       user_answer: str):
    sb = get_supabase()
    if bank_question_id:
        # 원자적 upsert (RPC)
        sb.rpc("add_question_wrong_with_bank", {
            "p_student_id":        student_id,
            "p_note_id":           note_id,
            "p_bank_question_id":  bank_question_id,
            "p_source_type":       source_type,
            "p_question_snapshot": question_snapshot,
            "p_user_answer":       user_answer,
        }).execute()
    else:
        # bank_id 없는 경우 (기출 등) — 단순 삽입
        sb.table("question_wrong_notes").insert({
            "student_id":        student_id or 0,
            "note_id":           note_id,
            "bank_question_id":  None,
            "source_type":       source_type,
            "question_snapshot": question_snapshot,  # JSONB
            "user_answer":       user_answer,
            "wrong_count":       1,
        }).execute()


def get_question_wrong_notes(student_id: int,
                             note_id: int | None = None,
                             source_type: str | None = None) -> list[dict]:
    sb = get_supabase()
    q  = sb.table("question_wrong_notes").select("*").eq("student_id", student_id)
    if note_id:     q = q.eq("note_id",     note_id)
    if source_type: q = q.eq("source_type", source_type)
    result = q.order("wrong_count", desc=True).order("last_wrong", desc=True).execute()
    rows = result.data or []
    # 하위 호환: question_data 키 추가
    for r in rows:
        snap = r.get("question_snapshot")
        r["question_data"] = snap if isinstance(snap, dict) else {}
    return rows


def save_question_wrong_explain(qwn_id: int, explain: str):
    sb = get_supabase()
    sb.table("question_wrong_notes").update({"ai_explain": explain}) \
      .eq("id", qwn_id).execute()


def remove_question_wrong(qwn_id: int):
    sb = get_supabase()
    sb.table("question_wrong_notes").delete().eq("id", qwn_id).execute()


# ─────────────────────────────────────────────────────────────────────────────
# 온라인 노트 세션
# ─────────────────────────────────────────────────────────────────────────────

def save_online_note_item(student_id: int, note_id: int, content_type: str,
                          item_index: int, user_input: str, completed: bool = False):
    sb = get_supabase()
    sb.rpc("upsert_online_note_item", {
        "p_student_id":   student_id,
        "p_note_id":      note_id,
        "p_content_type": content_type,
        "p_item_index":   item_index,
        "p_user_input":   user_input,
        "p_completed":    completed,
    }).execute()


def get_online_note_items(student_id: int, note_id: int,
                          content_type: str) -> list[dict]:
    sb = get_supabase()
    result = sb.table("online_note_sessions").select("*") \
               .eq("student_id", student_id) \
               .eq("note_id", note_id) \
               .eq("content_type", content_type) \
               .order("item_index").execute()
    return result.data or []


def get_online_note_progress(student_id: int, note_id: int) -> dict:
    """콘텐츠 타입별 완성률"""
    sb = get_supabase()
    result = sb.table("online_note_sessions").select("content_type,completed") \
               .eq("student_id", student_id).eq("note_id", note_id).execute()
    rows   = result.data or []
    groups: dict = {}
    for r in rows:
        ct = r["content_type"]
        if ct not in groups:
            groups[ct] = {"total": 0, "done": 0}
        groups[ct]["total"] += 1
        if r.get("completed"):
            groups[ct]["done"] += 1
    return groups


# ─────────────────────────────────────────────────────────────────────────────
# 학습 로그 (대시보드)
# ─────────────────────────────────────────────────────────────────────────────

def log_study_activity(student_id: int, note_id: int, activity: str,
                       score: int | None = None, total: int | None = None,
                       duration_sec: int = 0, details: dict | None = None):
    sb = get_supabase()
    sb.table("study_logs").insert({
        "student_id":   student_id or 0,
        "note_id":      note_id,
        "activity":     activity,
        "score":        score,
        "total":        total,
        "duration_sec": duration_sec,
        "details":      details or {},  # JSONB
    }).execute()


def get_study_logs(student_id: int, days: int = 7) -> list[dict]:
    sb     = get_supabase()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    result = sb.table("study_logs").select("*") \
               .eq("student_id", student_id) \
               .gte("created_at", cutoff) \
               .order("created_at", desc=True).execute()
    return result.data or []


def get_student_stats(student_id: int, note_id: int | None = None) -> dict:
    """대시보드용 종합 통계"""
    sb = get_supabase()

    # 단어 오답 수
    q_wn = sb.table("wrong_notes").select("*", count="exact") \
              .eq("student_id", student_id)
    if note_id:
        q_wn = q_wn.eq("note_id", note_id)
    word_wrong_cnt = (q_wn.execute().count or 0)

    # 문제 오답 수
    q_qwn = sb.table("question_wrong_notes").select("*", count="exact") \
               .eq("student_id", student_id)
    if note_id:
        q_qwn = q_qwn.eq("note_id", note_id)
    q_wrong_cnt = (q_qwn.execute().count or 0)

    # 최근 내신 점수 (마지막 3개)
    exam_result = sb.table("study_logs").select("score,total") \
                    .eq("student_id", student_id) \
                    .eq("activity", "exam") \
                    .order("created_at", desc=True).limit(3).execute()
    exam_scores = [
        (r["score"], r["total"])
        for r in (exam_result.data or [])
        if r.get("score") is not None
    ]

    # 최근 단어 정확도 (마지막 5개)
    vocab_result = sb.table("study_logs").select("score,total") \
                     .eq("student_id", student_id) \
                     .eq("activity", "word_quiz") \
                     .order("created_at", desc=True).limit(5).execute()
    vocab_rows    = vocab_result.data or []
    total_correct = sum(r["score"] for r in vocab_rows if r.get("score") is not None)
    total_tried   = sum(r["total"] for r in vocab_rows if r.get("total"))
    vocab_accuracy = int(total_correct / total_tried * 100) if total_tried else None

    return {
        "word_wrong_count":     word_wrong_cnt,
        "question_wrong_count": q_wrong_cnt,
        "exam_scores":          exam_scores,
        "vocab_accuracy":       vocab_accuracy,
    }


def get_rich_student_profile(student_id: int) -> dict:
    """AI 추천용 종합 학생 프로파일 — 선생님 대시보드에서 사용"""
    sb = get_supabase()

    # 전체 학습 로그
    logs_res = sb.table("study_logs").select("*") \
                 .eq("student_id", student_id) \
                 .order("created_at", desc=True).execute()
    logs = logs_res.data or []

    # 모듈별 통계 집계
    mod_stats: dict = {}
    for row in logs:
        act = row.get("activity", "")
        if act not in mod_stats:
            mod_stats[act] = {"sessions": 0, "scores": [], "last_score": None}
        mod_stats[act]["sessions"] += 1
        if row.get("score") is not None and row.get("total"):
            pct = row["score"] / row["total"] * 100
            mod_stats[act]["scores"].append(pct)
            if mod_stats[act]["last_score"] is None:
                mod_stats[act]["last_score"] = pct
    for act, stat in mod_stats.items():
        sc = stat["scores"]
        stat["avg_score"] = round(sum(sc) / len(sc), 1) if sc else None

    # 연속 학습일 계산
    from datetime import date, timedelta
    dates_set = {row["created_at"][:10] for row in logs}
    streak = 0
    cur = date.today()
    while str(cur) in dates_set:
        streak += 1
        cur -= timedelta(days=1)

    # 최근 7일 활동일 수
    cutoff7 = str(date.today() - timedelta(days=6))
    recent_days = len({row["created_at"][:10] for row in logs
                       if row.get("created_at", "") >= cutoff7})

    # 취약 단어 Top 5
    wn_res = sb.table("wrong_notes").select("word_en, wrong_count") \
               .eq("student_id", student_id) \
               .order("wrong_count", desc=True).limit(5).execute()
    weak_words = [r["word_en"] for r in (wn_res.data or [])]

    # 취약 문제 유형 (question_wrong_notes)
    qwn_res = sb.table("question_wrong_notes") \
                .select("source_type, question_snapshot, wrong_count") \
                .eq("student_id", student_id) \
                .order("wrong_count", desc=True).limit(10).execute()
    topic_map: dict = {}
    for r in (qwn_res.data or []):
        snap = r.get("question_snapshot") or {}
        gp   = snap.get("gp_name", snap.get("type", r.get("source_type", "")))
        topic_map[gp] = topic_map.get(gp, 0) + r.get("wrong_count", 1)
    weak_topics = [k for k, _ in sorted(topic_map.items(), key=lambda x: -x[1])][:5]

    # 오답 카운트
    word_wrong_cnt = (sb.table("wrong_notes").select("*", count="exact")
                       .eq("student_id", student_id).execute().count or 0)
    q_wrong_cnt    = (sb.table("question_wrong_notes").select("*", count="exact")
                       .eq("student_id", student_id).execute().count or 0)

    return {
        "module_stats":          mod_stats,
        "streak":                streak,
        "total_sessions":        len(logs),
        "recent_activity_days":  recent_days,
        "weak_words":            weak_words,
        "weak_q_topics":         weak_topics,
        "word_wrong_count":      word_wrong_cnt,
        "question_wrong_count":  q_wrong_cnt,
    }


def get_all_students_stats(note_id: int | None = None) -> list[dict]:
    """선생님 대시보드용 전체 학생 통계"""
    students = list_students()
    result   = []
    for s in students:
        sid   = s["id"]
        stats = get_student_stats(sid, note_id)

        # 온라인 노트 완성률
        sb = get_supabase()
        q  = sb.table("online_note_sessions").select("completed") \
               .eq("student_id", sid)
        if note_id:
            q = q.eq("note_id", note_id)
        prog_rows   = q.execute().data or []
        total_items = len(prog_rows)
        done_items  = sum(1 for r in prog_rows if r.get("completed"))
        online_pct  = int(done_items / total_items * 100) if total_items else 0

        result.append({
            **s,
            **stats,
            "online_pct": online_pct,
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 숙제 (homework) — 선생님 출제 / 학생 완료 확인
# ─────────────────────────────────────────────────────────────────────────────

def create_homework(
    note_id: int,
    title: str,
    description: str,
    due_date: str,          # "YYYY-MM-DD"
    hw_type: str,           # "word_quiz"|"grammar"|"exam"|"note_read"|"mixed"
    target_score: int = 80,
    question_ids: list | None = None,
) -> int:
    """숙제 출제. Returns homework id."""
    sb = get_supabase()
    payload = {
        "note_id":     note_id,
        "title":       title,
        "description": description,
        "due_date":    due_date,
        "hw_type":     hw_type,
        "target_score": target_score,
        "is_active":   True,
    }
    if question_ids:
        payload["question_ids"] = question_ids
    res = sb.table("homework").insert(payload).execute()
    return (res.data or [{}])[0].get("id", 0)


def list_homework(note_id: int | None = None, active_only: bool = True) -> list[dict]:
    """숙제 목록 조회."""
    sb = get_supabase()
    q  = sb.table("homework").select("*").order("due_date")
    if note_id:
        q = q.eq("note_id", note_id)
    if active_only:
        q = q.eq("is_active", True)
    return q.execute().data or []


def get_homework(hw_id: int) -> dict | None:
    sb = get_supabase()
    res = sb.table("homework").select("*").eq("id", hw_id).maybe_single().execute()
    return res.data


def deactivate_homework(hw_id: int):
    sb = get_supabase()
    sb.table("homework").update({"is_active": False}).eq("id", hw_id).execute()


def submit_homework(
    hw_id: int,
    student_id: int,
    score: int | None = None,
    total: int | None = None,
    memo: str = "",
) -> int:
    """학생 숙제 제출 기록. Returns submission id."""
    sb = get_supabase()
    # 기존 제출 확인 (있으면 업데이트)
    existing = sb.table("homework_submissions") \
                  .select("id") \
                  .eq("hw_id", hw_id) \
                  .eq("student_id", student_id) \
                  .maybe_single().execute()
    payload = {
        "hw_id":      hw_id,
        "student_id": student_id,
        "score":      score,
        "total":      total,
        "memo":       memo,
        "submitted":  True,
    }
    if existing.data:
        sid = existing.data["id"]
        sb.table("homework_submissions").update(payload).eq("id", sid).execute()
        return sid
    res = sb.table("homework_submissions").insert(payload).execute()
    return (res.data or [{}])[0].get("id", 0)


def get_homework_submission(hw_id: int, student_id: int) -> dict | None:
    sb = get_supabase()
    res = sb.table("homework_submissions") \
             .select("*").eq("hw_id", hw_id).eq("student_id", student_id) \
             .maybe_single().execute()
    return res.data


def get_homework_submissions_for(hw_id: int) -> list[dict]:
    """숙제 하나의 전체 제출 현황 (선생님용)."""
    sb = get_supabase()
    return sb.table("homework_submissions").select("*").eq("hw_id", hw_id).execute().data or []


def ensure_homework_tables():
    """homework / homework_submissions 테이블이 없으면 안내 메시지 출력용."""
    # Supabase에서 테이블은 SQL로 생성해야 하므로 여기서는 존재 여부만 확인
    try:
        sb = get_supabase()
        sb.table("homework").select("id").limit(1).execute()
        sb.table("homework_submissions").select("id").limit(1).execute()
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 망각 곡선 복습 스케줄러 (SM-2 알고리즘)
# ─────────────────────────────────────────────────────────────────────────────

# 간격 단계표: repetitions → 다음 간격(일)
_REVIEW_INTERVALS = [1, 3, 7, 21, 60]  # 0회→1일, 1회→3일, 2회→7일, 3회→21일, 4회→60일


def schedule_review(student_id: int, item_type: str, item_key: str,
                    item_data: dict, note_id: int | None = None) -> None:
    """오답 발생 시 복습 스케줄 등록 (또는 기존 항목 리셋).
    item_type: 'word' | 'grammar' | 'sentence'
    item_key : word_en / str(grammar_point_id) / 'note{id}_sent{idx}'
    """
    from datetime import date
    sb   = get_supabase()
    today = date.today().isoformat()
    next_dt = (date.today() + __import__("datetime").timedelta(days=1)).isoformat()

    # upsert — 이미 있으면 리셋, 없으면 신규
    sb.table("review_schedule").upsert(
        {
            "student_id":    student_id,
            "note_id":       note_id,
            "item_type":     item_type,
            "item_key":      item_key,
            "item_data":     item_data,
            "next_review":   next_dt,
            "interval_days": 1,
            "repetitions":   0,
            "ease_factor":   2.5,
            "last_reviewed": today,
            "is_mastered":   False,
            "updated_at":    __import__("datetime").datetime.now().isoformat(),
        },
        on_conflict="student_id,item_type,item_key",
    ).execute()


def get_due_reviews(student_id: int, limit: int = 30) -> list[dict]:
    """오늘 복습해야 할 항목 목록 (next_review <= today, 미마스터)"""
    from datetime import date
    sb    = get_supabase()
    today = date.today().isoformat()
    result = (
        sb.table("review_schedule")
        .select("*")
        .eq("student_id", student_id)
        .eq("is_mastered", False)
        .lte("next_review", today)
        .order("next_review")
        .limit(limit)
        .execute()
    )
    return result.data or []


def count_due_reviews(student_id: int) -> int:
    """오늘 복습 대기 항목 수"""
    from datetime import date
    sb    = get_supabase()
    today = date.today().isoformat()
    result = (
        sb.table("review_schedule")
        .select("*", count="exact")
        .eq("student_id", student_id)
        .eq("is_mastered", False)
        .lte("next_review", today)
        .execute()
    )
    return result.count or 0


def update_review_result(review_id: int, is_correct: bool) -> dict:
    """복습 결과 반영 → SM-2 알고리즘으로 다음 날짜 계산.
    Returns: {next_review, interval_days, is_mastered, message}
    """
    import datetime as dt
    sb = get_supabase()

    # 현재 항목 조회
    row = sb.table("review_schedule").select("*").eq("id", review_id).execute()
    if not row.data:
        return {}
    item = row.data[0]

    reps       = item.get("repetitions", 0)
    ease       = item.get("ease_factor", 2.5)
    today      = dt.date.today()

    if is_correct:
        new_reps  = reps + 1
        # 간격 계산: 단계표 범위 초과 시 마지막 간격 × ease_factor
        if new_reps - 1 < len(_REVIEW_INTERVALS):
            new_interval = _REVIEW_INTERVALS[new_reps - 1]
        else:
            new_interval = max(1, round(item.get("interval_days", 1) * ease))
        new_ease      = min(3.0, ease + 0.1)
        is_mastered   = new_reps >= len(_REVIEW_INTERVALS)   # 5번 성공 → 마스터
        msg = ["1일 후 복습", "3일 후 복습", "7일 후 복습",
               "21일 후 복습", "60일 후 복습", "🏆 마스터!"][min(new_reps, 5)]
    else:
        new_reps     = 0
        new_interval = 1
        new_ease     = max(1.3, ease - 0.2)
        is_mastered  = False
        msg          = "내일 다시 복습"

    next_dt = (today + dt.timedelta(days=new_interval)).isoformat()

    sb.table("review_schedule").update({
        "repetitions":   new_reps,
        "ease_factor":   new_ease,
        "interval_days": new_interval,
        "next_review":   next_dt,
        "last_reviewed": today.isoformat(),
        "is_mastered":   is_mastered,
        "updated_at":    dt.datetime.now().isoformat(),
    }).eq("id", review_id).execute()

    return {
        "next_review":   next_dt,
        "interval_days": new_interval,
        "is_mastered":   is_mastered,
        "message":       msg,
    }


def get_review_stats(student_id: int) -> dict:
    """복습 전체 통계: 대기/마스터/총합"""
    import datetime as dt
    sb    = get_supabase()
    today = dt.date.today().isoformat()

    total   = sb.table("review_schedule").select("*", count="exact") \
                .eq("student_id", student_id).execute().count or 0
    mastered = sb.table("review_schedule").select("*", count="exact") \
                 .eq("student_id", student_id).eq("is_mastered", True).execute().count or 0
    due     = sb.table("review_schedule").select("*", count="exact") \
                .eq("student_id", student_id).eq("is_mastered", False) \
                .lte("next_review", today).execute().count or 0

    return {"total": total, "mastered": mastered, "due": due,
            "in_progress": total - mastered - due}


def delete_review_item(review_id: int):
    get_supabase().table("review_schedule").delete().eq("id", review_id).execute()


def get_today_summary(student_id: int) -> dict:
    """홈 카드용 오늘 학습 요약 — 빠른 조회 (DB 호출 최소화)"""
    from datetime import date, timedelta
    sb    = get_supabase()
    today = date.today().isoformat()

    # 복습 대기 수
    due = (
        sb.table("review_schedule").select("*", count="exact")
          .eq("student_id", student_id).eq("is_mastered", False)
          .lte("next_review", today).execute().count or 0
    )
    # 마스터 단어 수
    mastered = (
        sb.table("review_schedule").select("*", count="exact")
          .eq("student_id", student_id).eq("is_mastered", True)
          .execute().count or 0
    )
    # 오늘 학습 로그
    today_logs = (
        sb.table("study_logs").select("activity,score,total")
          .eq("student_id", student_id)
          .gte("created_at", today).execute().data or []
    )
    today_sessions = len(today_logs)
    today_scores   = [r["score"] / r["total"] * 100
                      for r in today_logs
                      if r.get("score") is not None and r.get("total")]
    today_avg = round(sum(today_scores) / len(today_scores)) if today_scores else None

    # 연속 학습일 (최근 30일 로그 조회)
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    logs30 = (
        sb.table("study_logs").select("created_at")
          .eq("student_id", student_id)
          .gte("created_at", cutoff).execute().data or []
    )
    dates_set = {r["created_at"][:10] for r in logs30}
    streak, cur = 0, date.today()
    while str(cur) in dates_set:
        streak += 1
        cur -= timedelta(days=1)

    # 단어 오답 수
    word_wrong = (
        sb.table("wrong_notes").select("*", count="exact")
          .eq("student_id", student_id).execute().count or 0
    )

    return {
        "due":            due,
        "mastered":       mastered,
        "streak":         streak,
        "today_sessions": today_sessions,
        "today_avg":      today_avg,
        "word_wrong":     word_wrong,
    }
