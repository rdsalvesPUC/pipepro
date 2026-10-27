# pipepro

Mini framework para pipelines de processamento de dados em memória. Você monta uma
sequência de etapas (validação, transformação, filtro), e o pipeline pode ser
**interrompido**, **auditado** e **revertido** de forma estruturada.

## Equipe

| Integrante | GitHub |
|------------|--------|
| Eduardo Fabri | [@eduardofabrii](https://github.com/eduardofabrii) |
| João Pedro Cardoso de Liz | [@Jcliz](https://github.com/Jcliz) |
| João Vitor Correa Oliveira | [@jvecodev](https://github.com/jvecodev) |
| Rodrigo Alves | [@rdsalvesPUC](https://github.com/rdsalvesPUC) |

## Vídeo de apresentação

_Link do YouTube (não listado)_

## Instalação

```bash
pip install git+https://github.com/rdsalvesPUC/pipepro.git
```

Requer Python 3.10+ e não tem dependências.

## Uso padrão

Os dados são uma lista de registros (`dict`). O que vem pronto:

- **Steps:** `Validate`, `Transform`, `Filter`, `Rename`, `Select`, `CollectInto`.
- **Regras de validação:** `Required`, `TypeOf`, `Range`, `Check`.
- **Decorators:** `Retry`, `Timed`.
- **Listener de auditoria:** `AuditTrail`.

```python
from pipepro import AuditTrail, Pipeline, Range, Required

audit = AuditTrail()
pipeline = (
    Pipeline.builder("cadastro")
    .validate(Required("nome"), Range("idade", min=0, max=130), on_error="drop")
    .filter(lambda r: r["idade"] >= 18)
    .transform(lambda r: {**r, "nome": r["nome"].title()})
    .use("rename", mapping={"nome": "name"})
    .timed()
    .on(audit)
    .build()
)

result = pipeline.run([{"nome": "ana", "idade": 30}, {"nome": "", "idade": 40}])
result.data        # [{'name': 'Ana', 'idade': 30}]
result.meta        # {'invalid': [(1, [...])], 'timings': {...}}
audit.trail()      # [('step_started', 'cadastro'), ...]
```

`pipeline.run` devolve um `Context` com `data`, `meta`, `stopped` e `stop_reason`.

### Interromper, reverter e auditar

- **Interromper:** qualquer step pode lançar `StopPipeline("motivo")`. O pipeline para,
  mantém os dados como estavam até ali e devolve `stopped=True`. Com
  `Validate(..., on_error="stop")` isso acontece automaticamente.
- **Reverter:** se um step lança uma exceção, cada step já concluído executa seu `undo()`
  e os dados voltam ao estado anterior à execução. Depois disso a exceção é relançada.
  Com `on_error="raise"` (o padrão), `Validate` lança `ValidationError`.
- **Auditar:** passe listeners em `.on(...)` ou em `run(data, listeners=[...])`. Um
  listener é qualquer função que recebe um `Event`.

### Montar a partir de configuração

```python
pipeline = Pipeline.from_config([
    {"step": "rename", "mapping": {"nome": "name"}},
    {"step": "select", "fields": ["name"]},
])
```

### Pipelines aninhados

Um `Pipeline` também é um `Step`, então pode entrar como etapa de outro:

```python
limpeza = Pipeline.builder("limpeza").validate(Required("nome"), on_error="drop").build()
principal = Pipeline([limpeza, Select(["nome"])], name="principal")
```

## Estendendo a biblioteca

Nada disso exige alterar o código da lib.

**Novo step:** herde de `Step` e implemente `process`. Implemente também `undo` se o step
tiver efeito colateral, e `before`/`after` se precisar de ganchos.

```python
from pipepro import Step, register

@register("upper")                     # opcional: torna o step usável por nome/config
class Upper(Step):
    def __init__(self, field):
        super().__init__()
        self.field = field

    def process(self, data, ctx):
        return [{**r, self.field: r[self.field].upper()} for r in data]

Pipeline.builder().use("upper", field="nome").build()
```

**Nova regra de validação:** herde de `Rule`.

```python
from pipepro import Rule

class Cpf(Rule):
    def check(self, record):
        return None if len(record.get("cpf", "")) == 11 else "CPF inválido"
```

**Novo comportamento em volta de um step:** herde de `StepDecorator` e sobrescreva `process`.

**Novo destino de auditoria:** escreva uma função `def meu_listener(event): ...`.
