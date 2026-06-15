"""Dependency resolver — resolves component dependency DAG for the constructor.

Each component declares `requires` and `provides` in its manifest.
This module resolves the dependency graph and auto-adds missing providers.

Graph (from manifests):
  nextcloud requires: [database]       → provided by: postgresql, postgresql-redos
  grafana   requires: [monitoring, database] → provided by: prometheus, postgresql

Cycle handling
--------------
`DEPENDENCY_GRAPH` is hand-edited seed-time data, so we validate it
eagerly at construction time. A cycle (A→B→A) is a configuration bug —
the resolver refuses to operate on a cyclic graph and raises
`CyclicDependencyError` with the offending path so the operator can fix
the data. Without this guard, `while changed` in resolve() loops forever
when a capability-provider transitively depends on itself.
"""

import heapq

DEPENDENCY_GRAPH: dict[str, set[str]] = {
    "nextcloud": {"database"},
    "grafana": {"monitoring", "database"},
    "postgresql": set(),
    "postgresql-redos": set(),
    "nginx": set(),
    "angie-pro": set(),
    "prometheus": set(),
    "clickhouse-redos": set(),
    "mariadb-redos": set(),
    "redis": set(),
}

DEPENDENCY_PROVIDERS: dict[str, set[str]] = {
    "database": {"postgresql", "postgresql-redos", "mariadb-redos"},
    "monitoring": {"prometheus"},
    "analytics-database": {"clickhouse-redos"},
    "columnar-db": {"clickhouse-redos"},
    "cache": {"redis"},
    "key-value-store": {"redis"},
}

# Preferred provider when multiple options exist (first is default)
PREFERRED_PROVIDER: dict[str, str] = {
    "database": "postgresql",
    "monitoring": "prometheus",
}


class CyclicDependencyError(ValueError):
    """Raised when DEPENDENCY_GRAPH (or its reachable subgraph) contains a cycle.

    `cycle` is a list of slugs forming the loop, e.g. ['a', 'b', 'a'].
    The first and last elements are equal — a closed walk.
    """

    def __init__(self, cycle: list[str], message: str | None = None):
        self.cycle = list(cycle)
        rendered = " → ".join(self.cycle)
        if message is None:
            message = f"Cyclic dependency detected: {rendered}"
        super().__init__(message)


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """DFS to find any cycle in `graph`. Returns the cycle path or None.

    Three-colour DFS: WHITE (unvisited), GREY (on current path), BLACK (done).
    Back-edge to a GREY node = cycle. We return the slice of the recursion
    stack that forms the loop, with the closing node repeated at the end.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in graph}
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        color[node] = GREY
        path.append(node)
        for nxt in graph.get(node, ()):
            if nxt not in color:
                # Edge to a node outside the graph (treat as a leaf) — skip
                continue
            if color[nxt] == GREY:
                # Back-edge → cycle. Slice from nxt's first occurrence.
                idx = path.index(nxt)
                return path[idx:] + [nxt]
            if color[nxt] == WHITE:
                found = dfs(nxt)
                if found is not None:
                    return found
        path.pop()
        color[node] = BLACK
        return None

    for node in list(graph):
        if color[node] == WHITE:
            found = dfs(node)
            if found is not None:
                return found
    return None


class DependencyResolver:
    """Resolves component dependencies — auto-adds missing providers.

    Validates the dependency graph on construction. Raises
    `CyclicDependencyError` if a cycle is present. This is a fail-fast
    defence against bad seed data: the constructor endpoint then surfaces
    a 500 with a clear message, rather than hanging the worker on an
    infinite `while changed` loop.
    """

    def __init__(
        self,
        graph: dict[str, set[str]] | None = None,
        providers: dict[str, set[str]] | None = None,
        preferred: dict[str, str] | None = None,
    ):
        self.graph = graph or DEPENDENCY_GRAPH
        self.providers = providers or DEPENDENCY_PROVIDERS
        self.preferred = preferred or PREFERRED_PROVIDER
        # Fail-fast cycle check on the whole graph (covers self-loops too)
        cycle = _find_cycle(self.graph)
        if cycle is not None:
            raise CyclicDependencyError(cycle)

    def _check_reachable_subgraph(self, selected: set[str]) -> None:
        """Detect a cycle that only emerges from the user's selection.

        Example: graph {a: {b}, b: {c}, c: {b}} is acyclic in the abstract
        `a` doesn't reach `c` directly), but if the user picks `a` we
        expand to {a, b, c} and b↔c is a cycle. This protects the
        `while changed` loop in resolve() from going infinite.
        """
        # Build a projected graph restricted to reachable nodes
        # and run DFS again.
        projected: dict[str, set[str]] = {}
        # Expand: do a BFS from selected to gather all transitively
        # reachable slugs (capabilities expanded via providers).
        reachable: set[str] = set(selected)
        frontier = list(selected)
        while frontier:
            current = frontier.pop()
            for cap in self.graph.get(current, ()):
                available = self.providers.get(cap, set())
                if not (reachable & available):
                    provider = self.preferred.get(cap)
                    if provider not in available:
                        provider = next(iter(available), None)
                    if provider and provider not in reachable:
                        reachable.add(provider)
                        frontier.append(provider)
            # Also: a slug's "raw" deps (if it has slug→slug edges, treat
            # them as edges to those slugs)
            projected[current] = set(self.graph.get(current, set())) & reachable
        # Project to a slug-only graph: treat each capability edge as an
        # edge to its preferred provider (if one was selected).
        # For cycle detection, simplest correct approach: walk projected
        # graph and look for a cycle.
        cycle = _find_cycle(projected) if projected else None
        if cycle is not None:
            raise CyclicDependencyError(cycle)

    def resolve(self, selected_slugs: list[str]) -> list[str]:
        """Given selected component slugs, return all required slugs (including deps).

        Resolves transitively: if A needs B and B needs C, all three are included.

        **Output order is stable with respect to input order** for slugs
        that were already in `selected_slugs`. Auto-added providers are
        appended after them, in the order they were discovered. This
        matters for `sort_by_dependencies` and for callers that want
        deterministic output.
        """
        # Defensive: if the user's selection alone creates a cycle (e.g.
        # they pick a component that transitively loops), fail fast.
        self._check_reachable_subgraph(set(selected_slugs))

        # Deduplicate input while preserving order, then start resolving.
        resolved: list[str] = []
        seen: set[str] = set()
        for s in selected_slugs:
            if s not in seen:
                resolved.append(s)
                seen.add(s)
        resolved_set: set[str] = seen
        changed = True
        # Hard cap to detect an unexpected infinite loop in case our
        # pre-checks miss something exotic (e.g. capability-level cycles).
        # With a 10-node graph and no cycles, this loop runs ≤ N times.
        max_iter = 1000
        iters = 0
        while changed:
            changed = False
            iters += 1
            if iters > max_iter:
                raise CyclicDependencyError(
                    resolved,
                    f"resolve() exceeded {max_iter} iterations — possible undeclared cycle",
                )
            for slug in list(resolved):
                needs = self.graph.get(slug, set())
                for dep_type in needs:
                    available = self.providers.get(dep_type, set())
                    if not resolved_set & available:
                        # Pick preferred provider, fallback to first available
                        provider = self.preferred.get(dep_type)
                        if provider not in available:
                            provider = next(iter(available), None)
                        if provider and provider not in resolved_set:
                            resolved.append(provider)
                            resolved_set.add(provider)
                            changed = True

        return resolved

    def sort_by_dependencies(self, selected_slugs: list[str]) -> list[str]:
        """Topological sort: return slugs in dep-first order (Kahn's algorithm).

        Re-uses `resolve()` semantics: missing providers are auto-added.
        The output is a list where, if A requires B (transitively, via
        capability), B appears before A. For independent nodes the input
        order is preserved (stable).

        Raises `CyclicDependencyError` if the resulting graph is cyclic
        (Kahn's algorithm detects this when not all nodes are emitted).
        """
        # First, get the full closure (resolve auto-adds providers).
        # If resolve() raises CyclicDependencyError, propagate it.
        full = self.resolve(selected_slugs)
        return self._topological_sort(full)

    def _topological_sort(self, slugs: list[str]) -> list[str]:
        """Kahn's algorithm: emit slugs in dep-first order (stable).

        Build `out_edges[slug] = [provider1, provider2, ...]` from the
        capability→provider mapping. In the resulting graph, an edge
        u → v means "u depends on v" (u needs v as a provider). We
        want v emitted first, so we process the REVERSE graph: nodes
        with out_edges == [] (leaves in the depends-on graph, i.e.,
        pure providers) come out first. Ties are broken by input
        position for stable output.

        Raises `CyclicDependencyError` if any nodes are not emitted
        (which means there's a cycle that resolve() didn't catch).
        """
        slug_set = set(slugs)
        position = {slug: i for i, slug in enumerate(slugs)}

        # Build depends-on edges (out_edges[slug] = list of providers it requires)
        out_edges: dict[str, list[str]] = {s: [] for s in slugs}
        for slug in slugs:
            for cap in self.graph.get(slug, ()):
                available = self.providers.get(cap, set()) & slug_set
                if not available:
                    # Configuration bug: capability has no provider in the
                    # selected set. resolve() should have added one.
                    raise CyclicDependencyError(
                        [slug, cap],
                        f"Slug '{slug}' requires capability '{cap}' "
                        f"but no provider is in the selected set",
                    )
                provider = self.preferred.get(cap)
                if provider not in available:
                    # Stable fallback: lowest input position first
                    provider = min(available, key=lambda s: position[s])
                if provider != slug:  # skip self-loops
                    out_edges[slug].append(provider)

        # Inverted view: dependents[v] = slugs that need v as a provider
        dependents: dict[str, list[str]] = {s: [] for s in slugs}
        for u, deps in out_edges.items():
            for v in deps:
                dependents[v].append(u)

        # Kahn's on the INVERTED graph: start with nodes that have no
        # out_edges in the original (= no deps in the inverted sense).
        # Those are the providers; emit them first.
        remaining = {s: len(out_edges[s]) for s in slugs}
        heap: list[tuple[int, str]] = [
            (position[s], s) for s in slugs if remaining[s] == 0
        ]
        heapq.heapify(heap)

        result: list[str] = []
        emitted: set[str] = set()
        while heap:
            _, node = heapq.heappop(heap)
            if node in emitted:
                continue
            result.append(node)
            emitted.add(node)
            for u in dependents[node]:
                remaining[u] -= 1
                if remaining[u] == 0 and u not in emitted:
                    heapq.heappush(heap, (position[u], u))

        if len(result) != len(slugs):
            missing = [s for s in slugs if s not in emitted]
            raise CyclicDependencyError(
                missing + missing[:1],
                f"sort_by_dependencies: cycle detected, {len(missing)} nodes not emitted",
            )
        return result

    def resolve_with_metadata(
        self, selected_slugs: list[str]
    ) -> tuple[list[str], list[dict]]:
        """Return (resolved_slugs, auto_added_entries) for UI feedback.

        Each auto_added entry: {slug, reason, provided_by}
        """
        self._check_reachable_subgraph(set(selected_slugs))

        # Deduplicate input while preserving order
        resolved: list[str] = []
        resolved_set: set[str] = set()
        for s in selected_slugs:
            if s not in resolved_set:
                resolved.append(s)
                resolved_set.add(s)
        auto_added: list[dict] = []
        changed = True
        max_iter = 1000
        iters = 0
        while changed:
            changed = False
            iters += 1
            if iters > max_iter:
                raise CyclicDependencyError(
                    resolved,
                    f"resolve_with_metadata() exceeded {max_iter} iterations — possible undeclared cycle",
                )
            for slug in list(resolved):
                needs = self.graph.get(slug, set())
                for dep_type in needs:
                    available = self.providers.get(dep_type, set())
                    if not resolved_set & available:
                        provider = self.preferred.get(dep_type)
                        if provider not in available:
                            provider = next(iter(available), None)
                        if provider and provider not in resolved_set:
                            resolved.append(provider)
                            resolved_set.add(provider)
                            auto_added.append({
                                "slug": provider,
                                "reason": f"required by {slug}",
                                "provides": dep_type,
                            })
                            changed = True

        return resolved, auto_added
