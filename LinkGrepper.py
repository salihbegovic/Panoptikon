# get_links_from_telegram_live.py
#
# - Fetch existing messages from the Telegram chat (via invite link)
# - Extract all URLs
# - Keep unique links in AllLinks.txt (across restarts)
# - Write EVERY YouTube URL occurrence to youtube_links.txt (duplicates allowed)
# - Files are kept in REVERSE ORDER (newest at top)
# - New links are PREPENDED to files
#
# Requirements:
#   pip install telethon

import re
import os
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.errors import rpcerrorlist


# ---------- CONFIG ----------
api_id = 31184561
api_hash = "a9bfdde6cfe48313a46cc895ab3217ee"
session_name = "panoptikon_links"

INVITE_LINK = "https://t.me/+VSZz8Z5oo_w2MDRk"
MESSAGE_LIMIT = None
# ----------------------------

URL_REGEX = re.compile(r'(https?://[^\s<>\]\)"]+)', re.IGNORECASE)

ALL_LINKS_FILE = "AllLinks.txt"
YOUTUBE_LINKS_FILE = "youtube_links.txt"


# ---------- HELPERS ----------

def ensure_file_exists(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8"):
            pass


def is_youtube(url: str) -> bool:
    try:
        u = urlparse(url)
    except Exception:
        return False
    host = (u.hostname or "").lower()
    return host.endswith("youtube.com") or host.endswith("youtu.be")


def read_file_lines(path):
    ensure_file_exists(path)
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f if line.strip()]


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def prepend_lines(path, new_lines):
    if not new_lines:
        return
    existing = read_file_lines(path)
    write_lines(path, new_lines + existing)


def load_existing_all_links():
    return set(read_file_lines(ALL_LINKS_FILE))


# ---------- MAIN ----------

async def main():
    ensure_file_exists(ALL_LINKS_FILE)
    ensure_file_exists(YOUTUBE_LINKS_FILE)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print("✅ Client started.")

    try:
        entity = await client.get_entity(INVITE_LINK)
    except Exception as e:
        print(f"❌ Failed to resolve chat: {e}")
        return

    print(f"📨 Fetching messages from: {getattr(entity, 'title', str(entity))}")

    seen_all = load_existing_all_links()

    # ---------- INITIAL FETCH ----------
    unique_all_newest_first = []
    yt_newest_first = []

    async for msg in client.iter_messages(entity, limit=MESSAGE_LIMIT):
        text = msg.message or ""
        if not text:
            continue

        for match in URL_REGEX.findall(text):
            url = match.strip().rstrip(").,;\"'<>]")
            if not url:
                continue

            # newest-first by default
            if url not in seen_all:
                seen_all.add(url)
                unique_all_newest_first.append(url)

            if is_youtube(url):
                yt_newest_first.append(url)

    # Write newest-first
    prepend_lines(ALL_LINKS_FILE, unique_all_newest_first)
    prepend_lines(YOUTUBE_LINKS_FILE, yt_newest_first)

    print("✅ Initial fetch done.")
    print(f"🧩 AllLinks.txt +{len(unique_all_newest_first)}")
    print(f"🎬 youtube_links.txt +{len(yt_newest_first)}")

    # ---------- LIVE LISTENER ----------
    async def handle_new_message(event):
        text = event.raw_text or ""
        if not text:
            return

        prepend_all = []
        prepend_yt = []

        for match in URL_REGEX.findall(text):
            url = match.strip().rstrip(").,;\"'<>]")
            if not url:
                continue

            if url not in seen_all:
                seen_all.add(url)
                prepend_all.append(url)

            if is_youtube(url):
                prepend_yt.append(url)

        if prepend_all:
            prepend_lines(ALL_LINKS_FILE, prepend_all)

        if prepend_yt:
            prepend_lines(YOUTUBE_LINKS_FILE, prepend_yt)

        if prepend_all or prepend_yt:
            print("\n[NEW MESSAGE]")
            if prepend_all:
                print(f"  🧩 AllLinks.txt +{len(prepend_all)} (prepended)")
            if prepend_yt:
                print(f"  🎬 youtube_links.txt +{len(prepend_yt)} (prepended)")
                for u in prepend_yt:
                    print("     ", u)

    client.add_event_handler(handle_new_message, events.NewMessage(chats=entity))

    print("📡 Listening for new messages...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
