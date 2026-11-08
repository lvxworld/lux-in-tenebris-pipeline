#!/usr/bin/env python3
"""Minimal OpenRouter Image API client for Lux image-gen fallback.

Usage: gen.py <out_path> <model> <prompt_file>
Prints JSON: {"path":..., "cost":..., "usage":...}
"""
import base64
import json
import os
import sys
import urllib.request
import urllib.error

ENV = "/home/nttluke/.hermes/profiles/luke/.env"


def get_key() -> str:
    with open(ENV) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no OPENROUTER_API_KEY")


def main() -> int:
    out, model, prompt_file = sys.argv[1], sys.argv[2], sys.argv[3]
    prompt = open(prompt_file).read()
    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "n": 1,
    }
    if "gemini" in model or "seedream" in model:
        payload["resolution"] = "2K"
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/images/generations",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {get_key()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/NousResearch/hermes-agent",
            "X-Title": "Hermes Agent",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=420) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as exc:
        print(json.dumps({"error": exc.read().decode()[:800], "status": exc.code}))
        return 1
    entries = body.get("data") or []
    if not entries:
        print(json.dumps({"error": "no data", "body": json.dumps(body)[:600]}))
        return 1
    entry = entries[0]
    if entry.get("b64_json"):
        raw = base64.b64decode(entry["b64_json"])
        with open(out, "wb") as fh:
            fh.write(raw)
    elif entry.get("url"):
        with urllib.request.urlopen(entry["url"], timeout=180) as r:
            with open(out, "wb") as fh:
                fh.write(r.read())
    else:
        print(json.dumps({"error": "no b64/url", "entry": list(entry)[:10]}))
        return 1
    print(json.dumps({"path": out, "bytes": os.path.getsize(out),
                      "cost": (body.get("usage") or {}).get("cost"),
                      "usage": body.get("usage")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())