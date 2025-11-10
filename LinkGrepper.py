# get_links_from_telegram_live.py
#
# - Fetch existing links from the Telegram chat (via invite link)
# - Save unique links (newest -> oldest, same as your working script)
# - Then listen for new messages in that chat and append new unique links
#
# Requirements:
#   pip install telethon
#
# Output:
#   - AllLinks.txt         -> every unique link (newest → oldest on initial run, then appended)
#   - youtube_links.txt    -> only unique YouTube links

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
MESSAGE_LIMIT = None  # None = all available
# ----------------------------

URL_REGEX = re.compile(
    r'(https?://[^\s<>\]\)"]+)',
    re.IGNORECASE
)


def is_youtube(url: str) -> bool:
    try:
        u = urlparse(url)
    except Exception:
        return False
    host = (u.hostname or "").lower()
    return host.endswith("youtube.com") or host.endswith("youtu.be")


def load_existing_links_from_files():
    """
    If you restart the script, we don't want to re-add the same URLs.
    Reads from AllLinks.txt and youtube_links.txt if they exist.
    """
    existing = set()

    def read_file(path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url:
                        existing.add(url)

    read_file("AllLinks.txt")
    read_file("youtube_links.txt")
    return existing


def append_links(all_links, youtube_links):
    if all_links:
        with open("AllLinks.txt", "a", encoding="utf-8") as f:
            for url in all_links:
                f.write(url + "\n")

    if youtube_links:
        with open("youtube_links.txt", "a", encoding="utf-8") as f:
            for url in youtube_links:
                f.write(url + "\n")


async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()
    print("Client started.")

    # Resolve the chat from invite link
    try:
        entity = await client.get_entity(INVITE_LINK)
    except rpcerrorlist.InviteHashExpiredError:
        print("Invite link is expired or invalid.")
        return
    except rpcerrorlist.InviteHashInvalidError:
        print("Invite link is invalid.")
        return
    except Exception as e:
        print(f"Could not resolve chat from invite link: {e}")
        return

    print(f"Fetching messages from: {getattr(entity, 'title', str(entity))}")

    # Track seen links (include existing from disk so no dupes between runs)
    seen_links = load_existing_links_from_files()

    # ---------- INITIAL FETCH (your original behavior) ----------
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

    # Messages are newest → oldest by default; we keep that order
    append_links(new_links, new_yt_links)

    print(f"Initial fetch done.")
    print(f"New links this run: {len(new_links)}")
    print(f"New YouTube links this run: {len(new_yt_links)}")
    print(f"Total unique links known: {len(seen_links)}")

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

        print(f"[NEW MESSAGE] {len(added)} new link(s):")
        for u in added:
            print("   ", u)

    # Only listen to messages from THIS chat
    client.add_event_handler(handle_new_message, events.NewMessage(chats=entity))

    print("Now listening for new messages in that chat...")
    # This "hangs" by design: it's the long-running listener loop.
    await client.run_until_disconnected()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

