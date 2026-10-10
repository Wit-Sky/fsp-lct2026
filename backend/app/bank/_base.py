"""Основа банка заданий: параметрический шаблон = генератор варианта по сиду + калиброванная сложность b.

Правильный ответ всегда вычисляется генератором, а не хранится: слитый ответ одного варианта бесполезен
для другого кандидата — у него другие числа, имена и порядок вариантов.
"""
import random
from dataclasses import dataclass, field
from typing import Callable

KINDS = ("single", "number", "order")


@dataclass(frozen=True)
class Template:
    id: str
    spec: str
    topic: str
    b: float                      # сложность по шкале Раша (экспертная, уточняется симуляцией)
    kind: str                     # single | number | order
    about: str                    # что проверяет и почему такой b
    fn: Callable[[random.Random], dict] = field(repr=False, compare=False)
    enabled: bool = True

    def generate(self, seed: int) -> dict:
        """→ {template_id, text, code, kind, options, answer}. answer остаётся на сервере."""
        rng = random.Random(seed)
        raw = self.fn(rng)
        options = raw.get("options")
        answer = raw["answer"]
        if self.kind == "order":
            # options — шаги в правильном порядке; показываем перемешанными.
            correct = list(options)
            shown = correct[:]
            while len(shown) > 1 and shown == correct:
                rng.shuffle(shown)
            options, answer = shown, correct
        return {"template_id": self.id, "text": raw["text"], "code": raw.get("code"), "kind": self.kind,
                "options": options, "answer": answer}


REGISTRY: dict[str, Template] = {}


def template(id: str, spec: str, topic: str, b: float, kind: str, about: str, enabled: bool = True):
    assert kind in KINDS, kind

    def deco(fn):
        assert id not in REGISTRY, f"duplicate template {id}"
        REGISTRY[id] = Template(id=id, spec=spec, topic=topic, b=b, kind=kind, about=about, fn=fn, enabled=enabled)
        return fn
    return deco


def choice(rng: random.Random, correct, wrong) -> dict:
    """Варианты для single: правильный + уникальные дистракторы в случайном порядке."""
    opts, seen = [str(correct)], {str(correct)}
    for w in wrong:
        w = str(w)
        if w not in seen:
            opts.append(w)
            seen.add(w)
    opts = opts[:4]
    rng.shuffle(opts)
    return {"options": opts, "answer": str(correct)}


def var_name(rng: random.Random, pool=("a", "b", "c", "x", "y", "n", "m", "k", "val", "acc", "total", "cnt", "res", "tmp")) -> str:
    return rng.choice(pool)


def names(rng: random.Random, k: int, pool=("items", "data", "nums", "values", "arr", "xs", "lst", "seq", "buf", "parts")) -> list[str]:
    return rng.sample(pool, k)
