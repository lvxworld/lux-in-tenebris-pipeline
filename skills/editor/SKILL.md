---
name: editor
description: "V2 editor-in-chief. Merges scout JSONs into edition.json. Run after scouts complete."
---

# Editor V2 — Assembly

## When to use
After all 9 scouts have persisted their JSON to `/tmp/v2/scouts/`. The orchestrator calls you.

## Files to read
- `/tmp/v2/scouts/scout_x.json` (array)
- `/tmp/v2/scouts/scout_research.json` (array)
- `/tmp/v2/scouts/scout_official.json` (array)
- `/tmp/v2/scouts/scout_opensource.json` (**OBJECT** with `editorial` array + `trending` object)
- `/tmp/v2/scouts/scout_tools.json` (array)
- `/tmp/v2/scouts/scout_funding.json` (array)
- `/tmp/v2/scouts/scout_hardware.json` (array)
- `/tmp/v2/scouts/scout_youtube.json` (array)
- `/tmp/v2/scouts/scout_italia.json` (array)
- `/tmp/v2/free_models.json` (**OBJECT**, `openrouter` + `opencode_zen` sub-objects, pass through
  unchanged — like `trending`, this is produced by a deterministic non-LLM fetch
  (`fetch_free_models.py`), not one of the 9 scouts. If the file is missing, skip
  the `free_models` key entirely rather than inventing one.)
- **`headlines_history.json`** — `$DEPLOY_DIR/headlines_history.json` (path passed in the prompt).
  Holds every headline published so far. Use it for **cross-day deduplication**
  (step 4b) — do not republish a story already covered in the last 7 days.
- Date parameters in `/tmp/v2/scouts/_metadata.json` (produced by orchestrator)

## Workflow

1. Read metadata JSON → get `today`, `yesterday`, `today_human`, next issue number.
2. Read all 9 scout files.
3. **Special case for opensource:** split into `editorial` array (treat like other scouts) and `trending` object (pass through to output unchanged).
3b. **Free models:** if `/tmp/v2/free_models.json` exists, pass its content through to the `free_models` key unchanged — same treatment as `trending`. No judgment, no rewriting, no filtering beyond what render.py already does for broken URLs.
4. **Merge & dedup** all editorial arrays:
   - Drop duplicates by URL and near-identical headline (keep most authoritative source)
   - Discard items clearly dated outside [yesterday, today]
   - **Tag every item with its origin:** while reading, augment each item with
     `"scout_source": "<scout_name>"` (e.g., `"research"`, `"x"`, `"official"`,
     `"tools"`, `"funding"`, `"hardware"`, `"youtube"`, `"italia"`). Opensource editorial items
     get `"opensource"`. This tag is used in step 5 for tiering.
4b. **🔴 Cross-day dedup — CRITICAL** (run this BEFORE step 5):
   - **Read `headlines_history.json`** from `$DEPLOY_DIR/headlines_history.json`
   - **Extract headlines from the last 7 days only** (look at each entry's `"date"`
     field — keep only those within `[today-7, today]`).
   - **For each candidate item** (from scouts), compare its `title` against ALL
     headlines in the 7-day window using **fuzzy matching**:
     - Normalize both: lowercase, strip punctuation, remove stopwords
       (`the`, `a`, `an`, `of`, `in`, `to`, `for`, `and`, `with`).
     - If the normalized title has **>40% word overlap** OR the **core subject
       is identical** (e.g., "OpenAI drops GPT-5.6 gates" ≈ "OpenAI releases
       GPT-5.6 with gated access"), consider it a **duplicate topic**.
   - **Action on duplicate:** **DISCARD the item entirely.** Do not include it in
     the edition at any tier. Free up that slot for a different story that wasn't
     covered yet. Even if the new source is more mainstream, the story is already
     stale — readers have seen it. Give them something fresh.
   - **How to compare:** You can use `web_search` to verify that two differently-titled
     items from different scouts cover the same underlying event. Or use your own
     judgment on topic similarity.
   - **If `headlines_history.json` does not exist yet** (first run), skip this step.
   - **🔴 Two hard rules the 7-day sweep does NOT cover — apply them before assigning any tier:**
     1. **Lead and top stories get an ALL-TIME dedup, not a 7-day one.** A model
        launch, an IPO filing, a funding round or an acquisition is news **once**.
        For every candidate you are considering for `lead` or `top_stories`, sweep the
        **entire** `headlines_history.json` (all issues, no date filter) for the same
        **event** — not the same wording. *"Anthropic launches Claude Opus 5.5 at 40%
        lower cost"* (#90) and *"Anthropic launches Claude Opus 5.5, its new frontier
        flagship"* are the same launch 35 days apart: the second one is stale, and the
        7-day window will never catch it. Match on the **subject + verb** (who did what),
        ignoring adjectives, cost claims and the source outlet.
     2. **Verify the item's own publish date — never trust the scout's `date` field for
        lab blogs.** Vendor newsrooms (Anthropic, OpenAI, Google) and RSS feeds re-surface
        old posts. If you are promoting an official-lab item to lead or top story, open
        the URL and read the page's **own** date (the eyebrow line or `<time>` element).
        If that date is older than the window, **DISCARD the item** — do not re-date it,
        do not demote it. A Sep 22 announcement must never lead the Oct 28 edition.
5. **Judge importance** and assign tiers:
   - **Before rating, use scout_source tags from step 4 to determine eligibility.**
   - `lead` (exactly 1): most consequential **mainstream** story.
     ✅ Eligible scout_sources: `x`, `official`, `tools`, `funding`, `hardware`, `youtube`
     ❌ NOT eligible: `research`, `opensource` — unless the SAME story/topic ALSO
        appears in an eligible scout (genuine cross-source mainstream coverage).
        A paper/ML-model that exists ONLY on arXiv or GitHub is **never** lead material.
     Write `kicker` (2–4 words), headline, 2–3 sentence deck.
   - `top` (0–4): next most important. Priority to mainstream sources.
     Research/opensource items can appear here ONLY if the story had genuine
     mainstream impact — i.e., covered by major outlets (NYT, Reuters, Bloomberg,
     The Verge, Ars Technica, Wired, TechCrunch, CNBC, Financial Times).
     Pure arXiv/git-only items → sections or quick_hits, never top.
     One line summary each.
   - `sections` (substantive remainder): group by beat into this order:
     1. Research & Papers (research beat)
     2. Open Source & Models (opensource editorial beat)
     3. YouTube & Video (youtube beat)
     4. Hardware & Robotics (hardware beat)
     5. Tools & Startups (tools beat)
     6. Italia AI Spotlight (italia beat)
     7. Money & Markets (funding beat)
     Skip empty sections.
       - YouTube & Video: show if ≥2 items (collapse into quick_hits only if <2).
             - Italia AI Spotlight: show if ≥2 items (collapse into quick_hits if <2).
             - All other sections: show if ≥3 items (collapse into quick_hits if <3).
     ~3–5 items per section, best first. YouTube: 2–3 items, video cards.
   - `quick_hits` (8–12): real but minor. One headline + source, no summary.
   - `trending`: pass through from opensource scout unchanged.
   - `free_models`: pass through from `/tmp/v2/free_models.json` unchanged (see step 3b).
6. **Rewrite for page**: tighten headlines, keep summaries to 1–2 sentences. Sentence case, factual, no clickbait.
7. **🔴 URL validation — CRITICAL, DO NOT SKIP**:
   - **Every single item MUST have a real `http://` or `https://` URL.** No exceptions.
   - If a scout item has `"url": ""`, `"url": "#"`, or any fragment-only/anchor URL (`"url": "#section"`), **DO NOT keep the item**. Either:
     a) **Find the real URL** by searching for the paper/tool name (use your knowledge or web_search), OR
     b) **Discard the item entirely** — a headline without a link is better than a broken self-link.
   - **Explicitly forbidden values:** `"#"`, `""`, `null`, `"/"`, any URL starting with `#`. These all produce `href="#"` in the HTML.
   - Validate EVERY URL field in the JSON before proceeding. Not "most" — **every single one**.
8. **🔴 Post-editor sanity check (MANDATORY — run this every time)**:
   After assembling edition.json but BEFORE writing to disk, scan it yourself:
   ```
   Look for any occurrence of "url": "#" or "url": "" in the edition object.
   If ANY exist, fix them by finding the real URL or removing the item.
   ```
   Then write the file, and run the terminal check:
   ```bash
   grep '"#' /tmp/v2/edition.json
   ```
   If any match, fix them before proceeding to render.

🔴 **KNOWN LLM BLIND SPOT — LLMs commonly skip steps 7-8. This is the #1 source of broken links in the newspaper and a recurring bug.** After writing edition.json, ALWAYS run:
```bash
grep -E '"#"|"url": ""' /tmp/v2/edition.json
```
If any match, fix them before proceeding to render. Re-run the editor with explicit instruction if needed:
*"Step 7 and 8 — validate EVERY single URL field. None can be #, empty, fragment-only, or missing. If a scout returned an item without a real URL, either find it or remove the item."*
8b. **Tally what you killed** — while doing steps 4, 4b and 5 you discard a lot
   of items. Keep a running count of *why*, and emit it as a `spiked` object in
   edition.json. Use exactly these seven keys, omitting any that are zero:

   | key | you killed it because |
   |-----|----------------------|
   | `low signal` | signal 1–2: minor bump, rehash, no result behind it |
   | `out of window` | dated before yesterday |
   | `duplicate url` | two scouts returned the same URL |
   | `same story` | same event, different headline/outlet |
   | `already ran` | matched the 7-day headlines_history sweep |
   | `thin section` | section under threshold, folded into quick hits |
   | `no link` | no real URL after searching |

   ```json
   "spiked": { "low signal": 31, "out of window": 14, "duplicate url": 9 }
   ```

   This is a **count, not a list** — do not enumerate the discarded titles. It
   feeds the public "How this issue made itself" page, which currently has to
   show these rules without numbers because nobody was recording them.

   ⚠️ This must never come at the expense of the edition itself. If you are
   unsure of an exact figure, omit that key rather than estimating: the page
   shows a rule without a number quite happily, but a wrong number published
   as fact is worse than no number at all.

9. Write `/tmp/v2/edition.json` in the canonical shape.

10. **Image path preservation when re-running** — If edition.json already exists (from a prior image-gen run), parse it and extract any `"image": "images/..."` fields BEFORE overwriting. Re-inject them into the new edition.json. The editor overwrites edition.json from scratch and does NOT know about images — without this step, 3 generated images disappear from the rendered HTML despite existing on disk.

## Edition JSON shape

```json
{
  "issue_no": <int>,
  "date_iso": "<today>",
  "date_human": "<today_human>",
  "notice": null,
  "lead": {
    "kicker": "…",
    "title": "…",
    "summary": "…",
    "source": "…",
    "date": "…",
    "url": "…"
  },
  "top_stories": [ … ],
  "sections": [
    {"title": "Research & Papers", "items": [ … ]},
    {"title": "Open Source & Models", "items": [ … ]},
    …
  ],
  "trending": {
    "github": {"title": "…", "url": "…", "link_label": "…", "date": "…", "items": [ … ]},
    "huggingface": {"title": "…", "url": "…", "link_label": "…", "date": "…", "items": [ … ]}
  },
  "free_models": {
    "openrouter": {"title": "…", "url": "…", "link_label": "…", "date": "…", "items": [ … ]},
    "opencode_zen": {"title": "…", "url": "…", "link_label": "…", "date": "…", "items": [ … ]}
  },
  "quick_hits": [ … ],
  "spiked": { "low signal": <int>, "out of window": <int>, … }
}
```

`spiked` is optional and counts only — see step 8b. Omit keys you can't count
exactly; omit the whole object if you couldn't track it at all.

## Thin/quiet day rules
- Thin day: still assemble; set `notice` like `"Light news day — fewer fresh items than usual."`
- Quiet day (zero items): set `lead: null`, empty arrays, `notice: "Quiet news day — no fresh AI stories in the last 24 hours. The lamp stays lit."`

## Output
Write `/tmp/v2/edition.json` with `terminal` heredoc or Python one-liner. Never use `execute_code` (blocked in cron).

## All content MUST be in English.
