"""Estado que percorre o pipeline."""
from typing import Any


class Context:
    def __init__(self, data: Any):
        self.data = data
        self.meta: dict[str, Any] = {}
        self.stopped = False
        self.stop_reason: str | None = None
