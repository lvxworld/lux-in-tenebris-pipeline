---
name: image-gen
description: "V2 image generator. Creates ink/watercolor editorial illustrations for lead + sections. xAI Grok Imagine backend. Art direction: metaphor-driven, editorial illustration style (New Yorker cover logic), NOT literal/iconic."
---

# Image Gen V2 — Editorial Illustration Engine

## When to use
Called by orchestrator AFTER editor writes `/tmp/v2/edition.json`. Generates illustrations for the lead story and one per non-empty section.

## PHILOSOPHY — this is critical

These are **editorial illustrations**, NOT visual descriptions of the article content. Think *New Yorker* cover logic, not stock photo logic.

**WRONG** (literal/iconic — AVOID):
- "A stylized computer chip with neural network pathways"
- "A humanoid robot silhouette in a thoughtful pose"  
- "Abstract buildings with dollar signs morphing into circuits"
- "Three AI model icons orbiting a central point"

**RIGHT** (metaphorical/lateral — AIM FOR):
- "An astronomer peers through a brass telescope at a sky full of opening parentheses"
- "A single candle on a vast stone balcony, the only warm light in a cold city of towers"
- "A flock of origami cranes emerging from the pages of an open book, some still half-folded"
- "A watchmaker's hands assembling a gear train from translucent soap bubbles"
The image should make the reader pause and think "what does this mean?" — then realize it means everything about the story. The leap from image to idea is where the art lives.

## Image style (MANDATORY — always include this base)

```
Hand-painted watercolor tattoo style with hand-drawn ink outlines, infused with subtle street art urban energy.
Fluid spontaneous ink contour lines (not rigid or mechanical) with watercolor washes bleeding naturally.
Subtle street art texturing: light spray paint grain, occasional paint drips, soft splatter accents — but refined and elegant, not aggressive.
Multiple watercolor colors visible: deep blues, warm ambers, burnt sienna, muted greens, soft purples, ochres. Rich color palette — diverse hues blending and bleeding.
Composition fills 40-60% of space — balanced, not mostly empty.
Handmade aesthetic: visible brush strokes, imperfect organic ink lines, color transitions, urban texture overlays.
Think: watercolor tattoo meets Mr Brainwash light touch — colorful, raw, sophisticated, gallery-ready.
No digital polish, no photorealism, no 3D rendering.

AGED PAPER / SEPIA OVERLAY (CRITICAL — this defines the "tenebris" identity):
The overall image MUST feel like an antique artifact discovered in an old archive or manuscript.
Aged parchment texture subtly visible beneath the ink and watercolor — think foxed paper from the 1700s, warm ivory turning to ochre at the edges.
Soft sepia tonality layering the entire piece: shadows lean warm-brown rather than pure black.
Vignette darkening at corners and edges, as if the paper has darkened with age and handling.
Faint coffee-stain or foxing marks (tiny age spots) can appear in non-critical areas for authenticity.
The colors should feel muted and time-worn — not fresh and saturated, as if the illustration has been aging in a leather-bound book for centuries.
Overall mood: an ancient manuscript illustration reinterpreted through modern ink art — the bridge between old-world craftsmanship and contemporary street art sensibility.
```

### DUNE AESTHETIC (optional signature touch — use when the story's ideality aligns with desert, monumentality, ancient-future, or celestial themes)

The Dune aesthetic transforms the watercolor/ink base with a monumental desert atmosphere:

- **VAST SCALE:** massive geometric structures (half-temple, half-machine) rising from endless amber dunes, edges softened by wind and time
- **ATMOSPHERE:** dust-filled air, long golden light rays, deep warm-brown shadows, hazy horizons
- **COLOR PALETTE SHIFT:** terracotta, amber, burnt sienna, dusty gold, ochre, pale moon-silver — against deep warm-brown shadows. A single accent of deep indigo in the upper sky
- **ANCIENT-FUTURE:** technology that feels like it has been here for millennia, becoming part of the landscape. Ritual, sacred, prophetic undertones
- **FIGURES:** lone robed figures in vast landscapes, scale emphasizing the monumental
- **TEXTURE:** sand-worn surfaces, wind-carved stone, eroded edges
- **CELESTIAL MOTIFS:** when the story involves multiple entities or variants (e.g. model families), represent them as celestial bodies (sun, moon, earth) floating in the desert sky
- **SCENE TYPE:** prophecies being fulfilled, ancient rituals, discoveries in the desert, solitary figures contemplating cosmic forces

**How to apply:** APPEND the Dune Aesthetic block to the base style before the chosen approach. Rotate Dune-infused images across different approaches as the story's ideality permits — not every image needs it, but when it fits, lean in hard. The result should feel like pages from a lost manuscript found in the deep desert — ancient, warm, monumental.

Then append ONE of the metaphor prompts below. Rotate — never use the same approach twice in one run.

## THE APPROACH ROTATOR — pick one per image

Rotate through these. Each image in a run should use a DIFFERENT approach.

### A. Synecdoche — the tiny thing that holds the whole story
One hyper-specific, oddly mundane object that crystallizes the entire piece.
**Prompt pattern:** "A single [unusual object] on [unexpected surface/background], rendered as if studied by a 19th-century naturalist. The object contains within it, hinted at but not literal, the idea of [core concept]."
**Example for GPT-5.6 gated launch:** "A heavy brass keyhole plate mounted on a door made of cloud, rendered as a naturalist's specimen study. Only one tiny key exists. The surrounding paper is empty except for a small scale bar and a handwritten Latin label."

### B. Anachronism — old world meets new concept
A historical scene or setting where the anachronistic element is the AI concept, presented as completely normal.
**Prompt pattern:** "A [historical scene/era] where [AI concept] exists as a natural element, treated with the visual language of [period art style]. Figures behave as if this is entirely ordinary."
**Example for robotics:** "A Renaissance workshop where a humanoid figure is being fitted for armor, but its joints are visible ball-and-socket mechanisms. The artisan examines it with a calm professional expression, as if this were a Tuesday."

### C. Scale disorientation — the wrong-sized subject
Something enormous rendered as tiny, or something microscopic rendered as monumental.
**Prompt pattern:** "A [normally huge concept] rendered impossibly small in a [vast empty space] / A [tiny thing] rendered as a [monumental structure] filling the frame."
**Example for funding:** "A tiny seedling growing from a crack in an enormous stone cathedral floor, with a single drop of water falling from the vaulted ceiling above onto its leaf — the scale of the building makes the seedling feel both insignificant and profoundly important."

### D. Impossible object — the thing that shouldn't exist
A hybrid creature, structure, or scene that combines two categories that don't belong together.
**Prompt pattern:** "A [creature/object] made entirely of [unexpected material] in the act of [unexpected behavior]. No caption, no label, no explanation."
**Example for open-source models:** "A vast library whose books are all made of stained glass, light streaming through them casting colored patterns on the floor. A figure with no visible face stands reading one by holding it up to the window."

### E. Negative space / absence — what's NOT there
The illustration is about what's missing, implied, or about to happen.
**Prompt pattern:** "An otherwise [ordinary scene] with a conspicuous [absence/implied event]. Only ink outlines suggested, with watercolor suggesting the ghost of what was or will be."
**Example for AI safety/METR cheating findings:** "A classroom of empty desks, each with a perfectly sharpened pencil and a closed exam booklet. One desk has its booklet open and a small smear of wet ink on the page, still drying. No figures anywhere."

### F. Allegorical bestiary — the creature that represents the idea
An animal, plant, or organism that embodies the concept.
**Prompt pattern:** "A naturalist's illustration of [imaginary organism] whose anatomy encodes [concept]. Rendered with the clinical precision of an Audubon plate, but the subject is entirely invented."
**Example for multi-agent orchestration:** "Audubon-style plate of a creature with seven heads, each a different size and posture, all facing inward toward a small central light source. Tentacles extend from the base connecting to scattered objects in the margins. Ink wash with muted ochre and sienna watercolor."

### G. Monumental Desert — the ancient-future threshold (Dune-inspired)
A scene set in a vast desert landscape where the AI concept is rendered as a monumental structure, celestial phenomenon, or ritual artifact. Combines the base watercolor/ink style with the Dune Aesthetic block above.
**Prompt pattern:** "A [vast desert landscape] where [AI concept] is represented as [monumental/celestial/ritual element]. A lone [figure/observer] stands at the [threshold/edge] in [flowing robes]. The [element] feels simultaneously ancient and futuristic — as if it has been here for millennia. Golden light through dust-filled air. Massive scale emphasizing the smallness of the observer."
**Example for GPT-5.6 Sol/Terra/Luna:** "Three massive celestial orbs — a burning sun, a fertile earth, and a pale moon — float in a haze above an endless desert of amber dunes. Below them, a lone figure in flowing desert robes stands at the base of a monolithic stone structure, half-buried in sand, its surface carved with ancient geometric patterns. The figure raises one arm toward the orbs, as if in ritual acknowledgment. Golden light streams through dust-filled air, creating long solemn rays. The scene feels like a prophecy being fulfilled — ancient, sacred, and technological all at once."

## Aspect ratios
- Lead: `landscape` (16:9)
- Section hero: `landscape` (standard landscape)

## Process

1. Read `/tmp/v2/edition.json`.
2. For each image target (lead + each non-empty section):
   a. **Pick ONE** approach from the rotator (A-G). Each image in the same run MUST use a different approach.
   b. **Extract the core idea** of the article — NOT the subject, the IDEALITY (e.g., for "OpenAI launches restricted model" → the idea is *access*, *gatekeeping*, *scarcity of intelligence*).
   c. **Decide whether to use Dune Aesthetic** — consider if the story's ideality aligns with desert, monumentality, celestial motifs, or ancient-future themes. If yes, append the Dune Aesthetic block to the base style before the chosen approach prompt.
   d. Build prompt = **style base** + **(optional Dune Aesthetic block)** + **chosen approach pattern** + **specific details** tied to the article's ideality. Balanced composition (40-60% negative space). Multiple watercolor colors. Light street art texture (spray grain, drips, splatter) — refined, not aggressive.
   e. **CRITICAL**: Include ink outline contours (handmade, organic). Multiple watercolor hues. Light street art urban texturing (spray paint grain, subtle drips/splatter). Refined and elegant — gallery-ready.
   f. Call `image_generate` with the appropriate aspect_ratio.
   g. Save image to `/tmp/v2/images/` with deterministic name.
      **Check the `image` field returned by `image_generate`** — it may be a local file path
      (e.g. `/home/.../cache/images/...`) **OR a remote URL** (e.g. `https://files-cdn.x.ai/...`).
      - If local path → `cp "<path>" /tmp/v2/images/lead_<date_iso>.jpg`
      - If remote URL → `curl -sL "<url>" -o /tmp/v2/images/lead_<date_iso>.jpg`
      Repeat for sections: `section_<slug>_<date_iso>.jpg`.
      **CRITICAL: never skip this download/copy step.** The image exists only in the cloud
      or cache until you save it to `/tmp/v2/images/`.
   h. Update edition.json. **The `image` value MUST start with `images/` and the slug MUST
      use hyphens:**
      - lead → `e["lead"]["image"] = "images/lead_<date_iso>.jpg"`
      - section → `sec["image"] = "images/section_<slug>_<date_iso>.jpg"`, set on the
        **section dict**, NOT on the first item. `render.py` prefers `sec["image"]`; the
        item-level field is a legacy fallback that wraps the hero in a link plus a title
        overlay, so putting it on an item silently changes the layout you get.
      - `<slug>` = section title, lowercased, non-alphanumerics → `-`:
        `"Research & Papers"` → `research-papers`, `"Open Source & Models"` →
        `open-source-models`, `"Tools & Startups"` → `tools-startups`.
        **Hyphens, never underscores.**
      - **Verify before you finish:** every path you wrote must (a) start with `images/`
        and (b) exist on disk — `ls /tmp/v2/images/`. A bare filename with no directory
        resolves to `/<file>` on the live site → 404 → the hero renders as an empty box.
        This shipped on 2026-10-29: three sections went live with broken heroes because the
        paths were written bare and underscored (`section_research_papers_2026-10-29.jpg`).
        Do not trust a summary that says "wired into edition.json" — check the file.

## Anti-patterns (NEVER do these)

- NO generic neural network visualizations (nodes/edges/graphs)
- NO robot heads, glowing brains, matrix code, circuit boards
- NO dollar signs, bar charts, growth arrows
- NO "AI" text or acronyms anywhere
- NO photorealistic faces
- NO 3D rendering look
- NO stock photo compositions
- NO literal translations of the headline into visual form
- NO same approach twice in one run
- NO monochromatic watercolor — use multiple distinct colors (blues, ambers, greens, purples, etc.)
- NO mostly empty composition — aim for 40-60% negative space, not 80%+
- NO rigid/mechanical ink lines — keep them organic, handmade, imperfect
- NO aggressive street art (heavy spray paint, graffiti tags, chaotic splatter) — keep it refined and gallery-ready
- NO complex scenes, busy textures, or patterns

## Fallback on failure
If `image_generate` errors for any item, OMIT the `image` field and continue. The newspaper never fails for a missing illustration.

## Lookbook (reference)
See `references/metaphor-lookbook.md` for:
- Anti-pattern catalog (literal AI clichés to avoid)
- Curated ideality → metaphor mappings from past runs
- Extended examples for each of the 7 approaches
- The ideality-extraction rule (always abstract the idea BEFORE choosing the image)

## Layout rule
Images render as **full-width banners ABOVE** the section's grid, NOT inside individual column items. One hero image per section.

## Toolset requirement (CRITICAL for cron/orchestrator)

When called as `hermes chat -q` from orchestrator or from a cron-triggered pipeline, the invocation MUST include **`terminal`** in the toolset alongside `file` and `image_gen`:

```bash
hermes chat -q "..." --profile luke -s image-gen -t file,image_gen,terminal -Q --yolo
```

**Why this matters:** `image_generate` returns either a Hermes cache path (e.g. `~/.hermes/profiles/<profile>/cache/images/xai_grok-*.jpg`) or a remote URL (e.g. `https://files-cdn.x.ai/...`). The agent MUST check which type it received and use the appropriate command (`cp` for local, `curl` for remote) to copy/download it to `/tmp/v2/images/lead_<date>.jpg`. Without this step, images are generated but never reach the output directory — the HTML references non-existent files. This happened on 2026-07-10: 5 images were generated correctly but never downloaded from the xAI CDN.

**Rule:** any orchestration that calls image-gen outside interactive chat (bash orchestrator, cron, pipeline) must pass `-t file,image_gen,terminal` — NOT `-t file,image_gen`.