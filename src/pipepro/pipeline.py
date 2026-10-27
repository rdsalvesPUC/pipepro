"""Pipeline (Composite + Memento) e PipelineBuilder (Builder)."""
from typing import Any, Callable, Iterable

from .context import Context
from .events import Listener
from .step import Retry, Step, StopPipeline, Timed
from .steps import Filter, Rule, Transform, Validate


class Pipeline(Step):
    """Composite: um Pipeline é um Step, então pode ser usado dentro de outro."""

    # ponytail: os steps são encadeados in place; não reutilize a mesma instância
    # de Step em dois pipelines.
    def __init__(self, steps: Iterable[Step], name: str = "pipeline", listeners: Iterable[Listener] = ()):
        super().__init__(name)
        self.steps = list(steps)
        if not self.steps:
            raise ValueError("um pipeline precisa de pelo menos um step")
        self.listeners = list(listeners)
        for current, following in zip(self.steps, self.steps[1:]):
            current.set_next(following)
        self.steps[-1].set_next(None)

    def process(self, data: Any, ctx: Context) -> Any:
        snapshot = ctx.save()  # Memento: o pipeline é o caretaker
        try:
            self.steps[0].handle(ctx)
        except StopPipeline:
            raise
        except Exception:
            ctx.restore(snapshot)
            ctx.emit("rolled_back", self.name)
            raise
        return ctx.data

    def run(self, data: Any, listeners: Iterable[Listener] = ()) -> Context:
        """Executa e devolve o Context (data, meta, stopped, stop_reason).
        Em caso de erro, desfaz tudo e relança a exceção."""
        ctx = Context(data, [*self.listeners, *listeners])
        try:
            self.handle(ctx)
        except StopPipeline as stop:
            ctx.stopped = True
            ctx.stop_reason = str(stop) or None
            ctx.emit("pipeline_stopped", self.name, reason=ctx.stop_reason)
        return ctx

    @staticmethod
    def builder(name: str = "pipeline") -> "PipelineBuilder":
        return PipelineBuilder(name)


class PipelineBuilder:
    """Builder: API fluente para montar um Pipeline passo a passo."""

    def __init__(self, name: str = "pipeline"):
        self._name = name
        self._steps: list[Step] = []
        self._listeners: list[Listener] = []

    def add(self, step: Step) -> "PipelineBuilder":
        self._steps.append(step)
        return self

    def validate(self, *rules: Rule, on_error: str = "raise") -> "PipelineBuilder":
        return self.add(Validate(*rules, on_error=on_error))

    def transform(self, fn: Callable, name: str | None = None) -> "PipelineBuilder":
        return self.add(Transform(fn, name))

    def filter(self, predicate: Callable, name: str | None = None) -> "PipelineBuilder":
        return self.add(Filter(predicate, name))

    def retry(self, attempts: int = 3) -> "PipelineBuilder":
        """Aplica Retry ao último step adicionado."""
        return self._wrap_last(lambda step: Retry(step, attempts))

    def timed(self) -> "PipelineBuilder":
        """Aplica Timed ao último step adicionado."""
        return self._wrap_last(Timed)

    def on(self, listener: Listener) -> "PipelineBuilder":
        self._listeners.append(listener)
        return self

    def build(self) -> Pipeline:
        return Pipeline(self._steps, self._name, self._listeners)

    def _wrap_last(self, wrap: Callable[[Step], Step]) -> "PipelineBuilder":
        if not self._steps:
            raise ValueError("adicione um step antes de decorá-lo")
        self._steps[-1] = wrap(self._steps[-1])
        return self
