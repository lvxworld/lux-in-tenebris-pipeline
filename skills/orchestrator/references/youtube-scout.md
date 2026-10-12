# YouTube Scout — V2 Reference

## Architecture — Hybrid two-stage

Unlike other V2 scouts that are purely LLM-driven, the YouTube scout has **two stages**:

```
Stage 1 (DETERMINISTIC, Python, no LLM):
  youtube_scout.py → fetch RSS from 10 channels → get descriptions via yt-dlp
                  → get transcripts via youtube-transcript-api
                  → save /tmp/v2/scouts/scout_youtube_raw.json

Stage 2 (LLM, `$PIPELINE_MODEL`, dedicated model):
  scout-youtube skill → read raw JSON → extract newsworthy items
                         → write /tmp/v2/scouts/scout_youtube.json
```

## Stage 1: youtube_scout.py

**Location:** `~/.hermes/profiles/luke/scripts/v2/content/youtube_scout.py`

**Usage:**
```bash
# Standalone test (fetch last 24h, max 10 videos)
python3 ~/.hermes/profiles/luke/scripts/v2/content/youtube_scout.py --max 10

# Window override
python3 ~/.hermes/profiles/luke/scripts/v2/content/youtube_scout.py --hours 48 --max 5
```

### What it does
1. Iterates 10 hardcoded channel IDs
2. Fetches each channel's RSS feed (`https://www.youtube.com/feeds/videos.xml?channel_id=ID`)
3. Filters videos published within the time window (default 24h)
4. For each video, fetches description via `yt-dlp --print description`
5. For each video, fetches English transcript via `youtube-transcript-api`
6. Saves enriched data (title, preview, description, transcript, url, published)

### Output shape (`scout_youtube_raw.json`)
```json
{
  "count": 3,
  "generated_at": "2026-07-04T21:45:00",
  "videos": [
    {
      "video_id": "abc123...",
      "channel": "The AI Daily Brief",
      "title": "...",
      "preview": "First 200 chars of description",
      "description": "Full description (500 chars max)",
      "transcript": "First 2000 chars of English transcript (or null)",
      "url": "https://www.youtube.com/watch?v=abc123...",
      "published": "2026-07-04T12:00:00+00:00"
    }
  ]
}
```

### Dependencies
- `yt-dlp` (pip) — for descriptions
- `youtube-transcript-api` (pip) — for transcripts
- `requests` (stdlib) — for RSS feeds

### Channel list

Single source of truth: [`skills/_shared/sources.md`](../../_shared/sources.md),
under the `## YouTube Scout (\`scout-youtube\`)` section (10 channels, with
IDs). `youtube_scout.py` loads it directly. For selection methodology, frequency data, and the
step-by-step for adding a channel, see
[`scout-youtube/references/channels.md`](../../scout-youtube/references/channels.md)
— don't maintain a third copy of this list here.

### Common pitfalls

1. **yt-dlp is slow** — without JS runtime each call takes ~15s. With 5-10 videos this adds 1-2 min to the pipeline. Acceptable.
2. **Some videos lack transcripts** — `transcript: null` is handled gracefully. LLM should still use these if title+description have news value.
3. **RSS returns 15 videos max** — enough for daily window. Slower channels won't hit the limit.
4. **Channel IDs must be hardcoded** — handle resolution is slow, so IDs are resolved once and hardcoded.

## Stage 2: scout-youtube (LLM)

**Skill:** `scout-youtube`
**Model:** `$PIPELINE_MODEL` via `$PIPELINE_PROVIDER` — same as every other scout, no exception (see model-configuration.md).
**Tools:** Only `file` — no x_search, web_search, or terminal.

### What to extract
- Model releases, breakthroughs, research findings
- Policy changes, major tool launches
- AI industry analysis and debates

### What to skip
- Clickbait/opinion with no factual news
- Tutorials unless announcing a major new tool
- Content only tangentially about AI

## Pipeline integration

The 8th of 9 scouts in `run.sh` — scouts run **one at a time**, and this one
comes before Step 3 (validation).

```bash
# Python fetch
python3 "$SCRIPT_DIR/youtube_scout.py" --max 10

# LLM scout — model and provider both explicit
timeout "$TIMEOUT_SECS" "$HERMES_BIN" chat -q "..." \
  -s scout-youtube -t "file" \
  -m deepseek-v4-flash --provider "$PIPELINE_PROVIDER"
```

⚠️ `$PIPELINE_PROVIDER` is `localAIServer`, never `openrouter` — see model-configuration.md.

### Validation loop must include youtube
The `$SCOUT_NAMES` variable in Step 3 must contain `youtube`. Add it when adding this scout.

## Section threshold in editor

The `editor` skill has a **per-section item threshold** — YouTube & Video stays as a full section with **≥2 items**. With 0-1 items, it collapses into Quick Hits.

**Check if YouTube landed in Quick Hits:**
```bash
python3 -c "
import json
e = json.load(open('/tmp/v2/edition.json'))
sections = e.get('sections', [])
has_yt = any('youtube' in s.get('title','').lower() for s in sections)
qh = e.get('quick_hits',[])
yt_qh = [i for i in qh if 'youtube' in i.get('source','').lower()]
print(f'YouTube section: {has_yt}')
print(f'YouTube in quick_hits: {len(yt_qh)}')
"
```

## Testing

Test Python stage:
```bash
cd ~/.hermes/profiles/luke/scripts/v2/content
python3 youtube_scout.py --max 10
```

Test LLM stage (after Python):
```bash
hermes chat -q "..." --profile luke -s scout-youtube -t file \
  -m deepseek-v4-flash --provider localAIServer
```