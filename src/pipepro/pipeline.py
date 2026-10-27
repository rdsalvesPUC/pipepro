"""Pipeline: encadeia os steps e executa a cadeia."""
from typing import Any, Iterable

from .context import Context
from .step import Step, StopPipeline


class Pipeline:
    # ponytail: os steps são encadeados in place; não reutilize a mesma instância
    # de Step em dois pipelines.
    def __init__(self, steps: Iterable[Step], name: str = "pipeline"):
        self.name = name
        self.steps = list(steps)
        if not self.steps:
            raise ValueError("um pipeline precisa de pelo menos um step")
        for current, following in zip(self.steps, self.steps[1:]):
            current.set_next(following)
        self.steps[-1].set_next(None)

    def run(self, data: Any) -> Context:
        """Executa e devolve o Context (data, meta, stopped, stop_reason)."""
        ctx = Context(data)
        try:
            self.steps[0].handle(ctx)
        except StopPipeline as stop:
            ctx.stopped = True
            ctx.stop_reason = str(stop) or None
        return ctx
