#!/usr/bin/env python3
"""Build readable HTML views of all WhatsApp chat exports + landing page.

Auto-discovers any folder named ``WhatsApp Chat - <name>`` that contains
``_chat.txt`` and generates one HTML page per chat plus an ``index.html``
hub. No code changes needed when new chat folders are dropped in.
"""
import re
import html
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
CHAT_PREFIXES = (
    "WhatsApp Chat - ",          # iOS export, English locale
    "Чат WhatsApp с контактом ",  # Android export, Russian locale
)
ME_NAMES = {"🌏", "Андрей"}  # any of these is rendered on right as "me"

LRM = "‎"

# iOS:     [9/3/68, 13:41:40] ~PARINTON: text  (Buddhist year, brackets, seconds)
MSG_RE_IOS = re.compile(
    r'^‎?\[(\d{1,2})/(\d{1,2})/(\d{2,4}),\s*(\d{1,2}):(\d{2}):(\d{2})\]\s+([^:]+?):\s?(.*)$'
)
# Android: 24.12.2025, 03:13 - Sender: text  (full year, dots, no seconds, sender optional)
MSG_RE_ANDROID = re.compile(
    r'^‎?(\d{1,2})\.(\d{1,2})\.(\d{4}),\s*(\d{1,2}):(\d{2})\s*-\s*(?:([^:]{1,80}?):\s)?(.*)$'
)
ATTACH_RE_IOS = re.compile(r'‎?<прикреплено:\s*([^>]+)>')
ATTACH_RE_ANDROID = re.compile(r'‎?([^\n]+?)\s*\(файл добавлен\)')
PREFIX_RE = re.compile(r'^\d+-')
URL_RE = re.compile(r'(https?://[^\s<>"]+)')

MONTHS_RU_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня",
                 "июля", "августа", "сентября", "октября", "ноября", "декабря"]
MONTHS_RU_NOM = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                 "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
MONTHS_TH = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
             "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
BUDDHIST_OFFSET = 543

I18N_RU = {
    "archive_title": "WhatsApp архив",
    "all_chats": "Все чаты",
    "back_all": "‹ Все чаты",
    "home": "На главную",
    "menu": "Меню",
    "open_menu": "Открыть меню",
    "close": "Закрыть",
    "tab_messages": "Сообщения",
    "tab_media": "Медиа",
    "tab_docs": "Документы",
    "lbl_messages": "сообщений",
    "lbl_days": "дней",
    "lbl_media": "медиа",
    "lbl_chats": "чатов",
    "lbl_messages_short": "сообщ.",
    "lbl_days_short": "дн.",
    "personal_chat": "Личный чат",
    "group": "Группа",
    "filter_hint": "Выберите день — остальные сообщения скроются.",
    "no_messages_day": "За выбранный день нет сообщений.",
    "no_media": "В этом чате нет фото и видео.",
    "no_docs": "В этом чате нет документов и аудио.",
    "select_date": "Выбрать дату",
    "all_dates": "Все даты",
    "reset": "Сброс",
    "select_chat_hint": "Выберите чат для просмотра",
    "lang_label": "Язык",
    "more": "ещё",
}

I18N_TH = {
    "archive_title": "คลัง WhatsApp",
    "all_chats": "แชททั้งหมด",
    "back_all": "‹ แชททั้งหมด",
    "home": "หน้าแรก",
    "menu": "เมนู",
    "open_menu": "เปิดเมนู",
    "close": "ปิด",
    "tab_messages": "ข้อความ",
    "tab_media": "สื่อ",
    "tab_docs": "เอกสาร",
    "lbl_messages": "ข้อความ",
    "lbl_days": "วัน",
    "lbl_media": "สื่อ",
    "lbl_chats": "แชท",
    "lbl_messages_short": "ข้อความ",
    "lbl_days_short": "วัน",
    "personal_chat": "แชทส่วนตัว",
    "group": "กลุ่ม",
    "filter_hint": "เลือกวัน — ข้อความที่เหลือจะถูกซ่อน",
    "no_messages_day": "ไม่มีข้อความในวันที่เลือก",
    "no_media": "ไม่มีรูปภาพหรือวิดีโอในแชทนี้",
    "no_docs": "ไม่มีเอกสารหรือไฟล์เสียงในแชทนี้",
    "select_date": "เลือกวันที่",
    "all_dates": "วันที่ทั้งหมด",
    "reset": "รีเซ็ต",
    "select_chat_hint": "เลือกแชทเพื่อดู",
    "lang_label": "ภาษา",
    "more": "อีก",
}


def i18n(key: str) -> str:
    """Render a static UI string in both languages (CSS toggles which is shown)."""
    ru = html.escape(I18N_RU[key])
    th = html.escape(I18N_TH[key])
    return (f'<span class="i18n">'
            f'<span data-l="ru">{ru}</span>'
            f'<span data-l="th">{th}</span>'
            f'</span>')


def i18n_text(ru: str, th: str) -> str:
    return (f'<span class="i18n">'
            f'<span data-l="ru">{html.escape(ru)}</span>'
            f'<span data-l="th">{html.escape(th)}</span>'
            f'</span>')

SYSTEM_PATTERNS = (
    "сквозным шифрованием",
    "создал(-а) группу",
    "добавил(-а) вас",
    "добавил(-а)",
    "изменил(-а) картинку группы",
    "изменил(-а) название группы",
    "изменил(-а) описание группы",
    "удалил(-а)",
    "вышел(-а)",
    "присоединился",
    "присоединилась",
)

SENDER_NAME_COLORS = [
    "#1f7a8c", "#c8541f", "#5e4ec8", "#2d8659",
    "#a14545", "#a87800", "#1f5fc8", "#8e44ad",
    "#16a085", "#d35400", "#7f8c8d", "#c0392b",
]

CYRILLIC_TR = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'e','ж':'zh',
    'з':'z','и':'i','й':'i','к':'k','л':'l','м':'m','н':'n','о':'o',
    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts',
    'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}


def slugify(name: str) -> str:
    s = name.lower()
    out = []
    for ch in s:
        out.append(CYRILLIC_TR.get(ch, ch))
    s = "".join(out)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "chat"


def detect_format(raw: str) -> str:
    head = raw[:2000]
    if re.search(r'^‎?\[\d{1,2}/\d{1,2}/\d{2,4},', head, re.MULTILINE):
        return "ios"
    if re.search(r'^‎?\d{1,2}\.\d{1,2}\.\d{4},', head, re.MULTILINE):
        return "android"
    return "ios"


def parse_messages(txt_path: Path, fmt: str = None):
    raw = txt_path.read_text(encoding="utf-8")
    if fmt is None:
        fmt = detect_format(raw)
    regex = MSG_RE_ANDROID if fmt == "android" else MSG_RE_IOS

    msgs = []
    cur = None
    for line in raw.splitlines():
        m = regex.match(line)
        if m:
            if cur is not None:
                msgs.append(cur)
            if fmt == "android":
                d, mo, y, h, mi, sender, body = m.groups()
                second = 0
                year = int(y)
            else:
                d, mo, y, h, mi, s, sender, body = m.groups()
                second = int(s)
                year = int(y)
                if year < 100:
                    year += 1957  # Buddhist 2-digit -> Gregorian (2568 -> 2025)
            if sender is not None:
                cleaned_sender = sender.strip().lstrip("~").strip()
            else:
                cleaned_sender = ""  # system event with no explicit sender
            cur = {
                "d": int(d), "m": int(mo), "y": year,
                "hh": int(h), "mm": int(mi), "ss": second,
                "sender": cleaned_sender,
                "body": body,
            }
        else:
            if cur is not None:
                cur["body"] += "\n" + line
    if cur is not None:
        msgs.append(cur)
    return msgs


def find_txt(folder: Path):
    """Return the chat txt path for a folder, or None."""
    candidate = folder / "_chat.txt"
    if candidate.exists():
        return candidate
    txts = sorted(folder.glob("*.txt"))
    return txts[0] if txts else None


def folder_display_name(folder_name: str) -> str:
    """Return the chat name with prefix stripped, preserving original whitespace.

    Whitespace must stay as-is so system_sender matching against actual
    senders (e.g. group names with double spaces) keeps working.
    """
    normalized = _normalize_ws(folder_name)
    for prefix in CHAT_PREFIXES:
        if normalized.startswith(prefix):
            return folder_name[len(prefix):].strip()
    return folder_name.strip()


def media_kind(fname: str) -> str:
    f = fname.lower()
    if "sticker" in f and f.endswith((".webp", ".png", ".gif")):
        return "sticker"
    if f.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic")):
        return "image"
    if f.endswith((".mp4", ".mov", ".webm", ".m4v")):
        return "video"
    if f.endswith((".opus", ".mp3", ".m4a", ".wav", ".ogg", ".aac")):
        return "audio"
    if f.endswith(".pdf"):
        return "pdf"
    if f.endswith(".vcf"):
        return "vcf"
    if f.endswith((".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx")):
        return "office"
    if f.endswith((".zip", ".rar", ".7z", ".tar", ".gz")):
        return "archive"
    return "file"


def render_attachment(fname: str, chat_dir_name: str) -> str:
    kind = media_kind(fname)
    href = quote(f"{chat_dir_name}/{fname}")
    display_name = PREFIX_RE.sub("", fname)
    nm = html.escape(display_name)
    if kind == "sticker":
        return f'<img class="sticker" loading="lazy" src="{href}" alt="">'
    if kind == "image":
        return (f'<a class="img-link" href="{href}" target="_blank">'
                f'<img class="photo" loading="lazy" src="{href}" alt=""></a>')
    if kind == "video":
        return f'<video class="video" controls preload="none" src="{href}"></video>'
    if kind == "audio":
        return f'<audio class="audio" controls preload="none" src="{href}"></audio>'
    if kind == "pdf":
        return (f'<a class="file pdf" href="{href}" target="_blank">'
                f'<span class="file-icon">📄</span>'
                f'<span class="file-name">{nm}</span></a>')
    if kind == "vcf":
        return (f'<a class="file vcf" href="{href}" target="_blank">'
                f'<span class="file-icon">👤</span>'
                f'<span class="file-name">{nm}</span></a>')
    if kind == "office":
        return (f'<a class="file office" href="{href}" target="_blank">'
                f'<span class="file-icon">📝</span>'
                f'<span class="file-name">{nm}</span></a>')
    if kind == "archive":
        return (f'<a class="file archive" href="{href}" target="_blank">'
                f'<span class="file-icon">🗜️</span>'
                f'<span class="file-name">{nm}</span></a>')
    return (f'<a class="file" href="{href}" target="_blank">'
            f'<span class="file-icon">📎</span>'
            f'<span class="file-name">{nm}</span></a>')


def render_text(text: str) -> str:
    text = text.replace(LRM, "").strip()
    if not text:
        return ""
    escaped = html.escape(text)
    escaped = URL_RE.sub(r'<a href="\g<1>" target="_blank" rel="noopener">\g<1></a>', escaped)
    escaped = escaped.replace("\n", "<br>")
    return escaped


def date_key(msg) -> str:
    return f"{msg['y']}-{msg['m']:02d}-{msg['d']:02d}"


def fmt_date(msg) -> str:
    """Bilingual full date — '9 марта 2025' / '9 มีนาคม 2568'."""
    ru = f"{msg['d']} {MONTHS_RU_GEN[msg['m'] - 1]} {msg['y']}"
    th = f"{msg['d']} {MONTHS_TH[msg['m'] - 1]} {msg['y'] + BUDDHIST_OFFSET}"
    return i18n_text(ru, th)


def fmt_iso_date(iso: str) -> str:
    y, m, d = iso.split("-")
    ru = f"{int(d)} {MONTHS_RU_GEN[int(m) - 1]} {y}"
    th = f"{int(d)} {MONTHS_TH[int(m) - 1]} {int(y) + BUDDHIST_OFFSET}"
    return i18n_text(ru, th)


def fmt_day_month(iso: str) -> str:
    """Day + month (no year) for date chips."""
    y, m, d = iso.split("-")
    ru = f"{int(d)} {MONTHS_RU_GEN[int(m) - 1]}"
    th = f"{int(d)} {MONTHS_TH[int(m) - 1]}"
    return i18n_text(ru, th)


def fmt_month_year(ym: str) -> str:
    y, m = ym.split("-")
    ru = f"{MONTHS_RU_NOM[int(m) - 1]} {y}"
    th = f"{MONTHS_TH[int(m) - 1]} {int(y) + BUDDHIST_OFFSET}"
    return i18n_text(ru, th)


def fmt_time(msg) -> str:
    return f"{msg['hh']:02d}:{msg['mm']:02d}"


def count_label(n: int, key: str) -> str:
    """Render count + i18n word, e.g. '3458 сообщений' / '3458 ข้อความ'."""
    return f'{n} {i18n(key)}'


def is_group_system(text: str, attachments) -> bool:
    if attachments or not text:
        return False
    return any(p in text for p in SYSTEM_PATTERNS)


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s)


def discover_chats():
    found = []
    for entry in sorted(ROOT.iterdir()):
        if not entry.is_dir():
            continue
        normalized = _normalize_ws(entry.name)
        if not any(normalized.startswith(p) for p in CHAT_PREFIXES):
            continue
        txt = find_txt(entry)
        if not txt:
            continue
        raw = txt.read_text(encoding="utf-8")
        fmt = detect_format(raw)
        msgs = parse_messages(txt, fmt)
        if not msgs:
            continue
        found.append(make_chat_config(entry, msgs, fmt))
    return found


def make_chat_config(folder: Path, msgs: list, fmt: str) -> dict:
    name = folder_display_name(folder.name)
    slug = slugify(name)

    senders_seen = []
    seen = set()
    for m in msgs:
        s = m["sender"]
        if not s or s in seen:
            continue
        seen.add(s)
        senders_seen.append(s)

    system_candidate = name if name in seen else None
    other = [s for s in senders_seen
             if s not in ME_NAMES and s != system_candidate]
    is_group = len(other) >= 2

    if is_group:
        icon = "👥"
        names_str = ", ".join(other[:3])
        if len(other) > 3:
            names_str += f" +{len(other) - 3}"
        subtitle_other = names_str
        subtitle_kind = "group"
        system_sender = system_candidate
    else:
        icon = "👤"
        system_sender = None
        subtitle_kind = "personal"
        subtitle_other = other[0] if other else None

    return {
        "dir": folder.name,
        "out": f"{slug}.html",
        "title": name,
        "subtitle_kind": subtitle_kind,
        "subtitle_other": subtitle_other,
        "icon": icon,
        "system_sender": system_sender,
        "is_group": is_group,
        "fmt": fmt,
        "msgs": msgs,
    }


def render_subtitle(chat: dict) -> str:
    prefix = i18n("personal_chat" if chat["subtitle_kind"] == "personal" else "group")
    other = chat["subtitle_other"]
    if other:
        return f'{prefix} · {html.escape(other)}'
    return prefix


DOC_KINDS = {"pdf", "vcf", "office", "archive", "audio", "file"}
GALLERY_KINDS = {"image", "video", "sticker"}
DOC_ICONS = {"pdf": "📄", "vcf": "👤", "office": "📝",
             "archive": "🗜️", "audio": "🎙", "file": "📎"}


def collect_data(chat: dict) -> dict:
    """Walk messages once, return everything renderers need."""
    msgs = chat["msgs"]
    attach_re = ATTACH_RE_ANDROID if chat["fmt"] == "android" else ATTACH_RE_IOS

    senders_seen = OrderedDict()
    for m in msgs:
        s = m["sender"]
        if not s or s in ME_NAMES:
            continue
        if chat["system_sender"] and s == chat["system_sender"]:
            continue
        senders_seen.setdefault(s, True)
    other_senders = list(senders_seen.keys())
    sender_color = {s: SENDER_NAME_COLORS[i % len(SENDER_NAME_COLORS)]
                    for i, s in enumerate(other_senders)}

    rendered_msgs = []
    day_count = {}
    media_items = []
    doc_items = []

    for m in msgs:
        body = m["body"]
        attachments = attach_re.findall(body)
        text_only = attach_re.sub("", body).strip().replace(LRM, "").strip()

        is_sys = False
        if not m["sender"]:
            is_sys = True
        elif chat["system_sender"] and m["sender"] == chat["system_sender"]:
            is_sys = True
        elif is_group_system(text_only, attachments):
            is_sys = True

        if not text_only and not attachments and not is_sys:
            continue

        rendered_msgs.append((m, attachments, text_only, is_sys))
        if not is_sys:
            day_count[date_key(m)] = day_count.get(date_key(m), 0) + 1
            for fname in attachments:
                kind = media_kind(fname)
                item = {
                    "date": date_key(m),
                    "date_label": fmt_date(m),
                    "time": fmt_time(m),
                    "sender": m["sender"],
                    "kind": kind,
                    "fname": fname,
                }
                if kind in GALLERY_KINDS:
                    media_items.append(item)
                else:
                    doc_items.append(item)

    sorted_days = sorted(day_count.keys())
    return {
        "rendered_msgs": rendered_msgs,
        "day_count": day_count,
        "sorted_days": sorted_days,
        "min_date": sorted_days[0] if sorted_days else "",
        "max_date": sorted_days[-1] if sorted_days else "",
        "media_items": media_items,
        "doc_items": doc_items,
        "other_senders": other_senders,
        "sender_color": sender_color,
        "msg_count": len(rendered_msgs),
    }


def render_drawer(current_chat: dict, all_chats: list) -> str:
    parts = ['<aside id="nav-drawer" hidden data-i18n-aria="menu" aria-label="Меню">']
    parts.append('<div class="drawer-h">')
    parts.append(f'<div class="drawer-title">{i18n("archive_title")}</div>')
    parts.append('<button id="navClose" class="icon-btn" '
                 'data-i18n-aria="close" aria-label="Закрыть">✕</button>')
    parts.append('</div>')
    parts.append('<a class="drawer-home" href="index.html">'
                 f'<span class="dh-icon">🏠</span>{i18n("home")}</a>')
    parts.append(f'<div class="drawer-section">{i18n("all_chats")}</div>')
    parts.append('<nav class="drawer-chats">')
    for c in all_chats:
        is_active = c is current_chat
        href = quote(c["out"])
        title = html.escape(c["title"])
        msg_count = c["data"]["msg_count"]
        days = len(c["data"]["sorted_days"])
        active_cls = " active" if is_active else ""
        meta = (f'{msg_count} {i18n("lbl_messages_short")} · '
                f'{days} {i18n("lbl_days_short")}')
        parts.append(
            f'<a href="{href}" class="drawer-chat{active_cls}">'
            f'<span class="dc-icon">{c["icon"]}</span>'
            f'<span class="dc-info">'
            f'<span class="dc-name">{title}</span>'
            f'<span class="dc-meta">{meta}</span>'
            f'</span>'
            f'</a>'
        )
    parts.append('</nav>')
    parts.append(render_lang_switch_drawer())
    parts.append('</aside>')
    parts.append('<div id="nav-backdrop" hidden></div>')
    return "\n".join(parts)


def render_lang_switch(in_drawer: bool = False) -> str:
    cls = "lang-switch" + (" lang-switch-drawer" if in_drawer else "")
    return (
        f'<div class="{cls}" role="group" aria-label="Language">'
        '<button data-lang-set="ru" class="lang-btn">RU</button>'
        '<button data-lang-set="th" class="lang-btn">TH</button>'
        '</div>'
    )


def render_lang_switch_drawer() -> str:
    return (
        '<div class="drawer-footer">'
        f'<span class="dl-label">{i18n("lang_label")}</span>'
        f'{render_lang_switch(in_drawer=True)}'
        '</div>'
    )


def render_messages_section(chat: dict, data: dict) -> str:
    chat_dir_name = chat["dir"]
    sender_color = data["sender_color"]
    out = ['<div data-tab-content="messages">']
    out.append('<main class="chat">')
    out.append(f'<div id="empty-state" class="empty-state" hidden>'
               f'{i18n("no_messages_day")}</div>')

    last_date = None
    for m, attachments, text_only, is_sys in data["rendered_msgs"]:
        cur_date = (m["y"], m["m"], m["d"])
        dkey = date_key(m)
        if cur_date != last_date:
            out.append(
                f'<div class="date-divider" id="d-{dkey}" data-date="{dkey}">'
                f'<span>{fmt_date(m)}</span></div>'
            )
            last_date = cur_date

        if is_sys:
            sys_text = text_only or html.escape(m["sender"])
            out.append(
                f'<div class="system-msg" data-date="{dkey}">{render_text(sys_text)}</div>'
            )
            continue

        sender = m["sender"]
        if sender in ME_NAMES:
            side = "right"
            name_color = "#06796b"
        else:
            side = "left"
            name_color = sender_color.get(sender, SENDER_NAME_COLORS[0])

        bubble = [f'<div class="msg msg-{side}" data-date="{dkey}"><div class="bubble">']
        bubble.append(f'<div class="sender" style="color:{name_color}">'
                      f'{html.escape(sender)}</div>')
        for fname in attachments:
            bubble.append(f'<div class="attachment">'
                          f'{render_attachment(fname, chat_dir_name)}</div>')
        if text_only:
            bubble.append(f'<div class="text">{render_text(text_only)}</div>')
        bubble.append(f'<div class="time">{fmt_time(m)}</div>')
        bubble.append('</div></div>')
        out.append("".join(bubble))

    out.append('</main></div>')
    return "\n".join(out)


def render_media_section(chat: dict, data: dict) -> str:
    chat_dir_name = chat["dir"]
    items = data["media_items"]
    out = ['<div data-tab-content="media" hidden>']
    if not items:
        out.append(f'<div class="empty-state">{i18n("no_media")}</div>')
        out.append('</div>')
        return "\n".join(out)

    by_day = OrderedDict()
    for item in items:
        if item["date"] not in by_day:
            by_day[item["date"]] = {"date": item["date"], "items": []}
        by_day[item["date"]]["items"].append(item)

    out.append('<div class="media-wrap">')
    for dkey, group in by_day.items():
        out.append('<div class="media-day">')
        out.append(f'<div class="media-day-title">{fmt_iso_date(group["date"])} '
                   f'<span class="day-count-pill">{len(group["items"])}</span></div>')
        out.append('<div class="media-grid">')
        for item in group["items"]:
            href = quote(f"{chat_dir_name}/{item['fname']}")
            if item["kind"] == "video":
                out.append(
                    f'<a class="media-thumb video" href="{href}" target="_blank">'
                    f'<video preload="metadata" muted playsinline src="{href}#t=0.5"></video>'
                    f'<span class="play-icon">▶</span></a>'
                )
            elif item["kind"] == "sticker":
                out.append(
                    f'<a class="media-thumb sticker-thumb" href="{href}" target="_blank">'
                    f'<img loading="lazy" src="{href}" alt=""></a>'
                )
            else:
                out.append(
                    f'<a class="media-thumb" href="{href}" target="_blank">'
                    f'<img loading="lazy" src="{href}" alt=""></a>'
                )
        out.append('</div></div>')
    out.append('</div></div>')
    return "\n".join(out)


def render_docs_section(chat: dict, data: dict) -> str:
    chat_dir_name = chat["dir"]
    items = data["doc_items"]
    out = ['<div data-tab-content="docs" hidden>']
    if not items:
        out.append(f'<div class="empty-state">{i18n("no_docs")}</div>')
        out.append('</div>')
        return "\n".join(out)

    by_day = OrderedDict()
    for item in items:
        if item["date"] not in by_day:
            by_day[item["date"]] = {"date": item["date"], "items": []}
        by_day[item["date"]]["items"].append(item)

    out.append('<div class="docs-wrap">')
    for dkey, group in by_day.items():
        out.append('<div class="docs-day">')
        out.append(f'<div class="docs-day-title">{fmt_iso_date(group["date"])}</div>')
        out.append('<div class="docs-list">')
        for item in group["items"]:
            href = quote(f"{chat_dir_name}/{item['fname']}")
            display_name = PREFIX_RE.sub("", item["fname"])
            nm = html.escape(display_name)
            icon = DOC_ICONS.get(item["kind"], "📎")
            meta = html.escape(f"{item['sender']} · {item['time']}")
            if item["kind"] == "audio":
                out.append(
                    f'<div class="doc-item audio-item">'
                    f'<div class="doc-icon">{icon}</div>'
                    f'<div class="doc-meta">'
                    f'<div class="doc-name">{nm}</div>'
                    f'<div class="doc-info">{meta}</div>'
                    f'<audio controls preload="none" src="{href}"></audio>'
                    f'</div></div>'
                )
            else:
                out.append(
                    f'<a class="doc-item" href="{href}" target="_blank">'
                    f'<div class="doc-icon">{icon}</div>'
                    f'<div class="doc-meta">'
                    f'<div class="doc-name">{nm}</div>'
                    f'<div class="doc-info">{meta}</div>'
                    f'</div></a>'
                )
        out.append('</div></div>')
    out.append('</div></div>')
    return "\n".join(out)


def render_chat_page(chat: dict, all_chats: list):
    out_path = ROOT / chat["out"]
    data = chat["data"]
    title = chat["title"]
    msg_count = data["msg_count"]
    days = len(data["sorted_days"])
    media_count = len(data["media_items"])
    doc_count = len(data["doc_items"])

    months = OrderedDict()
    for k in data["sorted_days"]:
        ym = k[:7]
        months.setdefault(ym, []).append(k)

    out = [build_head(f"WhatsApp — {title}")]
    out.append('<body data-active-tab="messages">')
    out.append(render_drawer(chat, all_chats))

    out.append('<header class="chat-header"><div class="header-row">')
    out.append('<button id="navToggle" class="icon-btn menu-btn" '
               'data-i18n-aria="open_menu" data-i18n-title="menu" '
               'aria-label="Открыть меню" title="Меню">☰</button>')
    out.append('<div class="title-block">')
    out.append(f'<a class="back-link" href="index.html">{i18n("back_all")}</a>')
    out.append(f'<div class="title">{html.escape(title)}</div>')
    out.append(
        f'<div class="sub">{render_subtitle(chat)} · '
        f'{msg_count} {i18n("lbl_messages")} · '
        f'{days} {i18n("lbl_days")}</div>'
    )
    out.append('</div>')
    out.append('<div class="controls">')
    out.append(render_lang_switch())
    out.append(
        f'<input type="date" id="datePicker" min="{data["min_date"]}" '
        f'max="{data["max_date"]}" '
        f'data-i18n-aria="select_date" aria-label="Выбрать дату">'
    )
    out.append('<button id="togglePanel" class="icon-btn" aria-expanded="false" '
               'aria-controls="dates-panel" '
               'data-i18n-title="all_dates" title="Все даты">📅</button>')
    out.append(f'<button id="clearFilter" class="primary" hidden>{i18n("reset")}</button>')
    out.append('</div></div></header>')

    out.append('<div class="tabs" role="tablist">')
    out.append('<button class="tab active" data-tab="messages" role="tab">'
               f'{i18n("tab_messages")} <span class="tab-count">{msg_count}</span></button>')
    out.append('<button class="tab" data-tab="media" role="tab">'
               f'{i18n("tab_media")} <span class="tab-count">{media_count}</span></button>')
    out.append('<button class="tab" data-tab="docs" role="tab">'
               f'{i18n("tab_docs")} <span class="tab-count">{doc_count}</span></button>')
    out.append('</div>')

    out.append('<div id="backdrop" hidden></div>')
    out.append('<aside id="dates-panel" hidden aria-label="Список дат">')
    out.append(f'<p class="panel-hint">{i18n("filter_hint")}</p>')
    for ym, keys in months.items():
        out.append(f'<div class="month-block"><div class="month-title">{fmt_month_year(ym)}</div>')
        out.append('<div class="day-chips">')
        for k in keys:
            out.append(
                f'<a href="#d-{k}" class="day-chip" data-date="{k}">'
                f'{fmt_day_month(k)}<span class="count">{data["day_count"][k]}</span></a>'
            )
        out.append('</div></div>')
    out.append('</aside>')

    out.append(render_messages_section(chat, data))
    out.append(render_media_section(chat, data))
    out.append(render_docs_section(chat, data))

    out.append(chat_script_foot())
    out_path.write_text("\n".join(out), encoding="utf-8")


def build_index(chats):
    out = [build_head("WhatsApp архив")]
    out.append('<body data-page="hub">')
    out.append('<div class="hub">')
    out.append('<header class="hub-header">')
    out.append(f'<div class="hub-lang">{render_lang_switch()}</div>')
    out.append(f'<h1>{i18n("archive_title")}</h1>')
    out.append(f'<p>{len(chats)} {i18n("lbl_chats")}</p>')
    out.append('</header>')
    out.append('<div class="chat-cards">')
    for chat in chats:
        d = chat["data"]
        href = quote(chat["out"])
        title = html.escape(chat["title"])
        icon = chat["icon"]
        if d["min_date"]:
            range_label = (f"{fmt_iso_date(d['min_date'])} — "
                           f"{fmt_iso_date(d['max_date'])}")
        else:
            range_label = "—"
        out.append(
            f'<a class="chat-card" href="{href}">'
            f'<div class="card-icon">{icon}</div>'
            f'<div class="card-body">'
            f'<div class="card-title">{title}</div>'
            f'<div class="card-sub">{render_subtitle(chat)}</div>'
            f'<div class="card-meta">'
            f'<span>{d["msg_count"]} {i18n("lbl_messages")}</span><span>·</span>'
            f'<span>{len(d["sorted_days"])} {i18n("lbl_days")}</span><span>·</span>'
            f'<span>{len(d["media_items"])} {i18n("lbl_media")}</span>'
            f'</div>'
            f'<div class="card-range">{range_label}</div>'
            f'</div>'
            f'<div class="card-arrow">→</div>'
            f'</a>'
        )
    out.append('</div></div>')
    out.append(hub_script_foot())
    (ROOT / "index.html").write_text("\n".join(out), encoding="utf-8")


def build_head(title: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
{CSS}
</style>
</head>
"""


def i18n_js_payload() -> str:
    """JSON of i18n strings used for aria-label/title swaps in JS."""
    import json
    keys = ["menu", "open_menu", "close", "select_date", "all_dates", "lang_label"]
    payload = {
        "ru": {k: I18N_RU[k] for k in keys},
        "th": {k: I18N_TH[k] for k in keys},
    }
    return json.dumps(payload, ensure_ascii=False)


def chat_script_foot() -> str:
    return CHAT_SCRIPT_FOOT.replace("__I18N_JSON__", i18n_js_payload())


HUB_SCRIPT_FOOT = """<script>
(function() {
  const I18N = __I18N_JSON__;
  const LANGS = ['ru', 'th'];
  function readLang() {
    try {
      const v = localStorage.getItem('archiveLang');
      return LANGS.includes(v) ? v : 'ru';
    } catch (e) { return 'ru'; }
  }
  function applyLang(lang) {
    document.body.dataset.lang = lang;
    document.documentElement.lang = lang;
    try { localStorage.setItem('archiveLang', lang); } catch (e) {}
    document.querySelectorAll('[data-lang-set]').forEach(b => {
      b.classList.toggle('active', b.dataset.langSet === lang);
    });
  }
  document.querySelectorAll('[data-lang-set]').forEach(b => {
    b.addEventListener('click', () => applyLang(b.dataset.langSet));
  });
  applyLang(readLang());
})();
</script>
</body></html>
"""


def hub_script_foot() -> str:
    return HUB_SCRIPT_FOOT.replace("__I18N_JSON__", i18n_js_payload())


CSS = """
:root {
  --bg: #efeae2;
  --header: #008069;
  --header-2: #015e4f;
  --bubble-in: #ffffff;
  --bubble-out: #d9fdd3;
  --text: #111b21;
  --muted: #667781;
}

/* ===== i18n bilingual spans (CSS toggles which lang is visible) ===== */
.i18n { display: inline; }
.i18n > [data-l] { display: inline; }
.i18n > [data-l="th"] { display: none; }
body[data-lang="th"] .i18n > [data-l="ru"] { display: none; }
body[data-lang="th"] .i18n > [data-l="th"] { display: inline; }

/* ===== Language switcher pills ===== */
.lang-switch {
  display: inline-flex;
  background: rgba(255,255,255,0.18);
  border-radius: 8px;
  padding: 2px;
  flex: 0 0 auto;
}
.lang-switch .lang-btn {
  background: transparent; color: #fff;
  border: 0; padding: 5px 10px;
  font-size: 12.5px; font-weight: 600;
  font-family: inherit; cursor: pointer;
  border-radius: 6px;
  letter-spacing: 0.3px;
  min-height: 0;
  -webkit-tap-highlight-color: transparent;
}
.lang-switch .lang-btn:hover { background: rgba(255,255,255,0.18); }
.lang-switch .lang-btn.active {
  background: #fff; color: var(--header);
}
.lang-switch-drawer {
  background: #f0f2f5;
}
.lang-switch-drawer .lang-btn { color: var(--muted); }
.lang-switch-drawer .lang-btn:hover { background: rgba(0,0,0,0.04); }
.lang-switch-drawer .lang-btn.active {
  background: var(--header);
  color: #fff;
}
.drawer-footer {
  margin-top: auto;
  padding: 14px 18px 18px;
  border-top: 1px solid #eee;
  display: flex; align-items: center; gap: 12px;
  justify-content: space-between;
}
.dl-label {
  font-size: 12.5px; color: var(--muted);
  font-weight: 600;
}
.hub-lang {
  display: flex; justify-content: flex-end;
  margin-bottom: 14px;
}
.hub-lang .lang-switch { background: #f0f2f5; }
.hub-lang .lang-btn { color: var(--muted); }
.hub-lang .lang-btn.active { background: var(--header); color: #fff; }

* { box-sizing: border-box; }
html, body {
  margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", "Segoe UI",
               Roboto, "Noto Sans Thai", "Apple Color Emoji", sans-serif;
  font-size: 14.5px;
}
body {
  background-image:
    radial-gradient(rgba(0,0,0,0.025) 1px, transparent 1px),
    radial-gradient(rgba(0,0,0,0.025) 1px, transparent 1px);
  background-size: 22px 22px, 22px 22px;
  background-position: 0 0, 11px 11px;
}

/* ========== Hub (index.html) ========== */
.hub { max-width: 720px; margin: 0 auto; padding: 28px 18px 60px; }
.hub-header { text-align: center; padding: 18px 0 22px; }
.hub-header h1 {
  margin: 0 0 6px; color: var(--header);
  font-size: 26px; font-weight: 700; letter-spacing: -0.3px;
}
.hub-header p { margin: 0; color: var(--muted); font-size: 14px; }
.chat-cards { display: flex; flex-direction: column; gap: 12px; }
.chat-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; padding: 16px; border-radius: 14px;
  text-decoration: none; color: inherit;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}
.chat-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0,0,0,0.1);
}
.card-icon {
  flex: 0 0 56px; height: 56px; width: 56px;
  background: #d9fdd3; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
}
.card-body { flex: 1 1 auto; min-width: 0; }
.card-title {
  font-size: 16px; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.card-sub {
  color: var(--muted); font-size: 13px; margin-top: 3px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.card-meta {
  display: flex; gap: 6px; margin-top: 6px;
  color: #54656f; font-size: 12.5px;
}
.card-range { color: #8a929b; font-size: 12px; margin-top: 2px; }
.card-arrow { color: var(--header); font-size: 22px; flex: 0 0 auto; }

/* ========== Chat page ========== */
.chat-header {
  position: sticky; top: 0; z-index: 20;
  background: var(--header); color: #fff;
  padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.header-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; flex-wrap: wrap;
}
.title-block { min-width: 0; flex: 1 1 auto; }
.back-link {
  display: inline-block; color: #cbeee5;
  text-decoration: none; font-size: 12.5px; margin-bottom: 2px;
}
.back-link:hover { color: #fff; }
.title { font-weight: 600; font-size: 16px; line-height: 1.2; }
.sub { font-size: 12.5px; opacity: 0.85; margin-top: 2px; }
.controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.controls input[type=date],
.controls button {
  background: rgba(255,255,255,0.18);
  color: #fff; border: 0;
  padding: 8px 12px; border-radius: 8px;
  font-size: 14px; font-family: inherit;
  cursor: pointer; min-height: 38px;
  -webkit-tap-highlight-color: transparent;
}
.controls input[type=date] { color-scheme: dark; }
.controls button:hover,
.controls input[type=date]:hover { background: rgba(255,255,255,0.28); }
.controls button.primary { background: #fff; color: var(--header); font-weight: 600; }
.controls button.primary:hover { background: #f0f0f0; }
.controls button[hidden] { display: none; }
.icon-btn { padding: 8px 10px !important; font-size: 16px; }

#dates-panel {
  position: fixed;
  top: 78px; left: 0; right: 0;
  background: #fff;
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  z-index: 18;
  box-shadow: 0 4px 16px rgba(0,0,0,0.18);
  padding: 14px 16px 18px;
  border-bottom: 1px solid #e3e3e3;
}
#dates-panel[hidden] { display: none; }
.panel-hint { color: #54656f; font-size: 12.5px; margin: 0 0 10px; }
.month-block { margin-bottom: 14px; }
.month-block:last-child { margin-bottom: 0; }
.month-title {
  font-weight: 600; color: var(--header);
  font-size: 13px; margin: 4px 0 8px;
  text-transform: uppercase; letter-spacing: 0.4px;
}
.day-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.day-chip {
  background: #f0f2f5; border: 0; padding: 7px 11px;
  border-radius: 16px; font-size: 13px; cursor: pointer;
  text-decoration: none; color: inherit;
  display: inline-flex; align-items: center; gap: 6px;
  font-family: inherit; min-height: 32px;
}
.day-chip:hover { background: #d9fdd3; }
.day-chip.active { background: var(--header); color: #fff; }
.day-chip .count {
  font-size: 11px; background: rgba(0,0,0,0.08);
  padding: 1px 6px; border-radius: 10px;
}
.day-chip.active .count { background: rgba(255,255,255,0.25); }

#backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.35);
  z-index: 17;
}
#backdrop[hidden] { display: none; }

.chat { max-width: 960px; margin: 0 auto; padding: 18px 14px 80px; }
.date-divider { text-align: center; margin: 22px 0 14px; scroll-margin-top: 80px; }
.date-divider span {
  background: #ffffffd4; color: #54656f; font-size: 12.3px;
  padding: 5px 12px; border-radius: 8px;
  box-shadow: 0 1px 1px rgba(0,0,0,0.08);
}
.system-msg {
  text-align: center; margin: 14px auto; max-width: 580px;
  background: #fdf4c5; color: #54656f; font-size: 12.5px;
  padding: 8px 14px; border-radius: 8px;
  box-shadow: 0 1px 1px rgba(0,0,0,0.06);
}
.msg { display: flex; margin: 3px 0; }
.msg-left { justify-content: flex-start; }
.msg-right { justify-content: flex-end; }
.bubble {
  position: relative;
  max-width: min(78%, 620px);
  padding: 7px 10px 7px 11px; border-radius: 8px;
  box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
  word-wrap: break-word; overflow-wrap: anywhere;
}
.msg-left .bubble { background: var(--bubble-in); border-top-left-radius: 0; }
.msg-right .bubble { background: var(--bubble-out); border-top-right-radius: 0; }
.sender {
  font-size: 12.7px; font-weight: 600; margin-bottom: 3px;
}
.text { white-space: pre-wrap; line-height: 1.4; }
.text a { color: #027eb5; }
.time {
  font-size: 11px; color: var(--muted);
  text-align: right; margin-top: 3px; user-select: none;
}
.attachment { margin: 4px 0; }
.attachment + .attachment { margin-top: 6px; }
.photo, .video {
  max-width: 100%; max-height: 380px;
  border-radius: 6px; display: block;
}
.video { width: 340px; max-width: 100%; background: #000; }
.sticker { max-width: 160px; max-height: 160px; display: block; }
.audio { width: 100%; min-width: 240px; max-width: 340px; display: block; }
.file {
  display: flex; align-items: center; gap: 10px;
  background: rgba(0,0,0,0.06); padding: 10px 12px; border-radius: 8px;
  text-decoration: none; color: inherit;
  max-width: 360px;
}
.file:hover { background: rgba(0,0,0,0.1); }
.file-icon { font-size: 22px; flex: 0 0 auto; }
.file-name { word-break: break-all; font-size: 13.5px; }

.empty-state {
  text-align: center; color: var(--muted); padding: 40px 20px;
  font-size: 14px;
}
.empty-state[hidden] { display: none; }

/* ========== Nav drawer ========== */
#nav-drawer {
  position: fixed; top: 0; left: 0; bottom: 0;
  width: 320px; max-width: 88vw;
  background: #fff; z-index: 30;
  box-shadow: 4px 0 20px rgba(0,0,0,0.18);
  overflow-y: auto;
  display: flex; flex-direction: column;
}
#nav-drawer[hidden] { display: none; }
.drawer-h {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px;
  background: var(--header); color: #fff;
  position: sticky; top: 0;
}
.drawer-h .icon-btn {
  background: rgba(255,255,255,0.18); color: #fff;
  border: 0; border-radius: 8px;
  padding: 6px 10px; font-size: 14px; cursor: pointer;
}
.drawer-h .icon-btn:hover { background: rgba(255,255,255,0.28); }
.drawer-title { font-weight: 600; font-size: 16px; }
.drawer-home {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px;
  text-decoration: none; color: inherit;
  border-bottom: 1px solid #eee;
  font-size: 14.5px;
}
.drawer-home:hover { background: #f5f5f5; }
.dh-icon { font-size: 18px; }
.drawer-section {
  padding: 14px 18px 6px;
  font-size: 11.5px; font-weight: 600;
  color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px;
}
.drawer-chats { display: flex; flex-direction: column; padding-bottom: 16px; }
.drawer-chat {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 18px;
  text-decoration: none; color: inherit;
  border-left: 3px solid transparent;
  transition: background 0.1s;
}
.drawer-chat:hover { background: #f5f5f5; }
.drawer-chat.active {
  background: #e7f7e7;
  border-left-color: var(--header);
  pointer-events: none;
}
.dc-icon {
  flex: 0 0 38px; height: 38px; width: 38px;
  background: #d9fdd3; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 19px;
}
.dc-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1 1 auto; }
.dc-name {
  font-weight: 600; font-size: 14px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dc-meta { color: var(--muted); font-size: 12px; }
#nav-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  z-index: 29;
}
#nav-backdrop[hidden] { display: none; }

.menu-btn {
  background: rgba(255,255,255,0.18) !important;
  color: #fff !important;
  font-size: 18px !important;
  flex: 0 0 auto;
}

/* ========== Tabs ========== */
.tabs {
  display: flex;
  background: #fff;
  position: sticky; top: 78px; z-index: 15;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  padding: 0 8px;
  overflow-x: auto;
  scrollbar-width: none;
}
.tabs::-webkit-scrollbar { display: none; }
.tab {
  background: transparent; border: 0;
  padding: 12px 14px;
  font-size: 14px; font-family: inherit;
  cursor: pointer; color: #54656f;
  display: flex; align-items: center; gap: 6px;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}
.tab:hover { color: var(--header); }
.tab.active {
  color: var(--header);
  border-bottom-color: var(--header);
  font-weight: 600;
}
.tab-count {
  font-size: 11.5px;
  background: #f0f2f5;
  padding: 1px 7px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}
.tab.active .tab-count { background: #d9fdd3; }
[data-tab-content][hidden] { display: none; }

/* Hide filter controls outside messages tab */
body[data-active-tab="media"] .controls,
body[data-active-tab="docs"] .controls { display: none; }

/* ========== Media tab ========== */
.media-wrap { max-width: 1080px; margin: 0 auto; padding-bottom: 60px; }
.media-day { padding: 16px 14px 0; }
.media-day-title {
  font-size: 12.5px; color: #54656f;
  margin: 0 0 8px;
  text-transform: uppercase; letter-spacing: 0.3px;
  font-weight: 600;
  display: flex; align-items: center; gap: 8px;
}
.day-count-pill {
  background: #f0f2f5; padding: 1px 8px;
  border-radius: 10px; font-size: 11px;
  color: #54656f; text-transform: none; letter-spacing: 0;
}
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 4px;
}
.media-thumb {
  aspect-ratio: 1;
  overflow: hidden;
  border-radius: 4px;
  position: relative;
  display: block;
  background: #cfd2d6;
  cursor: zoom-in;
}
.media-thumb img,
.media-thumb video {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
  border-radius: 4px;
}
.media-thumb.video::before {
  content: "";
  position: absolute; inset: 0;
  background: rgba(0,0,0,0.18);
  border-radius: 4px;
  pointer-events: none;
}
.media-thumb .play-icon {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  color: #fff;
  font-size: 16px;
  background: rgba(0,0,0,0.55);
  width: 38px; height: 38px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  z-index: 2;
  padding-left: 3px;
}
.media-thumb.sticker-thumb { background: transparent; }
.media-thumb.sticker-thumb img { object-fit: contain; padding: 6px; }

/* ========== Docs tab ========== */
.docs-wrap { max-width: 760px; margin: 0 auto; padding: 0 14px 60px; }
.docs-day { padding-top: 16px; }
.docs-day-title {
  font-size: 12.5px; color: #54656f;
  margin: 0 0 8px; padding: 0 4px;
  text-transform: uppercase; letter-spacing: 0.3px;
  font-weight: 600;
}
.docs-list { display: flex; flex-direction: column; gap: 6px; }
.doc-item {
  display: flex; align-items: flex-start; gap: 12px;
  background: #fff; padding: 12px 14px;
  border-radius: 10px;
  text-decoration: none; color: inherit;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  transition: background 0.1s;
}
.doc-item:hover { background: #f9f9f9; }
.doc-icon {
  flex: 0 0 40px; font-size: 24px;
  text-align: center; line-height: 1.5;
}
.doc-meta { flex: 1 1 auto; min-width: 0; }
.doc-name { font-size: 14px; word-break: break-word; line-height: 1.35; }
.doc-info { color: var(--muted); font-size: 12.5px; margin-top: 3px; }
.doc-meta audio { width: 100%; max-width: 360px; margin-top: 8px; display: block; }
.audio-item { background: #fff; cursor: default; }

@media (max-width: 700px) {
  .tabs { top: 70px; padding: 0 4px; }
  .tab { padding: 10px 10px; font-size: 13px; }
  .tab-count { font-size: 11px; padding: 1px 6px; }
  .media-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 3px;
  }
  .media-day { padding: 12px 4px 0; }
  .media-day-title { padding: 0 4px; }
  .docs-wrap { padding: 0 6px 40px; }
  .doc-item { padding: 10px 12px; }
  #nav-drawer { width: 88vw; }
  .menu-btn { font-size: 16px !important; padding: 7px 9px !important; }
}

@media (max-width: 700px) {
  .chat-header { padding: 10px 12px; }
  .title { font-size: 15px; }
  .sub { font-size: 12px; }
  .controls { gap: 6px; }
  .controls input[type=date],
  .controls button { padding: 7px 10px; font-size: 13.5px; min-height: 36px; }
  .chat { padding: 12px 8px 80px; }
  .bubble { max-width: 92%; padding: 6px 9px; }
  .photo { max-height: 320px; }
  .video { width: 100%; }

  .hub { padding: 18px 14px 60px; }
  .hub-header h1 { font-size: 22px; }
  .chat-card { padding: 14px; gap: 12px; }
  .card-icon { flex-basis: 48px; height: 48px; width: 48px; font-size: 24px; }
  .card-title { font-size: 15px; }

  #dates-panel {
    top: auto; bottom: 0;
    left: 0; right: 0;
    border-radius: 16px 16px 0 0;
    max-height: 75vh;
    padding: 14px 14px 24px;
  }
  #dates-panel::before {
    content: ""; display: block;
    width: 36px; height: 4px; background: #ccc;
    border-radius: 2px; margin: -4px auto 12px;
  }
}
"""


CHAT_SCRIPT_FOOT = """<script>
(function() {
  // ===== Language switching =====
  const I18N = __I18N_JSON__;
  const LANGS = ['ru', 'th'];
  function readLang() {
    try {
      const v = localStorage.getItem('archiveLang');
      return LANGS.includes(v) ? v : 'ru';
    } catch (e) { return 'ru'; }
  }
  function applyLang(lang) {
    document.body.dataset.lang = lang;
    document.documentElement.lang = lang;
    try { localStorage.setItem('archiveLang', lang); } catch (e) {}
    document.querySelectorAll('[data-lang-set]').forEach(b => {
      b.classList.toggle('active', b.dataset.langSet === lang);
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      const key = el.dataset.i18nAria;
      if (I18N[lang] && I18N[lang][key]) el.setAttribute('aria-label', I18N[lang][key]);
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.dataset.i18nTitle;
      if (I18N[lang] && I18N[lang][key]) el.setAttribute('title', I18N[lang][key]);
    });
  }
  document.querySelectorAll('[data-lang-set]').forEach(b => {
    b.addEventListener('click', () => applyLang(b.dataset.langSet));
  });
  applyLang(readLang());

  // ===== Date filter (messages tab) =====
  const datePicker = document.getElementById('datePicker');
  const clearBtn   = document.getElementById('clearFilter');
  const toggleBtn  = document.getElementById('togglePanel');
  const panel      = document.getElementById('dates-panel');
  const backdrop   = document.getElementById('backdrop');
  const empty      = document.getElementById('empty-state');
  const items      = document.querySelectorAll('.msg, .date-divider, .system-msg');

  function setPanel(open) {
    panel.hidden = !open;
    backdrop.hidden = !open;
    toggleBtn.setAttribute('aria-expanded', String(open));
    document.body.style.overflow = open ? 'hidden' : '';
  }

  function applyFilter(date, opts) {
    opts = opts || {};
    let visible = 0;
    items.forEach(el => {
      const match = !date || el.dataset.date === date;
      el.style.display = match ? '' : 'none';
      if (match) visible++;
    });
    document.querySelectorAll('.day-chip').forEach(c => {
      c.classList.toggle('active', !!date && c.dataset.date === date);
    });
    clearBtn.hidden = !date;
    datePicker.value = date || '';
    if (empty) empty.hidden = visible > 0;

    if (date && opts.scroll !== false) {
      const target = document.getElementById('d-' + date);
      if (target) setTimeout(() => target.scrollIntoView({block: 'start'}), 30);
    }
  }

  datePicker.addEventListener('change', e => { applyFilter(e.target.value); setPanel(false); });
  clearBtn.addEventListener('click', () => { applyFilter(''); setPanel(false); });
  toggleBtn.addEventListener('click', () => setPanel(panel.hidden));
  backdrop.addEventListener('click', () => setPanel(false));
  panel.addEventListener('click', e => {
    const chip = e.target.closest('.day-chip');
    if (chip) {
      e.preventDefault();
      applyFilter(chip.dataset.date);
      setPanel(false);
    }
  });

  // ===== Tabs =====
  const tabBtns = document.querySelectorAll('.tab');
  const tabContents = document.querySelectorAll('[data-tab-content]');
  function activateTab(name) {
    tabBtns.forEach(b => b.classList.toggle('active', b.dataset.tab === name));
    tabContents.forEach(c => { c.hidden = c.dataset.tabContent !== name; });
    document.body.dataset.activeTab = name;
    if (name !== 'messages' && !panel.hidden) setPanel(false);
    window.scrollTo({top: 0, behavior: 'instant'});
  }
  tabBtns.forEach(b => b.addEventListener('click', () => activateTab(b.dataset.tab)));

  // ===== Nav drawer =====
  const drawer = document.getElementById('nav-drawer');
  const navBackdrop = document.getElementById('nav-backdrop');
  const navToggle = document.getElementById('navToggle');
  const navClose = document.getElementById('navClose');
  function setDrawer(open) {
    if (drawer) drawer.hidden = !open;
    if (navBackdrop) navBackdrop.hidden = !open;
    document.body.style.overflow = open ? 'hidden' : '';
  }
  if (navToggle) navToggle.addEventListener('click', () => setDrawer(true));
  if (navClose) navClose.addEventListener('click', () => setDrawer(false));
  if (navBackdrop) navBackdrop.addEventListener('click', () => setDrawer(false));

  // ===== Global Escape: close any open overlay =====
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    if (drawer && !drawer.hidden) { setDrawer(false); return; }
    if (!panel.hidden) { setPanel(false); return; }
  });
})();
</script>
</body></html>
"""


def main():
    chats = discover_chats()
    print(f"Discovered {len(chats)} chat folder(s).")
    # First pass: walk messages and collect per-chat data
    for chat in chats:
        chat["data"] = collect_data(chat)
    # Sort by message count desc → consistent nav drawer + index card order
    chats_sorted = sorted(chats, key=lambda c: c["data"]["msg_count"], reverse=True)
    # Second pass: render pages with full nav
    for chat in chats_sorted:
        render_chat_page(chat, chats_sorted)
        kind = "group" if chat["is_group"] else "personal"
        d = chat["data"]
        print(f"  → {chat['out']:30s} [{kind}] "
              f"{d['msg_count']} msgs, {len(d['sorted_days'])} days, "
              f"{len(d['media_items'])} media, {len(d['doc_items'])} docs")
    build_index(chats_sorted)
    print(f"  → index.html: {len(chats_sorted)} chats")


if __name__ == "__main__":
    main()
