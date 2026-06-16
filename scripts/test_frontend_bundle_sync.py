"""
Bug #16 TDD: verify frontend image in container matches host dist (no stale bundle).

Bug: docker compose build --no-cache frontend returned "Built" but did NOT
rebuild layers (BuildKit metadata-only cache). Result: running container
serves stale JS bundle (old hashes) even when host dist/ has new hashes
from code changes (e.g. Bug #12 OWASP fix, Bug #13 dep graph hint).

RED: This test should FAIL when host/frontend/dist hashes != container hashes.
GREEN: After proper rebuild + force-recreate, hashes match.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

HOST_DIST = Path("/opt/gosdocker/frontend/dist/assets")
CONTAINER = "gosdocker-frontend-1"
CONTAINER_ASSETS_DIR = "/usr/share/nginx/html/assets"


def host_hashes() -> dict[str, str]:
    """SHA256 of all built JS/CSS in host dist."""
    if not HOST_DIST.exists():
        return {}
    out = {}
    for f in sorted(HOST_DIST.iterdir()):
        if f.suffix in (".js", ".css"):
            out[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()[:12]
    return out


def container_hashes() -> dict[str, str]:
    """SHA256 of files inside the running frontend container."""
    cmd = [
        "docker", "exec", CONTAINER, "sh", "-c",
        f"cd {CONTAINER_ASSETS_DIR} && "
        f"for f in *.js *.css; do "
        f"  [ -f \"$f\" ] && sha256sum \"$f\"; "
        f"done"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    out = {}
    for line in result.stdout.strip().splitlines():
        m = re.match(r"^([a-f0-9]{64})\s+(\S+)$", line)
        if m:
            out[m.group(2)] = m.group(1)[:12]
    return out


def test_asset_routes_return_javascript_not_html():
    """
    Bug #16 root symptom: nginx serves /assets/*.js as text/html (SPA fallback).
    This means browser downloads HTML, not the JS bundle, and frontend breaks.
    """
    # Get the entry chunk name from host dist
    host = host_hashes()
    entry_js = next((n for n in host if n.startswith("index-") and n.endswith(".js")), None)
    assert entry_js, "no index-*.js found in host dist"

    result = subprocess.run(
        ["curl", "-sS", "-o", "/tmp/bug16_test.js",
         "-w", "%{http_code}|%{content_type}|%{size_download}",
         f"http://127.0.0.1/assets/{entry_js}"],
        capture_output=True, text=True, timeout=15,
    )
    status_ct_size = result.stdout.strip()
    http_code, content_type, size = status_ct_size.split("|")

    assert http_code == "200", f"expected 200, got {http_code}"
    assert content_type.startswith("application/javascript") or content_type == "text/javascript", \
        f"BUG #16: /assets/{entry_js} returned content_type={content_type!r} " \
        f"(should be application/javascript). HTML fallback in nginx means frontend is broken."
    assert int(size) > 1000, f"JS too small ({size} bytes), likely HTML fallback"


def test_container_hashes_match_host_hashes():
    """
    Bug #16: host dist/ has new hashes (after code change),
    but running container has old hashes → user sees stale UI.
    """
    host = host_hashes()
    container = container_hashes()

    assert host, "host dist empty — run `cd frontend && npm run build` first"
    assert container, "container has no JS/CSS — frontend image broken"

    if host != container:
        # Show the diff
        only_host = set(host) - set(container)
        only_container = set(container) - set(host)
        mismatched = [n for n in host if n in container and host[n] != container[n]]

        msg = f"BUG #16: bundle drift detected.\n"
        if only_host:
            msg += f"  Only in HOST (new code not deployed): {sorted(only_host)[:5]}\n"
        if only_container:
            msg += f"  Only in CONTAINER (stale, not in host dist): {sorted(only_container)[:5]}\n"
        if mismatched:
            msg += f"  HASH MISMATCH (same filename, different content): {mismatched[:5]}\n"
        msg += "\nFix: docker rmi -f gosdocker-frontend:latest && "
        msg += "docker build --no-cache --pull -t gosdocker-frontend frontend/"
        assert False, msg


if __name__ == "__main__":
    try:
        test_asset_routes_return_javascript_not_html()
        print("✓ test_asset_routes_return_javascript_not_html PASS")
    except AssertionError as e:
        print(f"✗ test_asset_routes_return_javascript_not_html FAIL: {e}")
        sys.exit(1)

    try:
        test_container_hashes_match_host_hashes()
        print("✓ test_container_hashes_match_host_hashes PASS")
    except AssertionError as e:
        print(f"✗ test_container_hashes_match_host_hashes FAIL: {e}")
        sys.exit(1)

    print("\n✅ All bundle-sync tests passed")
