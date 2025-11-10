# get_links_from_telegram.py
#
# Modified: Save links from newest to oldest (message order)
#
# Usage:
#   1. pip install telethon
#   2. Fill in api_id and api_hash below.
#   3. python get_links_from_telegram.py
#
# Output:
#   - links.txt          -> every unique link (newest → oldest)
#   - youtube_links.txt  -> only unique YouTube links (newest → oldest)

import re
from urllib.parse import urlparse
from telethon import TelegramClient
from telethon.errors import rpcerrorlist

# ---------- CONFIG ----------
api_id = 31184561
api_hash = "a9bfdde6cfe48313a46cc895ab3217ee"
session_name = "panoptikon_links"

INVITE_LINK = "https://t.me/+VSZz8Z5oo_w2MDRk"
MESSAGE_LIMIT = None
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

async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()

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

    seen_links = set()
    all_links_ordered = []
    youtube_links_ordered = []

    async for msg in client.iter_messages(entity, limit=MESSAGE_LIMIT):
        text = msg.message or ""
        if not text:
            continue

        for match in URL_REGEX.findall(text):
            url = match.strip().rstrip(").,;\"'<>]")
            if not url or url in seen_links:
                continue

            seen_links.add(url)
            all_links_ordered.append(url)
            if is_youtube(url):
                youtube_links_ordered.append(url)

    # Messages are fetched newest → oldest by default, so just write in order
    with open("links.txt", "w", encoding="utf-8") as f:
        for url in all_links_ordered:
            f.write(url + "\n")

    with open("youtube_links.txt", "w", encoding="utf-8") as f:
        for url in youtube_links_ordered:
            f.write(url + "\n")

    print(f"Done. Found {len(all_links_ordered)} unique links total.")
    print(f"      {len(youtube_links_ordered)} unique YouTube links.")
    print("Saved to links.txt and youtube_links.txt")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

