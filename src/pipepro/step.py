"""Step base (Chain of Responsibility)."""
from typing import Any

from .context import Context


class StopPipeline(Exception):
    """Interrompe o pipeline sem erro: os dados ficam como estão."""


class Step:
    """Uma etapa do pipeline. Subclasses implementam `process`."""

    name: str | None = None

    def __init__(self, name: str | None = None):
        self.name = name or self.name or type(self).__name__
        self._next: Step | None = None

    # Chain of Responsibility: cada etapa conhece só a próxima.
    def set_next(self, step: "Step | None") -> "Step | None":
        self._next = step
        return step

    def handle(self, ctx: Context) -> None:
        ctx.data = self.process(ctx.data, ctx)

        if self._next is None:
            return
        self._next.handle(ctx)

    def process(self, data: Any, ctx: Context) -> Any:
        raise NotImplementedError
