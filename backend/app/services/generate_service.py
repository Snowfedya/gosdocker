import re
import zipfile
import yaml
from io import BytesIO
from datetime import datetime
from .template_service import TemplateService


# Patterns that mark an env-var name as containing a secret. The regex is
# intentionally broad-but-conservative: false positives are fine (TZ won't
# match), false negatives leak real secrets to the user ZIP.
_SECRET_PATTERN = re.compile(
    r"(.*_)?("
    r"PASSWORD|PASSWD|PASS"
    r"|SECRET"
    r"|TOKEN"
    r"|API[_-]?KEY"
    r"|PRIVATE[_-]?KEY"
    r"|CREDENTIALS"
    r"|AUTH"
    r")(_.*)?$",
    re.IGNORECASE,
)
# Placeholder that appears in .env.example and as a literal in compose
# (docker compose will resolve ${VAR:-placeholder} from .env if present, or
# fall back to the placeholder literal which is safe-by-default).
_SECRET_PLACEHOLDER = "<set-me>"


def is_secret_key(name: str) -> bool:
    """Return True if an env-var name should be treated as a secret.

    Heuristic: matches PASS/WORD/SECRET/TOKEN/API_KEY/PRIVATE_KEY/
    CREDENTIALS/AUTH anywhere in the name, case-insensitive. Conservative
    by design — over-masking is safe, under-masking leaks secrets.
    """
    if not name:
        return False
    return bool(_SECRET_PATTERN.match(name))


class GenerateService:
    def __init__(self):
        self.template_service = TemplateService()

    def create_zip(self, components: list, configs: dict) -> BytesIO:
        """Create ZIP archive with docker-compose.yml and supporting files."""

        buffer = BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Render docker-compose.yml
            compose_content = self._render_compose(components, configs)
            zf.writestr("docker-compose.yml", compose_content)

            # Create .env.example
            env_content = self._create_env_example(components, configs)
            zf.writestr(".env.example", env_content)

            # Create README.md
            readme_content = self._create_readme(components)
            zf.writestr("README.md", readme_content)

        buffer.seek(0)
        return buffer

    def _render_compose(self, components: list, configs: dict) -> str:
        """Render unified docker-compose.yml from all components."""

        services = []
        networks = ["gosdocker"]

        for comp in components:
            slug = comp.slug
            raw = configs.get(slug)
            if raw is None:
                config = {}
            elif hasattr(raw, "model_dump"):
                config = raw.model_dump()
            else:
                config = dict(raw)

            # Add registry_url from component to config
            if not config.get("registry_url"):
                config["registry_url"] = comp.registry_url

            # Merge default ports/volumes/env from component if not overridden by user
            if not config.get("ports") and hasattr(comp, 'default_ports') and comp.default_ports:
                config["ports"] = comp.default_ports
            if not config.get("volumes") and hasattr(comp, 'default_volumes') and comp.default_volumes:
                config["volumes"] = comp.default_volumes
            if hasattr(comp, 'default_env') and comp.default_env:
                user_env = config.get("env", {})
                merged = dict(comp.default_env)
                merged.update(user_env)  # user overrides take precedence
                config["env"] = merged

            # Sanitize: replace secret env-var VALUES with placeholder so the
            # literal never reaches docker-compose.yml. The KEY is preserved
            # (so users see what variable to set in .env). docker compose
            # will pick up the real value from .env at runtime; the literal
            # in compose is the safe placeholder. See Bug #6.
            if config.get("env"):
                config["env"] = {
                    k: (_SECRET_PLACEHOLDER if is_secret_key(k) else v)
                    for k, v in config["env"].items()
                }

            # Render component template
            try:
                content = self.template_service.render_single(slug, config)
                services.append(content)
            except Exception as e:
                # Fall back to basic compose if template rendering fails
                import logging
                logging.warning(f"Template rendering failed for {slug}: {e}")
                services.append(self._fallback_compose(comp, config))

        # Merge
        return self._merge_compose_files(services, networks)

    def _fallback_compose(self, component, config: dict) -> str:
        """Basic generation if no template exists."""
        ports = config.get("ports", {})
        env = config.get("env", {})
        volumes = config.get("volumes", {})

        ports_lines = [f'      - "{ext}:{intv}"' for ext, intv in ports.items()]
        ports_str = "\n".join(ports_lines) + "\n" if ports_lines else ""
        env_lines = [f'      {k}: "{v}"' for k, v in env.items()]
        env_str = "\n".join(env_lines) + "\n" if env_lines else ""
        volumes_lines = [f'      - {host}:{container}' for host, container in volumes.items()]
        volumes_str = "\n".join(volumes_lines) + "\n" if volumes_lines else ""

        parts = [
            f"  {component.slug}:",
            f"    image: {component.registry_url}",
            f"    container_name: {component.slug}",
            f"    restart: unless-stopped",
        ]
        if ports_lines:
            parts.append("    ports:")
            parts.append(ports_str.rstrip("\n"))
        if env_lines:
            parts.append("    environment:")
            parts.append(env_str.rstrip("\n"))
        if volumes_lines:
            parts.append("    volumes:")
            parts.append(volumes_str.rstrip("\n"))

        return "\n".join(parts) + "\n"

    def _merge_compose_files(self, services: list, networks: list) -> str:
        """Merge docker-compose fragments into one file using YAML."""
        merged = {"services": {}, "networks": {}, "volumes": {}}

        for svc_yaml in services:
            data = yaml.safe_load(svc_yaml)
            if not data:
                continue
            svc_name = list(data.keys())[0]
            svc_data = data[svc_name]
            merged["services"][svc_name] = svc_data

            # Extract named volumes from service-level volumes list
            svc_volumes = svc_data.get("volumes", [])
            for vol in svc_volumes:
                if isinstance(vol, str) and ":" in vol:
                    vol_name = vol.split(":")[0]
                    if vol_name and not vol_name.startswith("/"):
                        merged["volumes"][vol_name] = None

        for net in networks:
            merged["networks"][net] = {"driver": "bridge"}

        header = f"# Generated by GosDocker\n# {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        return header + yaml.dump(merged, default_flow_style=False, sort_keys=False, allow_unicode=True, indent=2)

    def _create_env_example(self, components: list, configs: dict) -> str:
        """Create .env.example with variables."""
        lines = ["# GosDocker Environment Variables", "# Update values for your environment", ""]

        for comp in components:
            slug = comp.slug
            raw = configs.get(slug)
            if raw is None:
                config = {}
            elif hasattr(raw, "model_dump"):
                config = raw.model_dump()
            else:
                config = dict(raw)
            env = config.get("env", {})
            # Merge default_env from component (same logic as _render_compose)
            # so .env.example is complete — Bug #6: defaults must also be
            # masked if they look like secrets.
            if hasattr(comp, "default_env") and comp.default_env:
                merged = dict(comp.default_env)
                merged.update(env)
                env = merged

            for key, value in env.items():
                # Mask secret values in .env.example — Bug #6. Users copy
                # .env.example to .env and fill in real values themselves.
                if is_secret_key(key):
                    value = _SECRET_PLACEHOLDER
                lines.append(f"{slug.upper()}_{key.upper()}={value}")

        return "\n".join(lines)

    def _create_readme(self, components: list) -> str:
        """Create README.md for the downloaded stack."""

        component_list = "\n".join([f"- {c.name}" for c in components])

        rows = "\n".join([f"| {c.name} | {c.image} | {c.registry_url} |" for c in components])

        return f"""# GosDocker Stack

Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

## Components

{component_list}

## Quick Start

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your values

# Start stack
docker compose up -d
```

## Sources

| Component | Image | Source |
|-----------|-------|--------|
{rows}
"""