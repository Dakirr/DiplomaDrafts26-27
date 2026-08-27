from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .induction import (
    InductionConfig,
    InductionStage,
    certified_relation,
    generalisation_check_stages,
    instantiate_target,
)
from .sexpr import SExpr, SExprError, parse_one, render
from .spec import IDENTIFIER, RelationSpec
from .verifier import validate_semantics, verify


ANSWER_FILE = re.compile(r"^R_answer\{(.*)\}\.md$")
INTEGER = re.compile(r"^-?[0-9]+$")
MAX_CASE_BRANCHES = 8


class GeneralisationError(ValueError):
    """Raised when a generalised formula is outside the trusted DSL."""


@dataclass(frozen=True)
class GeneralisationVerification:
    verified: bool
    checked: int
    passed: int
    excluded: int
    failures: tuple[dict[str, object], ...]

    def feedback(self) -> dict[str, object]:
        return {
            "verified_on_bounded_domain": self.verified,
            "checked": self.checked,
            "passed": self.passed,
            "excluded": self.excluded,
            "failures": list(self.failures[:12]),
        }


def _generalisation_context_signature(
    source: RelationSpec, target_template: RelationSpec
) -> str:
    encoded = json.dumps(
        {
            "source": source.as_dict(),
            "target": target_template.as_dict(),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _empty_generalisation_context(
    source: RelationSpec, target_template: RelationSpec
) -> dict[str, object]:
    return {
        "format_version": 1,
        "relation_signature": _generalisation_context_signature(
            source, target_template
        ),
        "source": source.name,
        "target": target_template.name,
        "parameter_order": [
            parameter.name for parameter in target_template.parameters
        ],
        "failed_formulas": [],
    }


def _write_generalisation_context(
    path: Path, context: dict[str, object]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            json.dump(context, temporary, indent=2, ensure_ascii=False)
            temporary.write("\n")
        Path(temporary_name).replace(path)
    except OSError as error:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
        raise GeneralisationError(
            f"could not write generalisation context file {path}: {error}"
        ) from error


def reset_generalisation_context(
    path: Path,
    source: RelationSpec,
    target_template: RelationSpec,
) -> dict[str, object]:
    context = _empty_generalisation_context(source, target_template)
    _write_generalisation_context(path, context)
    return context


def record_failed_generalisation(
    path: Path,
    context: dict[str, object],
    *,
    candidate: str,
    explanation: str,
    verification: GeneralisationVerification,
) -> dict[str, object]:
    compact_failures = []
    for failure in verification.failures:
        compact_failures.append(
            {
                key: failure[key]
                for key in ("parameters", "status", "message", "counterexample")
                if key in failure and failure[key] is not None
            }
        )
    record = {
        "candidate": candidate,
        "explanation": explanation,
        "checked": verification.checked,
        "passed": verification.passed,
        "excluded": verification.excluded,
        "failures": compact_failures,
    }
    existing = context.get("failed_formulas")
    if not isinstance(existing, list):
        raise GeneralisationError("generalisation context has invalid failed_formulas")
    records = [
        item
        for item in existing
        if not isinstance(item, dict) or item.get("candidate") != candidate
    ]
    records.append(record)
    updated = {**context, "failed_formulas": records}
    _write_generalisation_context(path, updated)
    return updated


def load_candidate_outputs(
    output_directory: Path,
    target_template: RelationSpec,
) -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []
    for path in output_directory.iterdir():
        match = ANSWER_FILE.fullmatch(path.name)
        if match is None or not path.is_file():
            continue
        raw_values = [] if match.group(1) == "" else match.group(1).split(",")
        if len(raw_values) != len(target_template.parameters):
            continue
        values: list[int | str] = [
            int(value) if value.lstrip("-").isdigit() else value
            for value in raw_values
        ]
        numeric = all(isinstance(value, int) for value in values)
        observations.append(
            {
                "file": path.name,
                "parameters": {
                    parameter.name: value
                    for parameter, value in zip(target_template.parameters, values)
                },
                "measure": sum(values) if numeric else None,
                "candidate_markdown": path.read_text(encoding="utf-8"),
                "_sort_values": tuple(values),
            }
        )
    observations.sort(
        key=lambda item: (
            item["measure"] is None,
            item["measure"] if item["measure"] is not None else 0,
            tuple(
                (0, value) if isinstance(value, int) else (1, str(value))
                for value in item["_sort_values"]
            ),
        )
    )
    for observation in observations:
        observation.pop("_sort_values")
    return observations


def build_generalisation_prompt(
    source: RelationSpec,
    target_template: RelationSpec,
    observations: list[dict[str, object]],
    config: InductionConfig,
    previous_attempts: list[dict[str, object]] | None = None,
    failed_formula_context: list[dict[str, object]] | None = None,
) -> str:
    parameter_order = [parameter.name for parameter in target_template.parameters]
    source_interface = {
        "name": source.name,
        "description": source.description,
        "parameters": [
            {"name": parameter.name, "sort": parameter.sort}
            for parameter in source.parameters
        ],
        "arguments": [
            {"name": argument.name, "sort": argument.sort}
            for argument in source.arguments
        ],
    }
    target_family = {
        "name": target_template.name,
        "description": target_template.description,
        "parameters": [
            {"name": parameter.name, "sort": parameter.sort}
            for parameter in target_template.parameters
        ],
        "arguments": [
            {"name": argument.name, "sort": argument.sort}
            for argument in target_template.arguments
        ],
    }
    history = previous_attempts or []
    learned_failures = failed_formula_context or []
    return f"""GENERALISATION TASK

Infer one grouped formula for the whole parametrised relation family from the
verified concrete outputs. The formula will be specialised and compared with
the trusted target semantics by Z3 at every tuple selected by the configured
generalisation-check bounds.

Return JSON fields `candidate` and `explanation`.
- `candidate` must be exactly one S-expression in the formal DSL below.
- Do not return LaTeX, Markdown, prose, comments, coordinate names, or SMT commands
  in `candidate`.
- Use grouped parameter cases. Do not enumerate individual observed tuples.
- Prefer the shortest correct rule: minimise case branches, repeated clauses,
  iterator nesting, and relation calls. Do not add a special case unless the
  checker feedback shows that it is needed.
- At most {MAX_CASE_BRANCHES} `when` branches are accepted across the formula.
- Preserve parameter names and order exactly: {json.dumps(parameter_order)}.
- Parameter arithmetic is allowed only in case guards, iteration bounds, and the
  parameter-index positions of `R`.
- Point variables and relation arguments may never occur in parameter arithmetic.
- Relation logic may use only `R`, `{source.name}`, logical connectives, equality,
  distinctness, and Point quantifiers. Never expand semantic bodies and never use
  coordinate arithmetic such as abs(x-y), x_x, or y_y.

FORMAL DSL

Grouped cases:
  (cases
    (when PARAM_CONDITION RELATION_FORMULA)
    ...
    (else RELATION_FORMULA))

Parameter conditions:
  true, false, and, or, not, =>, xor, iff, =, distinct, <, <=, >, >=

Parameter integer expressions:
  declared parameters, bound iteration indices, integer literals,
  (+ ...), (- ...), (* ...), (abs p), (min ...), (max ...),
  (div p q), (mod p q), (pow p q), and (ite condition p q)

Bounded grouped iteration, with inclusive integer bounds:
  (bigand ((i LOWER UPPER)) RELATION_FORMULA)
  (bigor  ((i LOWER UPPER)) RELATION_FORMULA)
Several binders and nested iterations are permitted.

Indexed target-family calls:
  (R INDEX_1 ... INDEX_M arg1 ... argN)
The first M positions are parameter expressions in the exact declared parameter
order. The remaining N positions are logical relation arguments. At a concrete
stage, every referenced R instance must have strictly smaller measure and must
exist among the verified outputs.

Primitive relation calls:
  ({source.name} arg1 ... argN)

Other relation-formula constructs:
  and, or, not, =>, xor, iff, =, distinct, true, false,
  (exists ((z Point)) body), (forall ((z Point)) body)

PRIMITIVE RELATION INTERFACE (semantic coordinate body intentionally omitted):
{json.dumps(source_interface, indent=2, ensure_ascii=False)}

PARAMETRISED TARGET FAMILY:
{json.dumps(target_family, indent=2, ensure_ascii=False)}

INDUCTION AND GENERALISATION-CHECK BOUNDS:
{json.dumps(asdict(config), indent=2, ensure_ascii=False)}

VERIFIED CONCRETE OUTPUTS, IN INDUCTION ORDER:
{json.dumps(observations, indent=2, ensure_ascii=False)}

PERSISTED FAILED FORMULAS AND ALL TUPLES WHERE THEY FAILED:
{json.dumps(learned_failures, indent=2, ensure_ascii=False) if learned_failures else "None."}

COMPLETE ATTEMPT LOG FOR THIS GENERALISATION RUN:
{json.dumps(history, indent=2, ensure_ascii=False) if history else "None."}
"""


def _expect(node: SExpr, arity: int, context: str) -> list[SExpr]:
    if not isinstance(node, list) or len(node) != arity + 1:
        got = len(node) - 1 if isinstance(node, list) and node else 0
        raise GeneralisationError(f"{context} expects {arity} argument(s), got {got}")
    return node[1:]


def _parameter_integer(node: SExpr, environment: dict[str, int]) -> int:
    if isinstance(node, str):
        if INTEGER.fullmatch(node):
            return int(node)
        if node in environment:
            return environment[node]
        raise GeneralisationError(
            f"{node!r} is not a parameter, iteration index, or integer literal"
        )
    if not node or not isinstance(node[0], str):
        raise GeneralisationError("parameter expression must start with an operator")
    operator = node[0]
    args = node[1:]
    if operator == "ite":
        _expect(node, 3, operator)
        return _parameter_integer(
            args[1] if _parameter_condition(args[0], environment) else args[2],
            environment,
        )
    values = [_parameter_integer(arg, environment) for arg in args]
    if operator == "+" and values:
        return sum(values)
    if operator == "-" and values:
        return -values[0] if len(values) == 1 else values[0] - sum(values[1:])
    if operator == "*" and values:
        result = 1
        for value in values:
            result *= value
        return result
    if operator == "abs" and len(values) == 1:
        return abs(values[0])
    if operator == "min" and values:
        return min(values)
    if operator == "max" and values:
        return max(values)
    if operator in {"div", "mod"} and len(values) == 2:
        if values[1] == 0:
            raise GeneralisationError(f"{operator} by zero")
        return values[0] // values[1] if operator == "div" else values[0] % values[1]
    if operator == "pow" and len(values) == 2:
        if values[1] < 0 or values[1] > 12:
            raise GeneralisationError("pow exponent must be between 0 and 12")
        result = values[0] ** values[1]
        if abs(result) > 1_000_000_000:
            raise GeneralisationError("pow result is too large")
        return result
    raise GeneralisationError(f"unsupported parameter operation {operator!r}")


def _parameter_condition(node: SExpr, environment: dict[str, int]) -> bool:
    if node == "true":
        return True
    if node == "false":
        return False
    if not isinstance(node, list) or not node or not isinstance(node[0], str):
        raise GeneralisationError("parameter condition must be a Boolean application")
    operator = node[0]
    args = node[1:]
    if operator in {"and", "or"}:
        if not args:
            raise GeneralisationError(f"{operator} condition needs arguments")
        values = [_parameter_condition(arg, environment) for arg in args]
        return all(values) if operator == "and" else any(values)
    if operator == "not":
        return not _parameter_condition(_expect(node, 1, operator)[0], environment)
    if operator in {"=>", "xor", "iff"}:
        left_node, right_node = _expect(node, 2, operator)
        left = _parameter_condition(left_node, environment)
        right = _parameter_condition(right_node, environment)
        if operator == "=>":
            return not left or right
        if operator == "xor":
            return left != right
        return left == right
    if operator in {"=", "distinct", "<", "<=", ">", ">="}:
        if len(args) < 2:
            raise GeneralisationError(f"{operator} condition needs at least two terms")
        values = [_parameter_integer(arg, environment) for arg in args]
        if operator == "=":
            return all(left == right for left, right in zip(values, values[1:]))
        if operator == "distinct":
            return len(values) == len(set(values))
        comparison = {
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
        }[operator]
        return all(comparison(left, right) for left, right in zip(values, values[1:]))
    raise GeneralisationError(f"unsupported parameter condition {operator!r}")


def _count_case_branches(node: SExpr) -> int:
    if isinstance(node, str):
        return 0
    count = 0
    if node and node[0] == "cases":
        count += sum(
            1
            for branch in node[1:]
            if isinstance(branch, list) and branch and branch[0] == "when"
        )
    return count + sum(_count_case_branches(child) for child in node[1:])


def _validate_generalised_language(
    expression: SExpr,
    source: RelationSpec,
    target_template: RelationSpec,
) -> None:
    parameter_names = {parameter.name for parameter in target_template.parameters}
    parameter_operations = {"+", "-", "*", "abs", "min", "max", "div", "mod", "pow", "ite"}
    condition_operations = {"and", "or", "not", "=>", "xor", "iff", "=", "distinct", "<", "<=", ">", ">="}

    def parameter_expression(node: SExpr, available: set[str]) -> None:
        if isinstance(node, str):
            if INTEGER.fullmatch(node) or node in available:
                return
            raise GeneralisationError(
                f"{node!r} is not permitted in parameter arithmetic"
            )
        if not node or not isinstance(node[0], str) or node[0] not in parameter_operations:
            raise GeneralisationError("invalid parameter expression")
        if node[0] == "ite":
            if len(node) != 4:
                raise GeneralisationError("parameter ite expects three arguments")
            parameter_condition(node[1], available)
            parameter_expression(node[2], available)
            parameter_expression(node[3], available)
            return
        for child in node[1:]:
            parameter_expression(child, available)

    def parameter_condition(node: SExpr, available: set[str]) -> None:
        if isinstance(node, str) and node in {"true", "false"}:
            return
        if not isinstance(node, list) or not node or not isinstance(node[0], str):
            raise GeneralisationError("invalid parameter condition")
        if node[0] not in condition_operations:
            raise GeneralisationError(
                f"operator {node[0]!r} is not permitted in a parameter condition"
            )
        if node[0] in {"and", "or", "not", "=>", "xor", "iff"}:
            for child in node[1:]:
                parameter_condition(child, available)
        else:
            for child in node[1:]:
                parameter_expression(child, available)

    def logical_term(node: SExpr, logical_variables: set[str]) -> None:
        if not isinstance(node, str):
            raise GeneralisationError("relation arguments must be logical variables or literals")
        if INTEGER.fullmatch(node) or node in logical_variables:
            return
        if node in parameter_names:
            raise GeneralisationError(
                f"parameter {node!r} cannot be used as a logical relation argument"
            )
        raise GeneralisationError(f"unknown logical value {node!r}")

    def formula(
        node: SExpr,
        available_parameters: set[str],
        logical_variables: set[str],
    ) -> None:
        if isinstance(node, str):
            if node in {"true", "false"}:
                return
            logical_term(node, logical_variables)
            return
        if not node or not isinstance(node[0], str):
            raise GeneralisationError("relation formula must start with an operator")
        operator = node[0]
        args = node[1:]
        if operator == "cases":
            for branch in args:
                if not isinstance(branch, list) or not branch:
                    raise GeneralisationError("invalid cases branch")
                if branch[0] == "when" and len(branch) == 3:
                    parameter_condition(branch[1], available_parameters)
                    formula(branch[2], available_parameters, logical_variables)
                elif branch[0] == "else" and len(branch) == 2:
                    formula(branch[1], available_parameters, logical_variables)
                else:
                    raise GeneralisationError("cases branches must be when or else")
            return
        if operator in {"bigand", "bigor"}:
            if len(args) != 2 or not isinstance(args[0], list):
                raise GeneralisationError(f"invalid {operator} form")
            inner_parameters = set(available_parameters)
            for binder in args[0]:
                if (
                    not isinstance(binder, list)
                    or len(binder) != 3
                    or not isinstance(binder[0], str)
                ):
                    raise GeneralisationError(f"invalid {operator} binder")
                parameter_expression(binder[1], inner_parameters)
                parameter_expression(binder[2], inner_parameters)
                if binder[0] in inner_parameters:
                    raise GeneralisationError(
                        f"iteration index {binder[0]!r} shadows a parameter"
                    )
                inner_parameters.add(binder[0])
            formula(args[1], inner_parameters, logical_variables)
            return
        if operator == "R":
            parameter_count = len(target_template.parameters)
            logical_count = len(target_template.arguments)
            if len(args) != parameter_count + logical_count:
                raise GeneralisationError(
                    f"R expects {parameter_count} indices and {logical_count} arguments"
                )
            for index in args[:parameter_count]:
                parameter_expression(index, available_parameters)
            for argument in args[parameter_count:]:
                logical_term(argument, logical_variables)
            return
        if operator == source.name:
            if len(args) != len(source.arguments):
                raise GeneralisationError(
                    f"{source.name} expects {len(source.arguments)} arguments"
                )
            for argument in args:
                logical_term(argument, logical_variables)
            return
        if operator in {"exists", "forall"}:
            if len(args) != 2 or not isinstance(args[0], list):
                raise GeneralisationError(f"invalid {operator} form")
            inner_variables = set(logical_variables)
            for binder in args[0]:
                if (
                    not isinstance(binder, list)
                    or len(binder) != 2
                    or not isinstance(binder[0], str)
                    or binder[1] != "Point"
                ):
                    raise GeneralisationError(f"invalid {operator} Point binder")
                if binder[0] in parameter_names or binder[0] in inner_variables:
                    raise GeneralisationError(
                        f"logical binder {binder[0]!r} shadows another symbol"
                    )
                inner_variables.add(binder[0])
            formula(args[1], available_parameters, inner_variables)
            return
        if operator in {"and", "or", "not", "=>", "xor", "iff"}:
            for child in args:
                formula(child, available_parameters, logical_variables)
            return
        if operator in {"=", "distinct"}:
            for child in args:
                logical_term(child, logical_variables)
            return
        if operator in parameter_operations or operator in {"<", "<=", ">", ">="}:
            raise GeneralisationError(
                f"parameter operation {operator!r} occurs in relation logic"
            )
        raise GeneralisationError(
            f"relation operator {operator!r} is forbidden; use only R and {source.name}"
        )

    formula(
        expression,
        set(parameter_names),
        {argument.name for argument in target_template.arguments},
    )


def specialise_generalised_formula(
    formula: str,
    source: RelationSpec,
    target_template: RelationSpec,
    stage: InductionStage,
    dependencies: dict[tuple[int, ...], RelationSpec],
    *,
    expansion_limit: int,
) -> tuple[str, tuple[str, ...]]:
    try:
        expression = parse_one(formula)
    except SExprError as error:
        raise GeneralisationError(str(error)) from error
    _validate_generalised_language(expression, source, target_template)
    branch_count = _count_case_branches(expression)
    if branch_count > MAX_CASE_BRANCHES:
        raise GeneralisationError(
            f"formula has {branch_count} when branches; maximum is {MAX_CASE_BRANCHES}"
        )
    parameter_names = {parameter.name for parameter in target_template.parameters}
    environment = {
        parameter.name: int(parameter.value)
        for parameter in stage.target.parameters
        if parameter.value is not None
    }
    used_relations: set[str] = set()
    expansions = [0]

    def specialise(node: SExpr, parameter_environment: dict[str, int]) -> SExpr:
        if isinstance(node, str):
            if node in parameter_names or node in parameter_environment:
                raise GeneralisationError(
                    f"parameter {node!r} occurs outside a guard, iteration bound, "
                    "or R index"
                )
            return node
        if not node or not isinstance(node[0], str):
            raise GeneralisationError("relation formula application needs an operator")
        operator = node[0]
        args = node[1:]

        if operator == "cases":
            if not args:
                raise GeneralisationError("cases needs at least one branch")
            else_body: SExpr | None = None
            for index, branch in enumerate(args):
                if not isinstance(branch, list) or not branch or not isinstance(branch[0], str):
                    raise GeneralisationError("each cases branch must be when or else")
                if branch[0] == "when":
                    if len(branch) != 3:
                        raise GeneralisationError("when expects a condition and formula")
                    if _parameter_condition(branch[1], parameter_environment):
                        return specialise(branch[2], parameter_environment)
                elif branch[0] == "else":
                    if len(branch) != 2 or index != len(args) - 1:
                        raise GeneralisationError("else must be the final cases branch")
                    else_body = branch[1]
                else:
                    raise GeneralisationError("each cases branch must be when or else")
            if else_body is None:
                raise GeneralisationError("no cases branch matched and no else was supplied")
            return specialise(else_body, parameter_environment)

        if operator in {"bigand", "bigor"}:
            if len(args) != 2 or not isinstance(args[0], list):
                raise GeneralisationError(
                    f"{operator} expects a binder list and relation formula"
                )
            binders = args[0]
            if not binders:
                raise GeneralisationError(f"{operator} needs at least one binder")
            results: list[SExpr] = []

            def expand(index: int, current: dict[str, int]) -> None:
                if index == len(binders):
                    expansions[0] += 1
                    if expansions[0] > expansion_limit:
                        raise GeneralisationError(
                            f"bounded iteration expands beyond {expansion_limit} instances"
                        )
                    results.append(specialise(args[1], current))
                    return
                binder = binders[index]
                if (
                    not isinstance(binder, list)
                    or len(binder) != 3
                    or not isinstance(binder[0], str)
                    or not IDENTIFIER.fullmatch(binder[0])
                ):
                    raise GeneralisationError(
                        f"{operator} binders must have form (name lower upper)"
                    )
                name = binder[0]
                if name in parameter_names or name in current:
                    raise GeneralisationError(f"iteration index {name!r} shadows a parameter")
                lower = _parameter_integer(binder[1], current)
                upper = _parameter_integer(binder[2], current)
                for value in range(lower, upper + 1):
                    inner = dict(current)
                    inner[name] = value
                    expand(index + 1, inner)

            expand(0, dict(parameter_environment))
            if not results:
                return "true" if operator == "bigand" else "false"
            if len(results) == 1:
                return results[0]
            return ["and" if operator == "bigand" else "or", *results]

        if operator == "R":
            parameter_count = len(target_template.parameters)
            logical_count = len(target_template.arguments)
            if len(args) != parameter_count + logical_count:
                raise GeneralisationError(
                    f"R expects {parameter_count} parameter indices and "
                    f"{logical_count} logical arguments"
                )
            values = tuple(
                _parameter_integer(arg, parameter_environment)
                for arg in args[:parameter_count]
            )
            dependency = dependencies.get(values)
            if dependency is None:
                raise GeneralisationError(
                    f"R{values} is not among the verified concrete outputs"
                )
            if sum(values) >= stage.measure:
                raise GeneralisationError(
                    f"R{values} is not strictly smaller than stage {stage.values}"
                )
            used_relations.add(dependency.name)
            return [
                dependency.name,
                *(specialise(arg, parameter_environment) for arg in args[parameter_count:]),
            ]

        if operator in {"exists", "forall"}:
            if len(args) != 2 or not isinstance(args[0], list):
                raise GeneralisationError(f"invalid {operator} form")
            for binder in args[0]:
                if not isinstance(binder, list) or not binder or not isinstance(binder[0], str):
                    raise GeneralisationError(f"invalid {operator} binder")
                if binder[0] in parameter_names or binder[0] in parameter_environment:
                    raise GeneralisationError(
                        f"logical binder {binder[0]!r} shadows a parameter"
                    )
            return [operator, args[0], specialise(args[1], parameter_environment)]

        if operator in {"+", "-", "*", "abs", "min", "max", "div", "mod", "pow", "ite"}:
            raise GeneralisationError(
                f"parameter operation {operator!r} occurs in relation logic"
            )
        return [operator, *(specialise(arg, parameter_environment) for arg in args)]

    specialised = specialise(expression, environment)
    return render(specialised), tuple(sorted(used_relations))


def _dependency_relations(
    target_template: RelationSpec,
    observations: list[dict[str, object]],
) -> dict[tuple[int, ...], RelationSpec]:
    result: dict[tuple[int, ...], RelationSpec] = {}
    for observation in observations:
        raw_parameters = observation.get("parameters")
        if not isinstance(raw_parameters, dict):
            continue
        values = tuple(raw_parameters.get(parameter.name) for parameter in target_template.parameters)
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
            continue
        concrete_values = tuple(int(value) for value in values)
        target = instantiate_target(target_template, concrete_values)
        stage = InductionStage(target, concrete_values, sum(concrete_values))
        result[concrete_values] = certified_relation(target_template, stage, "").relation
    return result


def verify_generalised_formula(
    formula: str,
    source: RelationSpec,
    target_template: RelationSpec,
    observations: list[dict[str, object]],
    config: InductionConfig,
    *,
    timeout_ms: int = 30_000,
    z3_binary: str = "z3",
) -> GeneralisationVerification:
    dependencies = _dependency_relations(target_template, observations)
    dependency_by_name = {relation.name: relation for relation in dependencies.values()}
    checked = 0
    passed = 0
    excluded = 0
    failures: list[dict[str, object]] = []
    for stage in generalisation_check_stages(target_template, config):
        parameters = {
            parameter.name: parameter.value for parameter in stage.target.parameters
        }
        try:
            candidate, used_names = specialise_generalised_formula(
                formula,
                source,
                target_template,
                stage,
                dependencies,
                expansion_limit=config.max_formula_nodes,
            )
        except GeneralisationError as error:
            checked += 1
            failures.append(
                {"parameters": parameters, "status": "invalid", "message": str(error)}
            )
            continue
        sources = [source] + [dependency_by_name[name] for name in used_names]
        semantic_error = validate_semantics(sources, stage.target, z3_binary=z3_binary)
        if semantic_error is not None:
            if semantic_error.startswith("parameter constraints are inconsistent"):
                excluded += 1
                continue
            checked += 1
            failures.append(
                {
                    "parameters": parameters,
                    "status": "error",
                    "message": semantic_error,
                }
            )
            continue
        checked += 1
        result = verify(
            candidate,
            sources,
            stage.target,
            timeout_ms=timeout_ms,
            z3_binary=z3_binary,
            max_formula_nodes=config.max_formula_nodes,
        )
        if result.verified:
            passed += 1
        else:
            failures.append(
                {
                    "parameters": parameters,
                    "status": result.status,
                    "message": result.message,
                    "counterexample": result.counterexample,
                    "specialised_candidate": candidate,
                }
            )
    return GeneralisationVerification(
        verified=checked > 0 and passed == checked,
        checked=checked,
        passed=passed,
        excluded=excluded,
        failures=tuple(failures),
    )


def _latex_name(name: str) -> str:
    return r"\mathit{" + name.replace("_", r"\_") + "}"


def generalised_formula_to_latex(
    formula: str,
    source: RelationSpec,
    target_template: RelationSpec,
) -> str:
    expression = parse_one(formula)
    parameter_count = len(target_template.parameters)

    def latex(node: SExpr) -> str:
        if isinstance(node, str):
            if node == "true":
                return r"\top"
            if node == "false":
                return r"\bot"
            return node if INTEGER.fullmatch(node) else _latex_name(node)
        operator = node[0]
        if not isinstance(operator, str):
            raise GeneralisationError("invalid operator in LaTeX renderer")
        args = node[1:]
        if operator == "cases":
            rows = []
            for branch in args:
                if not isinstance(branch, list) or not branch:
                    raise GeneralisationError("invalid cases branch")
                if branch[0] == "when":
                    rows.append(latex(branch[2]) + r", & " + latex(branch[1]))
                elif branch[0] == "else":
                    rows.append(latex(branch[1]) + r", & \text{otherwise}")
            return r"\begin{cases}" + r" \\ ".join(rows) + r"\end{cases}"
        if operator in {"bigand", "bigor"}:
            binders = args[0]
            if not isinstance(binders, list):
                raise GeneralisationError("invalid iteration binders")
            symbol = r"\bigwedge" if operator == "bigand" else r"\bigvee"
            limits = []
            for binder in binders:
                if not isinstance(binder, list) or len(binder) != 3:
                    raise GeneralisationError("invalid iteration binder")
                limits.append(
                    latex(binder[1]) + r"\le " + latex(binder[0]) + r"\le " + latex(binder[2])
                )
            return symbol + r"_{\substack{" + r" \\ ".join(limits) + "}} " + latex(args[1])
        if operator == "R":
            indices = ",".join(latex(arg) for arg in args[:parameter_count])
            logical = ",".join(latex(arg) for arg in args[parameter_count:])
            base = r"\mathtt{" + (target_template.display_name or target_template.name).replace("_", r"\_") + "}"
            return base + "_{" + indices + r"}\left(" + logical + r"\right)"
        if operator == source.name:
            logical = ",".join(latex(arg) for arg in args)
            base = r"\mathtt{" + (source.display_name or source.name).replace("_", r"\_") + "}"
            return base + r"\left(" + logical + r"\right)"
        if operator in {"exists", "forall"}:
            quantifier = r"\exists" if operator == "exists" else r"\forall"
            binders = args[0]
            rendered = []
            if isinstance(binders, list):
                for binder in binders:
                    if isinstance(binder, list) and binder:
                        rendered.append(
                            quantifier + " " + latex(binder[0]) + r"\in\mathbb{Z}^{2}\;"
                        )
            return r"\left(" + "".join(rendered) + latex(args[1]) + r"\right)"
        rendered = [latex(arg) for arg in args]
        infix = {
            "and": r"\land",
            "or": r"\lor",
            "=>": r"\longrightarrow",
            "xor": r"\mathbin{\veebar}",
            "iff": r"\Leftrightarrow",
            "=": "=",
            "<": "<",
            "<=": r"\le",
            ">": ">",
            ">=": r"\ge",
            "+": "+",
            "-": "-",
            "*": r"\cdot",
        }
        if operator in infix:
            return r"\left(" + (" " + infix[operator] + " ").join(rendered) + r"\right)"
        if operator == "not":
            return r"\neg " + rendered[0]
        if operator == "distinct":
            return r"\operatorname{distinct}\left(" + ",".join(rendered) + r"\right)"
        return r"\operatorname{" + operator.replace("_", r"\_") + r"}\left(" + ",".join(rendered) + r"\right)"

    return latex(expression)


def write_generalised_formula(
    output_directory: Path,
    formula: str,
    observation_count: int,
    verification: GeneralisationVerification,
    source: RelationSpec,
    target_template: RelationSpec,
) -> Path:
    formula = formula.strip()
    if not formula:
        raise GeneralisationError("generalised formula is empty")
    latex_formula = generalised_formula_to_latex(formula, source, target_template)
    target_base = (
        r"\mathtt{"
        + (target_template.display_name or target_template.name).replace("_", r"\_")
        + "}"
    )
    target_indices = ",".join(
        _latex_name(parameter.name) for parameter in target_template.parameters
    )
    target_arguments = ",".join(
        _latex_name(argument.name) for argument in target_template.arguments
    )
    target_application = target_base
    if target_indices:
        target_application += "_{" + target_indices + "}"
    target_application += r"\left(" + target_arguments + r"\right)"
    if verification.verified:
        status = (
            f"Bounded verification passed at all {verification.checked} selected "
            "parameter tuples. This is not an unbounded proof."
        )
    else:
        status = (
            f"Bounded verification did not pass: {verification.passed} of "
            f"{verification.checked} checked tuples passed; "
            f"{verification.excluded} tuples were excluded by constraints."
        )
    failure_lines = [
        "- `" + json.dumps(failure.get("parameters"), ensure_ascii=False) + "`: "
        + str(failure.get("message"))
        for failure in verification.failures[:12]
    ]
    path = output_directory / "generalised_formula.md"
    content = [
        "# Generalised formula",
        "",
        f"> Status: {status}",
        f"> Inferred from {observation_count} verified concrete candidate(s).",
        "",
        "$$",
        target_application + r" \Leftrightarrow " + latex_formula,
        "$$",
        "",
        "## Formal generalisation DSL",
        "",
        "```text",
        formula,
        "```",
        "",
    ]
    if failure_lines:
        content.extend(["## Bounded-check failures", "", *failure_lines, ""])
    path.write_text("\n".join(content), encoding="utf-8")
    return path
