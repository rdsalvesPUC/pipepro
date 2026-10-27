"""Estado que percorre o pipeline."""
from typing import Any, Iterable

from .events import Event, Listener


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
