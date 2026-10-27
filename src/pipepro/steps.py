"""Steps e regras prontos para uso. Os dados são uma lista de registros (dicts)."""
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable

from .context import Context
from .step import Step, StopPipeline

Record = dict[str, Any]


# --- Strategy: regras de validação intercambiáveis ---------------------------

class Rule(ABC):
    @abstractmethod
    def check(self, record: Record) -> str | None:
        """Retorna uma mensagem de erro, ou None se o registro é válido."""


class Required(Rule):
    def __init__(self, *fields: str):
        self.fields = fields

    def check(self, record):
        missing = [f for f in self.fields if record.get(f) in (None, "")]
        return f"campos obrigatórios ausentes: {missing}" if missing else None


class TypeOf(Rule):
    def __init__(self, field: str, type_: type | tuple[type, ...]):
        self.field, self.type_ = field, type_

    def check(self, record):
        if self.field in record and not isinstance(record[self.field], self.type_):
            return f"{self.field} deveria ser {self.type_}"
        return None


class Range(Rule):
    def __init__(self, field: str, min: float | None = None, max: float | None = None):
        self.field, self.min, self.max = field, min, max

    def check(self, record):
        value = record.get(self.field)
        if value is None:
            return None
        if (self.min is not None and value < self.min) or (self.max is not None and value > self.max):
            return f"{self.field}={value} fora de [{self.min}, {self.max}]"
        return None


class Check(Rule):
    """Adapta uma função qualquer como regra."""

    def __init__(self, predicate: Callable[[Record], bool], message: str):
        self.predicate, self.message = predicate, message

    def check(self, record):
        return None if self.predicate(record) else self.message


class ValidationError(Exception):
    def __init__(self, errors: list[tuple[int, list[str]]]):
        self.errors = errors
        super().__init__(f"{len(errors)} registro(s) inválido(s): {errors[:3]}")


class Validate(Step):
    """on_error: "raise" (falha e faz rollback), "drop" (descarta inválidos) ou "stop" (interrompe)."""

    def __init__(self, *rules: Rule, on_error: str = "raise", name: str | None = None):
        if on_error not in ("raise", "drop", "stop"):
            raise ValueError(f"on_error inválido: {on_error!r}")
        super().__init__(name)
        self.rules = rules
        self.on_error = on_error

    def process(self, data, ctx):
        valid, errors = [], []
        for i, record in enumerate(data):
            problems = [msg for rule in self.rules if (msg := rule.check(record))]
            if problems:
                errors.append((i, problems))
            else:
                valid.append(record)
        if errors:
            ctx.meta.setdefault("invalid", []).extend(errors)
            if self.on_error == "raise":
                raise ValidationError(errors)
            if self.on_error == "stop":
                raise StopPipeline(f"{len(errors)} registro(s) inválido(s)")
        return valid


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


class CollectInto(Step):
    """Copia os registros para uma lista externa; `undo` os remove (Command)."""

    # ponytail: guarda o estado da última execução na instância; não use o mesmo
    # CollectInto em execuções simultâneas.
    def __init__(self, target: list, name: str | None = None):
        super().__init__(name)
        self.target = target
        self._added = 0

    def process(self, data, ctx: Context):
        items = list(data)
        self.target.extend(items)
        self._added = len(items)
        return items

    def undo(self, ctx):
        del self.target[len(self.target) - self._added:]
        self._added = 0
