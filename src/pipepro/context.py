"""Estado que percorre o pipeline, com Memento para rollback."""
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

from .events import Event, Listener


@dataclass(frozen=True)
class Snapshot:
    """Memento: cópia opaca do estado do Context num instante."""

    _data: Any
    _meta: dict


class Context:
    def __init__(self, data: Any, listeners: Iterable[Listener] = ()):
        self.data = data
        self.meta: dict[str, Any] = {}
        self.stopped = False
        self.stop_reason: str | None = None
        self._listeners = list(listeners)

    def emit(self, name: str, step: str, **info: Any) -> None:
        event = Event(name, step, info)
        for listener in self._listeners:
            listener(event)

    def save(self) -> Snapshot:
        return Snapshot(deepcopy(self.data), deepcopy(self.meta))

    def restore(self, snapshot: Snapshot) -> None:
        self.data = deepcopy(snapshot._data)
        self.meta = deepcopy(snapshot._meta)
