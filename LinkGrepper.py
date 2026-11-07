# get_links_from_telegram_live.py
#
# - Fetch existing messages from multiple Telegram chats (via invite links)
# - Extract all URLs
# - Keep unique links in AllLinks.txt (across restarts, across all chats)
# - Write EVERY YouTube URL occurrence to per-chat youtube_links*.txt (duplicates allowed)
# - Files are kept in REVERSE ORDER (newest at top)
# - New links are PREPENDED to files
#
# Requirements:
#   pip install telethon

import re
import os
from urllib.parse import urlparse
from telethon import TelegramClient, events


# ---------- CONFIG ----------
api_id = 31184561
api_hash = "a9bfdde6cfe48313a46cc895ab3217ee"
session_name = "panoptikon_links"

# Add the two new invite links here
CHATS = [
    {
        "name": "panoptikon",
        "invite": "https://t.me/+VSZz8Z5oo_w2MDRk",
        "yt_file": "youtube_links.txt",
    },
    {
        "name": "panoptikon 2",
        "invite": "https://t.me/+r0e1dkSwJyxhYjM0",
        "yt_file": "youtube_links2.txt",
    },
    {
        "name": "panoptikon 3",
        "invite": "https://t.me/+xtRkaiLmTmIwMDY0",
        "yt_file": "youtube_links3.txt",
    },
]

MESSAGE_LIMIT = None  # None = no limit
# ----------------------------

URL_REGEX = re.compile(r'(https?://[^\s<>\]\)"]+)', re.IGNORECASE)

ALL_LINKS_FILE = "AllLinks.txt"


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


def extract_urls(text: str):
    urls = []
    for match in URL_REGEX.findall(text or ""):
        url = match.strip().rstrip(").,;\"'<>]")
        if url:
            urls.append(url)
    return urls


# ---------- MAIN ----------

async def main():
    ensure_file_exists(ALL_LINKS_FILE)
    for c in CHATS:
        ensure_file_exists(c["yt_file"])

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print("✅ Client started.")

    # Resolve entities for all chats
    entities = []
    for c in CHATS:
        try:
            entity = await client.get_entity(c["invite"])
            entities.append((c, entity))
            print(f"✅ Resolved: {c['name']} -> {getattr(entity, 'title', str(entity))}")
        except Exception as e:
            print(f"❌ Failed to resolve {c['name']} ({c['invite']}): {e}")

    if not entities:
        print("❌ No chats resolved. Check your invite links.")
        return

    seen_all = load_existing_all_links()

    # ---------- INITIAL FETCH (per chat) ----------
    for c, entity in entities:
        print(f"\n📨 Fetching messages from: {c['name']} ({getattr(entity, 'title', str(entity))})")

        unique_all_newest_first = []
        yt_newest_first = []

        async for msg in client.iter_messages(entity, limit=MESSAGE_LIMIT):
            text = msg.message or ""
            if not text:
                continue

            for url in extract_urls(text):
                # newest-first by default
                if url not in seen_all:
                    seen_all.add(url)
                    unique_all_newest_first.append(url)

                if is_youtube(url):
                    yt_newest_first.append(url)

        prepend_lines(ALL_LINKS_FILE, unique_all_newest_first)
        prepend_lines(c["yt_file"], yt_newest_first)

        print("✅ Initial fetch done.")
        print(f"🧩 AllLinks.txt +{len(unique_all_newest_first)}")
        print(f"🎬 {c['yt_file']} +{len(yt_newest_first)}")

    # ---------- LIVE LISTENER ----------
    async def handle_new_message(event, chat_config):
        text = event.raw_text or ""
        if not text:
            return

        prepend_all = []
        prepend_yt = []

        for url in extract_urls(text):
            if url not in seen_all:
                seen_all.add(url)
                prepend_all.append(url)

            if is_youtube(url):
                prepend_yt.append(url)

        if prepend_all:
            prepend_lines(ALL_LINKS_FILE, prepend_all)

        if prepend_yt:
            prepend_lines(chat_config["yt_file"], prepend_yt)

        if prepend_all or prepend_yt:
            print(f"\n[NEW MESSAGE] {chat_config['name']}")
            if prepend_all:
                print(f"  🧩 AllLinks.txt +{len(prepend_all)} (prepended)")
            if prepend_yt:
                print(f"  🎬 {chat_config['yt_file']} +{len(prepend_yt)} (prepended)")
                for u in prepend_yt:
                    print("     ", u)

    # Register one handler per chat so we know which output file to use
    for c, entity in entities:
        client.add_event_handler(
            lambda e, c=c: handle_new_message(e, c),
            events.NewMessage(chats=entity),
        )

    print("\n📡 Listening for new messages in all chats...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

