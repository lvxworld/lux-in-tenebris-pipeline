#!/usr/bin/env python3
"""Pre-push guard: refuse to publish credential-like content to the PUBLIC deploy repo.

Why this exists: run.sh does `git add -A` inside the deploy worktree, so anything
that lands there — a stray .env, a raw API log, an auth dump, a debug script with
a hardcoded key — would be committed and pushed to a public repo automatically.

Two severities, on purpose:
  BLOCK  a credential store by filename, or a high-confidence token inside a
         non-content file (code, config, logs). Exit 1 → caller unstages and
         skips the push.
  WARN   a high-confidence token inside *news content* (index.html, editions/,
         archive/, rss.xml, markdown). A real key quoted by a news article is not
         our leak, and blocking the whole day's release over prose would be
         worse than the risk — so it is reported, not enforced.

Usage: secret_guard.py <deploy_dir>
Prints nothing when clean. Matched values are masked; never prints a whole key.
"""
import re
import subprocess
import sys

# High-confidence token shapes only. Deliberately NOT things like "sk-" followed
# by hyphens (that matched the company SK Hynix in news prose) or bare words like
# api_key=, which are normal in this codebase.
PATTERNS = [
    ("openrouter_key", r"\bsk-or-v1-[A-Za-z0-9]{20,}"),
    ("openai_style_key", r"\bsk-[A-Za-z0-9]{32,}\b"),
    ("anthropic_key", r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    ("xai_key", r"\bxai-[A-Za-z0-9]{25,}"),
    ("github_token", r"\b(?:ghp|gho|ghs|ghr)_[A-Za-z0-9]{30,}"),
    ("github_fine_grained", r"\bgithub_pat_[A-Za-z0-9_]{30,}"),
    ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b"),
    ("google_api_key", r"\bAIza[0-9A-Za-z_-]{30,}"),
    ("stripe_key", r"\bsk_live_[A-Za-z0-9]{20,}"),
    ("slack_token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    ("telegram_bot_token", r"\b\d{8,12}:AA[A-Za-z0-9_-]{31,40}\b"),
    ("discord_webhook", r"https://(?:discord|discordapp)\.com/api/webhooks/\d+/[A-Za-z0-9_-]{20,}"),
    ("elevenlabs_key", r"\bxi-api-key\b\s*[:=]\s*[\"']?[A-Za-z0-9]{25,}"),
    ("firecrawl_key", r"\bfc-[A-Za-z0-9]{20,}\b"),
    ("tavily_key", r"\btvly-[A-Za-z0-9_-]{20,}"),
    ("private_key_block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"),
]

# Assignments of a secret-looking value to a secret-sounding name. Only applied
# to NON-content files: in code/config/logs it is a real red flag, while news
# prose legitimately contains things like "api_key: required" and must not
# produce noise. Catches the provider keys with no distinctive prefix (our own
# API_SERVER_KEY, a dumped refresh_token, ...).
ASSIGNMENT = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:api[_-]?key|apikey|api[_-]?server[_-]?key|auth[_-]?token|"
    r"access[_-]?token|refresh[_-]?token|client[_-]?secret|secret[_-]?key|"
    r"password|passwd|private[_-]?key|bot[_-]?token)\b\s*[:=]\s*[\"']?([A-Za-z0-9_\-+/=]{16,})"
)

# filename → BLOCK on sight
BAD_PATH = re.compile(
    r"(?i)(^|/)("
    r"\.env(\..*)?|.*\.env|auth\.json|credentials?.*|.*credential.*|"
    r".*\.pem|.*\.key|.*\.p12|.*\.pfx|.*\.keystore|id_rsa.*|id_ed25519.*|"
    r"\.netrc|.*cookie.*|.*secret.*"
    r")$"
)

# News content: a token in here is reported (WARN), not enforced.
CONTENT = re.compile(
    r"(?i)(^|/)("
    r"index\.html|making-of\.html|edition\.json|rss\.xml|llms\.txt|headlines_history\.json|"
    r"editions/.*|archive/.*|.*\.md|.*\.woff2?|.*\.(jpg|jpeg|png|webp|gif|ogg|mp3|css)"
    r")$"
)


def staged_files(repo):
    out = subprocess.run(
        ["git", "-C", repo, "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True,
    ).stdout
    return [p for p in out.splitlines() if p.strip()]


def staged_content(repo, path):
    proc = subprocess.run(["git", "-C", repo, "show", f":{path}"], capture_output=True)
    if proc.returncode != 0:
        return ""
    if b"\x00" in proc.stdout[:8000]:
        return ""  # binary
    return proc.stdout.decode("utf-8", "replace")


def mask(fragment):
    return fragment[:8] + "…" + f"[{len(fragment)} char]"


def main():
    if len(sys.argv) < 2:
        print("usage: secret_guard.py <deploy_dir>", file=sys.stderr)
        return 2
    repo = sys.argv[1]
    blocked, warned = [], []

    for path in staged_files(repo):
        is_content = bool(CONTENT.search(path))
        if BAD_PATH.search(path):
            blocked.append(f"{path}: nome file da credenziale")
            continue
        text = staged_content(repo, path)
        if not text:
            continue
        for name, pattern in PATTERNS:
            for m in re.finditer(pattern, text):
                line = text.count("\n", 0, m.start()) + 1
                entry = f"{path}:{line} [{name}] {mask(m.group(0))}"
                (warned if is_content else blocked).append(entry)
        if not is_content:
            for m in ASSIGNMENT.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                name = m.group(0)[: m.start(1) - m.start(0)]
                blocked.append(f"{path}:{line} [assignment] {name}{mask(m.group(1))}")

    if blocked:
        print(f"secret_guard: ⛔ {len(blocked)} violazioni — push BLOCCATO")
        for e in blocked:
            print(f"  BLOCK  {e}")
    if warned:
        print(f"secret_guard: ⚠ {len(warned)} sospetti dentro contenuto editoriale (non bloccante)")
        for e in warned:
            print(f"  WARN   {e}")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
