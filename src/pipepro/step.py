"""Step base (Chain of Responsibility + Template Method)."""
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

    # Template Method: o esqueleto é fixo; before/process/after são os ganchos.
    def handle(self, ctx: Context) -> None:
        ctx.emit("step_started", self.name)
        try:
            self.before(ctx)
            ctx.data = self.process(ctx.data, ctx)
            self.after(ctx)
        except StopPipeline:
            raise
        except Exception as exc:
            ctx.emit("step_failed", self.name, error=exc)
            raise
        ctx.emit("step_finished", self.name)

        if self._next is None:
            return
        self._next.handle(ctx)

    def before(self, ctx: Context) -> None:
        pass

    def process(self, data: Any, ctx: Context) -> Any:
        raise NotImplementedError

    def after(self, ctx: Context) -> None:
        pass
