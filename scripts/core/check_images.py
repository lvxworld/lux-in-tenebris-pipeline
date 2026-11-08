#!/usr/bin/env python3
"""Validate that every local asset referenced by the published page exists on disk.

Why this exists: a wrong asset path fails SILENTLY. The page ships, HTTP returns 200,
and the reader just sees an empty box where the illustration should be. Two ways it
happens, both seen in production:

  * a bare filename with no directory (`src="section_x_2026-10-29.jpg"`) resolves to
    `/<file>` at the site root instead of `images/<file>` → 404 (2026-10-29, three
    section heroes shipped as empty boxes);
  * a slug written with underscores where the file on disk uses hyphens (or the other
    way round) → 404.

Usage:  check_images.py <page.html> <deploy_dir>

Behaviour: reports every missing reference, auto-heals a missing reference when a file
with the same name modulo `_`/`-` exists (rewriting the src in place), and always exits
0 — a missing illustration must never block the edition. Prints a summary line so the
run log shows the state of the assets at a glance.
"""
import os
import re
import sys

ASSET_RE = re.compile(r'(?:src|href)="([^"?#]+\.(?:jpg|jpeg|png|webp|ogg|mp3|woff2?))(?:\?[^"]*)?"')
BARE_RE = re.compile(r'(?:src|href)="([A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|webp|ogg|mp3))"')


def key(name):
    """Separator-insensitive key: `section_research-papers_2026-10-29.jpg` and
    `section_research_papers_2026_10_29.jpg` collapse to the same value, so a slug
    written with the wrong separator can still be matched to the real file."""
    return re.sub(r'[-_]', '', name.lower())


def find_match(dirpath, name):
    """Real filename in dirpath whose separator-insensitive key matches `name`."""
    if not os.path.isdir(dirpath):
        return None
    want = key(name)
    for entry in sorted(os.listdir(dirpath)):
        if key(entry) == want:
            return entry
    return None


def main():
    if len(sys.argv) < 3:
        print("usage: check_images.py <page.html> <deploy_dir>")
        return 0
    page, deploy = sys.argv[1], sys.argv[2]
    html = open(page, encoding='utf-8', errors='replace').read()

    refs = []
    for m in ASSET_RE.finditer(html):
        p = m.group(1)
        if p.startswith(('http://', 'https://', 'data:', '//')):
            continue
        refs.append(p)
    # Bare filenames are always a bug: they resolve to the site root, not to images/.
    bare = [m.group(1) for m in BARE_RE.finditer(html) if '/' not in m.group(1)]

    missing, healed = [], []
    for ref in sorted(set(refs) | set(bare)):
        target = os.path.join(deploy, ref)
        if os.path.exists(target):
            continue
        # auto-heal: match the real file by separator-insensitive key, in the ref's
        # own directory and — for a bare filename — in images/ too.
        fixed = None
        d, base = os.path.split(ref)
        for cand_dir in ([d] if d else ['', 'images']):
            match = find_match(os.path.join(deploy, cand_dir), base)
            if match:
                fixed = '/'.join(p for p in (cand_dir, match) if p)
                break
        if fixed:
            html = html.replace(f'"{ref}"', f'"{fixed}"')
            healed.append((ref, fixed))
            print(f"  ~ auto-fixed src: {ref} -> {fixed}")
        else:
            missing.append(ref)
            print(f"  ! MISSING ASSET: {ref} (no file at {target})")

    if healed:
        open(page, 'w', encoding='utf-8').write(html)

    total = len(set(refs) | set(bare))
    print(f"assets: {total} referenced, {len(healed)} auto-fixed, {len(missing)} missing")
    return 0


if __name__ == '__main__':
    sys.exit(main())
