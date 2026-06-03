# library.py — S.Y. 담당: SQLite 기반 노트 라이브러리
# 업로드된 스발노트(단어/대화문/본문)를 영구 저장·조회·삭제

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_DIR  = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "notes.db"


def _conn():
    DB_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                grade        TEXT    DEFAULT '',
                publisher    TEXT    DEFAULT '',
                author       TEXT    DEFAULT '',
                chapter      TEXT    DEFAULT '',
                content_type TEXT    DEFAULT '',   -- 단어|대화문|본문|전체
                words_json   TEXT    DEFAULT '[]',
                dlg_json     TEXT    DEFAULT '[]',
                text_json    TEXT    DEFAULT '{}',
                item_count   INTEGER DEFAULT 0,
                tags         TEXT    DEFAULT '',
                created_at   TEXT    NOT NULL
            )
        """)


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
) -> int:
    """
    노트를 라이브러리에 저장하고 새 id를 반환.
    words     : [(en, kr), ...]
    dialogues : [{'title': str, 'lines': [(en, kr), ...]}, ...]
    text_data : {'title_en': str, 'title_kr': str, 'sentences': [(en, kr), ...]}
    """
    init_db()

    words     = words     or []
    dialogues = dialogues or []
    text_data = text_data or {}

    if content_type == "단어":
        count = len(words)
    elif content_type == "대화문":
        count = sum(len(d.get("lines", [])) for d in dialogues)
    elif content_type == "본문":
        count = len(text_data.get("sentences", []))
    else:
        count = len(words) + sum(len(d.get("lines", [])) for d in dialogues) + len(text_data.get("sentences", []))

    with _conn() as con:
        cur = con.execute("""
            INSERT INTO notes
              (title, grade, publisher, author, chapter, content_type,
               words_json, dlg_json, text_json, item_count, tags, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            title, grade, publisher, author, chapter, content_type,
            json.dumps(words,     ensure_ascii=False),
            json.dumps(dialogues, ensure_ascii=False),
            json.dumps(text_data, ensure_ascii=False),
            count, tags,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))
        return cur.lastrowid


def list_notes(
    grade: str = "",
    publisher: str = "",
    content_type: str = "",
    search: str = "",
) -> list[dict]:
    """필터 조건으로 노트 목록 반환 (최신순)."""
    init_db()
    query  = "SELECT id,title,grade,publisher,author,chapter,content_type,item_count,tags,created_at FROM notes WHERE 1=1"
    params = []
    if grade:         query += " AND grade=?";        params.append(grade)
    if publisher:     query += " AND publisher=?";    params.append(publisher)
    if content_type:  query += " AND content_type=?"; params.append(content_type)
    if search:        query += " AND title LIKE ?";   params.append(f"%{search}%")
    query += " ORDER BY created_at DESC"

    with _conn() as con:
        return [dict(r) for r in con.execute(query, params).fetchall()]


def get_note(note_id: int) -> dict | None:
    """id로 노트 전체 데이터 반환."""
    init_db()
    with _conn() as con:
        row = con.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if row is None:
        return None
    note = dict(row)
    note["words"]     = json.loads(note.pop("words_json", "[]"))
    note["dialogues"] = json.loads(note.pop("dlg_json",   "[]"))
    note["text_data"] = json.loads(note.pop("text_json",  "{}"))

    # JSON에서 로드 시 list→tuple 복원
    note["words"]     = [tuple(w) for w in note["words"]]
    for d in note["dialogues"]:
        d["lines"] = [tuple(l) for l in d.get("lines", [])]
    td = note["text_data"]
    if "sentences" in td:
        td["sentences"] = [tuple(s) for s in td["sentences"]]
    return note


def delete_note(note_id: int):
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM notes WHERE id=?", (note_id,))


def duplicate_note(note_id: int, new_title: str | None = None) -> int | None:
    """기존 노트를 편집 가능한 사본으로 복제 → 새 id 반환.
    콘텐츠 공급 마찰 제거: 0부터 만들지 않고 기존 노트를 재활용.
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
    )


def update_note(note_id: int, **kwargs):
    """노트 업데이트 — 메타데이터 및 콘텐츠(단어/대화문/본문) 모두 지원."""
    init_db()

    set_parts: list[str] = []
    params:    list      = []

    # ── 메타데이터 컬럼 ─────────────────────────────────────
    for col in ("title", "grade", "publisher", "author", "chapter", "content_type", "tags"):
        if col in kwargs:
            set_parts.append(f"{col}=?")
            params.append(kwargs[col])

    # ── 콘텐츠 컬럼 ─────────────────────────────────────────
    if "words" in kwargs:
        set_parts.append("words_json=?")
        params.append(json.dumps(kwargs["words"], ensure_ascii=False))
    if "dialogues" in kwargs:
        set_parts.append("dlg_json=?")
        params.append(json.dumps(kwargs["dialogues"], ensure_ascii=False))
    if "text_data" in kwargs:
        set_parts.append("text_json=?")
        params.append(json.dumps(kwargs["text_data"], ensure_ascii=False))

    # ── item_count 재계산 (콘텐츠·유형 변경 시) ─────────────
    if any(k in kwargs for k in ("words", "dialogues", "text_data", "content_type")):
        with _conn() as con:
            row = con.execute(
                "SELECT words_json, dlg_json, text_json, content_type FROM notes WHERE id=?",
                (note_id,),
            ).fetchone()
        if row:
            w  = kwargs.get("words",      json.loads(row["words_json"]))
            d  = kwargs.get("dialogues",  json.loads(row["dlg_json"]))
            t  = kwargs.get("text_data",  json.loads(row["text_json"]))
            ct = kwargs.get("content_type", row["content_type"])

            if ct == "단어":
                count = len(w)
            elif ct == "대화문":
                count = sum(len(x.get("lines", [])) for x in d)
            elif ct == "본문":
                count = len(t.get("sentences", []))
            else:
                count = (len(w)
                         + sum(len(x.get("lines", [])) for x in d)
                         + len(t.get("sentences", [])))

            set_parts.append("item_count=?")
            params.append(count)

    if not set_parts:
        return

    params.append(note_id)
    with _conn() as con:
        con.execute(f"UPDATE notes SET {', '.join(set_parts)} WHERE id=?", params)


def get_all_values(field: str) -> list[str]:
    """특정 컬럼의 유니크 값 목록 (필터 드롭다운용)."""
    init_db()
    with _conn() as con:
        rows = con.execute(f"SELECT DISTINCT {field} FROM notes WHERE {field}!='' ORDER BY {field}").fetchall()
    return [r[0] for r in rows]
