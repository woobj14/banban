# study_class.py — 반반 BanBan 클래스(반) 관리 모듈
# 선생님: 클래스 생성 → 코드 공유 → 노트 배포 → 학생 현황 모니터링
# 학생:  코드 입력 → 클래스 가입 → 선생님 노트 자동 수신

import random
import string
import streamlit as st
from datetime import datetime

from icons import icon, section_md
from study_db import log_study_activity


# ─────────────────────────────────────────────────────────────────────────────
# DB 헬퍼 (Supabase)
# ─────────────────────────────────────────────────────────────────────────────

def _sb():
    from supabase_client import get_supabase
    return get_supabase()


def _gen_code(length: int = 6) -> str:
    """대문자+숫자 조합 클래스 코드 생성"""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


# ── 클래스 CRUD ───────────────────────────────────────────────────────────────

def create_class(teacher_id: int, name: str, grade: str = "",
                 description: str = "") -> dict:
    """클래스 생성 → {id, class_code, name, ...} 반환"""
    sb = _sb()
    # 중복 코드 방지: 최대 5회 시도
    for _ in range(5):
        code = _gen_code()
        dup = sb.table("classes").select("id").eq("class_code", code).execute()
        if not dup.data:
            break
    result = sb.table("classes").insert({
        "teacher_id":  teacher_id,
        "class_code":  code,
        "name":        name.strip(),
        "grade":       grade.strip(),
        "description": description.strip(),
        "is_active":   True,
    }).execute()
    return result.data[0] if result.data else {}


def get_class_by_code(code: str) -> dict | None:
    sb = _sb()
    result = sb.table("classes").select("*").eq("class_code", code.upper().strip()) \
               .eq("is_active", True).execute()
    return result.data[0] if result.data else None


def get_classes_by_teacher(teacher_id: int) -> list[dict]:
    sb = _sb()
    result = sb.table("classes").select("*").eq("teacher_id", teacher_id) \
               .eq("is_active", True).order("created_at", desc=True).execute()
    return result.data or []


def get_classes_by_student(student_id: int) -> list[dict]:
    """학생이 가입한 클래스 목록"""
    sb = _sb()
    result = sb.table("class_members").select(
        "class_id, joined_at, classes(id, name, grade, class_code, teacher_id, description)"
    ).eq("student_id", student_id).execute()
    rows = []
    for r in (result.data or []):
        cls = r.get("classes") or {}
        cls["joined_at"] = r.get("joined_at")
        rows.append(cls)
    return rows


def deactivate_class(class_id: int):
    _sb().table("classes").update({"is_active": False}).eq("id", class_id).execute()


# ── 멤버 관리 ─────────────────────────────────────────────────────────────────

def join_class(student_id: int, class_code: str) -> tuple[bool, str]:
    """코드로 클래스 가입 → (성공 여부, 메시지)"""
    cls = get_class_by_code(class_code)
    if not cls:
        return False, "❌ 존재하지 않는 클래스 코드예요."
    sb  = _sb()
    # 이미 가입 여부 확인
    dup = sb.table("class_members").select("id") \
            .eq("class_id", cls["id"]).eq("student_id", student_id).execute()
    if dup.data:
        return False, f"이미 '{cls['name']}' 클래스에 가입되어 있어요."
    sb.table("class_members").insert({
        "class_id":   cls["id"],
        "student_id": student_id,
    }).execute()
    return True, f"✅ '{cls['name']}' 클래스에 가입했어요!"


def get_class_members(class_id: int) -> list[dict]:
    sb = _sb()
    result = sb.table("class_members").select(
        "student_id, joined_at, profiles(name, grade, email)"
    ).eq("class_id", class_id).execute()
    rows = []
    for r in (result.data or []):
        prof = r.get("profiles") or {}
        rows.append({
            "student_id": r["student_id"],
            "name":       prof.get("name", f"학생 #{r['student_id']}"),
            "grade":      prof.get("grade", ""),
            "email":      prof.get("email", ""),
            "joined_at":  r.get("joined_at", ""),
        })
    return rows


def remove_member(class_id: int, student_id: int):
    _sb().table("class_members").delete() \
        .eq("class_id", class_id).eq("student_id", student_id).execute()


# ── 노트 배포 ─────────────────────────────────────────────────────────────────

def share_note_to_class(class_id: int, note_id: int, shared_by: int) -> bool:
    """선생님 노트를 클래스 전체에 배포"""
    sb = _sb()
    # 중복 방지
    dup = sb.table("class_notes").select("id") \
            .eq("class_id", class_id).eq("note_id", note_id).execute()
    if dup.data:
        return False  # 이미 공유됨
    sb.table("class_notes").insert({
        "class_id":  class_id,
        "note_id":   note_id,
        "shared_by": shared_by,
    }).execute()
    return True


def get_class_notes(class_id: int) -> list[dict]:
    """클래스에 공유된 노트 목록"""
    sb = _sb()
    result = sb.table("class_notes").select(
        "note_id, shared_at, shared_by"
    ).eq("class_id", class_id).order("shared_at", desc=True).execute()
    return result.data or []


def get_shared_note_ids(student_id: int) -> list[int]:
    """학생이 속한 클래스에 공유된 노트 ID 목록"""
    classes = get_classes_by_student(student_id)
    if not classes:
        return []
    sb = _sb()
    class_ids = [c["id"] for c in classes if c.get("id")]
    if not class_ids:
        return []
    result = sb.table("class_notes").select("note_id").in_("class_id", class_ids).execute()
    return list({r["note_id"] for r in (result.data or [])})


def unshare_note_from_class(class_id: int, note_id: int):
    _sb().table("class_notes").delete() \
        .eq("class_id", class_id).eq("note_id", note_id).execute()


# ── 학생 학습 현황 (선생님용) ─────────────────────────────────────────────────

def get_class_student_stats(class_id: int) -> list[dict]:
    """클래스 학생별 최근 학습 통계"""
    sb  = _sb()
    members = get_class_members(class_id)
    if not members:
        return []
    stats = []
    for m in members:
        sid = m["student_id"]
        # 최근 7일 학습 로그
        result = sb.table("study_logs").select("activity_type,score,total,created_at") \
                   .eq("student_id", sid) \
                   .order("created_at", desc=True).limit(20).execute()
        logs   = result.data or []
        # 오답 현황
        wn     = sb.table("wrong_notes").select("word_en, wrong_count") \
                   .eq("student_id", sid).order("wrong_count", desc=True) \
                   .limit(3).execute()
        top_wrong = [w["word_en"] for w in (wn.data or [])]
        stats.append({
            **m,
            "recent_logs":  logs[:5],
            "log_count":    len(logs),
            "top_wrong":    top_wrong,
            "last_active":  logs[0]["created_at"][:10] if logs else "—",
        })
    # 최근 활동 순 정렬
    stats.sort(key=lambda x: x["last_active"], reverse=True)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# UI — 선생님 클래스 관리 페이지
# ─────────────────────────────────────────────────────────────────────────────

def page_class_teacher(teacher_id: int, notes: list[dict]):
    """선생님: 클래스 생성·관리·배포 페이지"""

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0891B2,#0E7490);color:white;
     border-radius:14px;padding:18px 20px;margin-bottom:20px;">
  <div style="font-size:0.85rem;opacity:0.85;display:flex;align-items:center;gap:4px;">
    {icon("people", 14, "rgba(255,255,255,0.85)")} 클래스 관리
  </div>
  <div style="font-size:1.4rem;font-weight:800;margin-top:4px;">내 클래스</div>
  <div style="font-size:0.82rem;opacity:0.85;margin-top:4px;">
    클래스 코드로 학생을 초대하고, 노트를 바로 배포하세요
  </div>
</div>
""", unsafe_allow_html=True)

    tab_list, tab_create, tab_share = st.tabs([
        "📋 클래스 목록", "➕ 새 클래스", "📤 노트 배포"
    ])

    # ── 탭1: 클래스 목록 ──────────────────────────────────────────
    with tab_list:
        try:
            classes = get_classes_by_teacher(teacher_id)
        except Exception as e:
            _handle_table_error(e)
            return

        if not classes:
            st.markdown(f"""
<div style="text-align:center;padding:40px;background:#f0f9ff;border-radius:14px;
     border:2px dashed #bae6fd;">
  <div style="margin-bottom:8px;">{icon("people", 52, "#0891B2")}</div>
  <div style="font-weight:700;color:#0891B2;font-size:1.1rem;margin-top:8px;">
    아직 클래스가 없어요
  </div>
  <div style="color:#9ca3af;font-size:0.9rem;margin-top:4px;">
    '새 클래스' 탭에서 첫 번째 클래스를 만들어보세요!
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            for cls in classes:
                _render_class_card(cls, notes, teacher_id)

    # ── 탭2: 새 클래스 만들기 ─────────────────────────────────────
    with tab_create:
        st.markdown("""
<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:12px;
     padding:14px 16px;margin-bottom:16px;font-size:0.85rem;color:#0891B2;">
  💡 클래스를 만들면 6자리 코드가 생성돼요.<br>
  학생들이 코드를 입력하면 바로 합류! 노트도 한 번에 배포할 수 있어요.
</div>
""", unsafe_allow_html=True)

        c1, c2 = st.columns([3, 1])
        new_name  = c1.text_input("클래스 이름 *", key="cls_new_name",
                                   placeholder="예: 2학년 3반 영어 / 화목반 / 지유·반이·동현")
        new_grade = c2.selectbox("학년", ["중1", "중2", "중3", "고1", "혼합"],
                                  key="cls_new_grade")
        new_desc  = st.text_area("클래스 설명 (선택)", key="cls_new_desc", height=70,
                                  placeholder="예: NE능률 2학년 3과~5과 / 매주 화·목 오후 4시")

        if st.button("✅ 클래스 만들기", type="primary", use_container_width=True,
                     key="cls_create_btn"):
            if not new_name.strip():
                st.error("클래스 이름을 입력해주세요.")
            else:
                try:
                    cls = create_class(teacher_id, new_name, new_grade, new_desc)
                    if cls:
                        st.success(f"✅ '{cls['name']}' 클래스 생성!")
                        st.markdown(f"""
<div style="background:#0891B2;color:white;border-radius:14px;padding:20px;
     text-align:center;margin-top:12px;">
  <div style="font-size:0.85rem;opacity:0.85;margin-bottom:6px;">
    학생 초대 코드
  </div>
  <div style="font-size:2.8rem;font-weight:900;letter-spacing:8px;">
    {cls['class_code']}
  </div>
  <div style="font-size:0.8rem;opacity:0.75;margin-top:8px;">
    학생들에게 이 코드를 알려주세요 → 학습센터 → 클래스 입장
  </div>
</div>
""", unsafe_allow_html=True)
                        # 입력 초기화
                        for k in ["cls_new_name", "cls_new_desc"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                except Exception as e:
                    _handle_table_error(e)

    # ── 탭3: 노트 배포 ────────────────────────────────────────────
    with tab_share:
        try:
            classes = get_classes_by_teacher(teacher_id)
        except Exception as e:
            _handle_table_error(e)
            return

        if not classes:
            st.info("먼저 클래스를 만들어주세요.")
            return
        if not notes:
            st.info("공유할 노트가 없어요. 반반노트에서 노트를 먼저 만들어주세요.")
            return

        sel_cls = st.selectbox(
            "배포할 클래스",
            options=classes,
            format_func=lambda c: f"{c['name']} ({c['class_code']})",
            key="share_cls_sel",
        )
        sel_note = st.selectbox(
            "배포할 노트",
            options=notes,
            format_func=lambda n: n.get("title", f"노트 #{n.get('id', '?')}"),
            key="share_note_sel",
        )

        if sel_cls and sel_note:
            # 현재 배포 현황
            try:
                shared = get_class_notes(sel_cls["id"])
                shared_ids = {s["note_id"] for s in shared}
                already = sel_note.get("id") in shared_ids
            except Exception:
                shared_ids = set()
                already = False

            if already:
                st.markdown("""
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
     padding:10px 14px;font-size:0.85rem;color:#166534;">
  ✅ 이미 이 클래스에 배포된 노트예요.
</div>
""", unsafe_allow_html=True)
                if st.button("🗑 배포 취소", use_container_width=True,
                              key="unshare_btn"):
                    unshare_note_from_class(sel_cls["id"], sel_note["id"])
                    st.success("배포를 취소했어요.")
                    st.rerun()
            else:
                members = get_class_members(sel_cls["id"])
                st.markdown(f"""
<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
     padding:12px 14px;font-size:0.85rem;color:#1e40af;margin-bottom:12px;">
  📤 <b>{sel_cls['name']}</b> 클래스 학생 <b>{len(members)}명</b>에게
  <b>'{sel_note.get('title', '노트')}'</b>를 배포합니다.
</div>
""", unsafe_allow_html=True)
                if st.button("📤 노트 배포하기", type="primary",
                              use_container_width=True, key="share_btn"):
                    try:
                        ok = share_note_to_class(
                            sel_cls["id"], sel_note["id"], teacher_id
                        )
                        if ok:
                            st.success(f"✅ {len(members)}명에게 배포 완료!")
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("이미 배포된 노트예요.")
                    except Exception as e:
                        _handle_table_error(e)

        # 현재 배포 현황 목록
        if sel_cls:
            try:
                shared = get_class_notes(sel_cls["id"])
            except Exception:
                shared = []
            if shared:
                st.divider()
                st.caption(f"'{sel_cls['name']}' 클래스에 배포된 노트 {len(shared)}개")
                for s in shared:
                    note_match = next((n for n in notes if n.get("id") == s["note_id"]), None)
                    note_title = note_match.get("title", f"노트 #{s['note_id']}") if note_match else f"노트 #{s['note_id']}"
                    shared_dt  = (s.get("shared_at") or "")[:10]
                    st.markdown(f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
     padding:8px 12px;margin:4px 0;display:flex;justify-content:space-between;
     align-items:center;font-size:0.85rem;">
  <span>📄 {note_title}</span>
  <span style="color:#94a3b8;">{shared_dt}</span>
</div>
""", unsafe_allow_html=True)


def _render_class_card(cls: dict, notes: list[dict], teacher_id: int):
    """단일 클래스 카드 (멤버 현황 포함)"""
    try:
        members = get_class_members(cls["id"])
    except Exception:
        members = []

    with st.expander(
        f"🏫 **{cls['name']}** — 코드: `{cls['class_code']}` | 학생 {len(members)}명",
        expanded=False,
    ):
        # 코드 강조 표시
        st.markdown(f"""
<div style="background:#0891B2;color:white;border-radius:10px;padding:12px 16px;
     text-align:center;margin-bottom:12px;">
  <div style="font-size:0.75rem;opacity:0.85;">학생 초대 코드</div>
  <div style="font-size:2rem;font-weight:900;letter-spacing:6px;margin:4px 0;">
    {cls['class_code']}
  </div>
  <div style="font-size:0.72rem;opacity:0.75;">
    학생: 학습센터 → 내 클래스 → 코드 입력
  </div>
</div>
""", unsafe_allow_html=True)

        if cls.get("description"):
            st.caption(cls["description"])

        # 멤버 현황
        if not members:
            st.info("아직 가입한 학생이 없어요. 코드를 공유해주세요!")
        else:
            st.markdown(f"**학생 {len(members)}명**")
            try:
                stats = get_class_student_stats(cls["id"])
            except Exception:
                stats = members  # 통계 조회 실패 시 기본 정보만

            for m in (stats or members):
                name     = m.get("name", "학생")
                grade    = m.get("grade", "")
                last_act = m.get("last_active", "—")
                log_cnt  = m.get("log_count", 0)
                top_w    = m.get("top_wrong", [])
                wrong_str = ", ".join(top_w[:3]) if top_w else "없음"

                st.markdown(f"""
<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;
     padding:8px 12px;margin:3px 0;font-size:0.83rem;
     display:flex;justify-content:space-between;align-items:center;">
  <div>
    <span style="font-weight:700;">{name}</span>
    {f'<span style="color:#94a3b8;margin-left:6px;">{grade}</span>' if grade else ''}
    {f'<span style="background:#fee2e2;color:#dc2626;border-radius:4px;padding:1px 5px;font-size:0.7rem;margin-left:6px;">오답: {wrong_str}</span>' if top_w else ''}
  </div>
  <div style="color:#94a3b8;">
    최근 {last_act} | {log_cnt}회 학습
  </div>
</div>
""", unsafe_allow_html=True)

        # 삭제 버튼
        from icons import confirm_delete_btn
        st.markdown("")
        if confirm_delete_btn("클래스 삭제", key=f"cls_del_{cls['id']}",
                               item_name=cls["name"],
                               use_container_width=True):
            deactivate_class(cls["id"])
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# UI — 학생 클래스 입장 + 공유 노트 확인
# ─────────────────────────────────────────────────────────────────────────────

def page_class_student(student_id: int, notes: list[dict]):
    """학생: 클래스 가입 + 선생님 공유 노트 수신"""

    st.markdown(f"""
<div style="background:linear-gradient(135deg,#059669,#047857);color:white;
     border-radius:14px;padding:18px 20px;margin-bottom:20px;">
  <div style="font-size:0.85rem;opacity:0.85;">
    {icon("people", 14, "rgba(255,255,255,0.85)")} 내 클래스
  </div>
  <div style="font-size:1.4rem;font-weight:800;margin-top:4px;">클래스 입장</div>
  <div style="font-size:0.82rem;opacity:0.85;margin-top:4px;">
    선생님께 코드를 받아서 입력하면 노트가 자동으로 들어와요!
  </div>
</div>
""", unsafe_allow_html=True)

    tab_join, tab_my = st.tabs(["🔑 코드 입장", "📚 내 클래스"])

    # ── 탭1: 코드 입장 ────────────────────────────────────────────
    with tab_join:
        st.markdown("""
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;
     padding:14px 16px;margin-bottom:16px;font-size:0.85rem;color:#166534;">
  선생님이 알려준 6자리 코드를 입력하세요.<br>
  가입하면 선생님의 노트가 내 학습 목록에 바로 추가돼요!
</div>
""", unsafe_allow_html=True)

        code_input = st.text_input(
            "클래스 코드 (6자리)",
            key="cls_join_code",
            placeholder="예: AB1C2D",
            max_chars=6,
        ).upper().strip()

        if st.button("🚀 클래스 입장", type="primary",
                     use_container_width=True, key="cls_join_btn"):
            if len(code_input) != 6:
                st.error("코드는 6자리예요.")
            else:
                try:
                    ok, msg = join_class(student_id, code_input)
                    if ok:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.warning(msg)
                except Exception as e:
                    _handle_table_error(e)

    # ── 탭2: 내 클래스 ────────────────────────────────────────────
    with tab_my:
        try:
            my_classes = get_classes_by_student(student_id)
        except Exception as e:
            _handle_table_error(e)
            return

        if not my_classes:
            st.markdown(f"""
<div style="text-align:center;padding:40px;background:#f0fdf4;border-radius:14px;
     border:2px dashed #bbf7d0;">
  <div style="margin-bottom:8px;">{icon("people", 52, "#059669")}</div>
  <div style="font-weight:700;color:#059669;font-size:1.1rem;margin-top:8px;">
    가입한 클래스가 없어요
  </div>
  <div style="color:#9ca3af;font-size:0.9rem;margin-top:4px;">
    '코드 입장' 탭에서 선생님 코드를 입력해보세요!
  </div>
</div>
""", unsafe_allow_html=True)
        else:
            for cls in my_classes:
                cls_id     = cls.get("id")
                cls_name   = cls.get("name", "클래스")
                cls_code   = cls.get("class_code", "")
                joined     = (cls.get("joined_at") or "")[:10]

                with st.expander(f"🏫 {cls_name} ({cls_code})", expanded=True):
                    st.caption(f"가입일: {joined}")
                    if cls.get("description"):
                        st.caption(cls["description"])

                    # 선생님이 공유한 노트 목록
                    try:
                        shared = get_class_notes(cls_id)
                    except Exception:
                        shared = []

                    if not shared:
                        st.info("아직 선생님이 노트를 배포하지 않았어요.")
                    else:
                        st.markdown(f"**선생님 공유 노트 {len(shared)}개**")
                        for s in shared:
                            note_match = next(
                                (n for n in notes if n.get("id") == s["note_id"]), None
                            )
                            if note_match:
                                title    = note_match.get("title", "노트")
                                shared_dt = (s.get("shared_at") or "")[:10]
                                st.markdown(f"""
<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
     padding:10px 14px;margin:4px 0;font-size:0.85rem;">
  📄 <b>{title}</b>
  <span style="color:#94a3b8;margin-left:8px;">{shared_dt} 배포</span>
</div>
""", unsafe_allow_html=True)

                    # 클래스 탈퇴
                    if st.button(f"클래스 탈퇴", key=f"leave_{cls_id}",
                                  use_container_width=False):
                        remove_member(cls_id, student_id)
                        st.success("클래스를 탈퇴했어요.")
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 에러 핸들러
# ─────────────────────────────────────────────────────────────────────────────

def _handle_table_error(e: Exception):
    err = str(e)
    if "does not exist" in err or "42P01" in err:
        st.error(
            "❌ **Supabase 테이블 미설치** — 클래스 기능을 사용하려면 DB를 업데이트하세요.\n\n"
            "**해결**: Supabase 대시보드 > SQL Editor 에서 "
            "`supabase_migration_v4.sql` 내용을 붙여넣고 **Run** 클릭"
        )
    else:
        st.error(f"오류 발생: {err}")
