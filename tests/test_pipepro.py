import unittest

from pipepro import (
    AuditTrail, CollectInto, Pipeline, Range, Required, Rule, Step, StopPipeline, Transform, ValidationError,
    register,
)

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


class Boom(Step):
    def process(self, data, ctx):
        raise RuntimeError("boom")


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

    def test_stop_keeps_data(self):
        def stop(r):
            raise StopPipeline("chega")

        result = Pipeline([Transform(lambda r: {**r, "ok": True}), Transform(stop)]).run(PEOPLE[:1])
        self.assertTrue(result.stopped)
        self.assertEqual(result.stop_reason, "chega")
        self.assertEqual(result.data, [{"nome": "ana", "idade": 30, "ok": True}])

    def test_failure_rolls_back_and_undoes(self):
        sink, audit = [], AuditTrail()
        pipeline = Pipeline([CollectInto(sink), Boom()], listeners=[audit])
        with self.assertRaises(RuntimeError):
            pipeline.run(PEOPLE)
        self.assertEqual(sink, [])
        self.assertIn(("step_undone", "CollectInto"), audit.trail())
        self.assertIn(("rolled_back", "pipeline"), audit.trail())

    def test_retry_decorator(self):
        calls = []

        def flaky(r):
            calls.append(1)
            if len(calls) < 2:
                raise ConnectionError
            return r

        result = Pipeline.builder().transform(flaky).retry(3).timed().build().run(PEOPLE[:1])
        self.assertEqual(len(calls), 2)
        self.assertIn("flaky", result.meta["timings"])

    def test_nested_pipeline(self):
        inner = Pipeline([Transform(lambda r: {**r, "x": 1})], name="inner")
        outer = Pipeline([inner, Transform(lambda r: {**r, "y": 2})], name="outer")
        self.assertEqual(outer.run([{}]).data, [{"x": 1, "y": 2}])


if __name__ == "__main__":
    unittest.main()
