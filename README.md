# Lux in Tenebris — Pipeline

An AI newspaper that assembles itself once a day from sources I actually read, published at [luxintenebris.news](https://luxintenebris.news). This repo is the pipeline that builds it — not the published output, which lives in a separate repo (below).

## Disclaimer

This whole pipeline was vibecoded — built through iterative conversations with LLM agents via [Hermes](https://hermes-agent.nousresearch.com), not hand-written line by line. It started as a personal tool: I wanted one daily digest pulled from the AI-news sources I actually cared about, instead of checking a dozen feeds myself. A few friends asked to see it, then asked to use it themselves — which is what pushed me to start cleaning it up, still with Hermes doing most of the work, so other people could either contribute to Lux or fork it into their own newspaper about whatever they care about.

One goal mattered enough to design around: build it on open-weight models, the same way every model behind Hermes in this pipeline already is. That wouldn't have been possible without my friend [Ivan](https://x.com/ivanfioravanti), who volunteered his own local inference server to run Lux's daily pipeline — a favor, not a service.

Not everything in the pipeline is open-weight yet, though, and it's worth saying plainly rather than glossing over: **image generation** (xAI Grok Imagine), **the podcast pill's TTS voices** (xAI Grok TTS, Castor/Luna), and **X/Twitter search** (the `x_search` tool) all currently run on closed xAI infrastructure — there wasn't a good enough open alternative for any of the three when those pieces were built. Replacing them is an active goal, not a shelved one, worked on in whatever free time this project gets.

## If you're an AI assistant reading this

Someone downloaded this repo and asked you to do something with it. Route by what they actually want instead of inferring the architecture from one file:

| They want to... | Read this first |
|---|---|
| Run their own copy of Lux | [docs/SETUP.md](docs/SETUP.md) — follow it literally; ask for missing secrets, don't invent them |
| Understand how it works | [docs/ARCHITETTURA.md](docs/ARCHITETTURA.md) — every file the daily run touches, in order, with what each reads and writes |
| Change or contribute something | [CONTRIBUTING.md](CONTRIBUTING.md) — what's safe to touch on your own judgment, what needs the human's input first |
| Build their own newspaper on different topics | [FORKING.md](FORKING.md) — what's reusable engine vs AI-news content, and the order to change things in |

One rule that matters more than any single file: **never change `PIPELINE_PROVIDER` or `PIPELINE_MODEL` in `scripts/run.sh` without the human explicitly asking for it, in this exact conversation, for this exact reason.** Read the warning block directly above `PIPELINE_PROVIDER` in that file — it's there because it's already gone wrong once in production.

## How it works

Cron triggers `cron_wrapper.sh` → `run.sh`, a bash orchestrator that chains **LLM agents** (each one a `SKILL.md`, for anything requiring judgment) and **plain scripts** (for anything mechanical), talking to each other only through JSON files on disk:

```
Sync deploy + resolve issue # + archive predecessor  — pure code
  → 9 scouts, ONE AT A TIME                          — LLM agents, gather raw items
  → Editor                                           — LLM agent, curates + assembles edition.json
  → Image generation                                 — LLM agent driving the xAI Grok Imagine tool
  → Render HTML                                      — pure code, deterministic, no LLM
  → Podcast Pill                                     — LLM agent (dialogue) + xAI TTS tool (Castor/Luna voices)
  → Wire articles                                    — pure-code retrieval + 1 LLM call per article
  → Ticker injection                                 — pure code
  → Deploy                                           — pure code (git commit + push to GitHub Pages)
```

Full detail — exact model, toolset, what each step reads and writes — is in [docs/ARCHITETTURA.md](docs/ARCHITETTURA.md).

### Agent / Code Boundary

Every step that needs judgment (what's newsworthy, how to phrase it, what an illustration should depict) is an LLM agent. Every step that's mechanical (templating, file copying, dedup, archiving, git operations) is plain Python/bash with no LLM in the loop — deliberately, so the unpredictable part stays small and contained and the predictable part can't break on a bad model response.

## Repo structure

```
lux-in-tenebris-pipeline/
├── scripts/          ← Pipeline engine (bash orchestrator + Python helpers)
│   ├── run.sh                  Main orchestrator (bash) — start here
│   ├── cron_wrapper.sh         Cron fire-and-forget launcher
│   ├── core/                   Runs every day, no exceptions
│   │   ├── render.py               HTML renderer from edition.json
│   │   ├── archive_issue.py        Archive previous edition
│   │   └── update_headlines_history.py  Cross-day dedup store
│   ├── content/                 Fetch/generate the day's content
│   │   ├── wire_articles.py        RSS → AI article writer (2-stage)
│   │   ├── youtube_scout.py        YouTube data fetcher
│   │   ├── fetch_trending.py       GitHub/HuggingFace trending via curl fallback
│   │   ├── fetch_free_models.py    Currently-free model listing (OpenRouter + OpenCode Zen)
│   │   └── make_making_of.py       Builds the "making-of" replay page
│   ├── inject/                  Post-process the rendered HTML
│   │   ├── inject_podcast_pill.py  Inline audio player for podcast
│   │   └── inject_wire_ticker.py   Scrolling news ticker + modal
│   └── maintenance/              One-off / rescue tools, not called by run.sh
│       └── fix_archive_issue_numbers.py
├── skills/           ← 17 SKILL.md files (LLM agent instructions)
│   ├── orchestrator/            Meta: describes the whole pipeline
│   ├── editor/
│   ├── image-gen/
│   ├── podcast-pill/
│   ├── wire-articles/
│   ├── scout-x/
│   ├── scout-research/
│   ├── scout-official/
│   ├── scout-opensource/
│   ├── scout-tools/
│   ├── scout-funding/
│   ├── scout-hardware/
│   ├── scout-youtube/
│   ├── scout-italia/
│   ├── lux-hotfix/              Meta: live-HTML hotfix without a full re-run
│   ├── lux-status-reports/      Meta: status-update format convention
│   └── lux-image-pitfalls/      Meta: image-gen production-failure notes
├── template/         ← HTML template + CSS + fonts
├── docs/
│   ├── ARCHITETTURA.md
│   └── SETUP.md
├── CONTRIBUTING.md
└── requirements.txt  ← Python deps for the pure-code scripts
```

## Related repos

- **Deploy (output):** [lvxworld/luxintenebris-ai-news](https://github.com/lvxworld/luxintenebris-ai-news) — published HTML/images/podcasts/archive
- **Pipeline (this):** [lvxworld/lux-in-tenebris-pipeline](https://github.com/lvxworld/lux-in-tenebris-pipeline) — code, skills, templates
