"""Tests for sort_by_dependencies — Kahn's algorithm topological sort.

Why this exists:
  The VKR (Section 3.5) refers to `ordered = sort_by_dependencies(components)`
  — but the actual code only had a capability resolver, not a real
  topological sort. This module implements the contract:

    sort_by_dependencies(components) → list of slugs in dep-first order

  where 'deps first' means: if A requires B, B appears before A in the
  output. This matters for docker-compose up: a `depends_on:` clause is
  best-effort, but the rendered stack ZIP is more readable when
  dependencies precede dependents.

Algorithm: Kahn's BFS
  1. Compute in-degree for each node (deps they require).
  2. Start with nodes that have in-degree 0 (no unmet deps).
  3. Pop a node from the queue, append to result, decrement in-degree of
     nodes that "this node satisfies".
  4. If the result has fewer nodes than input → cycle → raise.

Note: the underlying `graph` here is slug→{capability}, and capabilities
are resolved to providers via the same `providers` map. For sort purposes
we treat each selected slug as a node with deps = its capabilities; a
capability is "satisfied" if any provider in `providers[cap]` is in the
selected set (or if the resolver auto-adds it, we add it to the result).
"""
import pytest

from app.services.dependency_resolver import (
    DependencyResolver,
    CyclicDependencyError,
)


# ── simple two-node dependency ──────────────────────────────


class TestBasicOrder:
    def test_two_components_dependency_first(self):
        """If A requires B (capability), B must come before A in the result."""
        # nextcloud requires "database" → provided by postgresql
        graph = {"nextcloud": {"database"}, "postgresql": set()}
        providers = {"database": {"postgresql"}}
        r = DependencyResolver(graph=graph, providers=providers, preferred={})
        ordered = r.sort_by_dependencies(["nextcloud", "postgresql"])
        # postgresql must come before nextcloud
        assert ordered.index("postgresql") < ordered.index("nextcloud")

    def test_independent_components_preserved(self):
        """Components with no inter-deps: any order is fine, but all must be present."""
        graph = {"nginx": set(), "redis": set()}
        r = DependencyResolver(graph=graph, providers={}, preferred={})
        ordered = r.sort_by_dependencies(["nginx", "redis"])
        assert set(ordered) == {"nginx", "redis"}
        assert len(ordered) == 2

    def test_single_component(self):
        graph = {"nginx": set()}
        r = DependencyResolver(graph=graph, providers={}, preferred={})
        assert r.sort_by_dependencies(["nginx"]) == ["nginx"]


# ── chain of three ──────────────────────────────────────────


class TestChain:
    def test_three_node_chain(self):
        """A→B→C: C must come first, A last."""
        # a requires "b-cap" (provided by b); b requires "c-cap" (provided by c)
        graph = {"a": {"b-cap"}, "b": {"c-cap"}, "c": set()}
        providers = {"b-cap": {"b"}, "c-cap": {"c"}}
        r = DependencyResolver(graph=graph, providers=providers, preferred={})
        ordered = r.sort_by_dependencies(["a"])
        # Expected: c, b, a
        assert ordered == ["c", "b", "a"]

    def test_diamond_dependency(self):
        """A requires B,C; B and C both require D. D first, A last."""
        # a → {b-cap, c-cap}; b → {d-cap}; c → {d-cap}; d → {}
        graph = {"a": {"b-cap", "c-cap"}, "b": {"d-cap"}, "c": {"d-cap"}, "d": set()}
        providers = {"b-cap": {"b"}, "c-cap": {"c"}, "d-cap": {"d"}}
        r = DependencyResolver(graph=graph, providers=providers, preferred={})
        ordered = r.sort_by_dependencies(["a"])
        assert ordered[0] == "d", f"D must be first: {ordered}"
        assert ordered[-1] == "a", f"A must be last: {ordered}"
        # B and C can be in any order between
        assert set(ordered[1:-1]) == {"b", "c"}


# ── cycle via sort (should raise) ───────────────────────────


class TestSortCycle:
    def test_cycle_raises_cyclic_dependency_error(self):
        """sort_by_dependencies on a cyclic graph must raise."""
        graph = {"a": {"b"}, "b": {"a"}}
        providers = {"b": {"b"}, "a": {"a"}}
        # The whole-graph cycle check fires on construction; sort_by_dependencies
        # propagates the error. Use the constructor pattern.
        from app.services.dependency_resolver import (
            DependencyResolver,
            CyclicDependencyError,
        )
        with pytest.raises(CyclicDependencyError):
            DependencyResolver(graph=graph, providers=providers, preferred={})


# ── stability and determinism ────────────────────────────────


class TestStability:
    def test_input_order_preserved_for_independent_nodes(self):
        """For nodes with no deps, input order is preserved (stable sort)."""
        graph = {"x": set(), "y": set(), "z": set()}
        r = DependencyResolver(graph=graph, providers={}, preferred={})
        # Input order: x, y, z — output must also be x, y, z
        ordered = r.sort_by_dependencies(["x", "y", "z"])
        assert ordered == ["x", "y", "z"]

    def test_input_order_in_reverse(self):
        """Reverse input: stable → reverse output for independent nodes."""
        graph = {"x": set(), "y": set(), "z": set()}
        r = DependencyResolver(graph=graph, providers={}, preferred={})
        ordered = r.sort_by_dependencies(["z", "y", "x"])
        assert ordered == ["z", "y", "x"]


# ── production graph (the real one) ─────────────────────────


class TestProductionSort:
    def test_default_graph_sorts_real_components(self):
        """Real DEPENDENCY_GRAPH: nextcloud pulls in postgresql, grafana
        pulls in postgresql + prometheus. Order must respect deps."""
        r = DependencyResolver()  # default
        ordered = r.sort_by_dependencies(["nextcloud", "grafana", "nginx", "prometheus", "postgresql"])
        # All selected + auto-added providers must appear
        assert set(ordered) >= {"nextcloud", "grafana", "nginx", "prometheus", "postgresql"}
        # postgresql must come before nextcloud and grafana
        idx_pg = ordered.index("postgresql")
        assert ordered.index("nextcloud") > idx_pg
        assert ordered.index("grafana") > idx_pg
        # prometheus must come before grafana
        assert ordered.index("prometheus") < ordered.index("grafana")
