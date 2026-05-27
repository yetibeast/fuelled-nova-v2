"""Per-row reasoning-trail builder.

Captures the step-by-step pricing path so a reader can reconstruct
how a row got its number without re-running the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReasoningTrail:
    lines: list[str] = field(default_factory=list)

    def add(self, label: str, detail: str) -> None:
        self.lines.append(f"{label}: {detail}")

    def render(self) -> str:
        return "\n".join(self.lines)
