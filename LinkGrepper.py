# get_links_from_telegram_live.py
#
# - Fetch existing messages from the Telegram chat (via invite link)
# - Extract all URLs, filter YouTube links
# - Keep unique links across restarts (via AllLinks.txt / youtube_links.txt)
# - Then listen live and append new unique links as they arrive
#
# Requirements:
#   pip install telethon
#
# Output files (in same folder as index.html):
#   - AllLinks.txt         -> every unique URL from the chat
#   - youtube_links.txt    -> every unique YouTube URL (this is what index.html reads)

import re
import os
from urllib.parse import urlparse
from telethon import TelegramClient, events
from telethon.errors import rpcerrorlist


# ---------- CONFIG ----------
api_id = 31184561  # replace if needed
api_hash = "a9bfdde6cfe48313a46cc895ab3217ee"  # replace if needed
session_name = "panoptikon_links"

INVITE_LINK = "https://t.me/+VSZz8Z5oo_w2MDRk"  # your chat's invite link
MESSAGE_LIMIT = None  # None = all available history
# ----------------------------

URL_REGEX = re.compile(r'(https?://[^\s<>\]\)"]+)', re.IGNORECASE)

ALL_LINKS_FILE = "AllLinks.txt"
YOUTUBE_LINKS_FILE = "youtube_links.txt"


# ---------- HELPER FUNCTIONS ----------

def ensure_file_exists(path):
    """Create the file if it doesn't exist."""
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("")  # create empty file


def is_youtube(url: str) -> bool:
    try:
        u = urlparse(url)
    except Exception:
        return False
    host = (u.hostname or "").lower()
    return host.endswith("youtube.com") or host.endswith("youtu.be")


def load_existing_links_from_files():
    """
    Make sure we don't re-add URLs across restarts.
    Ensures files exist before reading.
    """
    ensure_file_exists(ALL_LINKS_FILE)
    ensure_file_exists(YOUTUBE_LINKS_FILE)

    existing = set()
    for path in (ALL_LINKS_FILE, YOUTUBE_LINKS_FILE):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url:
                        existing.add(url)
        except Exception as e:
            print(f"Warning: could not read {path}: {e}")
    return existing


def append_links(all_links, youtube_links):
    """Append new links to the files, creating them if needed."""
    ensure_file_exists(ALL_LINKS_FILE)
    ensure_file_exists(YOUTUBE_LINKS_FILE)

    if all_links:
        with open(ALL_LINKS_FILE, "a", encoding="utf-8") as f:
            for url in all_links:
                f.write(url + "\n")

    if youtube_links:
        with open(YOUTUBE_LINKS_FILE, "a", encoding="utf-8") as f:
            for url in youtube_links:
                f.write(url + "\n")


# ---------- MAIN ----------

async def main():
    # Ensure output files exist
    ensure_file_exists(ALL_LINKS_FILE)
    ensure_file_exists(YOUTUBE_LINKS_FILE)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print("✅ Client started.")

    # Resolve the chat from invite link
    try:
        entity = await client.get_entity(INVITE_LINK)
    except rpcerrorlist.InviteHashExpiredError:
        print("❌ Invite link is expired or invalid.")
        return
    except rpcerrorlist.InviteHashInvalidError:
        print("❌ Invite link is invalid.")
        return
    except Exception as e:
        print(f"❌ Could not resolve chat from invite link: {e}")
        return

    print(f"📨 Fetching messages from: {getattr(entity, 'title', str(entity))}")

    seen_links = load_existing_links_from_files()

    # ---------- INITIAL FETCH ----------
    new_links = []
    new_yt_links = []

    async for msg in client.iter_messages(entity, limit=MESSAGE_LIMIT):
        text = msg.message or ""
        if not text:
            continue

        for match in URL_REGEX.findall(text):
            url = match.strip().rstrip(").,;\"'<>]")
            if not url or url in seen_links:
                continue

            seen_links.add(url)
            new_links.append(url)
            if is_youtube(url):
                new_yt_links.append(url)

    append_links(new_links, new_yt_links)

    print("✅ Initial fetch done.")
    print(f"🧩 New links this run: {len(new_links)}")
    print(f"🎬 New YouTube links this run: {len(new_yt_links)}")
    print(f"📦 Total unique links known: {len(seen_links)}")

    # ---------- LIVE LISTENER ----------
    async def handle_new_message(event):
        text = event.raw_text or ""
        if not text:
            return

        added = []
        added_yt = []

        for match in URL_REGEX.findall(text):
            url = match.strip().rstrip(").,;\"'<>]")
            if not url or url in seen_links:
                continue

            seen_links.add(url)
            added.append(url)
            if is_youtube(url):
                added_yt.append(url)

        if not added:
            return

        append_links(added, added_yt)

        print(f"\n[NEW MESSAGE] {len(added)} new link(s):")
        for u in added:
            print("   ", u)

    client.add_event_handler(handle_new_message, events.NewMessage(chats=entity))

    print("📡 Now listening for new messages in that chat...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

