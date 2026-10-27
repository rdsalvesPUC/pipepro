"""Steps prontos para uso. Os dados são uma lista de registros (dicts)."""
from typing import Any, Callable, Iterable

from .step import Step

Record = dict[str, Any]


# --- Transformação e filtro (a função recebida é a estratégia) ---------------

class Transform(Step):
    def __init__(self, fn: Callable[[Record], Record], name: str | None = None):
        super().__init__(name or getattr(fn, "__name__", None))
        self.fn = fn

    def process(self, data, ctx):
        return [self.fn(record) for record in data]


class Filter(Step):
    def __init__(self, predicate: Callable[[Record], bool], name: str | None = None):
        super().__init__(name or getattr(predicate, "__name__", None))
        self.predicate = predicate

    def process(self, data, ctx):
        return [record for record in data if self.predicate(record)]


class Rename(Step):
    def __init__(self, mapping: dict[str, str], name: str | None = None):
        super().__init__(name)
        self.mapping = mapping

    def process(self, data, ctx):
        return [{self.mapping.get(k, k): v for k, v in record.items()} for record in data]


class Select(Step):
    def __init__(self, fields: Iterable[str], name: str | None = None):
        super().__init__(name)
        self.fields = list(fields)

    def process(self, data, ctx):
        return [{f: record[f] for f in self.fields if f in record} for record in data]
