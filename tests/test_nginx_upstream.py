"""
AC-INF-2: nginx.conf must use runtime DNS resolution for upstreams.

Why: Without `resolver 127.0.0.11` + variable-based proxy_pass,
nginx resolves upstream hostnames ONCE at startup and caches the IP.
When the target container (backend/frontend) is recreated and gets
a new IP, nginx keeps hitting the old IP → 502 Bad Gateway.

Manifested in production on 15.06.2026 after AC-INF-1 fix was
deployed: backend container was recreated, IP changed from
172.18.0.2 → 172.18.0.3, but nginx kept resolving backend to
172.18.0.2 and returned 502. Recovery required `docker restart nginx`.

The fix is to drop the static `upstream {}` blocks and use
`resolver 127.0.0.11` + `set $var http://backend:port; proxy_pass $var;`
which forces re-resolution on every request (or every 10s per
`valid=10s` directive).

We assert on the on-disk config file, not on live container
behavior, to keep the test hermetic and CI-friendly.
"""
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NGINX_CONF = REPO_ROOT / "nginx" / "nginx.conf"


def test_nginx_conf_exists():
    assert NGINX_CONF.exists(), f"nginx.conf not found at {NGINX_CONF}"


def test_nginx_has_docker_resolver():
    """AC-INF-2: nginx must use Docker's embedded DNS resolver."""
    content = NGINX_CONF.read_text()
    assert "resolver 127.0.0.11" in content, (
        "nginx.conf is missing `resolver 127.0.0.11`. Without it, "
        "upstream hostnames are resolved once at startup and cached. "
        "When target container is recreated with a new IP, nginx keeps "
        "hitting the old IP and returns 502 Bad Gateway."
    )


def test_nginx_no_static_upstream_blocks():
    """AC-INF-2: no static `upstream {}` blocks for dynamic Docker services.

    Static `upstream backend { server backend:8000; }` blocks are resolved
    once and cached, which is exactly the bug we are fixing.
    """
    content = NGINX_CONF.read_text()
    # The fix removes the upstream {} blocks entirely; if anyone re-adds
    # them, this test must fail.
    assert "upstream frontend" not in content, (
        "nginx.conf contains `upstream frontend` block. Static upstream "
        "blocks resolve their hostnames once and cache the IP, which "
        "breaks on container recreation. Use `resolver 127.0.0.11` + "
        "set $var http://frontend:80; proxy_pass $var; instead."
    )
    assert "upstream backend" not in content, (
        "nginx.conf contains `upstream backend` block — same problem."
    )


def test_nginx_uses_variable_proxy_pass():
    """AC-INF-2: proxy_pass must reference a variable, not a hostname.

    The whole point of the fix: `proxy_pass http://backend;` → static
    (bad). `proxy_pass $backend_upstream;` after `set $backend_upstream
    http://backend:8000;` → dynamic (good, gets re-resolved).
    """
    content = NGINX_CONF.read_text()
    # Both / and /api locations must use the variable form
    assert "proxy_pass $frontend_upstream" in content
    assert "proxy_pass $backend_upstream" in content
    # And the variable must be set from a hostname (not hardcoded IP)
    assert "set $frontend_upstream http://frontend" in content
    assert "set $backend_upstream http://backend" in content


def test_nginx_syntax_validates_in_container():
    """AC-INF-2: the rewritten config must pass `nginx -t` in the running container."""
    import subprocess
    result = subprocess.run(
        ["docker", "exec", "gosdocker-nginx-1", "nginx", "-t"],
        capture_output=True, text=True, timeout=10
    )
    # `nginx -t` returns exit 0 + "syntax is ok" on success
    assert "syntax is ok" in (result.stdout + result.stderr), (
        f"nginx -t failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
