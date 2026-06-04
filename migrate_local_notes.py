# migrate_local_notes.py — 로컬 SQLite 노트 → Supabase 1회 업로드
# ─────────────────────────────────────────────────────────────────────
# 사용법:
#   1) 먼저 Supabase SQL Editor에서 supabase_migration_v11.sql 실행 (notes 테이블 생성)
#   2) python3 migrate_local_notes.py
#   3) (안내되는) setval SQL을 Supabase에서 1회 실행해 id 시퀀스 동기화
#
# - 기존 id를 그대로 보존해서 올립니다 (학습기록의 note_id 참조 안전).
# - 이미 같은 id가 Supabase에 있으면 건너뜁니다 (여러 번 실행해도 안전).
# ─────────────────────────────────────────────────────────────────────

import json
import sqlite3
from pathlib import Path

from supabase_client import get_supabase, is_supabase_configured

DB_PATH = Path(__file__).parent / "data" / "notes.db"


def main():
    if not is_supabase_configured():
        print("❌ Supabase 미설정 — .env에 SUPABASE_URL / SUPABASE_ANON_KEY를 확인하세요.")
        return
    if not DB_PATH.exists():
        print(f"❌ 로컬 노트 DB 없음: {DB_PATH}")
        return

    sb  = get_supabase()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM notes ORDER BY id").fetchall()
    print(f"📚 로컬 노트 {len(rows)}개 발견\n")

    # 이미 올라간 id 조회
    try:
        existing = {r["id"] for r in (sb.table("notes").select("id").execute().data or [])}
    except Exception as e:
        print(f"❌ Supabase notes 테이블 조회 실패 — migration v11을 먼저 실행했나요?\n   {e}")
        return

    uploaded, skipped, max_id = 0, 0, 0
    for r in rows:
        nid = r["id"]
        max_id = max(max_id, nid)
        if nid in existing:
            print(f"  ⏭️  id={nid}  이미 있음 — 건너뜀  ({r['title']})")
            skipped += 1
            continue
        payload = {
            "id":           nid,                                   # id 보존
            "title":        r["title"],
            "grade":        r["grade"]        or "",
            "publisher":    r["publisher"]    or "",
            "author":       r["author"]       or "",
            "chapter":      r["chapter"]      or "",
            "content_type": r["content_type"] or "",
            "words":        json.loads(r["words_json"] or "[]"),
            "dialogues":    json.loads(r["dlg_json"]   or "[]"),
            "text_data":    json.loads(r["text_json"]  or "{}"),
            "item_count":   r["item_count"]   or 0,
            "tags":         r["tags"]         or "",
            "created_at":   r["created_at"]   or "",
        }
        try:
            sb.table("notes").insert(payload).execute()
            print(f"  ✅  id={nid}  업로드  ({r['title']})")
            uploaded += 1
        except Exception as e:
            print(f"  ❌  id={nid}  실패: {e}")

    print(f"\n완료 — 업로드 {uploaded}개 · 건너뜀 {skipped}개")
    if uploaded:
        print(
            "\n⚠️  마지막으로 Supabase SQL Editor에서 아래를 1회 실행해 "
            "id 시퀀스를 동기화하세요 (새 노트 저장 시 id 충돌 방지):\n"
            f"  SELECT setval(pg_get_serial_sequence('notes','id'), {max_id});"
        )


if __name__ == "__main__":
    main()
