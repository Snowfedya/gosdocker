"""Dependency resolver — resolves component dependency DAG for the constructor.

Each component declares `requires` and `provides` in its manifest.
This module resolves the dependency graph and auto-adds missing providers.

Graph (from manifests):
  nextcloud requires: [database]       → provided by: postgresql, postgresql-redos
  grafana   requires: [monitoring]     → provided by: prometheus
"""

DEPENDENCY_GRAPH: dict[str, set[str]] = {
    "nextcloud": {"database"},
    "grafana": {"monitoring"},
    "postgresql": set(),
    "postgresql-redos": set(),
    "nginx": set(),
    "angie-pro": set(),
    "prometheus": set(),
}

DEPENDENCY_PROVIDERS: dict[str, set[str]] = {
    "database": {"postgresql", "postgresql-redos"},
    "monitoring": {"prometheus"},
}

# Preferred provider when multiple options exist (first is default)
PREFERRED_PROVIDER: dict[str, str] = {
    "database": "postgresql",
    "monitoring": "prometheus",
}


class DependencyResolver:
    """Resolves component dependencies — auto-adds missing providers."""

    def __init__(
        self,
        graph: dict[str, set[str]] | None = None,
        providers: dict[str, set[str]] | None = None,
        preferred: dict[str, str] | None = None,
    ):
        self.graph = graph or DEPENDENCY_GRAPH
        self.providers = providers or DEPENDENCY_PROVIDERS
        self.preferred = preferred or PREFERRED_PROVIDER

    def resolve(self, selected_slugs: list[str]) -> list[str]:
        """Given selected component slugs, return all required slugs (including deps).

        Resolves transitively: if A needs B and B needs C, all three are included.
        """
        resolved: set[str] = set(selected_slugs)
        changed = True
        while changed:
            changed = False
            for slug in list(resolved):
                needs = self.graph.get(slug, set())
                for dep_type in needs:
                    available = self.providers.get(dep_type, set())
                    if not resolved & available:
                        # Pick preferred provider, fallback to first available
                        provider = self.preferred.get(dep_type)
                        if provider not in available:
                            provider = next(iter(available), None)
                        if provider and provider not in resolved:
                            resolved.add(provider)
                            changed = True

        return list(resolved)

    def resolve_with_metadata(
        self, selected_slugs: list[str]
    ) -> tuple[list[str], list[dict]]:
        """Return (resolved_slugs, auto_added_entries) for UI feedback.

        Each auto_added entry: {slug, reason, provided_by}
        """
        resolved: set[str] = set(selected_slugs)
        auto_added: list[dict] = []
        changed = True
        while changed:
            changed = False
            for slug in list(resolved):
                needs = self.graph.get(slug, set())
                for dep_type in needs:
                    available = self.providers.get(dep_type, set())
                    if not resolved & available:
                        provider = self.preferred.get(dep_type)
                        if provider not in available:
                            provider = next(iter(available), None)
                        if provider and provider not in resolved:
                            resolved.add(provider)
                            auto_added.append({
                                "slug": provider,
                                "reason": f"required by {slug}",
                                "provides": dep_type,
                            })
                            changed = True

        return list(resolved), auto_added
