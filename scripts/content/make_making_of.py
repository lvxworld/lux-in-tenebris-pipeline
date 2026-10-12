#!/usr/bin/env python3
"""make_making_of.py — Build the "How this issue made itself" page.

Reads what the pipeline already left behind and turns it into a replayable
account of the run. Pure code: no LLM, no network, and strictly READ-ONLY on
pipeline state, so it can never affect the issue it is describing.

Sources, in order of trust:
  1. /tmp/v2/scouts/scout_*.json  — how much each scout actually returned
  2. /tmp/v2/logs/run_<date>.log  — which scouts failed, issue no, start/end
  3. mtimes of the per-step logs  — when each step finished (hence durations)
  4. /tmp/v2/edition.json         — what actually got published, and the lead

Counts come from the scout JSON files rather than the run log on purpose: the
log line "✓ scout N done (X items)" is only emitted by the seven scouts that go
through run_scout(); youtube and italia are invoked separately and never print
it, so parsing the log alone silently undercounts the desk.

Everything it prints is derived. Nothing is estimated or invented: if a number
can't be computed it is omitted rather than guessed.

Usage:
    python3 make_making_of.py <output.html> [--date YYYY-MM-DD]
                             [--logs DIR] [--edition PATH]

Prints a one-line JSON status (same convention as render.py). Exit non-zero on
error — callers in run.sh treat this step as non-fatal.
"""

import argparse
import html
import json
import os
import re
import sys
from datetime import date as _date, datetime

# Scouts in the order run.sh runs them. Display name + one-line description
# of what that beat is for; both are stable, neither is derived from a model.
SCOUTS = [
    ("x",          "X / Twitter",      "Sixteen hand-picked accounts, filtered to the last 24 hours. Announcements from labs, not commentary about them."),
    ("research",   "arXiv &amp; papers",   "The widest net of the morning, and the harshest cut. Volume is not news."),
    ("official",   "Lab blogs",        "The official announcement pages of the major labs, read directly."),
    ("opensource", "Open weights",     "New open-weights releases, plus the day's GitHub and Hugging Face trending boards."),
    ("tools",      "Tools",            "Product launches and developer tools — kept separate from funding so money never masquerades as product."),
    ("funding",    "Money",            "Who raised, who bought whom, at what valuation."),
    ("hardware",   "Silicon &amp; robots", "Chips, accelerators, humanoids. The only scout that curls every link to check it answers 200 before trusting it."),
    ("youtube",    "Video",            "Ten channels pulled by script, then read for actual news. Tutorials and thumbnail-bait are dropped before the desk sees them."),
    ("italia",     "Italia",           "Italian AI startups and funding. Headline translated to English, link left pointing at the Italian source."),
]

# The rules the editor kills by, taken from skills/editor/SKILL.md.
# Counts are deliberately NOT shown: the editor currently logs only a summary,
# not an itemised list, so a per-rule number would be invented. When the editor
# starts emitting `spiked` in edition.json, feed it in here and show real counts.
SPIKE_RULES = [
    ("low signal", "Not newsworthy enough",
     "Signal is rated 1 to 5. Ones and twos are noise — a minor version bump, a rehash, a thread with no result behind it."),
    ("out of window", "Older than yesterday",
     "The paper covers the last 24 hours. Anything dated before yesterday is somebody else's news, however good."),
    ("duplicate url", "Two scouts, one story",
     "Scouts overlap on purpose. When two surface the same URL the desk keeps the most authoritative source and kills the rest."),
    ("same story", "Same story, different headline",
     "Two outlets writing up one event is one story. Matched on meaning rather than wording, so a reworded headline does not slip through."),
    ("already ran", "Already published this week",
     "Checked against every headline from the last seven days. A story readers already saw is not news, however strong."),
    ("thin section", "Section below threshold",
     "A section needs at least two stories to exist. Below that it folds into the quick hits rather than running half-empty."),
    ("no link", "No usable link",
     "An item without a real link cannot be published. The desk searches once, then kills it — a headline nobody can follow is worse than a shorter paper."),
]


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=False)


def hhmm(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def human_dur(sec):
    sec = int(sec)
    if sec < 60:
        return "%ds" % sec
    return "%dm%02ds" % (sec // 60, sec % 60)


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def last_touch(*paths):
    """Latest mtime among the given files — when that step really stopped.

    A scout writes stdout and stderr to two different files, and they do NOT
    finish together. When a scout is killed by its timeout, stdout stops at the
    banner (nothing was ever produced) while stderr keeps being written right up
    to the kill: on 2026-07-30 the timed-out `official` scout left .out at
    06:44 and .err at 07:04. Taking only .out made the *next* scout look like it
    had run for 34 minutes. The later of the two is the honest end time.
    """
    ts = [t for t in (mtime(p) for p in paths) if t]
    return max(ts) if ts else None


def count_scout(scouts_dir, key):
    """Authoritative item count for one scout, straight from its JSON output.
    Returns None when the file is missing or unreadable, so the caller can tell
    'scout produced nothing' apart from 'scout never ran'."""
    path = os.path.join(scouts_dir, "scout_%s.json" % key)
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if isinstance(d, list):
        return len(d)
    if isinstance(d, dict):
        return len(d.get("editorial") or [])
    return 0


def parse_run_log(path):
    """Pull failures, issue number and run bounds out of the run log.
    Counts deliberately come from count_scout(), not from here."""
    out = {"failed": set(), "issue": None, "start": None, "end": None,
           "images": None, "wire": None, "podcast": None}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return out

    for m in re.finditer(r"✗ scout (\w+) FAILED or TIMEOUT", text):
        out["failed"].add(m.group(1))

    m = re.search(r"✓ issue #(\d+)", text)
    if m:
        out["issue"] = int(m.group(1))
    m = re.search(r"LUX IN TENEBRIS V2 — (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", text)
    if m:
        out["start"] = m.group(1)
    m = re.search(r"V2 PIPELINE COMPLETE — (\d{2}:\d{2}:\d{2})", text)
    if m:
        out["end"] = m.group(1)
    m = re.search(r"Images:\s+(\d+)", text)
    if m:
        out["images"] = int(m.group(1))
    m = re.search(r"✓ (\d+) wire articles written", text)
    if m:
        out["wire"] = int(m.group(1))
    out["podcast"] = "podcast pill injected" in text
    return out


def read_edition(path):
    """What actually made the paper."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    sections = d.get("sections") or []
    published = (
        (1 if d.get("lead") else 0)
        + len(d.get("top_stories") or [])
        + sum(len(s.get("items") or []) for s in sections)
        + len(d.get("quick_hits") or [])
    )
    # Trending is passed through from the opensource scout untouched — the
    # editor neither selects nor spikes it, so it sits outside the editorial
    # funnel. render.py DOES count it in the masthead total, which is why the
    # front page says 61 while the desk only chose 36. Tracked separately so
    # the page can reconcile the two numbers instead of contradicting them.
    trending = d.get("trending") or {}
    passthrough = sum(
        len((trending.get(k) or {}).get("items") or [])
        for k in ("github", "huggingface")
    )
    return {
        "passthrough": passthrough,
        "issue": d.get("issue_no"),
        "date_human": d.get("date_human") or "",
        "date_iso": d.get("date_iso") or "",
        "published": published,
        "lead_title": (d.get("lead") or {}).get("title") or "",
        "lead_summary": (d.get("lead") or {}).get("summary") or "",
        "top": [s.get("title") for s in (d.get("top_stories") or [])],
        "sections": [(s.get("title"), len(s.get("items") or [])) for s in sections],
        "quick": len(d.get("quick_hits") or []),
        # Optional: the editor's own record of what it killed, keyed by rule.
        # Absent until the editor starts emitting it — the page must work either
        # way, so everything downstream treats this as "may be missing".
        "spiked": d.get("spiked") if isinstance(d.get("spiked"), dict) else None,
    }


def build_events(run, ed, logs, scouts_dir, day):
    """Assemble the replay timeline. Durations come from log mtimes; a step with
    no readable mtime simply carries no duration rather than a made-up one."""
    ev = []
    prev_end = None

    start_ts = None
    if run.get("start"):
        try:
            start_ts = datetime.strptime(run["start"], "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            pass
    if start_ts:
        prev_end = start_ts

    issue = run.get("issue") or (ed or {}).get("issue") or "—"
    ev.append({
        "t": hhmm(start_ts) if start_ts else "—",
        "who": "Orchestrator", "host": "self",
        "name": "Wakes up", "meta": "issue #%s" % issue,
        "head": "The presses are set for No. %s." % issue,
        "deck": "Syncs with what is already published, reads the live front page to "
                "work out which issue this is, and archives it before overwriting it.",
        "note": "Yesterday's issue is filed away first. Nothing is lost by starting.",
    })

    gathered = 0
    for key, label, blurb in SCOUTS:
        n = count_scout(scouts_dir, key)
        failed = key in run["failed"]
        if n is None and not failed:
            continue  # scout never ran at all
        info = {"n": n or 0, "failed": failed}
        end = last_touch(
            os.path.join(logs, "scout_%s_%s.out" % (key, day)),
            os.path.join(logs, "scout_%s_%s.err" % (key, day)),
            os.path.join(logs, "scout_%s_%s.log" % (key, day)),
        )
        dur = None
        if end and prev_end and end > prev_end:
            dur = end - prev_end

        if info["failed"]:
            meta = "timed out" + (" · %s" % human_dur(dur) if dur else "")
            head = "One scout does not come back."
            deck = ("The %s scout hits its ceiling and is killed. It returns an empty "
                    "file instead of a broken one, and the morning carries on without it."
                    % label.replace("&amp;", "and").lower())
            note = ("Nothing downstream stops. A missing scout costs the issue a few "
                    "stories, never the issue itself.")
        else:
            gathered += info["n"]
            meta = "%d found" % info["n"] + (" · %s" % human_dur(dur) if dur else "")
            head = "%d %s from the %s beat." % (
                info["n"], "item" if info["n"] == 1 else "items", label.replace("&amp;", "and").lower())
            deck = blurb
            note = None

        ev.append({
            "t": hhmm(prev_end) if prev_end else "—",
            "who": "Scout · " + label, "host": "self",
            "name": label, "meta": meta,
            "head": head, "deck": deck, "note": note,
            "found": 0 if info["failed"] else info["n"],
            "fail": info["failed"],
        })
        if end:
            prev_end = end

    published = (ed or {}).get("published")
    spiked = (gathered - published) if (published is not None and gathered >= published) else None

    ed_end = mtime(os.path.join(logs, "editor_%s.log" % day))
    ev.append({
        "t": hhmm(prev_end) if prev_end else "—",
        "who": "Editor", "host": "self",
        "name": "Editor sits down", "meta": "%d on the desk" % gathered,
        "head": "%d items. Room for %s." % (gathered, published if published is not None else "a few dozen"),
        "deck": "Everything the scouts found lands on one desk. From here on, the work is subtraction.",
        "note": "No external service takes part in a single one of the decisions that follow.",
        "desk": gathered,
    })

    ev.append({
        "t": hhmm(prev_end) if prev_end else "—",
        "who": "Editor", "host": "self",
        "name": "The spike", "meta": ("%d killed" % spiked) if spiked is not None else "the cut",
        "head": ("%d stories go on the spike." % spiked) if spiked is not None
                else "Most of the desk goes on the spike.",
        "deck": "Nothing is dropped on a whim. Every kill traces to one of seven written "
                "rules — open any of them to see what it takes down, and why it exists.",
        "spike": True,
    })

    if ed and ed.get("lead_title"):
        ev.append({
            "t": hhmm(prev_end) if prev_end else "—",
            "who": "Editor", "host": "self",
            "name": "Sets the lead", "meta": "front page",
            "head": ed["lead_title"],
            "deck": ed.get("lead_summary") or "The most consequential story of the day.",
            "note": "Research and open-source items can never lead. A paper that exists "
                    "only on arXiv is not a front page, however good the result.",
        })

    if ed:
        secs = ", ".join("%s (%d)" % (t, n) for t, n in ed["sections"]) or "no sections"
        pt = ed.get("passthrough") or 0
        # Reconcile with the masthead. The front page counts trending entries in
        # its story total, the desk does not — without saying so, a reader
        # clicking through from "61 stories" lands on "36 published" and assumes
        # one of the two is wrong.
        recon = ""
        if pt:
            recon = (" Alongside them the issue carries %d trending entries — GitHub and "
                     "Hugging Face leaderboards reported as they stand, neither chosen nor "
                     "spiked by the desk. That is why the front page counts %d where the "
                     "desk counts %d." % (pt, (published or 0) + pt, published or 0))
        ev.append({
            "t": hhmm(ed_end) if ed_end else (hhmm(prev_end) if prev_end else "—"),
            "who": "Editor", "host": "self",
            "name": "Files the issue", "meta": "%d kept" % (published or 0),
            "head": "One lead, %d top stories, %d sections, %d quick hits." % (
                len(ed["top"]), len(ed["sections"]), ed["quick"]),
            "deck": "Sections this morning: %s. Every remaining URL is checked to be real "
                    "before the file is written — no anchors, no placeholders, no dead links.%s"
                    % (secs, recon),
            "published": published,
        })
    if ed_end:
        prev_end = ed_end

    img_end = mtime(os.path.join(logs, "imagegen_%s.log" % day))
    n_img = run.get("images")
    if n_img:
        dur = img_end - prev_end if (img_end and prev_end and img_end > prev_end) else None
        ev.append({
            "t": hhmm(prev_end) if prev_end else "—",
            "who": "Illustrator", "host": "split",
            "name": "Paints the plates",
            "meta": "%d illustrations" % n_img + (" · %s" % human_dur(dur) if dur else ""),
            "head": "The metaphor is written here. The pixels are not.",
            "deck": "The editor picks the idea behind the story — not the subject, the "
                    "meaning — and writes the scene. Only then does an outside service render it.",
            "plate": "Lead plate · No. %s" % issue,
            "handoff": True,
        })
        if img_end:
            prev_end = img_end

    if run.get("podcast"):
        pod_end = mtime(os.path.join(logs, "podcast_%s.log" % day))
        ev.append({
            "t": hhmm(prev_end) if prev_end else "—",
            "who": "Podcast", "host": "split",
            "name": "The Divide", "meta": "two voices",
            "head": "Castor argues. Luna answers.",
            "deck": "A ninety-second disagreement about the lead story, written line by "
                    "line here, then spoken aloud by an outside voice model. The words are "
                    "ours; only the throat is rented.",
        })
        if pod_end:
            prev_end = pod_end

    total = None
    if start_ts and run.get("end"):
        try:
            end_dt = datetime.strptime("%s %s" % (day, run["end"]), "%Y-%m-%d %H:%M:%S")
            total = end_dt.timestamp() - start_ts
        except ValueError:
            pass

    bits = []
    if ed:
        bits.append("front page")
    if n_img:
        bits.append("%d illustrations" % n_img)
    if run.get("wire"):
        bits.append("%d wire dispatches" % run["wire"])
    if run.get("podcast"):
        bits.append("one podcast")

    ev.append({
        "t": run.get("end", "—")[:5] if run.get("end") else "—",
        "who": "Deploy", "host": "self",
        "name": "Goes to press", "meta": "live",
        "head": "No. %s is on the street." % issue,
        "deck": (", ".join(bits).capitalize() if bits else "The issue") +
                " — committed, pushed, live. One run, no human touched it.",
        "note": ("%s from first scout to publication." % human_dur(total)) if total else None,
    })

    return ev, {"gathered": gathered, "published": published, "spiked": spiked,
                "total": total, "issue": issue,
                "by_rule": (ed or {}).get("spiked")}


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>How this issue made itself — LVX IN TENEBRIS No. {ISSUE}</title>
  <meta name="description" content="A replayable account of how issue No. {ISSUE} of Lux in Tenebris assembled itself: nine scouts, one editor, and every story that got killed.">
  <link rel="stylesheet" href="style.css">
  <style>
{CSS}
  </style>
</head>
<body>
<div class="container">

  <header class="masthead">
    <div class="topline"></div>
    <div class="ears">
      <span class="left">Est. MMXXVI</span>
      <span class="right">No. {ISSUE} <a href="/archive/" class="ar" title="Browse past issues">◆ Archive</a></span>
    </div>
    <div class="nameplate">LVX IN <span class="lux">TENEBRIS</span></div>
    <hr class="rule-double">
    <div class="dateline">
      <span>{DATE_HUMAN}</span>
      <span class="dot">◆</span>
      <span class="tag">AI dispatches from the dark</span>
      <span class="dot">◆</span>
      <span>{PUBLISHED} stories</span>
    </div>
    <div class="devocracy-credit">Inference server generously provided by <a href="https://x.com/ivanfioravanti" target="_blank" rel="noopener">Devocracy</a> · powered by DwarfStar · DeepSeek V4 Flash 0731 (M3 Ultra)!</div>
    <hr class="rule-thin">
  </header>

  <div class="mk-intro">
    <h1>How this issue made itself <span class="mk-betabig">beta</span></h1>
    <p>Nine scouts, one editor, one illustrator — and not a single human decision.
       Replay the run that produced No. {ISSUE}{SPIKED_LINE}</p>
    <a class="mk-back" href="index.html">← Back to the front page</a>
  </div>

  <div class="mk-transport">
    <button class="mk-btn" id="play" type="button">▶ Replay</button>
    <button class="mk-btn ghost" id="restart" type="button">↺ Restart</button>
    <div class="mk-progress"><div class="mk-fill" id="fill"></div></div>
    <div class="mk-clock"><b id="clock">{FIRST_T}</b> &nbsp;/&nbsp; {LAST_T}</div>
    <p class="mk-hint">Click any step on the left to jump straight to it — the replay pauses, nothing restarts.</p>
  </div>

  <div class="mk-split">
    <aside class="mk-ledger">
      <div class="mk-colhead"><span>The night desk</span><span>{NSTEPS} steps</span></div>
      <ol id="ledger"></ol>
    </aside>
    <main class="mk-stage">
      <div class="mk-card" id="stage" aria-live="polite"></div>
    </main>
  </div>

  <div class="mk-tally">
    <div><div class="k">Gathered</div><div class="val" id="t-found">0</div><div class="sub">by nine scouts</div></div>
    <div><div class="k">Published</div><div class="val amber" id="t-pub">0</div><div class="sub">made the issue</div></div>
    <div><div class="k">Spiked</div><div class="val dim" id="t-kill">0</div><div class="sub">killed on the desk</div></div>
    <div><div class="k">Self-hosted</div><div class="val amber" id="t-self">—</div><div class="sub">of every decision</div></div>
  </div>

  <footer class="colophon">
    <p class="mark">Per aspera ad astra</p>
    <p class="meta">Compiled by Hermes Agent · {DATE_ISO} · <a href="https://github.com/lvxworld/luxintenebris-ai-news" target="_blank" rel="noopener">source</a></p>
  </footer>

</div>

<script>
var MK_EVENTS = {EVENTS_JSON};
var MK_SPIKE  = {SPIKE_JSON};
var MK_STATS  = {STATS_JSON};
{JS}
</script>
</body>
</html>
"""

CSS = """    .mk-intro{ margin:30px 0 0; text-align:center; }
    .mk-intro h1{ font-family:var(--serif); font-weight:700; font-size:clamp(27px,4.6vw,44px);
      line-height:1.12; text-wrap:balance; margin:0; color:var(--type); }
    .mk-intro p{ font-family:var(--serif); font-size:17px; line-height:1.6; color:var(--type-dim);
      max-width:58ch; margin:13px auto 0; }
    .mk-betabig{ font-family:var(--sans); font-size:11px; font-weight:600; letter-spacing:.16em;
      text-transform:uppercase; color:var(--muted); border:1px solid var(--rule-strong);
      border-radius:2px; padding:2px 7px; vertical-align:middle; margin-left:8px; }
    .mk-back{ display:inline-block; margin:18px 0 0; font-family:var(--sans); font-size:10.5px;
      font-weight:600; letter-spacing:.14em; text-transform:uppercase; color:var(--lux-soft);
      text-decoration:none; border-bottom:1px solid var(--rule-strong); padding-bottom:2px;
      transition:color .18s ease, border-color .18s ease; }
    .mk-back:hover{ color:var(--lux); border-color:var(--lux-soft); }
    .mk-transport{ display:flex; align-items:center; gap:16px; flex-wrap:wrap; margin:30px 0 0;
      padding:14px 18px; border-top:1px solid var(--rule); border-bottom:1px solid var(--rule); }
    .mk-btn{ font-family:var(--sans); font-size:11px; font-weight:600; letter-spacing:.12em;
      text-transform:uppercase; color:var(--ink); background:var(--lux); border:1px solid var(--lux);
      padding:8px 18px; cursor:pointer; transition:background .18s ease, border-color .18s ease; }
    .mk-btn:hover{ background:var(--lux-soft); border-color:var(--lux-soft); }
    .mk-btn.ghost{ background:transparent; color:var(--lux-soft); border-color:var(--rule-strong); }
    .mk-btn.ghost:hover{ color:var(--lux); border-color:var(--lux-soft); }
    .mk-btn:focus-visible{ outline:2px solid var(--lux); outline-offset:3px; }
    .mk-progress{ flex:1 1 200px; min-width:150px; height:2px; background:var(--rule);
      position:relative; overflow:hidden; }
    .mk-fill{ position:absolute; inset:0 auto 0 0; width:0%; background:var(--lux);
      transition:width .28s linear; }
    .mk-clock{ font-family:var(--sans); font-size:11px; font-weight:500; letter-spacing:.1em;
      color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
    .mk-clock b{ color:var(--type-dim); font-weight:600; }
    .mk-hint{ font-family:var(--sans); font-size:10px; letter-spacing:.06em; color:var(--muted);
      flex:1 1 100%; margin:2px 0 0; }
    .mk-split{ display:grid; grid-template-columns:250px 1fr; gap:36px; margin:30px 0 0; align-items:start; }
    @media (max-width:860px){ .mk-split{ grid-template-columns:1fr; gap:24px; }
      .mk-ledger{ position:static !important; } }
    .mk-colhead{ font-family:var(--sans); font-size:9.5px; font-weight:600; letter-spacing:.2em;
      text-transform:uppercase; color:var(--muted); padding:0 0 10px; border-bottom:1px solid var(--rule);
      display:flex; justify-content:space-between; align-items:baseline; }
    .mk-ledger{ position:sticky; top:18px; }
    .mk-ledger ol{ list-style:none; margin:0; padding:0; }
    .mk-lg{ display:grid; grid-template-columns:48px 12px 1fr; gap:8px; align-items:baseline;
      width:100%; text-align:left; padding:8px 8px 8px 4px; margin:0; background:none; border:0;
      border-bottom:1px solid rgba(39,39,45,.55); border-left:2px solid transparent; font:inherit;
      color:inherit; cursor:pointer; opacity:.34;
      transition:opacity .35s ease, background .16s ease, border-color .16s ease; }
    .mk-lg:hover{ opacity:1; background:rgba(240,162,60,.05); border-left-color:var(--rule-strong); }
    .mk-lg:focus-visible{ outline:2px solid var(--lux); outline-offset:-2px; opacity:1; }
    .mk-lg.seen{ opacity:1; }
    .mk-lg.now{ opacity:1; border-left-color:var(--lux); background:rgba(240,162,60,.07); }
    .mk-lg .t{ font-family:var(--sans); font-size:10.5px; color:var(--muted);
      font-variant-numeric:tabular-nums; letter-spacing:.04em; }
    .mk-lg .m{ font-family:var(--sans); font-size:10px; line-height:1.5; }
    .mk-lg .m.ok{ color:var(--lux-soft); }
    .mk-lg .m.bad{ color:var(--ember); }
    .mk-lg .n{ font-family:var(--serif); font-size:13.5px; color:var(--type-dim); }
    .mk-lg.seen .n, .mk-lg:hover .n{ color:var(--type); }
    .mk-lg.now .n{ color:var(--lux); }
    .mk-lg .n em{ font-family:var(--sans); font-style:normal; font-size:10px; color:var(--muted);
      letter-spacing:.04em; display:block; margin-top:1px; font-variant-numeric:tabular-nums; }
    .mk-stage{ min-height:460px; }
    .mk-card{ border-left:1px solid var(--rule); padding:2px 0 0 30px; }
    @media (max-width:860px){ .mk-card{ border-left:0; padding-left:0; } }
    .mk-actor{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-family:var(--sans);
      font-size:9.5px; font-weight:600; letter-spacing:.2em; text-transform:uppercase; color:var(--muted); }
    .mk-host{ padding:2px 9px; border:1px solid var(--rule-strong); border-radius:2px;
      letter-spacing:.1em; font-size:9px; }
    .mk-host.self{ color:var(--lux-soft); border-color:var(--lux-soft); }
    .mk-host.ext{ color:var(--ember); border-color:rgba(255,107,53,.45); }
    .mk-head{ font-family:var(--serif); font-weight:600; font-size:clamp(23px,3.4vw,33px);
      line-height:1.18; text-wrap:balance; margin:14px 0 0; }
    .mk-deck{ font-family:var(--serif); font-size:16.5px; line-height:1.62; color:var(--type-dim);
      max-width:62ch; margin:13px 0 0; }
    .mk-note{ font-family:var(--serif); font-style:italic; font-size:15.5px; line-height:1.6;
      color:var(--lux-soft); max-width:58ch; margin:20px 0 0; padding:0 0 0 16px;
      border-left:2px solid var(--rule-strong); }
    .mk-spike{ margin:24px 0 0; border-top:1px solid var(--rule); padding-top:20px; }
    .mk-spikehead{ font-family:var(--sans); font-size:9.5px; font-weight:600; letter-spacing:.2em;
      text-transform:uppercase; color:var(--muted); margin-bottom:14px; }
    .mk-rule{ border:1px solid var(--rule); border-left:2px solid var(--ember); margin:0 0 9px; }
    .mk-rule > summary{ list-style:none; cursor:pointer; padding:11px 14px; display:flex;
      align-items:baseline; gap:11px; flex-wrap:wrap; transition:background .16s ease; }
    .mk-rule > summary::-webkit-details-marker{ display:none; }
    .mk-rule > summary:hover{ background:rgba(255,107,53,.05); }
    .mk-rule > summary:focus-visible{ outline:2px solid var(--lux); outline-offset:-2px; }
    .mk-rule .count{ font-family:var(--sans); font-size:11px; font-weight:600; color:var(--ember);
      font-variant-numeric:tabular-nums; min-width:26px; }
    .mk-rule .rname{ font-family:var(--serif); font-size:15.5px; color:var(--type); flex:1 1 200px; }
    .mk-rule .rcode{ font-family:var(--sans); font-size:9px; letter-spacing:.14em;
      text-transform:uppercase; color:var(--muted); border:1px solid var(--rule-strong);
      border-radius:2px; padding:2px 7px; }
    .mk-rule .body{ padding:0 14px 14px; }
    .mk-rule .why{ font-family:var(--serif); font-style:italic; font-size:14.5px; line-height:1.55;
      color:var(--lux-soft); margin:0; max-width:60ch; }
    .mk-plate{ margin:22px 0 0; border:1px solid var(--rule-strong); aspect-ratio:16/7;
      position:relative; overflow:hidden; filter:saturate(.85);
      background:
        radial-gradient(70% 120% at 26% 18%, rgba(240,162,60,.30), transparent 62%),
        radial-gradient(80% 120% at 78% 76%, rgba(255,107,53,.20), transparent 60%),
        radial-gradient(60% 90% at 55% 50%, rgba(202,162,106,.15), transparent 70%),
        #14110e; }
    .mk-plate::after{ content:""; position:absolute; inset:0; mix-blend-mode:multiply;
      background:repeating-linear-gradient(98deg, rgba(0,0,0,.16) 0 1px, transparent 1px 3px); }
    .mk-plate .cap{ position:absolute; left:0; right:0; bottom:0; z-index:2; padding:9px 13px;
      background:linear-gradient(transparent, rgba(14,14,16,.94) 55%); font-family:var(--sans);
      font-size:9.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); }
    .mk-handoff{ display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin:20px 0 0;
      font-family:var(--sans); font-size:11px; letter-spacing:.04em; color:var(--type-dim); }
    .mk-handoff .arrow{ color:var(--rule-strong); font-size:15px; }
    .mk-tally{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:1px;
      margin:34px 0 0; background:var(--rule); border:1px solid var(--rule); }
    .mk-tally div{ background:var(--ink); padding:18px; }
    .mk-tally .k{ font-family:var(--sans); font-size:9.5px; font-weight:600; letter-spacing:.18em;
      text-transform:uppercase; color:var(--muted); }
    .mk-tally .val{ font-family:var(--serif); font-size:33px; font-weight:600; line-height:1.1;
      margin:7px 0 0; font-variant-numeric:tabular-nums; }
    .mk-tally .val.amber{ color:var(--lux); }
    .mk-tally .val.dim{ color:var(--muted); }
    .mk-tally .sub{ font-family:var(--sans); font-size:10px; color:var(--muted);
      letter-spacing:.03em; margin-top:3px; }
    @media (prefers-reduced-motion:reduce){
      *{ transition-duration:.01ms !important; animation-duration:.01ms !important; } }"""

JS = r"""
(function(){
  "use strict";
  var EVENTS = MK_EVENTS, SPIKE = MK_SPIKE, STATS = MK_STATS;
  if (!EVENTS || !EVENTS.length) return;

  var HOLD = 2600;
  EVENTS.forEach(function(e){ e.hold = e.spike ? 4200 : (e.note ? 3100 : HOLD); });
  var TOTAL = EVENTS.reduce(function(a,e){ return a + e.hold; }, 0);

  var IDLE = {
    who:"Ready", host:"self",
    head:"The run, replayed in a minute.",
    deck:"Nine scouts comb the web, an editor decides what deserves the front page, "
       + "and an illustrator paints it. Press replay to watch it happen — or click "
       + "any step on the left to go straight there.",
    note:"The interesting part is not what got printed. It is everything that did not."
  };

  var $ = function(id){ return document.getElementById(id); };
  var ledgerEl=$("ledger"), stageEl=$("stage"), fillEl=$("fill"),
      clockEl=$("clock"), playBtn=$("play"), restartBtn=$("restart");

  var OFFSET=[], acc=0;
  EVENTS.forEach(function(e){ OFFSET.push(acc); acc += e.hold; });

  EVENTS.forEach(function(e,i){
    var li=document.createElement("li"), b=document.createElement("button");
    b.className="mk-lg"; b.id="lg"+i; b.type="button";
    var mark = e.fail ? '<span class="m bad">✗</span>' : '<span class="m ok">✓</span>';
    b.innerHTML='<span class="t">'+e.t+'</span>'+mark+
                '<span class="n">'+e.name+'<em>'+e.meta+'</em></span>';
    b.addEventListener("click", function(){ jump(i); });
    li.appendChild(b); ledgerEl.appendChild(li);
  });

  var timers=[], playing=false, idx=-1, elapsed=0, tick=null;

  function hostTag(h){
    if (h==="self") return '<span class="mk-host self">self-hosted</span>';
    if (h==="ext")  return '<span class="mk-host ext">external</span>';
    return '<span class="mk-host self">self-hosted</span><span class="mk-host ext">external</span>';
  }

  function spikeHTML(){
    var h='<div class="mk-spike"><div class="mk-spikehead">On the spike — '+
          (STATS.spiked!=null ? STATS.spiked+' killed, ' : '')+'seven rules</div>';
    SPIKE.forEach(function(r){
      // Per-rule counts appear only when the editor actually reported them.
      // Until then the rule is shown without a number rather than with a
      // guessed one — the whole page is worth nothing if its figures aren't real.
      var n = (STATS.by_rule && STATS.by_rule[r[0]] != null) ? STATS.by_rule[r[0]] : null;
      h+='<details class="mk-rule"><summary>'+
         (n !== null ? '<span class="count">'+n+'</span>' : '')+
         '<span class="rname">'+r[1]+
         '</span><span class="rcode">'+r[0]+'</span></summary>'+
         '<div class="body"><p class="why">'+r[2]+'</p></div></details>';
    });
    return h+'</div>';
  }

  function render(e){
    var h='<div class="mk-actor"><span>'+e.who+'</span>'+hostTag(e.host)+'</div>';
    h+='<h2 class="mk-head">'+e.head+'</h2>';
    h+='<p class="mk-deck">'+e.deck+'</p>';
    if (e.plate){ h+='<div class="mk-plate"><div class="cap">'+e.plate+'</div></div>'; }
    if (e.handoff){ h+='<div class="mk-handoff"><span>DeepSeek writes the scene</span>'+
      '<span class="arrow">→</span><span>Grok Imagine renders it</span></div>'; }
    if (e.note){ h+='<p class="mk-note">'+e.note+'</p>'; }
    if (e.spike){ h+=spikeHTML(); }
    stageEl.innerHTML=h;
  }

  function counters(upTo){
    var found=0;
    for (var i=0;i<=upTo && i<EVENTS.length;i++){ if (EVENTS[i].found) found+=EVENTS[i].found; }
    var pub=0, kill=0, self="—";
    for (var j=0;j<=upTo && j<EVENTS.length;j++){
      if (EVENTS[j].published!=null) pub=EVENTS[j].published;
      if (EVENTS[j].spike && STATS.spiked!=null) kill=STATS.spiked;
      if (EVENTS[j].desk!=null) self="100%";
    }
    $("t-found").textContent=found;
    $("t-pub").textContent=pub;
    $("t-kill").textContent=kill;
    $("t-self").textContent=self;
  }

  function show(i, scroll){
    idx=i; render(EVENTS[i]); clockEl.textContent=EVENTS[i].t;
    EVENTS.forEach(function(_,j){
      var el=$("lg"+j);
      el.classList.toggle("seen", j<=i);
      el.classList.toggle("now", j===i);
    });
    counters(i);
    if (scroll!==false){
      var el=$("lg"+i);
      if (el && el.scrollIntoView) el.scrollIntoView({block:"nearest", behavior:"smooth"});
    }
  }

  function clearAll(){ timers.forEach(clearTimeout); timers=[]; if(tick){clearInterval(tick); tick=null;} }

  function schedule(fromIdx, fromElapsed){
    var a=fromElapsed;
    for (var i=fromIdx;i<EVENTS.length;i++){
      (function(k,d){ timers.push(setTimeout(function(){ show(k); }, d)); })(i, a-fromElapsed);
      a+=EVENTS[i].hold;
    }
    timers.push(setTimeout(function(){ playing=false; playBtn.textContent="▶ Replay"; }, a-fromElapsed));
    var t0=Date.now();
    tick=setInterval(function(){
      elapsed=Math.min(fromElapsed+(Date.now()-t0), TOTAL);
      fillEl.style.width=(elapsed/TOTAL*100)+"%";
      if (elapsed>=TOTAL){ clearInterval(tick); tick=null; }
    },100);
  }

  function play(){
    if (playing) return;
    if (elapsed>=TOTAL) reset();
    playing=true; playBtn.textContent="❙❙ Pause";
    var start=0,a=0;
    for (var i=0;i<EVENTS.length;i++){
      if (a+EVENTS[i].hold>elapsed){ start=i; break; }
      a+=EVENTS[i].hold; start=i+1;
    }
    if (start<EVENTS.length && start!==idx) show(start);
    schedule(Math.min(start+1, EVENTS.length), elapsed);
  }

  function pause(){ playing=false; playBtn.textContent="▶ Replay"; clearAll(); }

  function jump(i){
    pause(); elapsed=OFFSET[i];
    fillEl.style.width=(elapsed/TOTAL*100)+"%";
    show(i,false);
  }

  function reset(){
    clearAll(); playing=false; idx=-1; elapsed=0;
    fillEl.style.width="0%"; clockEl.textContent=EVENTS[0].t;
    playBtn.textContent="▶ Replay";
    EVENTS.forEach(function(_,j){ $("lg"+j).classList.remove("seen","now"); });
    counters(-1); render(IDLE);
  }

  playBtn.addEventListener("click", function(){ playing ? pause() : play(); });
  restartBtn.addEventListener("click", function(){ reset(); play(); });

  render(IDLE); counters(-1);
})();
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output", help="path to write making-of.html")
    ap.add_argument("--date", default=_date.today().isoformat())
    ap.add_argument("--logs", default="/tmp/v2/logs")
    ap.add_argument("--edition", default="/tmp/v2/edition.json")
    ap.add_argument("--scouts", default="/tmp/v2/scouts")
    args = ap.parse_args()

    day = args.date
    run = parse_run_log(os.path.join(args.logs, "run_%s.log" % day))
    ed = read_edition(args.edition)

    any_scout = any(count_scout(args.scouts, k) is not None for k, _, _ in SCOUTS)
    if not any_scout and ed is None:
        print(json.dumps({"status": "error",
                          "error": "no scout output and no edition.json — nothing to describe"}))
        sys.exit(1)

    events, stats = build_events(run, ed, args.logs, args.scouts, day)
    if not events:
        print(json.dumps({"status": "error", "error": "no events derived"}))
        sys.exit(1)

    spiked_line = ""
    if stats["spiked"]:
        spiked_line = ", including the %d stories that never made it." % stats["spiked"]
    else:
        spiked_line = "."

    page = PAGE.format(
        ISSUE=esc(stats["issue"]),
        DATE_HUMAN=esc((ed or {}).get("date_human") or day),
        DATE_ISO=esc((ed or {}).get("date_iso") or day),
        PUBLISHED=esc(stats["published"] if stats["published"] is not None else "—"),
        SPIKED_LINE=esc(spiked_line),
        FIRST_T=esc(events[0]["t"]),
        LAST_T=esc(events[-1]["t"]),
        NSTEPS=len(events),
        CSS=CSS,
        EVENTS_JSON=json.dumps(events, ensure_ascii=False),
        SPIKE_JSON=json.dumps(SPIKE_RULES, ensure_ascii=False),
        STATS_JSON=json.dumps(stats, ensure_ascii=False),
        JS=JS,
    )

    try:
        outdir = os.path.dirname(os.path.abspath(args.output))
        if outdir:
            os.makedirs(outdir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(page)
    except OSError as e:
        print(json.dumps({"status": "error", "error": "cannot write output: %s" % e}))
        sys.exit(1)

    print(json.dumps({"status": "ok", "output": args.output, "steps": len(events),
                      "gathered": stats["gathered"], "published": stats["published"],
                      "spiked": stats["spiked"]}))


if __name__ == "__main__":
    main()
