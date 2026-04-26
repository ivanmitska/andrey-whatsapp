#!/usr/bin/env python3
"""Build readable HTML views of multiple WhatsApp chat exports + landing page."""
import re
import html
from collections import OrderedDict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent

CHATS = [
    {
        "dir": "WhatsApp Chat - +66 91 824 1010",
        "out": "parinton.html",
        "title": "+66 91 824 1010",
        "subtitle": "Личный чат · ~PARINTON",
        "icon": "👤",
        "system_sender": None,
    },
    {
        "dir": "WhatsApp Chat - Andrey Freedom  beach case",
        "out": "beach-case.html",
        "title": "Andrey Freedom — beach case",
        "subtitle": "Группа · Алиса адвокат, NikitaBKK и др.",
        "icon": "👥",
        "system_sender": "Andrey Freedom  beach case",
    },
]

ME = "🌏"  # always on right with green bubble

LRM = "‎"
MSG_RE = re.compile(
    r'^‎?\[(\d{1,2})/(\d{1,2})/(\d{2,4}),\s*(\d{1,2}):(\d{2}):(\d{2})\]\s+([^:]+?):\s?(.*)$'
)
ATTACH_RE = re.compile(r'‎?<прикреплено:\s*([^>]+)>')
PREFIX_RE = re.compile(r'^\d+-')
URL_RE = re.compile(r'(https?://[^\s<>"]+)')

MONTHS_RU_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня",
                 "июля", "августа", "сентября", "октября", "ноября", "декабря"]
MONTHS_RU_NOM = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                 "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

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


def parse_messages(txt_path: Path):
    raw = txt_path.read_text(encoding="utf-8")
    msgs = []
    cur = None
    for line in raw.splitlines():
        m = MSG_RE.match(line)
        if m:
            if cur is not None:
                msgs.append(cur)
            d, mo, y, h, mi, s, sender, body = m.groups()
            year = int(y)
            if year < 100:
                year += 1957  # Buddhist 2-digit -> Gregorian (2568 -> 2025)
            cleaned_sender = sender.strip().lstrip("~").strip()
            cur = {
                "d": int(d), "m": int(mo), "y": year,
                "hh": int(h), "mm": int(mi), "ss": int(s),
                "sender": cleaned_sender,
                "body": body,
            }
        else:
            if cur is not None:
                cur["body"] += "\n" + line
    if cur is not None:
        msgs.append(cur)
    return msgs


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
    return f"{msg['d']} {MONTHS_RU_GEN[msg['m'] - 1]} {msg['y']}"


def fmt_time(msg) -> str:
    return f"{msg['hh']:02d}:{msg['mm']:02d}"


def is_group_system(text: str, attachments, chat) -> bool:
    if attachments:
        return False
    if not text:
        return False
    return any(p in text for p in SYSTEM_PATTERNS)


def render_chat_page(chat: dict) -> dict:
    """Build one chat HTML, return stats."""
    chat_dir_name = chat["dir"]
    chat_dir = ROOT / chat_dir_name
    txt = chat_dir / "_chat.txt"
    out_path = ROOT / chat["out"]
    msgs = parse_messages(txt)

    # Collect senders excluding ME and group system sender
    senders_seen = OrderedDict()
    for m in msgs:
        s = m["sender"]
        if s == ME:
            continue
        if chat.get("system_sender") and s == chat["system_sender"]:
            continue
        if s not in senders_seen:
            senders_seen[s] = True
    other_senders = list(senders_seen.keys())
    sender_color = {}
    for i, s in enumerate(other_senders):
        sender_color[s] = SENDER_NAME_COLORS[i % len(SENDER_NAME_COLORS)]

    # Pre-process messages
    rendered_msgs = []
    day_count = {}
    for m in msgs:
        body = m["body"]
        attachments = ATTACH_RE.findall(body)
        text_only = ATTACH_RE.sub("", body).strip().replace(LRM, "").strip()

        is_sys = False
        if chat.get("system_sender") and m["sender"] == chat["system_sender"]:
            is_sys = True
        elif is_group_system(text_only, attachments, chat):
            is_sys = True

        if not text_only and not attachments and not is_sys:
            continue

        rendered_msgs.append((m, attachments, text_only, is_sys))
        if not is_sys:
            key = date_key(m)
            day_count[key] = day_count.get(key, 0) + 1

    sorted_days = sorted(day_count.keys())
    min_date = sorted_days[0] if sorted_days else ""
    max_date = sorted_days[-1] if sorted_days else ""

    months = OrderedDict()
    for k in sorted_days:
        ym = k[:7]
        months.setdefault(ym, []).append(k)

    # Compose HTML
    title = chat["title"]
    subtitle = chat["subtitle"]
    senders_label = ", ".join([ME] + other_senders) if other_senders else ME

    out = [build_head(f"WhatsApp Chat — {title}")]
    out.append('<header class="chat-header"><div class="header-row">')
    out.append('<div class="title-block">')
    out.append('<a class="back-link" href="index.html">‹ Все чаты</a>')
    out.append(f'<div class="title">{html.escape(title)}</div>')
    out.append(f'<div class="sub">{html.escape(subtitle)} · {len(rendered_msgs)} сообщений · {len(sorted_days)} дней</div>')
    out.append('</div>')
    out.append('<div class="controls">')
    out.append(f'<input type="date" id="datePicker" min="{min_date}" max="{max_date}" aria-label="Выбрать дату">')
    out.append('<button id="togglePanel" class="icon-btn" aria-expanded="false" aria-controls="dates-panel" title="Все даты">📅</button>')
    out.append('<button id="clearFilter" class="primary" hidden>Сброс</button>')
    out.append('</div></div></header>')

    out.append('<div id="backdrop" hidden></div>')
    out.append('<aside id="dates-panel" hidden aria-label="Список дат">')
    out.append('<p class="panel-hint">Выберите день — остальные сообщения скроются.</p>')
    for ym, keys in months.items():
        y, mo = ym.split("-")
        m_title = f"{MONTHS_RU_NOM[int(mo) - 1]} {y}"
        out.append('<div class="month-block">')
        out.append(f'<div class="month-title">{m_title}</div>')
        out.append('<div class="day-chips">')
        for k in keys:
            _, _, dd = k.split("-")
            label = f"{int(dd)} {MONTHS_RU_GEN[int(mo) - 1]}"
            out.append(
                f'<a href="#d-{k}" class="day-chip" data-date="{k}">'
                f'<span>{label}</span><span class="count">{day_count[k]}</span></a>'
            )
        out.append('</div></div>')
    out.append('</aside>')

    out.append('<main class="chat">')
    out.append('<div id="empty-state" class="empty-state" hidden>За выбранный день нет сообщений.</div>')

    last_date = None
    for m, attachments, text_only, is_sys in rendered_msgs:
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
        if sender == ME:
            side = "right"
            name_color = "#06796b"
        else:
            side = "left"
            name_color = sender_color.get(sender, SENDER_NAME_COLORS[0])

        bubble = [f'<div class="msg msg-{side}" data-date="{dkey}"><div class="bubble">']
        bubble.append(f'<div class="sender" style="color:{name_color}">{html.escape(sender)}</div>')
        for fname in attachments:
            bubble.append(f'<div class="attachment">{render_attachment(fname, chat_dir_name)}</div>')
        if text_only:
            bubble.append(f'<div class="text">{render_text(text_only)}</div>')
        bubble.append(f'<div class="time">{fmt_time(m)}</div>')
        bubble.append('</div></div>')
        out.append("".join(bubble))

    out.append('</main>')
    out.append(CHAT_SCRIPT_FOOT)
    out_path.write_text("\n".join(out), encoding="utf-8")

    return {
        "messages": len(rendered_msgs),
        "days": len(sorted_days),
        "min_date": min_date,
        "max_date": max_date,
        "senders": [ME] + other_senders,
    }


def build_index(chat_stats):
    out = [build_head("WhatsApp архив")]
    out.append('<div class="hub">')
    out.append('<header class="hub-header">')
    out.append('<h1>WhatsApp архив</h1>')
    out.append('<p>Выберите чат для просмотра</p>')
    out.append('</header>')
    out.append('<div class="chat-cards">')
    for chat, stats in chat_stats:
        href = quote(chat["out"])
        title = html.escape(chat["title"])
        subtitle = html.escape(chat["subtitle"])
        icon = chat["icon"]
        if stats["min_date"]:
            min_label = format_iso_date(stats["min_date"])
            max_label = format_iso_date(stats["max_date"])
            range_label = f"{min_label} — {max_label}"
        else:
            range_label = "—"
        out.append(
            f'<a class="chat-card" href="{href}">'
            f'<div class="card-icon">{icon}</div>'
            f'<div class="card-body">'
            f'<div class="card-title">{title}</div>'
            f'<div class="card-sub">{subtitle}</div>'
            f'<div class="card-meta">'
            f'<span>{stats["messages"]} сообщений</span>'
            f'<span>·</span>'
            f'<span>{stats["days"]} дней</span>'
            f'</div>'
            f'<div class="card-range">{range_label}</div>'
            f'</div>'
            f'<div class="card-arrow">→</div>'
            f'</a>'
        )
    out.append('</div></div>')
    out.append('</body></html>')
    (ROOT / "index.html").write_text("\n".join(out), encoding="utf-8")


def format_iso_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(d)} {MONTHS_RU_GEN[int(m) - 1]} {y}"


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
<body>
"""


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
.hub {
  max-width: 720px; margin: 0 auto; padding: 28px 18px 60px;
}
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
    empty.hidden = visible > 0;

    if (date && opts.scroll !== false) {
      const target = document.getElementById('d-' + date);
      if (target) {
        setTimeout(() => target.scrollIntoView({block: 'start'}), 30);
      }
    }
  }

  datePicker.addEventListener('change', e => {
    applyFilter(e.target.value);
    setPanel(false);
  });
  clearBtn.addEventListener('click', () => {
    applyFilter('');
    setPanel(false);
  });
  toggleBtn.addEventListener('click', () => setPanel(panel.hidden));
  backdrop.addEventListener('click', () => setPanel(false));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !panel.hidden) setPanel(false);
  });
  panel.addEventListener('click', e => {
    const chip = e.target.closest('.day-chip');
    if (chip) {
      e.preventDefault();
      applyFilter(chip.dataset.date);
      setPanel(false);
    }
  });
})();
</script>
</body></html>
"""


def main():
    chat_stats = []
    for chat in CHATS:
        chat_dir = ROOT / chat["dir"]
        if not chat_dir.exists():
            print(f"SKIP: {chat['dir']} (folder missing)")
            continue
        stats = render_chat_page(chat)
        chat_stats.append((chat, stats))
        print(f"  → {chat['out']}: {stats['messages']} messages, {stats['days']} days, senders: {stats['senders']}")
    build_index(chat_stats)
    print(f"  → index.html: {len(chat_stats)} chats")


if __name__ == "__main__":
    main()
