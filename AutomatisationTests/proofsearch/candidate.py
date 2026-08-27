from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from collections.abc import Sequence

from .sexpr import SExpr, SExprError, node_count, parse_one
from .spec import IDENTIFIER, RelationSpec


INTEGER = re.compile(r"^-?[0-9]+$")


class CandidateError(ValueError):
    """Raised when a proposed definition is outside the trusted DSL."""


@dataclass(frozen=True)
class Value:
    sort: str
    parts: tuple[str, ...]

    @property
    def scalar(self) -> str:
        if len(self.parts) != 1:
            raise CandidateError(f"{self.sort} is not a scalar SMT value")
        return self.parts[0]


def _free_environment(target: RelationSpec) -> dict[str, Value]:
    return {
        argument.name: Value(argument.sort, argument.smt_names)
        for argument in target.arguments
    }


def _expect_arity(operator: str, args: list[SExpr], expected: int) -> None:
    if len(args) != expected:
        raise CandidateError(
            f"{operator} expects {expected} argument(s), got {len(args)}"
        )


def _boolean(value: Value, context: str) -> str:
    if value.sort != "Bool":
        raise CandidateError(f"{context} expects Bool, got {value.sort}")
    return value.scalar


def _same_sort(values: list[Value], context: str) -> str:
    sorts = {value.sort for value in values}
    if len(sorts) != 1:
        raise CandidateError(f"{context} arguments must have one sort, got {sorted(sorts)}")
    return values[0].sort


def _point_distinct(values: list[Value]) -> str:
    pair_formulas = []
    for left, right in itertools.combinations(values, 2):
        pair_formulas.append(
            f"(or (distinct {left.parts[0]} {right.parts[0]}) "
            f"(distinct {left.parts[1]} {right.parts[1]}))"
        )
    if len(pair_formulas) == 1:
        return pair_formulas[0]
    return f"(and {' '.join(pair_formulas)})"


def _sources(source: RelationSpec | Sequence[RelationSpec]) -> tuple[RelationSpec, ...]:
    sources = (source,) if isinstance(source, RelationSpec) else tuple(source)
    if not sources:
        raise CandidateError("at least one source relation is required")
    names = [spec.name for spec in sources]
    if len(names) != len(set(names)):
        raise CandidateError("source relation names must be unique")
    return sources


def compile_candidate(
    text: str,
    source: RelationSpec | Sequence[RelationSpec],
    target: RelationSpec,
    *,
    max_nodes: int | None = None,
) -> str:
    """Compile the coordinate-free candidate DSL to an SMT-LIB Bool expression."""
    try:
        expression = parse_one(text)
    except SExprError as error:
        raise CandidateError(str(error)) from error
    if max_nodes is not None:
        if max_nodes < 1:
            raise CandidateError("max_nodes must be positive")
        count = node_count(expression)
        if count > max_nodes:
            raise CandidateError(
                f"candidate has {count} syntax nodes; the configured maximum is {max_nodes}"
            )

    sources = _sources(source)
    relation_by_name = {spec.name: spec for spec in sources}

    def compile_expr(node: SExpr, environment: dict[str, Value]) -> Value:
        if isinstance(node, str):
            if node == "true" or node == "false":
                return Value("Bool", (node,))
            if INTEGER.fullmatch(node):
                return Value("Int", (node,))
            if node in environment:
                return environment[node]
            raise CandidateError(f"unknown symbol {node!r}")

        if not node or not isinstance(node[0], str):
            raise CandidateError("every application must start with an operator name")
        operator = node[0]
        args = node[1:]

        if operator in {"exists", "forall"}:
            _expect_arity(operator, args, 2)
            binders = args[0]
            if not isinstance(binders, list):
                raise CandidateError(f"{operator} binders must be a list")
            if not binders:
                raise CandidateError(f"{operator} needs at least one Point binder")
            inner_environment = dict(environment)
            smt_binders: list[str] = []
            for binder in binders:
                if (
                    not isinstance(binder, list)
                    or len(binder) != 2
                    or not isinstance(binder[0], str)
                    or binder[1] != "Point"
                ):
                    raise CandidateError(
                        f"{operator} binders must have the form (name Point)"
                    )
                name = binder[0]
                if not IDENTIFIER.fullmatch(name):
                    raise CandidateError(f"invalid bound variable name {name!r}")
                if name in inner_environment:
                    raise CandidateError(f"bound variable {name!r} shadows another variable")
                parts = (f"{name}_x", f"{name}_y")
                occupied = {
                    part
                    for value in inner_environment.values()
                    for part in value.parts
                }
                if occupied.intersection(parts):
                    raise CandidateError(f"bound variable {name!r} causes an SMT name collision")
                inner_environment[name] = Value("Point", parts)
                smt_binders.extend(f"({part} Int)" for part in parts)
            body = compile_expr(args[1], inner_environment)
            return Value(
                "Bool",
                (f"({operator} ({' '.join(smt_binders)}) {_boolean(body, operator)})",),
            )

        compiled = [compile_expr(arg, environment) for arg in args]

        if operator in {"and", "or"}:
            if not compiled:
                raise CandidateError(f"{operator} needs at least one argument")
            bodies = [_boolean(value, operator) for value in compiled]
            return Value("Bool", (f"({operator} {' '.join(bodies)})",))
        if operator == "not":
            _expect_arity(operator, args, 1)
            return Value("Bool", (f"(not {_boolean(compiled[0], operator)})",))
        if operator in {"=>", "xor", "iff"}:
            _expect_arity(operator, args, 2)
            left = _boolean(compiled[0], operator)
            right = _boolean(compiled[1], operator)
            smt_operator = "=" if operator == "iff" else operator
            return Value("Bool", (f"({smt_operator} {left} {right})",))
        if operator == "=":
            _expect_arity(operator, args, 2)
            sort = _same_sort(compiled, operator)
            if sort == "Point":
                left, right = compiled
                return Value(
                    "Bool",
                    (
                        f"(and (= {left.parts[0]} {right.parts[0]}) "
                        f"(= {left.parts[1]} {right.parts[1]}))",
                    ),
                )
            if sort not in {"Int", "Bool"}:
                raise CandidateError(f"equality is not implemented for {sort}")
            return Value("Bool", (f"(= {compiled[0].scalar} {compiled[1].scalar})",))
        if operator == "distinct":
            if len(compiled) < 2:
                raise CandidateError("distinct needs at least two arguments")
            sort = _same_sort(compiled, operator)
            if sort == "Point":
                return Value("Bool", (_point_distinct(compiled),))
            if sort not in {"Int", "Bool"}:
                raise CandidateError(f"distinct is not implemented for {sort}")
            return Value(
                "Bool", (f"(distinct {' '.join(value.scalar for value in compiled)})",)
            )
        relation_spec = relation_by_name.get(operator)
        if relation_spec is not None:
            if len(compiled) != len(relation_spec.arguments):
                raise CandidateError(
                    f"{relation_spec.name} expects "
                    f"{len(relation_spec.arguments)} logical argument(s), "
                    f"got {len(compiled)}"
                )
            flattened: list[str] = []
            for index, (value, formal) in enumerate(
                zip(compiled, relation_spec.arguments)
            ):
                if value.sort != formal.sort:
                    raise CandidateError(
                        f"{relation_spec.name} argument {index + 1} expects "
                        f"{formal.sort}, "
                        f"got {value.sort}"
                    )
                flattened.extend(value.parts)
            suffix = (" " + " ".join(flattened)) if flattened else ""
            return Value("Bool", (f"({relation_spec.name}{suffix})",))

        allowed_relations = ", ".join(spec.name for spec in sources)
        raise CandidateError(
            f"operator {operator!r} is forbidden; candidates may use only "
            f"{allowed_relations}, "
            "equality, distinct, Boolean operators, and Point quantifiers"
        )

    result = compile_expr(expression, _free_environment(target))
    return _boolean(result, "candidate")
