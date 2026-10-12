# Model Configuration Topology — Lux V2 Pipeline

> Rewritten 2026-07-26 — the previous version of this doc described an
> architecture where most steps inherited the Hermes profile default. That's
> no longer true: verified against the live `run.sh` and the current
> `~/.hermes/profiles/luke/config.yaml`, **every** pipeline step now pins its
> own model and provider explicitly. Nothing in the daily run falls back to
> the profile default.

## 1. Profile Default (`config.yaml`) — NOT used by the pipeline

```yaml
model:
  default: deepseek/deepseek-v4-flash
  provider: openrouter
  base_url: https://openrouter.ai/api/v1
```

This is the fallback for ad-hoc/manual `hermes chat` commands run outside
`run.sh`. Every step the pipeline itself invokes passes an explicit
`-m ... --provider localAIServer`, so changing this default has **no effect** on the
daily run.

## 2. What the pipeline actually uses: explicit `localAIServer` provider

`localAIServer` is a custom provider pointing at a private, third-party-hosted
LiteLLM server (URL and key deliberately not in this public repo — see
`docs/SETUP.md`). Every `hermes chat` call in `run.sh`, and the hardcoded
default in `wire_articles.py`, targets it directly:

Every step passes the provider through the single `PIPELINE_PROVIDER`
variable defined at the top of `run.sh` (`PIPELINE_PROVIDER="localAIServer"`), so
there is exactly one place to look and one place to change:

| Step | Model | Provider | Where |
|------|-------|----------|-------|
| All 7 `run_scout()` calls (x, research, official, opensource, tools, funding, hardware) | `$PIPELINE_MODEL` | `$PIPELINE_PROVIDER` | inside the `run_scout()` helper, `run.sh` |
| YouTube scout | `$PIPELINE_MODEL` | `$PIPELINE_PROVIDER` | `run.sh`, step 2 |
| Italia scout | `$PIPELINE_MODEL` | `$PIPELINE_PROVIDER` | `run.sh`, step 2 |
| Editor | `$PIPELINE_MODEL` | `$PIPELINE_PROVIDER` | `run.sh`, step 4 |
| Image gen orchestrator | `$PIPELINE_MODEL` | `$PIPELINE_PROVIDER` | `run.sh`, step 5 (the `image_generate` tool call itself still goes to xAI regardless — see §3) |
| Podcast pill dialogue | `$PIPELINE_MODEL` | `$PIPELINE_PROVIDER` | `run.sh`, step 7 (the actual TTS audio still goes to xAI — see §3) |
| Wire articles | `$PIPELINE_MODEL` | `localAIServer` | `wire_articles.py` defaults (`MODEL`/`PROVIDER`, overridable via `--model`/`--provider`) |

**Do not swap the provider.** These are not pinned as incidental drift
protection — the pipeline has to run on this specific self-hosted server,
while the operator's own Hermes chats run on openrouter. On 2026-07-28 an
interactive session asked to raise the scout timeout also rewrote all 8
`--provider localAIServer` flags to `openrouter`, unrequested; the day's edition was
produced on the wrong (paid, metered) backend before anyone noticed. The
`PIPELINE_PROVIDER` indirection and the warning block above it exist because
of that.

Being one self-hosted box is also why scouts run **one at a time** — see
`docs/ARCHITETTURA.md#scout-concurrency--why-sequential`.

## 3. Components that bypass `localAIServer` entirely (xAI direct)

These use tool-level integrations, not `hermes chat -m`, so they're
unaffected by any of the above:

| Component | Tool | Provider | Auth |
|-----------|------|----------|------|
| **Image gen** (Grok Imagine) | `image_generate` | xAI API | `xai-oauth` (OAuth) |
| **TTS voices** (podcast Castor/Luna) | `text_to_speech` | xAI API | `xai-oauth` (OAuth) |

Both authenticate against the same xAI account, which is why image gen and
podcast credit exhaustion look related — but they don't always fail on the
same day (see `docs/ARCHITETTURA.md#independent-credit-checks-image-gen-vs-podcast`).
Each has its own independent credit check in `run.sh` as of 2026-07-26.

## 4. Auxiliary Hermes models (`config.yaml`) — unrelated to Lux

Separate from anything above; used by the Hermes gateway itself for internal
features, not invoked by the Lux pipeline:

| Purpose | Provider | Model |
|---------|----------|-------|
| `title_generation` | openrouter | openrouter/owl-alpha |
| `vision` | openrouter | openrouter/owl-alpha |
| `compression` | openrouter | openrouter/owl-alpha |
| `curator` | openrouter | openrouter/owl-alpha |

## How to Change a Step's Model

1. **Identify the step** in `run.sh` (look for the `hermes chat -q` block, or the `run_scout()` helper if it's one of the 8 parallel scouts).
2. **Change its `-m <model> --provider <provider>` flags** directly — there's no default to fall back to, so this fully determines what that step uses.
3. **Test** by running just that step standalone:
   ```bash
   hermes chat -q "..." -s <skill> -t <toolsets> -m <model> --provider <provider> -Q --yolo
   ```
4. **Confirm with the user before editing `run.sh`** — it's the live production orchestrator, symlinked directly into the cron path.
