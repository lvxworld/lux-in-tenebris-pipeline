# Setup — Lux in Tenebris Pipeline

## Prerequisites

- WSL / Linux
- [Hermes Agent](https://hermes-agent.nousresearch.com), with a profile configured
  (this doc uses `<profile>` as a placeholder — substitute your own profile name
  everywhere below, e.g. `~/.hermes/profiles/<profile>/` → `~/.hermes/profiles/jane/`)
- GitHub SSH keys configured
- Git
- Python 3.13+ with `pip install -r requirements.txt` (`requests`,
  `youtube-transcript-api`, `yt-dlp` — everything else is stdlib; `yt-dlp` is
  shelled out to as a CLI by `youtube_scout.py`, not imported)
- Inside Hermes, tool access for: `web_search`/`web_extract` (most scouts),
  `x_search` (X/Twitter — scout-x, scout-opensource, scout-hardware), and an
  xAI account connected via OAuth (`image_generate` for the lead/section
  illustrations, `text_to_speech` for the podcast pill). Both media steps are
  **non-fatal** — the pipeline degrades gracefully and just skips them if
  xAI isn't connected, so you can get a working (text-only) edition without it.

## Installation

### 1. Clone the pipeline repo

```bash
git clone git@github.com:lvxworld/lux-in-tenebris-pipeline.git
```

### 2. Symlink to Hermes paths

The pipeline repo contains ALL code, but Hermes expects files at specific
profile-relative paths. Symlinks bridge this gap:

```bash
# Pipeline scripts
mkdir -p ~/.hermes/profiles/<profile>/scripts
cd ~/.hermes/profiles/<profile>/scripts
ln -s ~/lux-in-tenebris-pipeline/scripts v2

# Skills
mkdir -p ~/.hermes/profiles/<profile>/skills
cd ~/.hermes/profiles/<profile>/skills
ln -s ~/lux-in-tenebris-pipeline/skills ai-news-v2
```

(If you're taking over an *existing* profile that already has something at
either path, back it up first — `mv v2 v2.backup` / `mv ai-news-v2
ai-news-v2.backup` — before linking.)

### 3. Verify

```bash
ls -la ~/.hermes/profiles/<profile>/scripts/v2
# → lrwxrwxrwx ... ~/lux-in-tenebris-pipeline/scripts

ls -la ~/.hermes/profiles/<profile>/skills/ai-news-v2
# → lrwxrwxrwx ... ~/lux-in-tenebris-pipeline/skills
```

### 4. Point the orchestrator at your profile

`scripts/run.sh` self-locates its own script/template paths (works
wherever the repo is cloned or symlinked), so the only thing you actually
need to set is which Hermes profile it should use. Everything below has a
default that matches the original author's setup — override only what's
different for you, via environment variables read at the top of the script:

| Variable | Default | What it is |
|---|---|---|
| `LUX_PROFILE` | `luke` | Your Hermes profile name — **set this** |
| `LUX_HERMES_BIN` | `$HOME/.local/bin/hermes` | Path to the `hermes` binary |
| `LUX_DEPLOY_DIR` | `$HOME/ai-news-deploy` | Local clone of your deploy repo (see step 6) |
| `LUX_TG_ENV` | `$HOME/.hermes/profiles/$LUX_PROFILE/.env` | Optional `.env` for Telegram notifications (step 7) |

Export these in whatever launches the pipeline for you — e.g. a small
untracked wrapper script outside this repo, the same way the original cron
entry point works (see [Cron Job Chain](#5-cron-job)):

```bash
#!/bin/bash
export LUX_PROFILE="<profile>"
export LUX_DEPLOY_DIR="$HOME/ai-news-deploy"
exec bash ~/.hermes/profiles/<profile>/scripts/v2/cron_wrapper.sh
```

### 5. Cron job

```bash
hermes cron create \
  --name "Lux in Tenebris" \
  --schedule "30 6 * * *" \
  --script v2/cron_wrapper.sh \
  --no-agent \
  --deliver telegram
```

`--deliver telegram` is optional (Hermes-side delivery of the cron's own
output — separate from the pipeline's own richer Telegram milestone
notifications, see step 7). Drop it if you don't use Telegram.

### 6. Deploy repository

The pipeline pushes the rendered output to a **separate** repo (keeps the
pipeline's own history free of generated HTML/images/audio):

1. Create an empty repo (e.g. `<you>/your-news-deploy`) and enable GitHub
   Pages on it (Settings → Pages → Deploy from a branch → `main`).
2. `git clone` it locally to wherever `LUX_DEPLOY_DIR` points (default
   `~/ai-news-deploy`).
3. **First run only:** the pipeline reads the issue number from the *live*
   page's own masthead, so on a brand-new deploy repo with no `index.html`
   yet it starts at issue `#1` automatically — nothing to bootstrap by hand.
4. A custom domain (Cloudflare or otherwise) is optional — the default
   `https://<you>.github.io/your-news-deploy/` URL works with no extra setup.

### 7. LiteLLM private server

The pipeline runs its models (`deepseek-v4-flash`, `kimi-k3`) through a
private, third-party-hosted LiteLLM server, configured as a custom provider
named `localAIServer` in `~/.hermes/profiles/<profile>/config.yaml`. The base URL and
API key are private and deliberately not included in this public repo — ask
the repo owner if you need them, or point `localAIServer` at your own
OpenAI-compatible/LiteLLM endpoint instead:

```yaml
custom_providers:
  - name: localAIServer
    base_url: <your LiteLLM / OpenAI-compatible endpoint>
    api_key: <your key>
    models:
      - deepseek-v4-flash
```

**Every pipeline step pins `--provider localAIServer` explicitly** (via the
`PIPELINE_PROVIDER` variable at the top of `run.sh`). The Hermes profile
default is deliberately *not* used, and must not be: the profile default is
whatever the user chats on, while the pipeline has to stay on this server.
If your backend is a single self-hosted box like the original author's,
that's also why scouts run one at a time rather than in parallel — see
[Scout Concurrency](ARCHITETTURA.md#scout-concurrency--why-sequential).

### 8. Telegram notifications (optional)

`run.sh` posts short milestone updates (scout progress, failures, final
report) to Telegram if it finds credentials — silently skips this
entirely otherwise, no crash either way. To enable it, create the file at
`LUX_TG_ENV` (default `~/.hermes/profiles/<profile>/.env`) with:

```
TELEGRAM_BOT_TOKEN=<your bot token>
TELEGRAM_HOME_CHANNEL=<your chat id>
```

## Update Workflow

1. Always work inside `~/lux-in-tenebris-pipeline/`
2. `git add`, `git commit`, `git push`
3. Symlinks mean Hermes sees changes immediately
4. The cron job uses symlinks → changes are active on the next run

## Separate Deploy Repository

The output HTML lives in a separate deploy repo (see step 6 above). Do not
manually modify it — the pipeline overwrites it on every run.
