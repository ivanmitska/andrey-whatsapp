#!/usr/bin/env python3
"""Translate one WhatsApp chat to Thai using Google Translate (deep-translator).

Caches every translation by hash → re-runs are free. Skips messages already in Thai.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parent
TR_DIR = ROOT / "translations"
TR_DIR.mkdir(exist_ok=True)

# Reuse parsing logic from build_chat
sys.path.insert(0, str(ROOT))
from build_chat import (  # noqa: E402
    parse_messages, detect_format, find_txt,
    ATTACH_RE_IOS, ATTACH_RE_ANDROID, LRM,
    folder_display_name, slugify, _normalize_ws, CHAT_PREFIXES,
)

URL_RE = re.compile(r'https?://\S+')
THAI_RANGE = (0x0E00, 0x0E7F)


def thai_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    thai = sum(1 for c in letters if THAI_RANGE[0] <= ord(c) <= THAI_RANGE[1])
    return thai / len(letters)


def needs_translation(text: str) -> bool:
    if not text or len(text.strip()) < 2:
        return False
    stripped = URL_RE.sub("", text).strip()
    if len(stripped) < 2:
        return False
    if not any(c.isalpha() for c in stripped):
        return False
    if thai_ratio(stripped) > 0.55:
        return False
    return True


def find_chat(name_query: str):
    q = name_query.lower()
    candidates = []
    for entry in sorted(ROOT.iterdir()):
        if not entry.is_dir():
            continue
        normalized = _normalize_ws(entry.name)
        if not any(normalized.startswith(p) for p in CHAT_PREFIXES):
            continue
        display = folder_display_name(entry.name)
        slug = slugify(display)
        candidates.append((entry, display, slug))
    # 1. Exact match wins (so "tooni" doesn't match "toonii" by substring)
    for entry, display, slug in candidates:
        if q == slug or q == display.lower():
            return entry, display, slug
    # 2. Substring fallback
    for entry, display, slug in candidates:
        if q in slug or q in display.lower():
            return entry, display, slug
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chat", help="Chat slug or display-name substring (e.g. 'alisa', 'alisa-advokat')")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of new translations (0 = all)")
    ap.add_argument("--delay", type=float, default=0.15, help="Sleep between requests (sec)")
    ap.add_argument("--save-every", type=int, default=15, help="Save cache every N translations")
    args = ap.parse_args()

    found = find_chat(args.chat)
    if not found:
        print(f"No chat folder matched '{args.chat}'.")
        sys.exit(1)
    folder, display, slug = found
    print(f"Chat: {display}  →  slug: {slug}")

    txt = find_txt(folder)
    raw = txt.read_text(encoding="utf-8")
    fmt = detect_format(raw)
    attach_re = ATTACH_RE_ANDROID if fmt == "android" else ATTACH_RE_IOS
    msgs = parse_messages(txt, fmt)
    print(f"Parsed {len(msgs)} messages, format={fmt}")

    cache_path = TR_DIR / f"{slug}.json"
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"Loaded cache: {len(cache)} entries from {cache_path.name}")
    else:
        cache = {}

    # Collect unique texts that need translation
    unique = []
    seen = set()
    for m in msgs:
        text_only = attach_re.sub("", m["body"]).strip().replace(LRM, "").strip()
        if not needs_translation(text_only):
            continue
        if text_only in seen:
            continue
        seen.add(text_only)
        h = hashlib.sha1(text_only.encode("utf-8")).hexdigest()[:16]
        if h in cache:
            continue
        unique.append((h, text_only))

    print(f"Unique non-Thai texts to translate: {len(unique)}")
    if args.limit:
        unique = unique[: args.limit]
        print(f"  → limited to {len(unique)} for this run")

    tr = GoogleTranslator(source="auto", target="th")
    total = len(unique)
    errors = 0
    consecutive_errors = 0
    for i, (h, text) in enumerate(unique, 1):
        chunk = text[:4800]  # Google ~5000 char limit
        backoff = args.delay
        translated = None
        for attempt in range(4):
            try:
                translated = tr.translate(chunk)
                consecutive_errors = 0
                break
            except Exception as e:
                errors += 1
                consecutive_errors += 1
                wait = min(60, 5 * (2 ** attempt))
                print(f"  [{i}/{total}] ERROR (attempt {attempt+1}): {type(e).__name__}: {e}; sleep {wait}s",
                      flush=True)
                time.sleep(wait)
        if translated is None:
            print(f"  [{i}/{total}] FAILED after retries, skipping", flush=True)
            if consecutive_errors >= 5:
                print("  Too many consecutive errors — saving cache and stopping", flush=True)
                break
            continue
        cache[h] = translated
        if i <= 5 or i % 25 == 0 or i == total:
            preview = (translated or "")[:80].replace("\n", " ")
            src_preview = text[:60].replace("\n", " ")
            print(f"  [{i}/{total}] {src_preview!r} → {preview!r}", flush=True)
        if i % args.save_every == 0:
            cache_path.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        time.sleep(backoff)

    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\nDone. {len(cache)} translations in {cache_path}, errors: {errors}")


if __name__ == "__main__":
    main()
