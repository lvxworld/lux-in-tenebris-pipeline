---
name: lux-hotfix
description: "Hotfix a published Lux edition without re-running pipeline."
---

# Lux V2 — Hotfix a Published Edition (deploy today, no re-run)

Companion to `orchestrator`. Use when Luke wants a change
on the LIVE site today (or for tomorrow's release) without bumping the issue number
or triggering a full pipeline run.

## Core rule: NEVER re-render index.html to apply a live change

`render.py` reads edition.json + template and outputs a **BARE page** — it strips
everything the pipeline injected afterwards: the **podcast pill** block, the **wire
ticker** (`.wt`), and **section images / interleaved elements**. Re-rendering on top
of an already-published edition silently DESTROYS that content. Confirmed 2026-08-10
(credit edit wiped podcast pill + ticker; restored from backup).

**Correct hotfix = surgical string replacement** on the live HTML in the deploy dir
(`~/ai-news-deploy/`), never regeneration.

## The Devocracy credit lives in TWO places (not one)

- `template/newspaper.html` → drives the home `index.html` (via render.py)
- `scripts/make_making_of.py` → drives `making-of.html`, which has its OWN hardcoded
  header and does NOT load newspaper.html

A credit / model-name change must be applied to **BOTH**, or one page keeps the old
string. Do NOT remove the `ivanfioravanti` (Devocracy) mention when editing it.

For tomorrow's release: edit the two SOURCE files above; the cron uses them directly.
For today's live site (already published): edit the two live HTML files in the deploy dir.

## Safe hotfix procedure (live, today)

1. **Back up** the live files first: `cp index.html /tmp/index.html.bak.$(date +%H%M%S)`
   (same for making-of.html).
2. **Surgical replace** the exact string in `index.html` + `making-of.html`. Prefer a
   small python script in `/tmp/` over big inline `perl -i` one-liners — oversized
   inline payloads trip the terminal blocklist.
3. **Verify integrity** of the touched file — the injected content must still be
   present: `podcast-pill`, `class="wt"`, `images/*.jpg` counts.
4. **Keep `.issue` unchanged** (do not bump for a hotfix).
5. **`git add` ONLY the touched files** (never `git add -A` in the deploy dir — stray
   files can overwrite index.html).
6. Commit + push; GitHub Actions deploys in ~1-2 min.
7. **Verify on the LIVE domain** `https://luxintenebris.news/` (github.io now 301-redirects
   there) — grep the rendered credit text, not `github.io`.

## Pitfalls

- `git add -A` in deploy dir picks up stray files → check diff before commit.
- The live domain is `luxintenebris.news`; `luxintenebris.news`
  returns 301. Always verify on the custom domain with `-L` or directly.
