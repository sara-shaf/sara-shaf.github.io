#!/usr/bin/env python3
"""
Fetches Sara Shafiee's publication list from the public ORCID API
and rewrites the section of README.md between the markers:
  <!--PUBLICATIONS:START--> ... <!--PUBLICATIONS:END-->

Uses only the Python standard library (no pip installs needed in CI).
"""
import json
import re
import urllib.request
from pathlib import Path

ORCID_ID = "0000-0001-9433-5060"
API_URL = f"https://pub.orcid.org/v3.0/{ORCID_ID}/works"
README_PATH = Path(__file__).resolve().parent.parent / "README.md"
MAX_ITEMS = 8

START_MARKER = "<!--PUBLICATIONS:START-->"
END_MARKER = "<!--PUBLICATIONS:END-->"


def fetch_works():
    req = urllib.request.Request(API_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    return data.get("group", [])


def extract_entry(group):
    """Pull the most useful work-summary out of a group (ORCID groups duplicate
    submissions of the same work together)."""
    summaries = group.get("work-summary", [])
    if not summaries:
        return None
    summary = summaries[0]

    title = (
        summary.get("title", {})
        .get("title", {})
        .get("value", "Untitled")
    )
    journal = (summary.get("journal-title") or {}).get("value")
    date = summary.get("publication-date") or {}
    year = (date.get("year") or {}).get("value")

    doi = None
    for eid in (summary.get("external-ids") or {}).get("external-id", []):
        if eid.get("external-id-type") == "doi":
            doi = eid.get("external-id-value")
            break

    link = f"https://doi.org/{doi}" if doi else f"https://orcid.org/{ORCID_ID}"

    sort_key = year or "0"
    return sort_key, title, journal, year, link


def format_line(entry):
    _, title, journal, year, link = entry
    meta = " · ".join(x for x in (journal, year) if x)
    if meta:
        return f"- [{title}]({link}) — {meta}"
    return f"- [{title}]({link})"


def main():
    groups = fetch_works()
    entries = [extract_entry(g) for g in groups]
    entries = [e for e in entries if e]
    entries.sort(key=lambda e: e[0], reverse=True)
    top = entries[:MAX_ITEMS]

    if not top:
        lines = ["- (No publications found via ORCID — check the API response.)"]
    else:
        lines = [format_line(e) for e in top]

    block = "\n".join(lines)

    text = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{block}\n{END_MARKER}"
    new_text = pattern.sub(replacement, text)

    README_PATH.write_text(new_text, encoding="utf-8")
    print(f"Updated README with {len(top)} publications.")


if __name__ == "__main__":
    main()
