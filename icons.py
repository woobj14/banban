# icons.py — Lucide 아이콘 인라인 SVG 헬퍼

_P: dict[str, str] = {
    # ── 네비게이션 ──────────────────────────────────────────
    "book-open":      ('<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
                       '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 0 3-3h7z"/>'),
    "plus-circle":    ('<circle cx="12" cy="12" r="10"/>'
                       '<line x1="12" x2="12" y1="8" y2="16"/>'
                       '<line x1="8" x2="16" y1="12" y2="12"/>'),
    "layers":         ('<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83'
                       'l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>'
                       '<path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/>'
                       '<path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>'),
    # ── 파일 / 저장 ────────────────────────────────────────
    "download":       ('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>'
                       '<polyline points="7 10 12 15 17 10"/>'
                       '<line x1="12" x2="12" y1="15" y2="3"/>'),
    "save":           ('<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
                       '<polyline points="17 21 17 13 7 13 7 21"/>'
                       '<polyline points="7 3 7 8 15 8"/>'),
    "file-text":      ('<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
                       '<polyline points="14 2 14 8 20 8"/>'
                       '<line x1="16" x2="8" y1="13" y2="13"/>'
                       '<line x1="16" x2="8" y1="17" y2="17"/>'
                       '<line x1="10" x2="8" y1="9" y2="9"/>'),
    # ── 콘텐츠 유형 ────────────────────────────────────────
    "message-circle": '<path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z"/>',
    "book":           '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    "eye":            ('<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>'
                       '<circle cx="12" cy="12" r="3"/>'),
    "pencil":         ('<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>'
                       '<path d="m15 5 4 4"/>'),
    # ── 동작 ───────────────────────────────────────────────
    "trash-2":        ('<path d="M3 6h18"/>'
                       '<path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>'
                       '<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>'
                       '<line x1="10" x2="10" y1="11" y2="17"/>'
                       '<line x1="14" x2="14" y1="11" y2="17"/>'),
    "search":         ('<circle cx="11" cy="11" r="8"/>'
                       '<path d="m21 21-4.35-4.35"/>'),
    "filter":         '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "arrow-right":    ('<path d="M5 12h14"/>'
                       '<path d="m12 5 7 7-7 7"/>'),
    "refresh-cw":     ('<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
                       '<path d="M21 3v5h-5"/>'
                       '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
                       '<path d="M8 16H3v5"/>'),
    # ── 이미지 / 스캔 ──────────────────────────────────────
    "camera":         ('<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16'
                       'a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/>'
                       '<circle cx="12" cy="13" r="3"/>'),
    "image":          ('<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>'
                       '<circle cx="9" cy="9" r="2"/>'
                       '<path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>'),
    "scan":           ('<path d="M3 7V5a2 2 0 0 1 2-2h2"/>'
                       '<path d="M17 3h2a2 2 0 0 1 2 2v2"/>'
                       '<path d="M21 17v2a2 2 0 0 1-2 2h-2"/>'
                       '<path d="M7 21H5a2 2 0 0 1-2-2v-2"/>'),
    "wand-2":         ('<path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0'
                       'L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28'
                       'a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/>'
                       '<path d="m14 7 3 3"/>'),
    # ── 상태 / UI ──────────────────────────────────────────
    "check-circle":   ('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
                       '<polyline points="22 4 12 14.01 9 11.01"/>'),
    "x-circle":       ('<circle cx="12" cy="12" r="10"/>'
                       '<path d="m15 9-6 6"/>'
                       '<path d="m9 9 6 6"/>'),
    "check-square":   ('<polyline points="9 11 12 14 22 4"/>'
                       '<path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'),
    "square":         '<rect width="18" height="18" x="3" y="3" rx="2"/>',
    "info":           ('<circle cx="12" cy="12" r="10"/>'
                       '<path d="M12 16v-4"/>'
                       '<path d="M12 8h.01"/>'),
    "tag":            ('<path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0'
                       'l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/>'
                       '<path d="M7 7h.01"/>'),
    "clipboard":      ('<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/>'
                       '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6'
                       'a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>'),
    "graduation-cap": ('<path d="M22 10v6M2 10l10-5 10 5-10 5z"/>'
                       '<path d="M6 12v5c3 3 9 3 12 0v-5"/>'),
    "sparkles":       ('<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275'
                       'L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275'
                       'L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275'
                       'L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/>'
                       '<path d="M5 3v4"/><path d="M19 17v4"/>'
                       '<path d="M3 5h4"/><path d="M17 19h4"/>'),
    "merge":          ('<circle cx="18" cy="18" r="3"/>'
                       '<circle cx="6" cy="6" r="3"/>'
                       '<path d="M6 21V9a9 9 0 0 0 9 9"/>'),
    "list":           ('<line x1="8" x2="21" y1="6" y2="6"/>'
                       '<line x1="8" x2="21" y1="12" y2="12"/>'
                       '<line x1="8" x2="21" y1="18" y2="18"/>'
                       '<line x1="3" x2="3.01" y1="6" y2="6"/>'
                       '<line x1="3" x2="3.01" y1="12" y2="12"/>'
                       '<line x1="3" x2="3.01" y1="18" y2="18"/>'),
    # ── 학습 시스템 전용 ────────────────────────────────────────
    "cloud-upload":   ('<polyline points="16 16 12 12 8 16"/>'
                       '<line x1="12" x2="12" y1="12" y2="21"/>'
                       '<path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26'
                       'A8 8 0 1 0 3 16.3"/>'),
    "alert-circle":   ('<circle cx="12" cy="12" r="10"/>'
                       '<line x1="12" x2="12" y1="8" y2="12"/>'
                       '<line x1="12" x2="12.01" y1="16" y2="16"/>'),
    "zap":            '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "sliders":        ('<line x1="4" x2="4" y1="21" y2="14"/>'
                       '<line x1="4" x2="4" y1="10" y2="3"/>'
                       '<line x1="12" x2="12" y1="21" y2="12"/>'
                       '<line x1="12" x2="12" y1="8" y2="3"/>'
                       '<line x1="20" x2="20" y1="21" y2="16"/>'
                       '<line x1="20" x2="20" y1="12" y2="3"/>'
                       '<line x1="1" x2="7" y1="14" y2="14"/>'
                       '<line x1="9" x2="15" y1="8" y2="8"/>'
                       '<line x1="17" x2="23" y1="16" y2="16"/>'),
    "award":          ('<circle cx="12" cy="8" r="6"/>'
                       '<path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>'),
    "target":         ('<circle cx="12" cy="12" r="10"/>'
                       '<circle cx="12" cy="12" r="6"/>'
                       '<circle cx="12" cy="12" r="2"/>'),
    "user":           ('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
                       '<circle cx="12" cy="7" r="4"/>'),
    "rotate-ccw":     ('<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
                       '<path d="M3 3v5h5"/>'),
    "flip-horizontal":('<path d="M8 3H5a2 2 0 0 0-2 2v14c0 1.1.9 2 2 2h3"/>'
                       '<path d="M16 3h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-3"/>'
                       '<path d="M12 20v2"/>'
                       '<path d="M12 14v2"/>'
                       '<path d="M12 8v2"/>'
                       '<path d="M12 2v2"/>'),
    "database":        ('<ellipse cx="12" cy="5" rx="9" ry="3"/>'
                        '<path d="M3 5v14a9 3 0 0 0 18 0V5"/>'
                        '<path d="M3 12a9 3 0 0 0 18 0"/>'),
    "bar-chart-2":     ('<line x1="18" x2="18" y1="20" y2="10"/>'
                        '<line x1="12" x2="12" y1="20" y2="4"/>'
                        '<line x1="6" x2="6" y1="20" y2="14"/>'),
    "star":            '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    # ── 인증 / 관리자 ───────────────────────────────────────────
    "flower":           ('<path d="M12 7.5a4.5 4.5 0 1 1 4.5 4.5'
                         'M12 7.5A4.5 4.5 0 1 0 7.5 12M12 7.5V9'
                         'm-4.5 3a4.5 4.5 0 1 0 4.5 4.5M7.5 12H9'
                         'm7.5 0a4.5 4.5 0 1 1-4.5 4.5m4.5-4.5H15'
                         'm-3 4.5V15"/>'
                         '<circle cx="12" cy="12" r="3"/>'),
    "lock":             ('<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/>'
                         '<path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
    "mail":             ('<rect width="20" height="16" x="2" y="4" rx="2"/>'
                         '<path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>'),
    "log-in":           ('<path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>'
                         '<polyline points="10 17 15 12 10 7"/>'
                         '<line x1="15" x2="3" y1="12" y2="12"/>'),
    "log-out":          ('<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
                         '<polyline points="16 17 21 12 16 7"/>'
                         '<line x1="21" x2="9" y1="12" y2="12"/>'),
    "shield":           '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "volume-2":         ('<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>'
                         '<path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>'
                         '<path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>'),
    "moon":             '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "sunrise":          ('<path d="M12 2v8"/><path d="m4.93 10.93 1.41 1.41"/>'
                         '<path d="M2 18h2"/><path d="M20 18h2"/>'
                         '<path d="m19.07 10.93-1.41 1.41"/><path d="M22 22H2"/>'
                         '<path d="m8 6 4-4 4 4"/><path d="M16 18a4 4 0 0 0-8 0"/>'),
    "sunset":           ('<path d="M12 10V2"/><path d="m4.93 10.93 1.41 1.41"/>'
                         '<path d="M2 18h2"/><path d="M20 18h2"/>'
                         '<path d="m19.07 10.93-1.41 1.41"/><path d="M22 22H2"/>'
                         '<path d="m16 6-4 4-4-4"/><path d="M16 18a4 4 0 0 0-8 0"/>'),
    "trending-up":      ('<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>'
                         '<polyline points="16 7 22 7 22 13"/>'),
    "calendar":         ('<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/>'
                         '<line x1="16" x2="16" y1="2" y2="6"/>'
                         '<line x1="8" x2="8" y1="2" y2="6"/>'
                         '<line x1="3" x2="21" y1="10" y2="10"/>'),
    "clock":            ('<circle cx="12" cy="12" r="10"/>'
                         '<polyline points="12 6 12 12 16 14"/>'),
    "alert-triangle":   ('<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
                         '<line x1="12" x2="12" y1="9" y2="13"/>'
                         '<line x1="12" x2="12.01" y1="17" y2="17"/>'),
    "party-popper":     ('<path d="M5.8 11.3 2 22l10.7-3.79"/>'
                         '<path d="M4 3h.01"/><path d="M22 8h.01"/><path d="M15 2h.01"/>'
                         '<path d="M22 20h.01"/>'
                         '<path d="m22 2-2.24.75a2.9 2.9 0 0 0-1.96 3.12c.1.86-.57 1.63-1.45 1.63h-.38c-.86 0-1.6.6-1.76 1.44L12 10"/>'
                         '<path d="m22 13-.82-.33c-.86-.34-1.82.2-1.98 1.11c-.11.7-.72 1.22-1.43 1.22H17"/>'
                         '<path d="m11 2 .33.82c.34.86-.2 1.82-1.11 1.98C9.52 4.9 9 5.52 9 6.23V7"/>'
                         '<path d="M11 13c1.93 1.93 2.83 4.17 2 5-.83.83-3.07-.07-5-2-1.93-1.93-2.83-4.17-2-5 .83-.83 3.07.07 5 2Z"/>'),
    "settings":         ('<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1'
                         ' 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73'
                         'l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51'
                         'a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38'
                         'a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25'
                         'a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18'
                         'a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08'
                         'a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08'
                         'a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09'
                         'a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08'
                         'a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>'
                         '<circle cx="12" cy="12" r="3"/>'),
    "printer":          ('<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>'
                         '<path d="M6 9V2h12v7"/>'
                         '<rect x="6" y="14" width="12" height="8" rx="1"/>'),
    "bookmark":         ('<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>'),
    "users":            ('<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
                         '<circle cx="9" cy="7" r="4"/>'
                         '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
                         '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
    "trophy":           ('<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>'
                         '<path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>'
                         '<path d="M4 22h16"/>'
                         '<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>'
                         '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>'
                         '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>'),
    "arrow-counterclockwise": ('<path d="M3 2v6h6"/>'
                         '<path d="M3 8a9 9 0 1 0 2.83-6.36L3 8"/>'),
    "pencil-square":    ('<path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
                         '<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4Z"/>'),
}


def icon(name: str, size: int = 18, color: str = "currentColor") -> str:
    """Lucide 아이콘 인라인 SVG 반환.
    unsafe_allow_html=True 인 st.markdown() 블록에서 사용.
    """
    paths = _P.get(name, _P["info"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="vertical-align:middle;margin-right:6px;'
        f'display:inline-block;flex-shrink:0;">'
        f'{paths}</svg>'
    )


# ─────────────────────────────────────────────────────────────────────────────
# 표준 태그(칩) — CRM 키트 스타일. 전 페이지 공통 사용
# ─────────────────────────────────────────────────────────────────────────────

# 의미별 색상 프리셋 (배경, 글자)
_TAG_TONES = {
    "indigo": ("#EEF2FF", "#4338CA"),
    "cyan":   ("#E0F2FE", "#075985"),
    "violet": ("#F5F3FF", "#6D28D9"),
    "green":  ("#F0FDF4", "#15803D"),
    "amber":  ("#FFFBEB", "#B45309"),
    "red":    ("#FEF2F2", "#B91C1C"),
    "gray":   ("#F1F3F7", "#475569"),
    "teal":   ("#F0FDFA", "#0F766E"),
}

# content_type → tone 매핑 (앱 전역 일관)
_CTYPE_TONE = {"단어": "cyan", "대화문": "violet", "본문": "green", "전체": "indigo"}


def tag(text: str, tone: str = "gray", icon_name: str = "") -> str:
    """표준 pill 태그 HTML. unsafe_allow_html=True 블록에서 사용."""
    bg, fg = _TAG_TONES.get(tone, _TAG_TONES["gray"])
    ic = (icon(icon_name, 11, fg) if icon_name else "")
    gap = "gap:4px;" if icon_name else ""
    return (
        f'<span style="display:inline-flex;align-items:center;{gap}'
        f'background:{bg};color:{fg};border-radius:20px;padding:3px 11px;'
        f'font-size:0.72rem;font-weight:700;line-height:1.4;white-space:nowrap;">'
        f'{ic}{text}</span>'
    )


def ctype_tag(content_type: str) -> str:
    """content_type 전용 표준 태그 (단어/대화문/본문/전체)."""
    return tag(content_type, _CTYPE_TONE.get(content_type, "indigo"))


def tag_row(tags: list, gap: int = 6) -> str:
    """여러 태그를 flex-wrap 칩 행으로. tags: [str | (text, tone) | (text, tone, icon)]"""
    chips = ""
    for t in tags:
        if isinstance(t, (list, tuple)):
            chips += tag(*t)
        else:
            chips += tag(str(t))
    return (f'<div style="display:flex;flex-wrap:wrap;gap:{gap}px;'
            f'align-items:center;">{chips}</div>')


def title_md(icon_name: str, text: str,
             size: int = 30, color: str = "#1a4fa0") -> str:
    """페이지 제목용 아이콘 + 텍스트 HTML"""
    return (
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
        f'{icon(icon_name, size, color)}'
        f'<span style="font-size:1.9rem;font-weight:800;color:{color};'
        f'line-height:1.2;">{text}</span>'
        f'</div>'
    )


def section_md(icon_name: str, text: str,
               size: int = 20, color: str = "#1a4fa0") -> str:
    """섹션 헤더용 아이콘 + 텍스트 HTML"""
    return (
        f'<div style="display:flex;align-items:center;gap:6px;'
        f'margin:1rem 0 0.4rem 0;">'
        f'{icon(icon_name, size, color)}'
        f'<span style="font-size:1.15rem;font-weight:700;color:#1f2937;">'
        f'{text}</span>'
        f'</div>'
    )


def confirm_delete_btn(
    label: str,
    key: str,
    item_name: str = "",
    use_container_width: bool = True,
    btn_type: str = "secondary",
) -> bool:
    """2단계 삭제 확인 버튼.

    사용법::

        if confirm_delete_btn("삭제", key=f"del_{nid}", item_name=note_title):
            delete_note(nid)
            st.rerun()

    - 1차 클릭: 인라인 확인 UI 표시
    - 2차 '삭제' 클릭: True 반환 → 호출부에서 실제 삭제 수행
    - '취소' 클릭: 원래 버튼으로 복귀
    """
    import streamlit as st

    confirm_key = f"_cdel_{key}"

    if not st.session_state.get(confirm_key, False):
        # ── 1단계: 일반 삭제 버튼 ────────────────────────────
        if st.button(label, key=key,
                     use_container_width=use_container_width,
                     type=btn_type):
            st.session_state[confirm_key] = True
            st.rerun()
        return False

    # ── 2단계: 인라인 확인 팝업 ──────────────────────────────
    name_part = f"<b>'{item_name}'</b> " if item_name else ""
    st.markdown(
        f'<div style="background:#FEF2F2;border:1.5px solid #FCA5A5;'
        f'border-radius:10px;padding:10px 12px;margin:4px 0 6px 0;">'
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
        f'viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 '
        f'1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
        f'<line x1="12" x2="12" y1="9" y2="13"/>'
        f'<line x1="12" x2="12.01" y1="17" y2="17"/>'
        f'</svg>'
        f'<span style="font-size:0.82rem;font-weight:700;color:#991B1B;">'
        f'{name_part}삭제하면 복구할 수 없습니다.</span>'
        f'</div>'
        f'<div style="font-size:0.78rem;color:#B91C1C;">정말 삭제하시겠습니까?</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    confirmed = c1.button(
        "삭제", key=f"{key}_yes",
        type="primary", use_container_width=True,
    )
    cancelled = c2.button(
        "취소", key=f"{key}_no",
        use_container_width=True,
    )

    if cancelled:
        st.session_state[confirm_key] = False
        st.rerun()
    if confirmed:
        st.session_state[confirm_key] = False
        return True
    return False
