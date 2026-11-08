#!/usr/bin/env python3
"""
render.py — Lux in Tenebris newspaper renderer.

Turns ONE edited "edition" JSON (produced by the Editor-in-Chief agent) into the
final front page. No LLM ever writes raw HTML: the editor only decides importance,
section, and wording; this script lays it out deterministically so the page can
never break.

Usage:
    python3 render.py <edition.json> <output.html> [--templates DIR]

Edition JSON shape:
{
  "issue_no": 142,
  "date_iso": "2026-06-23",
  "date_human": "Tuesday, 23 June 2026",
  "notice": null,                      # or a short string for light/quiet days
  "lead":  {"kicker","title","summary","source","date","url"},   # the single biggest story
  "top_stories": [ {title,summary,source,date,url}, ... ],        # 0-3 prominent stories
  "sections": [                        # ordered; each rendered as a ruled block
     {"title":"Research & Papers", "items":[ {title,summary,source,date,url}, ... ]},
     ...
  ],
  "quick_hits": [ {title,source,url}, ... ]                       # ~10 one-liners
}

Prints a JSON status line to stdout: {"status":"ok",...} or {"status":"error","error":...}.
Exit code is non-zero on error.
"""
import sys
import os
import json
import html
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load(templates_dir, name):
    with open(os.path.join(templates_dir, name), "r", encoding="utf-8") as f:
        return f.read()


def esc(value, default=""):
    """Escape for HTML text content."""
    return html.escape(str(value if value is not None else default), quote=False)


def esc_attr(value, default=""):
    """Escape for an HTML attribute (e.g. href)."""
    return html.escape(str(value if value is not None else default), quote=True)


def is_valid_url(url):
    """Return True if url is a real http/https link (not #, empty, or fragment-only)."""
    if not url:
        return False
    u = str(url).strip()
    return u.startswith("http://") or u.startswith("https://")


def clean_edition(data):
    """Pre-process edition JSON: remove items with missing/broken URLs.
    This is the LAST LINE OF DEFENSE against href='#' in the HTML."""
    import sys

    removed = {"lead": 0, "top": 0, "sections": 0, "quick_hits": 0, "trending": 0, "free_models": 0}

    # Lead
    lead = data.get("lead") or {}
    if lead and not is_valid_url(lead.get("url")):
        print(f"  [render] WARNING: lead story '{lead.get('title','?')[:50]}...' has no valid URL — setting lead to null", file=sys.stderr)
        data["lead"] = None
        removed["lead"] = 1

    # Top stories
    top = data.get("top_stories") or []
    filtered_top = [s for s in top if is_valid_url(s.get("url"))]
    removed["top"] = len(top) - len(filtered_top)
    data["top_stories"] = filtered_top

    # Sections
    sections = data.get("sections") or []
    for sec in sections:
        items = sec.get("items") or []
        filtered = [it for it in items if is_valid_url(it.get("url"))]
        removed_count = len(items) - len(filtered)
        if removed_count > 0:
            print(f"  [render] WARNING: {removed_count} item(s) in section '{sec.get('title','?')}' dropped (no valid URL)", file=sys.stderr)
        removed["sections"] += removed_count
        sec["items"] = filtered
    # Remove empty sections
    data["sections"] = [s for s in sections if s.get("items")]

    # Quick hits
    qh = data.get("quick_hits") or []
    filtered_qh = [h for h in qh if is_valid_url(h.get("url"))]
    removed["quick_hits"] = len(qh) - len(filtered_qh)
    data["quick_hits"] = filtered_qh

    # Trending items
    trending = data.get("trending")
    if trending:
        for key in ("github", "huggingface"):
            sub = trending.get(key) or {}
            items = sub.get("items") or []
            filtered_t = [it for it in items if is_valid_url(it.get("url"))]
            removed_count = len(items) - len(filtered_t)
            if removed_count > 0:
                print(f"  [render] WARNING: {removed_count} trending {key} item(s) dropped (no valid URL)", file=sys.stderr)
            removed["trending"] += removed_count
            sub["items"] = filtered_t

    # Free models items
    free_models = data.get("free_models")
    if free_models:
        for key in ("openrouter", "opencode_zen"):
            sub = free_models.get(key) or {}
            items = sub.get("items") or []
            filtered_f = [it for it in items if is_valid_url(it.get("url"))]
            removed_count = len(items) - len(filtered_f)
            if removed_count > 0:
                print(f"  [render] WARNING: {removed_count} free_models {key} item(s) dropped (no valid URL)", file=sys.stderr)
            removed["free_models"] += removed_count
            sub["items"] = filtered_f

    total = sum(removed.values())
    if total > 0:
        detail = ", ".join(f"{k}={v}" for k, v in removed.items() if v > 0)
        print(f"  [render] {total} item(s) removed due to invalid URLs ({detail})", file=sys.stderr)

    return data


def fill(template, mapping):
    out = template
    for key, val in mapping.items():
        out = out.replace("{{" + key + "}}", val)
    return out


def render_lead(tpl, lead):
    if not lead:
        return ""
    # Handle optional image for lead
    image_html = ""
    if lead.get("image"):
        image_html = f'<img src="{esc_attr(norm_img_path(lead["image"]))}" alt="" class="lead-image">'
    return fill(tpl, {
        "KICKER": esc(lead.get("kicker", "Top Story")) or "Top Story",
        "TITLE": esc(lead.get("title")),
        "SUMMARY": esc(lead.get("summary")),
        "SOURCE": esc(lead.get("source", "—")),
        "DATE": esc(lead.get("date", "")),
        "URL": esc_attr(lead.get("url", "#")) or "#",
        "IMAGE": image_html,
    })


def render_item(tpl, item):
    return fill(tpl, {
        "TITLE": esc(item.get("title")),
        "SUMMARY": esc(item.get("summary", "")),
        "SOURCE": esc(item.get("source", "—")),
        "DATE": esc(item.get("date", "")),
        "URL": esc_attr(item.get("url", "#")) or "#",
    })


def render_top(top_wrap, top_item_tpl, stories):
    if not stories:
        return ""
    items = "\n".join(render_item(top_item_tpl, s) for s in stories[:3])
    return fill(top_wrap, {"ITEMS": items})


def norm_img_path(p):
    """Image srcs are relative to the page root, so they MUST be 'images/<file>'.
    A bare filename (no directory part) resolves to /<file> on the live site and
    404s silently — the section hero renders as a broken/empty box (2026-10-29)."""
    p = (p or "").strip()
    if not p or p.startswith(("http://", "https://", "/", "images/", "data:")):
        return p
    return "images/" + p


def render_sections(section_tpl, item_tpl, sections):
    blocks = []
    for sec in sections or []:
        items = sec.get("items") or []
        if not items:
            continue
        rendered = "\n".join(render_item(item_tpl, it) for it in items)
        # Section-level image (preferred) OR item-level image (legacy/fallback).
        # If the section itself has an "image" field, render it as a hero banner
        # with no link overlay. Otherwise scan items for an image.
        section_image_html = ""
        if sec.get("image"):
            # Section-level image: full-width banner, no overlay title
            section_image_html = (
                f'<div class="section-hero">'
                f'<img src="{esc_attr(norm_img_path(sec["image"]))}" alt="" class="section-hero-img">'
                f'</div>'
            )
        else:
            # Fallback: first item with an image becomes the hero
            for it in items:
                if it.get("image"):
                    img_tag = (
                        f'<a href="{esc_attr(it.get("url", "#")) or "#"}" '
                        f'target="_blank" rel="noopener" class="section-hero">'
                        f'<img src="{esc_attr(norm_img_path(it["image"]))}" alt="" class="section-hero-img">'
                        f'<h4 class="hero-title">{esc(it.get("title",""))}</h4>'
                        f'</a>'
                    )
                    section_image_html = img_tag
                    break
        blocks.append(fill(section_tpl, {
            "SECTION_TITLE": esc(sec.get("title", "Stories")),
            "SECTION_COUNT": f"{len(items):02d}",
            "ITEMS": rendered,
            "SECTION_IMAGE": section_image_html,
        }))
    return "\n".join(blocks)


def render_trending_section(tpl_section, tpl_item, trending):
    """Render dual-column trending (GitHub + HuggingFace side by side)."""
    if not trending:
        return ""

    gh = (trending.get("github") or {}).get("items") or []
    hf = (trending.get("huggingface") or {}).get("items") or []

    if not gh and not hf:
        return ""

    gh_html = "\n".join(
        render_trending_item(tpl_item, i + 1, it)
        for i, it in enumerate(gh[:15])
    )

    hf_html = "\n".join(
        render_trending_item(tpl_item, i + 1, it)
        for i, it in enumerate(hf[:10])
    )

    out = tpl_section
    out = out.replace("{{GITHUB_ITEMS}}", gh_html)
    out = out.replace("{{HUGGINGFACE_ITEMS}}", hf_html)
    return out


def render_free_models_section(tpl_section, tpl_item, free_models):
    """Render dual-column free-models widget (OpenRouter + OpenCode Zen side by side).
    Reuses the same item template/markup as trending (rank + name + meta)."""
    if not free_models:
        return ""

    openrouter = (free_models.get("openrouter") or {}).get("items") or []
    opencode_zen = (free_models.get("opencode_zen") or {}).get("items") or []

    if not openrouter and not opencode_zen:
        return ""

    openrouter_shown = openrouter[:20]
    opencode_zen_shown = opencode_zen[:20]

    openrouter_html = "\n".join(
        render_trending_item(tpl_item, i + 1, it)
        for i, it in enumerate(openrouter_shown)
    )

    opencode_zen_html = "\n".join(
        render_trending_item(tpl_item, i + 1, it)
        for i, it in enumerate(opencode_zen_shown)
    )

    out = tpl_section
    out = out.replace("{{OPENROUTER_ITEMS}}", openrouter_html)
    out = out.replace("{{OPENCODE_ZEN_ITEMS}}", opencode_zen_html)
    out = out.replace("{{FREE_MODELS_COUNT}}", f"{len(openrouter_shown) + len(opencode_zen_shown):02d}")
    return out


def render_trending_item(tpl, rank, item):
    out = tpl
    out = out.replace("{{RANK}}", f"{rank:02d}")
    out = out.replace("{{NAME}}", html.escape(str(item.get("name", "")), quote=False))
    out = out.replace("{{URL}}", html.escape(str(item.get("url", "#")), quote=True))
    meta = item.get("meta", "")
    out = out.replace("{{META}}", html.escape(str(meta), quote=False) if meta else "")
    return out


def render_quick(quick_wrap, quick_item_tpl, hits):
    if not hits:
        return ""
    items = "\n".join(
        fill(quick_item_tpl, {
            "TITLE": esc(h.get("title")),
            "SOURCE": esc(h.get("source", "—")),
            "URL": esc_attr(h.get("url", "#")) or "#",
        }) for h in hits
    )
    return fill(quick_wrap, {"ITEMS": items, "COUNT": f"{len(hits):02d}"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edition", help="path to edition JSON")
    ap.add_argument("output", help="path to output HTML (e.g. index.html in the deploy dir)")
    ap.add_argument("--templates", default=os.path.join(SCRIPT_DIR, "templates"),
                    help="templates directory (default: ./templates next to render.py)")
    args = ap.parse_args()

    try:
        with open(args.edition, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"cannot read edition JSON: {e}"}))
        sys.exit(1)

    tdir = args.templates
    p = os.path.join(tdir, "partials")
    try:
        page_tpl = load(tdir, "newspaper.html")
        lead_tpl = load(p, "lead.html")
        top_wrap = load(p, "top-wrap.html")
        top_item = load(p, "top-item.html")
        section_tpl = load(p, "section.html")
        std_item = load(p, "standard-item.html")
        quick_wrap = load(p, "quick-hits.html")
        quick_item = load(p, "quick-hit.html")
        notice_tpl = load(p, "notice.html")
        trending_tpl = load(p, "trending-section.html")
        trending_item = load(p, "trending-item.html")
        free_models_tpl = load(p, "free-models-section.html")
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"cannot read template: {e}"}))
        sys.exit(1)

    lead = data.get("lead") or {}
    top = data.get("top_stories") or []
    sections = data.get("sections") or []
    quick = data.get("quick_hits") or []
    notice = data.get("notice")
    trending = data.get("trending")
    free_models = data.get("free_models")

    # Inject item_tpl into trending sub-sections so render_trending_section can use it
    if trending:
        for key in ("github", "huggingface"):
            if trending.get(key):
                trending[key]["item_tpl"] = trending_item

    section_total = sum(len(s.get("items") or []) for s in sections)
    trending_count = 0
    if trending:
        trending_count += len((trending.get("github") or {}).get("items") or [])
        trending_count += len((trending.get("huggingface") or {}).get("items") or [])
    free_models_count = 0
    if free_models:
        free_models_count += len((free_models.get("openrouter") or {}).get("items") or [])
        free_models_count += len((free_models.get("opencode_zen") or {}).get("items") or [])
    count = (1 if lead else 0) + len(top) + section_total + len(quick) + trending_count + free_models_count

    notice_html = fill(notice_tpl, {"NOTICE_TEXT": esc(notice)}) if notice else ""

    # Only point the masthead at #free-models if that section will actually
    # render today — an anchor to a section that isn't there is dead chrome.
    free_models_masthead_link = (
        ' <a href="#free-models" class="ar" title="Today\'s free AI models">⌁ Free Models</a>'
        if free_models_count > 0 else ""
    )

    html_out = fill(page_tpl, {
        "ISSUE_NO": esc(data.get("issue_no", "—")),
        "DATE_HUMAN": esc(data.get("date_human", "")),
        "DATE_ISO": esc(data.get("date_iso", "")),
        "COUNT": str(count),
        "NOTICE": notice_html,
        "LEAD": render_lead(lead_tpl, lead),
        "TOP_STORIES": render_top(top_wrap, top_item, top),
        "SECTIONS": render_sections(section_tpl, std_item, sections),
        "TRENDING": render_trending_section(trending_tpl, trending_item, trending),
        "FREE_MODELS": render_free_models_section(free_models_tpl, trending_item, free_models),
        "FREE_MODELS_MASTHEAD_LINK": free_models_masthead_link,
        "QUICK_HITS": render_quick(quick_wrap, quick_item, quick),
    })

    try:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_out)
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"cannot write output: {e}"}))
        sys.exit(1)

    print(json.dumps({
        "status": "ok",
        "output": args.output,
        "counts": {
            "lead": 1 if lead else 0,
            "top_stories": len(top),
            "sections": {s.get("title", "?"): len(s.get("items") or []) for s in sections},
            "trending_github": len((trending.get("github") or {}).get("items") or []) if trending else 0,
            "trending_huggingface": len((trending.get("huggingface") or {}).get("items") or []) if trending else 0,
            "free_models_openrouter": len((free_models.get("openrouter") or {}).get("items") or []) if free_models else 0,
            "free_models_opencode_zen": len((free_models.get("opencode_zen") or {}).get("items") or []) if free_models else 0,
            "quick_hits": len(quick),
            "total": count,
        },
    }))


if __name__ == "__main__":
    main()
