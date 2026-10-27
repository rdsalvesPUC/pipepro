"""Factory/Registry: cria steps pelo nome, para montar pipelines a partir de configuração."""
from typing import Any, Callable

from .step import Step

StepFactory = Callable[..., Step]


class StepRegistry:
    def __init__(self):
        self._factories: dict[str, StepFactory] = {}

    def register(self, name: str, factory: StepFactory | None = None):
        """Use direto (`register("x", Classe)`) ou como decorator (`@register("x")`)."""

        def add(f: StepFactory) -> StepFactory:
            if name in self._factories:
                raise ValueError(f"step já registrado: {name!r}")
            self._factories[name] = f
            return f

        return add(factory) if factory else add

    def create(self, name: str, **options: Any) -> Step:
        try:
            factory = self._factories[name]
        except KeyError:
            raise KeyError(f"step desconhecido: {name!r}; registrados: {self.names()}") from None
        return factory(**options)

    def names(self) -> list[str]:
        return sorted(self._factories)


registry = StepRegistry()
register = registry.register
