"""Security profiles — three compose presets that control container security settings.

Each profile defines Docker compose fields injected into the generated compose.
Profiles stack: hardened extends standard, standard extends basic.
"""

from typing import Any


# Base compose additions per profile
PROFILES: dict[str, dict[str, Any]] = {
    "basic": {
        "label": "Базовый",
        "description": "Минимальные настройки безопасности, максимальная совместимость",
        "compose_additions": {
            "restart": "unless-stopped",
        },
        "service_overrides": {
            "read_only": False,
        },
    },
    "standard": {
        "label": "Стандартный",
        "description": "Рекомендуемый уровень для типовых госучреждений",
        "compose_additions": {
            "restart": "unless-stopped",
        },
        "service_overrides": {
            "read_only": True,
            "cap_drop": ["ALL"],
            "cap_add": ["NET_BIND_SERVICE", "CHOWN"],
            "healthcheck": {
                "test": ["CMD-SHELL", "exit 0"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "30s",
            },
        },
    },
    "hardened": {
        "label": "Усиленный",
        "description": "Максимальный уровень для защищённых контуров и режимных объектов",
        "compose_additions": {
            "restart": "unless-stopped",
        },
        "service_overrides": {
            "read_only": True,
            "cap_drop": ["ALL"],
            "cap_add": ["NET_BIND_SERVICE"],
            "security_opt": ["seccomp:default", "no-new-privileges:true"],
            "healthcheck": {
                "test": ["CMD-SHELL", "exit 0"],
                "interval": "30s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "30s",
            },
        },
    },
}


def apply_profile(compose_yaml: dict, profile: str = "standard") -> dict:
    """Apply security profile overrides to a docker-compose YAML dict.

    Args:
        compose_yaml: Parsed docker-compose YAML as dict (services section)
        profile: One of 'basic', 'standard', 'hardened'

    Returns:
        Modified compose dict with profile overrides applied per service
    """
    profile_config = PROFILES.get(profile)
    if not profile_config:
        return compose_yaml

    overrides = profile_config["service_overrides"]

    services = compose_yaml.get("services", {})
    for svc_name in list(services.keys()):
        for key, value in overrides.items():
            # Don't override build: — it's essential
            if key == "build":
                continue
            services[svc_name][key] = value

    compose_yaml["services"] = services
    return compose_yaml


def get_profile_info(profile: str) -> dict[str, Any] | None:
    """Return profile metadata for API responses."""
    p = PROFILES.get(profile)
    if p:
        return {"slug": profile, "label": p["label"], "description": p["description"]}
    return None


def list_profiles() -> list[dict[str, Any]]:
    """Return all available profiles for frontend selector."""
    return [
        {"slug": slug, "label": p["label"], "description": p["description"]}
        for slug, p in PROFILES.items()
    ]
