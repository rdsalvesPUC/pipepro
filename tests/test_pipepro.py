import unittest

from pipepro import Pipeline, Range, Required, Rule, Step, ValidationError, register

PEOPLE = [{"nome": "ana", "idade": 30}, {"nome": "bia", "idade": 17}, {"nome": "", "idade": 40}]


@register("test_upper")
class Upper(Step):  # extensão do cliente: novo step, sem mexer na lib
    def __init__(self, field):
        super().__init__()
        self.field = field

    def process(self, data, ctx):
        return [{**r, self.field: r[self.field].upper()} for r in data]


class EvenAge(Rule):  # extensão do cliente: nova regra
    def check(self, record):
        return None if record["idade"] % 2 == 0 else "idade ímpar"


class PipelineTest(unittest.TestCase):
    def test_default_flow(self):
        result = (
            Pipeline.builder()
            .validate(Required("nome"), on_error="drop")
            .filter(lambda r: r["idade"] >= 18)
            .use("rename", mapping={"nome": "name"})
            .build()
            .run(PEOPLE)
        )
        self.assertEqual(result.data, [{"name": "ana", "idade": 30}])
        self.assertEqual(len(result.meta["invalid"]), 1)

    def test_extension_via_registry_and_config(self):
        pipeline = Pipeline.from_config([{"step": "test_upper", "field": "nome"}, {"step": "select", "fields": ["nome"]}])
        self.assertEqual(pipeline.run(PEOPLE[:1]).data, [{"nome": "ANA"}])

    def test_custom_rule_raises(self):
        with self.assertRaises(ValidationError):
            Pipeline.builder().validate(EvenAge(), Range("idade", max=100)).build().run(PEOPLE)


if __name__ == "__main__":
    unittest.main()
