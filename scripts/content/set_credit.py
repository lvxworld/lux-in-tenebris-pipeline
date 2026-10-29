#!/usr/bin/env python3
"""set_credit.py — make the masthead credit line match the backend that ACTUALLY ran.

The credit is hardcoded in template/newspaper.html and make_making_of.py as the
ailab/Devocracy attribution. When a run goes out on another provider (a sanctioned
openrouter rescue), the published page credited Ivan's server for work it never did.
This rewrites the .devocracy-credit div content from $PIPELINE_PROVIDER/$PIPELINE_MODEL.

Usage:
    python3 set_credit.py <file.html> <provider> <model> [--output OUT]

Idempotent: re-running with the same arguments leaves the file byte-identical.
"""
import re
import sys
from pathlib import Path

DIV_RE = re.compile(
    r'(<div class="devocracy-credit">)(.*?)(</div>)', re.DOTALL)

AILAB = (
    'Inference server generously provided by '
    '<a href="https://x.com/ivanfioravanti" target="_blank" rel="noopener">Devocracy</a>'
    ' · lux (GLM-5.3 Flash EXL3)!'
)


def credit_html(provider: str, model: str) -> str:
    if provider == "localAIServer":
        return AILAB
    if provider == "openrouter":
        return (
            'Inference via '
            '<a href="https://openrouter.ai" target="_blank" rel="noopener">OpenRouter</a>'
            f' · {model}'
        )
    return f'Inference via {provider} · {model}'


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = None
    if "--output" in sys.argv:
        out = sys.argv[sys.argv.index("--output") + 1]
    if len(args) != 3:
        print(__doc__)
        return 2
    path, provider, model = args
    p = Path(path)
    if not p.is_file():
        print(f"set_credit: file not found: {path}", file=sys.stderr)
        return 1
    html = p.read_text(encoding="utf-8")
    new = DIV_RE.sub(lambda m: m.group(1) + credit_html(provider, model) + m.group(3), html)
    if new == html:
        print("set_credit: no devocracy-credit div found (nothing changed)")
    Path(out or path).write_text(new, encoding="utf-8")
    print(f"set_credit: credit set for provider={provider} model={model} -> {out or path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
