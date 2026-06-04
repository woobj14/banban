# library.py — S.Y. 담당: 노트 라이브러리 (Supabase 기반)
# 업로드된 반반노트(단어/대화문/본문)를 Supabase에 영구 저장·조회·삭제.
# v11에서 로컬 SQLite(data/notes.db) → Supabase `notes` 테이블로 이전.
#   - 로컬에서 만든 노트가 배포(홈페이지)에서도 그대로 보임
#   - 재배포/재시작에도 데이터가 사라지지 않음
# 함수 시그니처와 반환 구조는 기존 SQLite 버전과 100% 호환.

from datetime import datetime
import streamlit as st
from supabase_client import get_supabase

_TABLE = "notes"


def _invalidate():
    """노트 변경 시 조회 캐시 무효화 (목록/상세/필터값)."""
    try:
        list_notes.clear()
        get_note.clear()
        get_all_values.clear()
        count_my_notes.clear()
    except Exception:
        pass

# 목록 조회용 컬럼 (콘텐츠 JSONB 제외 — 가볍게)
_META_COLS = ("id,title,grade,publisher,author,chapter,"
              "content_type,item_count,tags,created_at,owner_id,visibility")


def init_db():
    """Supabase 전환 후 no-op (테이블은 supabase_migration_v11.sql로 생성)."""
    return


# ─────────────────────────────────────────────────────────────────────────────
# 내부 유틸 — JSON 정규화 (tuple → list, list → tuple)
# ─────────────────────────────────────────────────────────────────────────────

def _listify(obj):
    """tuple을 list로 재귀 변환 (JSONB 저장용)."""
    if isinstance(obj, tuple):
        return [_listify(x) for x in obj]
    if isinstance(obj, list):
        return [_listify(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _listify(v) for k, v in obj.items()}
    return obj


def _count_items(content_type: str, words: list, dialogues: list, text_data: dict) -> int:
    if content_type == "단어":
        return len(words)
    if content_type == "대화문":
        return sum(len(d.get("lines", [])) for d in dialogues)
    if content_type == "본문":
        return len(text_data.get("sentences", []))
    return (len(words)
            + sum(len(d.get("lines", [])) for d in dialogues)
            + len(text_data.get("sentences", [])))


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

def save_note(
    *,
    title: str,
    grade: str = "",
    publisher: str = "",
    author: str = "",
    chapter: str = "",
    content_type: str = "",  # 단어|대화문|본문|전체
    words: list | None = None,
    dialogues: list | None = None,
    text_data: dict | None = None,
    tags: str = "",
    owner_id: str | None = None,      # 제작자(선생님) auth user id
    visibility: str = "private",      # 'private'(나+내 학생) | 'public'(공용 자료실)
) -> int:
    """노트를 라이브러리에 저장하고 새 id를 반환.
    words     : [(en, kr), ...]
    dialogues : [{'title': str, 'lines': [(en, kr), ...]}, ...]
    text_data : {'title_en': str, 'title_kr': str, 'sentences': [(en, kr), ...]}
    """
    words     = words     or []
    dialogues = dialogues or []
    text_data = text_data or {}
    count = _count_items(content_type, words, dialogues, text_data)

    sb  = get_supabase()
    res = sb.table(_TABLE).insert({
        "title":        title,
        "grade":        grade,
        "publisher":    publisher,
        "author":       author,
        "chapter":      chapter,
        "content_type": content_type,
        "words":        _listify(words),
        "dialogues":    _listify(dialogues),
        "text_data":    _listify(text_data),
        "item_count":   count,
        "tags":         tags,
        "owner_id":     owner_id,
        "visibility":   visibility if visibility in ("private", "public") else "private",
        "created_at":   datetime.now().strftime("%Y-%m-%d %H:%M"),
    }).execute()
    _invalidate()
    return res.data[0]["id"] if res.data else 0


@st.cache_data(ttl=120, show_spinner=False)
def list_notes(
    grade: str = "",
    publisher: str = "",
    content_type: str = "",
    search: str = "",
    scope: str = "all",                # 'mine' | 'public' | 'student' | 'all'
    owner_id: str | None = None,       # scope='mine' / 'student'(우리 선생님)일 때
) -> list[dict]:
    """필터 조건으로 노트 목록 반환 (최신순). 콘텐츠 제외 메타데이터만.

    scope:
      'mine'    — owner_id가 만든 내 노트만
      'public'  — 공용 자료실(visibility='public')만
      'student' — 우리 선생님(owner_id) 노트 + 공용 자료실
      'all'     — 전체 (관리자/하위호환)
    """
    sb = get_supabase()
    q  = sb.table(_TABLE).select(_META_COLS)
    if grade:        q = q.eq("grade", grade)
    if publisher:    q = q.eq("publisher", publisher)
    if content_type: q = q.eq("content_type", content_type)
    if search:       q = q.ilike("title", f"%{search}%")

    # ── 가시성 범위 ──────────────────────────────────────────
    if scope == "mine" and owner_id:
        q = q.eq("owner_id", owner_id)
    elif scope == "public":
        q = q.eq("visibility", "public")
    elif scope == "student" and owner_id:
        # 우리 선생님 노트 + 공용 자료실
        q = q.or_(f"owner_id.eq.{owner_id},visibility.eq.public")
    elif scope == "student":
        # 선생님 없는 개인 학생 → 공용 자료실만
        q = q.eq("visibility", "public")
    # scope == "all" → 필터 없음

    res = q.order("created_at", desc=True).execute()
    return res.data or []


@st.cache_data(ttl=120, show_spinner=False)
def count_my_notes(owner_id: str) -> int:
    """내가 만든 노트 수 (노트 생성 한도 게이팅용)."""
    if not owner_id:
        return 0
    sb  = get_supabase()
    res = sb.table(_TABLE).select("id", count="exact").eq("owner_id", owner_id).execute()
    return res.count or 0


@st.cache_data(ttl=120, show_spinner=False)
def get_note(note_id: int) -> dict | None:
    """id로 노트 전체 데이터 반환 (콘텐츠 포함, list→tuple 복원)."""
    sb  = get_supabase()
    res = sb.table(_TABLE).select("*").eq("id", note_id).limit(1).execute()
    if not res.data:
        return None
    note = res.data[0]

    # JSONB는 이미 list/dict로 옴 → tuple 복원 (기존 get_note 동작과 동일)
    note["words"]     = [tuple(w) for w in (note.get("words") or [])]
    note["dialogues"] = note.get("dialogues") or []
    for d in note["dialogues"]:
        d["lines"] = [tuple(l) for l in d.get("lines", [])]
    note["text_data"] = note.get("text_data") or {}
    if "sentences" in note["text_data"]:
        note["text_data"]["sentences"] = [tuple(s) for s in note["text_data"]["sentences"]]
    return note


def delete_note(note_id: int):
    get_supabase().table(_TABLE).delete().eq("id", note_id).execute()
    _invalidate()


def duplicate_note(note_id: int, new_title: str | None = None,
                   owner_id: str | None = None) -> int | None:
    """기존 노트를 편집 가능한 사본으로 복제 → 새 id 반환.
    공용 자료실 노트를 '내 것으로' 가져올 때 사용 — 복제자가 새 owner, 기본 비공개.
    owner_id 미지정 시 원본 소유자 유지(같은 선생님의 자기 노트 복제).
    """
    src = get_note(note_id)
    if not src:
        return None
    title = new_title or f"{src.get('title','노트')} (복사본)"
    return save_note(
        title        = title,
        grade        = src.get("grade", ""),
        publisher    = src.get("publisher", ""),
        author       = src.get("author", ""),
        chapter      = src.get("chapter", ""),
        content_type = src.get("content_type", ""),
        words        = src.get("words", []),
        dialogues    = src.get("dialogues", []),
        text_data    = src.get("text_data", {}),
        tags         = src.get("tags", ""),
        owner_id     = owner_id if owner_id is not None else src.get("owner_id"),
        visibility   = "private",   # 복제본은 항상 비공개로 시작
    )


def update_note(note_id: int, **kwargs):
    """노트 업데이트 — 메타데이터 및 콘텐츠(단어/대화문/본문) 모두 지원."""
    payload: dict = {}

    # ── 메타데이터 컬럼 ─────────────────────────────────────
    for col in ("title", "grade", "publisher", "author", "chapter",
                "content_type", "tags", "visibility"):
        if col in kwargs:
            payload[col] = kwargs[col]

    # ── 콘텐츠 컬럼 ─────────────────────────────────────────
    if "words" in kwargs:
        payload["words"] = _listify(kwargs["words"])
    if "dialogues" in kwargs:
        payload["dialogues"] = _listify(kwargs["dialogues"])
    if "text_data" in kwargs:
        payload["text_data"] = _listify(kwargs["text_data"])

    # ── item_count 재계산 (콘텐츠·유형 변경 시) ─────────────
    if any(k in kwargs for k in ("words", "dialogues", "text_data", "content_type")):
        cur = get_note(note_id) or {}
        w  = kwargs.get("words",        cur.get("words", []))
        d  = kwargs.get("dialogues",    cur.get("dialogues", []))
        t  = kwargs.get("text_data",    cur.get("text_data", {}))
        ct = kwargs.get("content_type", cur.get("content_type", ""))
        payload["item_count"] = _count_items(ct, w, d, t)

    if not payload:
        return
    get_supabase().table(_TABLE).update(payload).eq("id", note_id).execute()
    _invalidate()


@st.cache_data(ttl=120, show_spinner=False)
def get_all_values(field: str) -> list[str]:
    """특정 컬럼의 유니크 값 목록 (필터 드롭다운용)."""
    sb  = get_supabase()
    res = sb.table(_TABLE).select(field).execute()
    seen = sorted({(r.get(field) or "") for r in (res.data or []) if r.get(field)})
    return [v for v in seen if v]
