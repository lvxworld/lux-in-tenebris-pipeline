---
name: lux-image-pitfalls
description: "Pitfalls and corrections for Lux in Tenebris image generation. Load after image-gen for the production-failure knowledge that the base skill doesn't cover."
---

# Lux Image Gen — Pitfalls Reference

## When to use
Load AFTER `image-gen` when you're about to generate images for Lux. This skill contains production-failure learnings that the base skill doesn't capture.

## 🔴 P1: You MUST load image-gen first
**NEVER** write image prompts from general knowledge or intuition. The Lux style is highly specific: watercolor/ink, editorial metaphor, aged paper/sepia, approach rotator (A-G). Without loading the skill, you'll produce literal/iconic stock-photo-style images that the user will immediately reject.

**Rule:** Always `skill_view(name='image-gen')` before any `image_generate` call.

## 🔴 P2: Section images go on the section dict, not the first item
The base skill's step 2h says "add `\"image\"` to lead or to **first item in each section**" — this is **incorrect**. The render.py template checks `sec["image"]` (the section dict itself):

```python
# render.py line 175-178
if sec.get("image"):
    section_image_html = f'<img src="{esc_attr(sec["image"])}" ...>'
```

**Correct:** Add `"image": "images/section_<slug>_<date_iso>.jpg"` directly to each section dict in the `edition.json` `sections` array.

**Verification:**
```bash
grep -o '"image": "[^"]*"' /tmp/v2/edition.json
# Expected: 1 lead + N section images
```

## 🔴 P3: Re-render wipes wire ticker — re-inject
After re-rendering, `index.html` is regenerated from scratch. The wire ticker is lost. Re-inject:

```bash
python3 scripts/inject/inject_wire_ticker.py /tmp/v2/output/index.html /tmp/v2/scouts/scout_wire.json --output /tmp/v2/output/index.html
```

## 🔴 P4: Re-render also wipes podcast pill
Same as P3 — re-inject the podcast pill after re-render if applicable.

## 🔴 P5: Lead image filename must match edition.json
The lead image filename must be `lead_<date_iso>.jpg` (not `.png`). The `image` field in edition.json references `images/lead_<date_iso>.jpg`. If the xAI CDN returns a `.png`, convert or rename to `.jpg` when saving.

## 🔴 P6: Grok returns 403 spending-limit → use the nano-banana fallback, never touch config
When `image_generate` returns `403 personal-team-blocked:spending-limit`, xAI Grok Imagine is out of
account credits/subscription — that is NOT an auth failure. `hermes --profile luke auth refresh xai-oauth`
succeeds and changes nothing; do not waste a step on it and do not touch `image_gen.provider` in
config.yaml (Luke's rule; and the config must stay on Grok so it resumes automatically once credits return).

**Correct action — runtime fallback to OpenRouter nano-banana:**

```bash
python3 /home/nttluke/lux-in-tenebris-pipeline/scripts/core/lux_image_fallback.py \
    /tmp/v2/images/lead_<date_iso>.jpg google/gemini-3-pro-image /tmp/v2/prompt_lead.txt
```

Same prompt (style base + Dune block + approach A-G), 16:9 2K, ~$0.14/image. Report the backend and the
total cost in your final summary. Full details live in the `image-gen` skill.
