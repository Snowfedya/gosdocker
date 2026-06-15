"""Tests for secret sanitization in generated ZIPs (Bug #6).

Bug: When user supplies config[slug].env = {"POSTGRES_PASSWORD": "MySuperSecret123"},
the literal password ends up in BOTH docker-compose.yml and .env.example inside
the downloaded ZIP. The VKR promises real secrets do not appear in compose.

What we want:
  - .env.example masks secrets: POSTGRES_PASSWORD=<set-me>
  - docker-compose.yml does NOT contain the literal secret value
  - Non-secret env values (TZ, etc.) pass through unchanged

Run: cd backend && python3 -m pytest tests/test_secret_sanitization.py -v
"""
import re
import sys
import zipfile
from io import BytesIO

sys.path.insert(0, '.')

from app.services.generate_service import GenerateService


class _StubComponent:
    """Minimal Component-shaped object used by GenerateService."""
    def __init__(self, slug="nginx", name="Nginx", image="nginx:alpine",
                 registry_url="nginx:alpine", default_env=None,
                 default_ports=None):
        self.slug = slug
        self.name = name
        self.image = image
        self.image_source = "docker.io"
        self.registry_url = registry_url
        self.is_registry = False
        self.registry_number = None
        self.description = "stub"
        self.version = "1.0"
        self.category = "web"
        self.default_ports = default_ports or {"80": 80}
        self.default_volumes = {}
        self.default_env = default_env or {}
        self.variables_schema = {}


def _read_zip(zb: bytes) -> dict[str, str]:
    """Return {filename: content} for every file in the ZIP."""
    with zipfile.ZipFile(BytesIO(zb)) as zf:
        return {n: zf.read(n).decode("utf-8", errors="replace") for n in zf.namelist()}


class TestIsSecretKey:
    """Helper: detect if an env-var name is a secret (PASSWORD/SECRET/TOKEN/...)."""

    def test_password_suffix_is_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("POSTGRES_PASSWORD") is True
        assert is_secret_key("MY_PASSWORD") is True

    def test_password_prefix_is_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("PASSWORD") is True
        assert is_secret_key("PASSWORD_HERE") is True

    def test_secret_keyword_is_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("API_SECRET") is True
        assert is_secret_key("JWT_SECRET") is True
        assert is_secret_key("SECRET_KEY") is True

    def test_token_keyword_is_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("GITHUB_TOKEN") is True
        assert is_secret_key("API_TOKEN") is True

    def test_api_key_is_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("API_KEY") is True
        assert is_secret_key("PRIVATE_KEY") is True

    def test_credentials_is_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("DB_CREDENTIALS") is True

    def test_case_insensitive(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("postgres_password") is True
        assert is_secret_key("Postgres_Password") is True

    def test_tz_is_not_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("TZ") is False

    def test_app_name_is_not_secret(self):
        from app.services.generate_service import is_secret_key
        assert is_secret_key("APP_NAME") is False
        assert is_secret_key("DATABASE_URL") is False
        assert is_secret_key("LANG") is False


class TestEnvExampleSanitization:
    """The .env.example in the ZIP must mask secret values."""

    def test_user_password_is_masked_in_env_example(self):
        svc = GenerateService()
        comp = _StubComponent(slug="nginx")
        cfg = {"nginx": {"ports": {}, "volumes": {},
                          "env": {"POSTGRES_PASSWORD": "MySuperSecret123"}}}
        zb = svc.create_zip([comp], cfg)
        files = _read_zip(zb.getvalue())
        env = files[".env.example"]
        assert "MySuperSecret123" not in env, f"Password leaked into .env.example:\n{env}"
        assert "<set-me>" in env

    def test_non_secret_env_unchanged(self):
        svc = GenerateService()
        comp = _StubComponent(slug="nginx")
        cfg = {"nginx": {"ports": {}, "volumes": {},
                          "env": {"TZ": "Europe/Moscow", "APP_NAME": "myapp"}}}
        zb = svc.create_zip([comp], cfg)
        files = _read_zip(zb.getvalue())
        env = files[".env.example"]
        assert "TZ=Europe/Moscow" in env
        assert "APP_NAME=myapp" in env
        # No masking for non-secrets
        assert "<set-me>" not in env

    def test_token_secret_key_all_masked(self):
        svc = GenerateService()
        comp = _StubComponent(slug="nginx")
        cfg = {"nginx": {"ports": {}, "volumes": {},
                          "env": {
                              "POSTGRES_PASSWORD": "hunter2",
                              "GITHUB_TOKEN": "ghp_***",
                              "JWT_SECRET": "my-jwt",
                              "API_KEY": "sk-***",
                          }}}
        zb = svc.create_zip([comp], cfg)
        env = _read_zip(zb.getvalue())[".env.example"]
        assert "hunter2" not in env
        assert "ghp_***" not in env
        assert "my-jwt" not in env
        assert "sk-***" not in env
        # All four should be masked (4 <set-me> occurrences)
        assert env.count("<set-me>") == 4

    def test_default_changeme_password_is_also_masked(self):
        """Even default seed passwords like 'changeme' get masked in .env.example.

        Why: we don't want to encourage shipping known defaults.
        """
        svc = GenerateService()
        comp = _StubComponent(slug="nginx", default_env={"POSTGRES_PASSWORD": "changeme"})
        cfg = {"nginx": {"ports": {}, "volumes": {}, "env": {}}}
        zb = svc.create_zip([comp], cfg)
        env = _read_zip(zb.getvalue())[".env.example"]
        assert "changeme" not in env
        assert "<set-me>" in env


class TestComposeSanitization:
    """The docker-compose.yml in the ZIP must NOT contain literal secret values."""

    def test_user_password_not_in_compose(self):
        svc = GenerateService()
        comp = _StubComponent(slug="nginx")
        cfg = {"nginx": {"ports": {}, "volumes": {},
                          "env": {"POSTGRES_PASSWORD": "MySuperSecret123"}}}
        zb = svc.create_zip([comp], cfg)
        compose = _read_zip(zb.getvalue())["docker-compose.yml"]
        assert "MySuperSecret123" not in compose, f"Password leaked into compose:\n{compose}"

    def test_user_token_not_in_compose(self):
        svc = GenerateService()
        comp = _StubComponent(slug="nginx")
        cfg = {"nginx": {"ports": {}, "volumes": {},
                          "env": {"GITHUB_TOKEN": "ghp_supersecret"}}}
        zb = svc.create_zip([comp], cfg)
        compose = _read_zip(zb.getvalue())["docker-compose.yml"]
        assert "ghp_supersecret" not in compose

    def test_non_secret_env_still_in_compose(self):
        """Non-secret env (TZ, APP_NAME) must still appear literally in compose —
        otherwise we'd break working configs."""
        svc = GenerateService()
        comp = _StubComponent(slug="nginx")
        cfg = {"nginx": {"ports": {}, "volumes": {},
                          "env": {"TZ": "Europe/Moscow"}}}
        zb = svc.create_zip([comp], cfg)
        compose = _read_zip(zb.getvalue())["docker-compose.yml"]
        # The literal TZ value must appear somewhere (template puts it in env: block)
        assert "Europe/Moscow" in compose

    def test_zip_contains_no_user_supplied_secrets(self):
        """The strongest guarantee: no file in the ZIP contains the secret value."""
        svc = GenerateService()
        comp = _StubComponent(slug="nginx")
        secret = "UserProvidedSecretValue_42"
        cfg = {"nginx": {"ports": {}, "volumes": {},
                          "env": {
                              "POSTGRES_PASSWORD": secret,
                              "API_KEY": secret,
                              "DB_CREDENTIALS": secret,
                          }}}
        zb = svc.create_zip([comp], cfg)
        files = _read_zip(zb.getvalue())
        for name, content in files.items():
            assert secret not in content, (
                f"Secret leaked into {name}:\n--- {name} ---\n{content}"
            )
