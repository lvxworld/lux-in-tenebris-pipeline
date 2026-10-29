---
name: scout-official
description: "V2 scout: Official AI lab blogs. Returns JSON array."
---

# Scout V2 — Official Blogs

## Sources
Read `skills/_shared/sources.md` with `read_file`, find the
`## Scout Official Blogs (\`scout-official\`)` section, and take the array
from the `json` code block right under it — that's the current list (single
source of truth; don't hardcode it here, it drifts out of sync with the
file otherwise).

## Method
web_fetch each URL from that list. Scan for posts dated within [yesterday, today].

**🔴 Report the article's OWN publish date, never today's date.** Read the date off the
page itself — the eyebrow line, the byline, or the `<time datetime="…">` element. If the
page shows no date, or shows a date **older than the window**, **DROP the item** — do not
stamp it with yesterday/today to make it fit. Lab newsrooms and RSS feeds re-surface old
posts, and a stale item dated as fresh will be believed: on 2026-10-28 an Anthropic Opus 5.5
post from **Sep 22** was reported as `2026-10-27`, passed the editor's 7-day dedup, and
became the front-page lead of a paper that had already covered that launch in issues #90
and #94.

## Output contract
Return ONLY a JSON array (no prose, no fences). Each element:
```json
{"title":"…","summary":"1–2 factual sentences","source":"Lab name",
 "url":"https://…","date":"YYYY-MM-DD","beat":"official","signal":1-5}
```

## Signal guide
- Official blog posts are HIGH signal by default (3+). These are announcements, not rumours.
- Major model releases / policy announcements: 4–5
- Minor feature updates: 3

## Rules
- Every `url` MUST come from the actual fetched page. Never synthesize URLs.
- If a blog is unreachable, skip it silently.
- Return `[]` if nothing found in-window. All content in ENGLISH.

## Link-Source Validation (MANDATORY — run before writing final JSON)

After gathering all items but BEFORE writing the final JSON, validate EVERY item:

1. **Domain consistency:** Extract the domain from `url`. The `source` field and the URL domain must be aligned:
   - ✓ source="TechCrunch", url="https://techcrunch.com/..." — domain "techcrunch.com" matches
   - ✓ source="Hacker News", url="https://news.ycombinator.com/..." — "ycombinator" in URL
   - ✓ source="arXiv", url="https://arxiv.org/abs/..." — "arxiv" in both
   - ✓ source="@karpathy" / "Karpathy", url="https://x.com/..." — exception for X/Twitter users
   - ✗ source="Hacker News", url="https://medium.com/..." — domain doesn't match
   - ✗ source="TechCrunch", url="https://someothersite.com/..." — domain doesn't match

2. **Auto-fix on mismatch (max 3 attempts per item):** If source and URL domain don't align, use `web_search` with the article title + source name to find the real URL. Each attempt = one search cycle.

3. **Discard unfixable items:** After 3 failed attempts, REMOVE the item from your array. Do NOT keep items with mismatched source↔url.

4. **No placeholder URLs:** Never use "#", empty strings, or null as URLs. If a real URL can't be found after 3 attempts, discard the item entirely.
