"""Step base (Chain of Responsibility + Template Method + Command) e decorators."""
from time import perf_counter
from typing import Any

from .context import Context


class StopPipeline(Exception):
    """Interrompe o pipeline sem erro: nada é desfeito, os dados ficam como estão."""


class Step:
    """Uma etapa do pipeline. Subclasses implementam `process` e, se tiverem
    efeitos colaterais, `undo`."""

    name: str | None = None

    def __init__(self, name: str | None = None):
        self.name = name or self.name or type(self).__name__
        self._next: Step | None = None

    # Chain of Responsibility: cada etapa conhece só a próxima.
    def set_next(self, step: "Step | None") -> "Step | None":
        self._next = step
        return step

    # Template Method: o esqueleto é fixo; before/process/after/undo são os ganchos.
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
        try:
            self._next.handle(ctx)
        except StopPipeline:
            raise
        except Exception:
            # Command: na volta da cadeia, cada etapa concluída desfaz o próprio efeito.
            self.undo(ctx)
            ctx.emit("step_undone", self.name)
            raise

    def before(self, ctx: Context) -> None:
        pass

    def process(self, data: Any, ctx: Context) -> Any:
        raise NotImplementedError

    def after(self, ctx: Context) -> None:
        pass

    def undo(self, ctx: Context) -> None:
        pass


class StepDecorator(Step):
    """Decorator: envolve um Step e acrescenta comportamento sem alterá-lo."""

    def __init__(self, inner: Step, name: str | None = None):
        super().__init__(name or inner.name)
        self.inner = inner

    def before(self, ctx: Context) -> None:
        self.inner.before(ctx)

    def process(self, data: Any, ctx: Context) -> Any:
        return self.inner.process(data, ctx)

    def after(self, ctx: Context) -> None:
        self.inner.after(ctx)

    def undo(self, ctx: Context) -> None:
        self.inner.undo(ctx)


class Retry(StepDecorator):
    def __init__(self, inner: Step, attempts: int = 3, exceptions: tuple[type[Exception], ...] = (Exception,)):
        if attempts < 1:
            raise ValueError("attempts deve ser >= 1")
        super().__init__(inner)
        self.attempts = attempts
        self.exceptions = exceptions

    def process(self, data: Any, ctx: Context) -> Any:
        for attempt in range(1, self.attempts + 1):
            try:
                return self.inner.process(data, ctx)
            except StopPipeline:
                raise
            except self.exceptions as exc:
                if attempt == self.attempts:
                    raise
                ctx.emit("step_retry", self.name, attempt=attempt, error=exc)


class Timed(StepDecorator):
    """Guarda a duração em ctx.meta["timings"][nome]."""

    def process(self, data: Any, ctx: Context) -> Any:
        start = perf_counter()
        try:
            return self.inner.process(data, ctx)
        finally:
            ctx.meta.setdefault("timings", {})[self.name] = perf_counter() - start
