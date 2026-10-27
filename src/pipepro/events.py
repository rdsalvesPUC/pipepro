"""Observer: eventos emitidos durante a execução e um listener de auditoria pronto."""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Event:
    name: str  # step_started, step_finished, step_failed, step_undone, rolled_back, pipeline_stopped
    step: str
    info: dict[str, Any] = field(default_factory=dict)


# Qualquer callable que receba um Event é um listener.
Listener = Callable[[Event], None]


class AuditTrail:
    """Listener que guarda todos os eventos, para auditar uma execução."""

    def __init__(self):
        self.events: list[Event] = []

    def __call__(self, event: Event) -> None:
        self.events.append(event)

    def trail(self) -> list[tuple[str, str]]:
        return [(e.name, e.step) for e in self.events]
