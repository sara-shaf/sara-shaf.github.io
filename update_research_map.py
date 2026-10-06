"""Weekly updater for research-map-data.json (Sara Shafiee's research map).

Fetches works from ORCID, adds papers that are not yet on the map, assigns each new
paper to a theme by keywords, and writes research-map-data.json.
Existing entries are never removed, so manual corrections stay in place.
"""
import json, re, sys, urllib.request

ORCID_ID = "0000-0001-9433-5060"
DATA_FILE = "research-map-data.json"

# Titles to keep off the map (lower-case, start of title is enough).
EXCLUDE = [
    "retraction note",
    "improving financial literacy and supporting financial decisions",  # retracted
]

# Theme rules: first match wins; the last rule catches everything else.
THEME_RULES = [
    ("ai",    r"agentic|generative ai|synthetic data|deep learning|anomaly|llm|large language|judge|neural|machine learning(?!.*recommender)|simulation-based|manufacturing system reconfiguration|product and manufacturing design"),
    ("rec",   r"recommender|recommendation|bert|online reviews|consumer|co-demanded|community|user implicit|co-creation|customisation model|innovation strategy|expert systems|generative ai products"),
    ("aec",   r"\baec\b|construction|modulari|building|off-site|facade|fa\u00e7ade"),
    ("agile", r"scrum|agile|design thinking|model-driven|behavio[u]?r-driven|rational unified|computer-aided software|user-cent|use-oriented|knowledge domains|ui/ux|traditional versus"),
    ("org",   r"digital transformation|organi[sz]ation|leadership|team learning|reintegration|patient|resistance to innovation|supply chain|well-being"),
    ("pcs",   r"."),
]

# Extra details for specific papers (matched by start of title, lower-case).
EXTRAS = {
    "agentic data analysis for intelligent manufacturing": {"code": "https://github.com/Nastaran95/agentic-man-da"},
    "evaluating agentic ai systems in manufacturing": {"code": "https://github.com/Nastaran95/manufacturing-agentic-evaluation"},
    "cpjudgebench": {"code": "https://github.com/Nastaran95/CPJudgeBench"},
}


def norm(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())[:70]


def theme_for(title):
    tl = title.lower()
    for key, rx in THEME_RULES:
        if re.search(rx, tl):
            return key
    return "pcs"


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "research-map-updater"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def orcid_works():
    data = get(f"https://pub.orcid.org/v3.0/{ORCID_ID}/works")
    out = []
    for g in data.get("group", []):
        s = (g.get("work-summary") or [{}])[0]
        title = (((s.get("title") or {}).get("title") or {}).get("value") or "").strip()
        if not title:
            continue
        year = (((s.get("publication-date") or {}).get("year") or {}).get("value"))
        venue = ((s.get("journal-title") or {}).get("value") or "").strip()
        doi = ""
        for eid in ((s.get("external-ids") or {}).get("external-id") or []):
            if (eid.get("external-id-type") or "").lower() == "doi":
                doi = eid.get("external-id-value") or ""
                break
        out.append({"t": title, "y": int(year) if year else None, "v": venue, "doi": doi,
                    "type": s.get("type") or "", "put": s.get("put-code")})
    return out


def authors(put_code):
    try:
        w = get(f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{put_code}")
    except Exception:
        return []
    names = []
    for c in ((w.get("contributors") or {}).get("contributor") or []):
        n = ((c.get("credit-name") or {}).get("value") or "").strip()
        if n:
            parts = n.replace(",", " ").split()
            names.append(f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else n)
    return names


def main():
    data = json.load(open(DATA_FILE, encoding="utf-8"))
    pubs = data["pubs"]
    known = {norm(p["t"]) for p in pubs}
    try:
        works = orcid_works()
    except Exception as e:
        print("Could not reach ORCID, map left unchanged:", e)
        return 0
    added = 0
    for w in works:
        tl = w["t"].lower()
        if not w["y"] or any(tl.startswith(x) for x in EXCLUDE) or norm(w["t"]) in known:
            continue
        rec = {"t": w["t"], "y": w["y"], "v": w["v"], "a": authors(w["put"]) or ["S. Shafiee"],
               "j": w["type"] == "journal-article", "th": theme_for(w["t"])}
        if w["doi"]:
            rec["doi"] = w["doi"]
        for k, extra in EXTRAS.items():
            if tl.startswith(k):
                rec.update(extra)
        pubs.append(rec)
        known.add(norm(w["t"]))
        added += 1
        print("Added:", w["y"], w["t"])
    # attach DOIs from ORCID to existing entries that lack one
    by = {norm(w["t"]): w for w in works}
    for p in pubs:
        w = by.get(norm(p["t"]))
        if w and w["doi"] and not p.get("doi"):
            p["doi"] = w["doi"]
    pubs.sort(key=lambda p: (-p["y"], p["t"]))
    json.dump(data, open(DATA_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Done: {added} new publication(s), {len(pubs)} in total.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
