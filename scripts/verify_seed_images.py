#!/usr/bin/env python3
"""Verify that every registry_url in seed.py actually exists in the registry.

Bug #2 reproduction: `clickhouse-redos` and `mariadb-redos` reference
URLs in registry.red-soft.ru that don't exist (verified by /v2/_catalog,
2026-06-15: 118 repos, no clickhouse, no mariadb).

Usage:
    cd /opt/gosdocker/backend
    python3 ../scripts/verify_seed_images.py
    # or with a specific file:
    python3 ../scripts/verify_seed_images.py --file ../backend/seed.py

Exit code:
    0 — every image either pulled OK or already cached locally
    1 — at least one image is missing (with details printed)

This is a HUMAN-VERIFIED gate, not a runtime check. Run before re-seeding.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


# Match dict-style entries in seed.py. Catches the pattern:
#   "registry_url": "registry.red-soft.ru/ubi8/postgresql-17",
# Group 1 is the URL.
_URL_RE = re.compile(r'"registry_url"\s*:\s*"([^"]+)"')


def extract_urls(seed_path: Path) -> list[str]:
    """Pull every registry_url value out of seed.py."""
    text = seed_path.read_text(encoding="utf-8")
    urls = _URL_RE.findall(text)
    # Dedupe, preserve order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def verify_one(url: str, timeout: int = 180) -> tuple[bool, str]:
    """Try to `docker pull` the URL. Returns (ok, message)."""
    try:
        result = subprocess.run(
            ["docker", "pull", url],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"TIMEOUT after {timeout}s"
    except FileNotFoundError:
        return False, "docker CLI not found in PATH"

    out = (result.stdout + result.stderr).strip()
    last_line = out.splitlines()[-1] if out else "<no output>"
    if result.returncode == 0:
        return True, last_line
    return False, last_line


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).parent.parent / "backend" / "seed.py",
        help="Path to seed.py",
    )
    args = parser.parse_args()

    seed_path: Path = args.file.resolve()
    if not seed_path.exists():
        print(f"ERROR: seed file not found: {seed_path}", file=sys.stderr)
        return 2

    urls = extract_urls(seed_path)
    print(f"Found {len(urls)} registry_url entries in {seed_path.name}")
    print("=" * 70)

    failures: list[tuple[str, str]] = []
    for url in urls:
        print(f"  → {url} ... ", end="", flush=True)
        ok, msg = verify_one(url)
        if ok:
            print(f"OK  ({msg[:60]})")
        else:
            print(f"FAIL  ({msg[:80]})")
            failures.append((url, msg))

    print("=" * 70)
    if failures:
        print(f"\n❌ {len(failures)}/{len(urls)} images FAILED verification:")
        for url, msg in failures:
            print(f"  • {url}")
            print(f"      {msg[:120]}")
        return 1
    print(f"\n✅ All {len(urls)} images verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
