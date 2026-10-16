import os
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

START = "<!-- DAILY-VERSE:START -->"
END = "<!-- DAILY-VERSE:END -->"

API_BASE = "https://api.youversion.com/v1"
TIMEZONE = ZoneInfo("Asia/Manila")
BIBLE_ID = 3034  # Berean Standard Bible


def api_get(path):
    api_key = os.environ.get("YVP_APP_KEY")

    if not api_key:
        raise RuntimeError("Missing YVP_APP_KEY GitHub secret.")

    request = Request(
        f"{API_BASE}{path}",
        headers={
            "X-YVP-App-Key": api_key,
            "Accept": "application/json",
        },
    )

    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_daily_passage(day_of_year):
    data = api_get(f"/verse-of-the-days/{day_of_year}")
    passage_id = data.get("passage_id")

    if not passage_id:
        raise RuntimeError("No daily passage ID returned by the API.")

    return passage_id


def get_passage(passage_id):
    safe_id = quote(passage_id, safe=".")
    data = api_get(
        f"/bibles/{BIBLE_ID}/passages/{safe_id}?format=text"
    )

    verse = data.get("content", "").strip()
    reference = data.get("reference", "").strip()

    if not verse or not reference:
        raise RuntimeError("The API returned incomplete passage data.")

    # Keep the verse safe to insert into HTML.
    verse = re.sub(r"\s+", " ", verse)
    verse = (
        verse.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

    return verse, reference


def main():
    now = datetime.now(TIMEZONE)
    passage_id = get_daily_passage(now.timetuple().tm_yday)
    verse, reference = get_passage(passage_id)

    bible_url = (
        f"https://www.bible.com/bible/{BIBLE_ID}/"
        f"{quote(passage_id, safe='.')}"
    )

    section = f"""\
{START}
<h2>𓆩♡𓆪 𝓐 𝓦𝓸𝓻𝓭 𝓯𝓸𝓻 𝓣𝓸𝓭𝓪𝔂 𓆩♡𓆪</h2>

<p><sub>✧ {now.strftime("%A · %B %d, %Y").upper()} ✧</sub></p>

<p><i>“{verse}”</i></p>

<p><b>— {reference} (BSB)</b></p>

<p><a href="{bible_url}">♡ Read today's passage on Bible.com ♡</a></p>
{END}"""

    if not README.exists():
        raise FileNotFoundError("README.md was not found.")

    content = README.read_text(encoding="utf-8")

    if content.count(START) != 1 or content.count(END) != 1:
        raise RuntimeError(
            "README.md must contain exactly one START and one END marker."
        )

    start_index = content.index(START)
    end_index = content.index(END)

    if end_index < start_index:
        raise RuntimeError("The README markers are in the wrong order.")

    end_index += len(END)
    updated = content[:start_index] + section + content[end_index:]

    if updated != content:
        README.write_text(updated, encoding="utf-8")
        print(f"Daily verse updated: {reference}")
    else:
        print("The README already contains the current verse.")


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError) as error:
        raise SystemExit(f"Daily verse update failed: {error}") from error
