---
name: orchestrator
description: "Lux in Tenebris V2 production pipeline. Bash orchestrator with fire-and-forget cron, 8 atomic scouts + 1 Python/LLM hybrid run sequentially, editor, image-gen, render, podcast pill, wire articles, deploy to GitHub Pages."
---

# Orchestrator V2 — Production Pipeline

## Purpose
Daily AI news production: 9 scouts → editor → image generation → HTML render → podcast pill → wire articles → deploy to GitHub Pages.

## Architecture

**Core principle:** Cron is a scheduler, not a state manager. Every step is
isolated and stateless, communicating only through JSON files in `/tmp/v2/`.

```
Cron (06:30, no_agent=true, fire-and-forget)
  ↓
cron_wrapper.sh (nohup bash run.sh &)
  ↓
run.sh (bash orchestrator)
  ↓
Sync deploy dir → resolve issue # → archive predecessor edition
  ↓
9 scouts, ONE AT A TIME (see "Why sequential" below)
  ↓
Editor (editor, deepseek-v4-flash) → edition.json
  ↓
Image-gen → Render → index.html
  ↓
Podcast Pill → Wire articles → ticker injection
  ↓
Copy → headlines history → git add → commit → push
  ↓
Step 11b: wait for the Pages run of THIS commit → retry once on failure → report
```

## Step 11b — the release check (added 2026-11-26)

`git push` returning 0 is not a release. On 2026-11-25 the push succeeded while
the Pages workflow failed (`No artifacts named "github-pages" were found for
this workflow run`), so the site served the previous day's issue for a full day
and nobody knew until a human spotted it. Nothing in the pipeline watched
Actions, because nothing in it *could* — the push says nothing about the deploy.

Step 11b closes that loop: it finds the Pages run whose `headSha` matches the
commit just pushed, polls it (bounded, ~5 min), and puts the outcome in the
milestone notification:

- `✅ Lux #N is live — … Release verificata live (Pages run <id>).`
- `⚠ Lux #N — pubblicata, release non confermata` (check skipped / no run found)
- `⛔ Lux #N — NON live … il sito è ANCORA sull'edizione precedente.`

On failure it retries by dispatching a **fresh** `workflow_dispatch` run of
`deploy.yml --ref main`.

### 🔴 Never retry a failed Pages run with `gh run rerun --failed`

Re-running the job re-uploads the artifact while the previous attempt's artifact
is still attached to the **same** run, so `deploy-pages` finds two and dies with:

```
Multiple artifacts named "github-pages" were unexpectedly found for this
workflow run. Artifact count is 2.
```

That is not a retry, it is a guaranteed second failure — it turned 2026-11-27's
transient upload glitch into a whole day stuck on the previous issue. A new run
gets a clean artifact namespace; `rerun` never does. This was shipped wrong once
and caught by the step's own first production run, which is the only reason it
is documented here.

### Link previews: always notify with `?ed=<issue>`

Telegram caches link previews per URL, so a bare `https://luxintenebris.news`
keeps showing whatever `<title>` was captured on an earlier day — the report
"the message still shows yesterday's edition" is this, not a deploy failure.
The notification URL carries `?ed=$NEXT_ISSUE` to force a fresh preview, and
because step 11b waits for the deploy first, the title it reads is today's.

`template/newspaper.html` also carries explicit `og:*` / `twitter:*` tags
(`og:title` = "… · {{DATE_HUMAN}} — No. {{ISSUE_NO}}", `og:image` = today's lead
illustration, `<link rel="canonical">`). Before 2026-11-27 the page had only
`<title>` and `meta description`, so every preview depended on a fallback. Note
`og:url` deliberately stays the canonical bare URL while the *notification* link
carries `?ed=` — preview caching keys on the linked URL, not on `og:url`.

**Auth:** the ambient `gh` login is used (NTTLuke has admin on the deploy repo,
which is what dispatching and re-running workflow runs needs). `GITHUB_TOKEN`
from the profile `.env` is only exported after it validates — the one stored
there is expired, and a bad `GH_TOKEN` would 401 every check.

**Never make this step fatal:** no gh, no login, or an API outage must leave
`RELEASE_STATUS=unverified` and let the run finish. A missed notification is
recoverable; a killed pipeline is not.

## Why sequential scouts (changed 2026-07-28)

Scouts used to run 3-up in parallel phases. That works against a distributed
API but not against `localAIServer`, which is a **single self-hosted box**. A scout is
not one request — it's a whole multi-turn agent session (searches, tool calls,
reasoning). Three concurrent sessions saturate the machine and all three crawl.

Evidence (logs, 2026-07-26/27/28): every 3-up phase ran exactly to the
per-scout ceiling and got killed — **0 scouts completed** across those runs.
The same scouts against a distributed provider finished a whole phase in
4.7-6.7 min. Serialising trades wall clock (free here — it's a fire-and-forget
06:30 cron) for actually finishing.

**Do not re-parallelise** without first confirming the inference backend can
take concurrent agent sessions.

## Timeouts

Every LLM call is wrapped in `timeout`. Nothing may hang forever — five calls
used to have no timeout at all (italia scout, editor, image-gen, podcast), and
they produced 40-minute stalls in the logs.

| Budget | Value | Applies to |
|--------|-------|------------|
| `TIMEOUT_SECS` | 20 min | each scout |
| `STEP_TIMEOUT_SECS` | 20 min | italia scout |
| `EDITOR_TIMEOUT_SECS` | 40 min | editor — its own, larger budget |
| `MEDIA_TIMEOUT_SECS` | 15 min | image gen, podcast (xAI-bound) |
| `MASTER_TIMEOUT` | 4h | whole pipeline |

The editor is the only FATAL step and does the most work in one call, so it
gets 40 min: on 2026-07-29 it was killed by the shared 20-min ceiling and took
the whole run down with it. See `docs/ARCHITETTURA.md` for measured timings.

**Per-step logs are appended, never truncated** (`>>` + a `▶` banner per
attempt). A manual re-run used to overwrite the log of the automated attempt
that had just failed, erasing the evidence. Credit checks read only the last
banner-delimited block via `last_attempt()`, so a stale error from earlier the
same day doesn't permanently skip a step.

`MASTER_TIMEOUT` must cover the **sum** of sequential scouts, not the max. It
was 90 min while scouts ran in parallel; that is far too tight now.

## Provider pinning

Every step passes `--provider "$PIPELINE_PROVIDER"` (= `localAIServer`) explicitly.
The Hermes profile default is deliberately not used — the user chats on
openrouter, but the pipeline must stay on their friend's server. See the
comment block at the top of `run.sh` before changing anything here.

### wire_articles.py
- `--model`, `--provider` args for per-edition model selection
- Each edition gets its own wire articles written by its respective model
- **CRITICAL:** `build_prompt` uses `os.environ.get('WIRE_MODEL', MODEL)`. If `MODEL` global is overridden via `--model`, the prompt's `model_name` follows correctly. Was `deepseek/deepseek-v4-flash` hardcoded (fix applied 2026-07-17).

### fetch_trending.py
- `python3 fetch_trending.py [--output-json PATH]`
- Fetches GitHub Trending (15 repos) and HuggingFace Trending (10 models) via **curl** (bypasses Firecrawl/Tavily)
- Used as auto-fallback when the opensource scout fails (web_extract connection errors)
- Outputs JSON matching the scout-opensource `trending` contract
- **Location:** `~/.hermes/profiles/luke/scripts/v2/content/fetch_trending.py`

### fetch_free_models.py
- `python3 fetch_free_models.py [--output-json PATH]`
- Fetches currently-free models from OpenRouter (public models API — free
  means every pricing sub-field is zero, output is text-only, and the id
  isn't an `openrouter/*` routing alias; the `:free` id suffix alone was
  tried first and found both under- and over-inclusive on the live catalog,
  see `_is_actually_free()` in the script) and OpenCode Zen (joins two tables
  scraped from their static docs page — no pricing field in their `/v1/models`
  API) via **curl**, same style as `fetch_trending.py`. No LLM, no API key,
  deterministic.
- Outputs the `free_models` contract (`openrouter` + `opencode_zen` sub-objects,
  each shaped like a `trending` column) — the editor passes it through unchanged
  (see `editor` SKILL.md step 3b).
- GitHub Models and Nous Portal/Hermes were investigated and dropped: GitHub
  Models' catalog API returns 410 (being retired); Nous Portal's public
  `/v1/models` is a straight mirror of OpenRouter's own catalog, so it would
  just duplicate the OpenRouter column under a different name.
- **Wired into `run.sh` as step 3b** (2026-08-22, after an explicit go-ahead),
  right after scout validation and before the editor — writes
  `$V2_DIR/free_models.json`, which the editor's prompt explicitly points at
  (belt-and-suspenders alongside the skill's own "Files to read" entry).
  Non-fatal: a failed/missing fetch just means the section is skipped that day.
- **Location:** `scripts/content/fetch_free_models.py` (this repo)

### fix_archive_issue_numbers.py
- `python3 fix_archive_issue_numbers.py`
- Fixes incorrect issue numbers in archived HTML files and regenerates the archive listing
- Also sets `.issue` to the correct value for the next pipeline run
- **Location:** `~/.hermes/profiles/luke/scripts/v2/maintenance/fix_archive_issue_numbers.py`

## Edition components

Single edition. The K3 "The Lens" second edition was **fully removed on
2026-07-28** — it had been render-disabled since 07-25 while its editor and
wire steps still ran daily, burning LLM calls on output nothing consumed.
`editor-k3`, `transform_layout_k3.py` and `inject_version_badge.py` are
deleted; there is no second version, so no version selector either.

| Component | Value |
|-----------|-------|
| Editor skill | `editor` |
| Model | `deepseek-v4-flash` (provider `localAIServer`) |
| Edition file | `edition.json` |
| Output path | `index.html` |
| Wire articles | `scout_wire.json` |

## 🔴 WEB-TOOL FALLBACK — when web_search/web_extract fail

### Root cause
Both `web_search` and `web_extract` currently run on `ddgs` (DuckDuckGo, free) —
check `web.search_backend` / `web.extract_backend` in `config.yaml` before
assuming otherwise.

They fail for several unrelated reasons, and the fallback should trigger on
**any** of them, not just one:
- rate limiting / temporary blocks from DuckDuckGo
- the `ddgs` package missing or broken in the environment
- network errors and timeouts
- `"Payment Required"` / credit errors — this was the dominant failure when
  `extract_backend` was Firecrawl (a paid API). It is no longer the configured
  backend, so **do not treat "Payment Required" as the only trigger.**

### Solution — curl-based fallback
Each scout skill includes a fallback section with `terminal` + `curl` commands
that bypass the web tools entirely and hit free APIs directly.

Key free API fallbacks used across scouts:
- **TechCrunch**: WordPress JSON API (`wp-json/wp/v2/posts`)
- **HuggingFace Papers**: direct HTML scraping via `curl`
- **arXiv**: `export.arxiv.org/api/query` (free XML API)
- **Hacker News**: `hn.algolia.com/api/v1` (free JSON API)
- **Product Hunt**: HTML regex parsing from Next.js props
- **DuckDuckGo / Bing**: direct HTML search via `curl`
- **Generic page fetch**: `curl` + regex title/body extraction

### When to use
Whenever `web_search`/`web_extract` fail for any reason, the scout should attempt
the curl fallbacks described in its own skill before emitting `[]`.

## Pitfalls

1. **Do not re-parallelise the scouts** — see "Why sequential scouts" above.
   Running them 3-up against `localAIServer` produced 0 completed scouts across three
   consecutive days.

2. **Do not swap the provider** — every step must stay on `localAIServer` via
   `$PIPELINE_PROVIDER`. An interactive session silently rewrote all of them
   to `openrouter` on 2026-07-28 while doing an unrelated timeout change.

3. **Wire articles model_name** — `build_prompt()` in `wire_articles.py` uses
   `os.environ.get('WIRE_MODEL', MODEL)` so the attribution line follows
   `--model` instead of a hardcoded value. Fixed 2026-07-17.

4. **Issue number and archiving happen in step 1b**, before the scouts, against
   a freshly `git reset --hard` deploy dir. The issue number is read from the
   **live index.html masthead**, not `.issue` (a crashed run can leave that
   stale/unpushed — it silently burned issue #31 on 2026-07-27). Same date as
   today ⇒ same-day re-run ⇒ reuse the number. Different date ⇒ increment and
   archive the predecessor *before* this run overwrites it.

5. **Trending fallback (fetch_trending.py)** — The opensource scout uses `web_extract`, which can fail with `Connection error` or simply return nothing. The pipeline auto-fallback calls `fetch_trending.py` via curl when trending data is missing (<3 items). To manually re-run: `python3 ~/.hermes/profiles/luke/scripts/v2/content/fetch_trending.py --output-json /tmp/v2/scouts/scout_opensource.json`

## Reference files

Deeper technical detail for specific pieces lives in `references/`, not
inline here:

| File | Covers |
|------|--------|
| `../_shared/sources.md` | Every scout's fixed source list (handles, blogs, feeds, channels) *and* why each was picked / ideas for expansion — single file, not split across a data file and a doc anymore |
| `references/model-configuration.md` | Full model/provider topology — which step uses what, and why it's pinned |
| `references/archive-system.md` | How `archive_issue.py` + the template work together, troubleshooting |
| `references/link-validation.md` | Post-deploy dead-link checking procedure |
| `references/youtube-scout.md` | YouTube scout's two-stage (Python + LLM) architecture in detail |
| `references/wire-articles-scout.md` | Wire articles' RSS→LLM pipeline and ticker CSS architecture in detail |