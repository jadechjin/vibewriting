"""Lightweight DAG runner for the data processing pipeline.

Supports topological sort, cycle detection, and sequential execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CycleDetectedError(Exception):
    """Raised when the DAG contains a cycle."""


@dataclass
class DAGNode:
    """A node in the processing DAG."""

    name: str
    fn: Callable[[dict[str, Any]], dict[str, Any]]
    depends_on: list[str] = field(default_factory=list)


@dataclass
class DAGResult:
    """Result of a DAG run."""

    context: dict[str, Any]
    completed: list[str]
    failed: str | None = None
    error: str | None = None


class DAGRunner:
    """Topological-sort based sequential DAG executor."""

    def __init__(self) -> None:
        self._nodes: dict[str, DAGNode] = {}

    def add_node(self, node: DAGNode) -> None:
        self._nodes[node.name] = node

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm for topological sort with cycle detection."""
        in_degree: dict[str, int] = {name: 0 for name in self._nodes}
        adjacency: dict[str, list[str]] = {name: [] for name in self._nodes}

        for name, node in self._nodes.items():
            for dep in node.depends_on:
                if dep not in self._nodes:
                    raise ValueError(f"Node '{name}' depends on unknown node '{dep}'")
                adjacency[dep].append(name)
                in_degree[name] += 1

        queue = sorted([n for n, d in in_degree.items() if d == 0])
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            for neighbor in sorted(adjacency[current]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
            queue.sort()

        if len(result) != len(self._nodes):
            raise CycleDetectedError(
                "DAG contains a cycle; cannot determine execution order"
            )

        return result

    def run(self, context: dict[str, Any] | None = None) -> DAGResult:
        """Execute all nodes in topological order.

        Each node receives and returns a context dict.
        On failure, execution stops and returns partial results.
        """
        ctx = dict(context or {})
        order = self._topological_sort()
        completed: list[str] = []

        for name in order:
            node = self._nodes[name]
            logger.info("Running node: %s", name)
            try:
                ctx = node.fn(ctx)
                completed.append(name)
                logger.info("Completed node: %s", name)
            except Exception as exc:
                logger.error("Node '%s' failed: %s", name, exc)
                return DAGResult(
                    context=ctx,
                    completed=completed,
                    failed=name,
                    error=str(exc),
                )

        return DAGResult(context=ctx, completed=completed)
