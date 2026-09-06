#!/usr/bin/env python3
"""
Fetches a random quote and writes it between the QUOTE markers in ReadMe.md.
Run daily by .github/workflows/update-quote.yml.
"""

import os
import re
import json
import urllib.request
import urllib.error

README_PATH = os.environ.get("README_PATH", "ReadMe.md")

START_MARKER = "<!-- QUOTE:START -->"
END_MARKER = "<!-- QUOTE:END -->"

# zenquotes.io is the primary — reliable, no key required.
API_URL = "https://zenquotes.io/api/random"
# quotable.io kept as a secondary fallback.
FALLBACK_URL = "https://api.quotable.io/random"


def fetch_quote():
    req = urllib.request.Request(API_URL, headers={"User-Agent": "readme-bot"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            item = data[0]
            return item["q"], item["a"]
    except Exception as e:
        print(f"WARN: primary quote API failed ({e}), trying fallback")

    req = urllib.request.Request(FALLBACK_URL, headers={"User-Agent": "readme-bot"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data["content"], data["author"]
    except Exception as e:
        print(f"WARN: fallback quote API also failed ({e})")
        return "Building things, breaking things, fixing things.", "Pankaj"


def main():
    quote, author = fetch_quote()
    block = (
        f"{START_MARKER}\n"
        f"> {quote}\n"
        f">\n"
        f"> — {author}\n"
        f"{END_MARKER}"
    )

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )

    if pattern.search(content):
        new_content = pattern.sub(block, content)
    else:
        # Markers not found yet — append a new section at the end.
        new_content = content.rstrip() + "\n\n## 💭 Thought of the Day\n\n" + block + "\n"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated quote: \"{quote}\" — {author}")


if __name__ == "__main__":
    main()
