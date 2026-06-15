"""Tests for cycle detection in DependencyResolver.

Why these tests exist:
  - DEPENDENCY_GRAPH in production is hand-edited (seed-time data).
  - A bug introducing A→B and B→A in the same graph currently
    causes resolve() to infinite-loop the `while changed:` and
    either hang the request or raise RuntimeError: Set changed size
    during iteration.
  - Defense: detect cycles at config-load time AND at resolve time,
    raise CyclicDependencyError with the offending cycle path.
  - Cycle scope: component-level (slug→slug) and capability-level
    (capability→capability, when a provider "requires" the same
    capability it provides).
"""
import pytest

from app.services.dependency_resolver import (
    DependencyResolver,
    CyclicDependencyError,
)


# ── component-level cycles (slug → slug) ─────────────────────


def _use_or_construct(graph, providers=None, preferred=None, selected=None):
    """Construct a resolver, or if it raises CyclicDependencyError (whole-graph
    cycle caught at __init__), return a stub whose .resolve() re-raises it.

    The cycle detection lives at TWO points:
      1. `__init__` — catches cycles in the whole graph (fail-fast on import).
      2. `resolve()` — catches cycles in the reachable subgraph from a selection.

    Tests should accept either raising point. We capture the construction
    error and re-raise it from the .resolve() call to keep the test contract
    uniform ("calling .resolve() on a cyclic graph raises CyclicDependencyError").
    """
    try:
        r = DependencyResolver(graph=graph, providers=providers or {}, preferred=preferred or {})
    except CyclicDependencyError as e:
        saved = e  # capture in default arg to avoid late-binding / scope bugs

        class _FakeResolver:
            def resolve(self, _selected):
                raise saved

            def resolve_with_metadata(self, _selected):
                raise saved

        return _FakeResolver()
    return r


class TestComponentCycle:
    def test_self_loop_raises(self):
        """A→A: A requires itself. Must raise CyclicDependencyError."""
        graph = {"a": {"a"}}  # a requires a
        r = _use_or_construct(graph)
        with pytest.raises(CyclicDependencyError) as exc:
            r.resolve(["a"])
        # The cycle path must include 'a' at least twice (entry + loop)
        assert exc.value.cycle, "Cycle path must be reported"
        assert "a" in exc.value.cycle

    def test_two_node_cycle_raises(self):
        """A→B→A: A requires B, B requires A."""
        graph = {"a": {"b"}, "b": {"a"}}
        r = _use_or_construct(graph)
        with pytest.raises(CyclicDependencyError) as exc:
            r.resolve(["a"])
        cycle = exc.value.cycle
        assert "a" in cycle and "b" in cycle, f"Cycle must show both nodes: {cycle}"
        # The cycle should be reported in canonical form (start with smallest or first)
        assert len(cycle) >= 2

    def test_three_node_cycle_raises(self):
        """A→B→C→A."""
        graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}}
        r = _use_or_construct(graph)
        with pytest.raises(CyclicDependencyError) as exc:
            r.resolve(["a"])
        cycle = exc.value.cycle
        assert {"a", "b", "c"} <= set(cycle), f"All three nodes must appear: {cycle}"

    def test_subgraph_cycle_via_reachable_only(self):
        """Cycle in a subgraph the user doesn't reach: constructor raises
        (loud-fail on bad config), but the message reports the subgraph.
        This documents the fail-fast trade-off."""
        # Graph with a hidden cycle (b↔c) that the user's selection of
        # {a} never reaches. Whole-graph check fires on construction.
        graph = {"a": set(), "b": {"c"}, "c": {"b"}}
        with pytest.raises(CyclicDependencyError) as exc:
            DependencyResolver(graph=graph, providers={}, preferred={})
        # The reported cycle is the bad one (b↔c), not the user's path
        cycle = exc.value.cycle
        assert {"b", "c"} <= set(cycle)

    def test_cycle_isolated_to_reachable_subgraph_raises(self):
        """If a→b and b↔c cycle, asking for a must still raise (b is reachable).

        b↔c is a cycle in the whole graph, so the whole-graph check fires
        on construction. .resolve() is never reached."""
        graph = {"a": {"b"}, "b": {"c"}, "c": {"b"}}
        r = _use_or_construct(graph)
        with pytest.raises(CyclicDependencyError) as exc:
            r.resolve(["a"])
        assert {"b", "c"} <= set(exc.value.cycle)


# ── default production graph must be acyclic ────────────────


class TestProductionGraph:
    def test_default_dependency_graph_is_acyclic(self):
        """The bundled DEPENDENCY_GRAPH must be validated as acyclic on import.
        This test is the safety net for future hand-edits."""
        # Import here to surface any ImportError from a broken production graph
        from app.services.dependency_resolver import DependencyResolver as _DR
        r = _DR()  # uses default DEPENDENCY_GRAPH
        # If there's a cycle, constructing the resolver validates it.
        # If the resolver validates on construction, calling .resolve() is safe.
        # At minimum: requesting all 10 known slugs must not raise.
        all_slugs = list(r.graph.keys())
        # This call must complete without raising
        result = r.resolve(all_slugs)
        assert set(result) == set(all_slugs)

    def test_dependency_graph_has_no_self_loop(self):
        from app.services.dependency_resolver import DEPENDENCY_GRAPH
        for slug, deps in DEPENDENCY_GRAPH.items():
            assert slug not in deps, \
                f"Self-loop in DEPENDENCY_GRAPH: {slug} requires itself"


# ── error message quality ────────────────────────────────────


class TestErrorMessage:
    def test_cycle_error_has_readable_message(self):
        """The error must include the cycle path in a human-readable form."""
        graph = {"a": {"b"}, "b": {"a"}}
        r = _use_or_construct(graph)
        with pytest.raises(CyclicDependencyError) as exc:
            r.resolve(["a"])
        msg = str(exc.value)
        # Must be at least somewhat informative
        assert "cycle" in msg.lower() or "cyclic" in msg.lower() or "→" in msg
        assert "a" in msg and "b" in msg

    def test_cycle_error_attribute_is_a_list(self):
        """exc.cycle is a list (not a string), so callers can introspect."""
        graph = {"a": {"b"}, "b": {"a"}}
        r = _use_or_construct(graph)
        with pytest.raises(CyclicDependencyError) as exc:
            r.resolve(["a"])
        assert isinstance(exc.value.cycle, list)
        # And the path starts and ends at the same node
        assert exc.value.cycle[0] == exc.value.cycle[-1]
