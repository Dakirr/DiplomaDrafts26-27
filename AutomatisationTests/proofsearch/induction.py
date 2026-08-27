from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from .sexpr import SExpr, parse_one
from .spec import Parameter, RelationSpec, SpecError, preformat_json


GENERALISATION_REASONING_EFFORTS = frozenset(
    {"minimal", "low", "medium", "high", "xhigh"}
)


@dataclass(frozen=True)
class ParameterBounds:
    min_parameter_value: int
    max_parameter_value: int


@dataclass(frozen=True)
class GeneralisationCheckConfig:
    default_min_parameter_value: int
    default_max_parameter_value: int
    min_measure: int
    max_measure: int
    parameter_overrides: dict[str, ParameterBounds] = field(default_factory=dict)


@dataclass(frozen=True)
class InductionConfig:
    min_parameter_value: int = 0
    max_parameter_value: int = 5
    min_measure: int = 0
    max_measure: int = 5
    attempts_per_step: int = 5
    generalisation_attempts: int = 5
    generalisation_reasoning_effort: str | None = None
    max_formula_nodes: int = 200
    parallelism: int = 4
    generalisation_check: GeneralisationCheckConfig | None = None


@dataclass(frozen=True)
class InductionStage:
    target: RelationSpec
    values: tuple[int, ...]
    measure: int

    @property
    def label(self) -> str:
        return "{" + ",".join(str(value) for value in self.values) + "}"


@dataclass(frozen=True)
class CertifiedRelation:
    stage: InductionStage
    relation: RelationSpec
    candidate: str


def load_induction_config(path: Path) -> InductionConfig:
    try:
        data = json.loads(preformat_json(path.read_text(encoding="utf-8")))
    except FileNotFoundError as error:
        raise SpecError(f"induction config does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise SpecError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise SpecError(f"{path}: top-level value must be an object")

    allowed = {
        "format_version",
        "min_parameter_value",
        "max_parameter_value",
        "min_measure",
        "max_measure",
        "attempts_per_step",
        "generalisation_attempts",
        "generalisation_reasoning_effort",
        "max_formula_nodes",
        "parallelism",
        "generalisation_check",
    }
    extra = set(data) - allowed
    if extra:
        raise SpecError(f"{path}: unknown fields: {', '.join(sorted(extra))}")
    if data.get("format_version") != 1:
        raise SpecError(f"{path}: format_version must be 1")

    values: dict[str, object] = {}
    defaults = InductionConfig()
    integer_fields = allowed - {
        "format_version",
        "generalisation_check",
        "generalisation_reasoning_effort",
    }
    for config_field in integer_fields:
        value = data.get(config_field, getattr(defaults, config_field))
        if isinstance(value, bool) or not isinstance(value, int):
            raise SpecError(f"{path}: {config_field} must be an integer")
        values[config_field] = value
    reasoning_effort = data.get("generalisation_reasoning_effort")
    if reasoning_effort is not None and (
        not isinstance(reasoning_effort, str)
        or reasoning_effort not in GENERALISATION_REASONING_EFFORTS
    ):
        allowed_efforts = ", ".join(sorted(GENERALISATION_REASONING_EFFORTS))
        raise SpecError(
            f"{path}: generalisation_reasoning_effort must be one of: "
            f"{allowed_efforts}"
        )
    values["generalisation_reasoning_effort"] = reasoning_effort
    values["generalisation_check"] = _load_generalisation_check_config(
        data.get("generalisation_check"),
        path,
        default_min_measure=int(values["min_measure"]),
        default_max_measure=int(values["max_measure"]),
    )
    config = InductionConfig(**values)
    if config.min_parameter_value < 0:
        raise SpecError(f"{path}: min_parameter_value must be nonnegative")
    if config.max_parameter_value < config.min_parameter_value:
        raise SpecError(
            f"{path}: max_parameter_value must be at least min_parameter_value"
        )
    if config.min_measure < 0:
        raise SpecError(f"{path}: min_measure must be nonnegative")
    if config.max_measure < config.min_measure:
        raise SpecError(f"{path}: max_measure must be at least min_measure")
    if config.attempts_per_step < 1:
        raise SpecError(f"{path}: attempts_per_step must be positive")
    if config.generalisation_attempts < 1:
        raise SpecError(f"{path}: generalisation_attempts must be positive")
    if config.max_formula_nodes < 1:
        raise SpecError(f"{path}: max_formula_nodes must be positive")
    if config.parallelism < 1:
        raise SpecError(f"{path}: parallelism must be positive")
    return config


def _load_generalisation_check_config(
    data: object,
    path: Path,
    *,
    default_min_measure: int,
    default_max_measure: int,
) -> GeneralisationCheckConfig | None:
    if data is None:
        return None
    label = f"{path}: generalisation_check"
    if not isinstance(data, dict):
        raise SpecError(f"{label} must be an object")
    allowed = {
        "default_min_parameter_value",
        "default_max_parameter_value",
        "min_measure",
        "max_measure",
        "parameter_overrides",
    }
    extra = set(data) - allowed
    if extra:
        raise SpecError(f"{label}: unknown fields: {', '.join(sorted(extra))}")
    required = {
        "default_min_parameter_value",
        "default_max_parameter_value",
    }
    missing = required - set(data)
    if missing:
        raise SpecError(f"{label}: missing fields: {', '.join(sorted(missing))}")

    default_min = data["default_min_parameter_value"]
    default_max = data["default_max_parameter_value"]
    for name, value in (
        ("default_min_parameter_value", default_min),
        ("default_max_parameter_value", default_max),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise SpecError(f"{label}: {name} must be an integer")
    if default_max < default_min:
        raise SpecError(
            f"{label}: default_max_parameter_value must be at least "
            "default_min_parameter_value"
        )
    min_measure = data.get("min_measure", default_min_measure)
    max_measure = data.get("max_measure", default_max_measure)
    for name, value in (("min_measure", min_measure), ("max_measure", max_measure)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise SpecError(f"{label}: {name} must be an integer")
    if max_measure < min_measure:
        raise SpecError(f"{label}: max_measure must be at least min_measure")

    raw_overrides = data.get("parameter_overrides", {})
    if not isinstance(raw_overrides, dict):
        raise SpecError(f"{label}: parameter_overrides must be an object")
    overrides: dict[str, ParameterBounds] = {}
    for parameter_name, raw_bounds in raw_overrides.items():
        override_label = f"{label}.parameter_overrides[{parameter_name!r}]"
        if not isinstance(parameter_name, str) or not parameter_name:
            raise SpecError(f"{label}: override names must be nonempty strings")
        if not isinstance(raw_bounds, dict):
            raise SpecError(f"{override_label} must be an object")
        bound_fields = {"min_parameter_value", "max_parameter_value"}
        bound_extra = set(raw_bounds) - bound_fields
        if bound_extra:
            raise SpecError(
                f"{override_label}: unknown fields: "
                f"{', '.join(sorted(bound_extra))}"
            )
        minimum = raw_bounds.get("min_parameter_value", default_min)
        maximum = raw_bounds.get("max_parameter_value", default_max)
        for name, value in (
            ("min_parameter_value", minimum),
            ("max_parameter_value", maximum),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise SpecError(f"{override_label}: {name} must be an integer")
        if maximum < minimum:
            raise SpecError(
                f"{override_label}: max_parameter_value must be at least "
                "min_parameter_value"
            )
        overrides[parameter_name] = ParameterBounds(minimum, maximum)
    return GeneralisationCheckConfig(
        default_min,
        default_max,
        min_measure,
        max_measure,
        overrides,
    )


def instantiate_target(
    template: RelationSpec,
    parameter_values: tuple[int, ...],
    *,
    name: str | None = None,
    display_name: str | None = None,
) -> RelationSpec:
    if len(parameter_values) != len(template.parameters):
        raise ValueError(
            f"expected {len(template.parameters)} parameter values, "
            f"got {len(parameter_values)}"
        )
    parameters = tuple(
        Parameter(parameter.name, parameter.sort, value)
        for parameter, value in zip(template.parameters, parameter_values)
    )
    return replace(
        template,
        name=name or template.name,
        parameters=parameters,
        display_name=display_name,
    )


def induction_stages(
    template: RelationSpec, config: InductionConfig
) -> list[InductionStage]:
    parameter_count = len(template.parameters)
    if parameter_count == 0:
        raise SpecError("induction requires at least one target parameter")
    domain = range(config.min_parameter_value, config.max_parameter_value + 1)
    stages: list[InductionStage] = []
    for parameter_values in itertools.product(domain, repeat=parameter_count):
        measure = sum(parameter_values)
        if measure < config.min_measure or measure > config.max_measure:
            continue
        target = instantiate_target(template, parameter_values)
        values = tuple(parameter.value for parameter in target.parameters)
        if any(value is None for value in values):
            raise AssertionError("an induction stage retained a symbolic parameter")
        stages.append(
            InductionStage(target, tuple(int(value) for value in values), measure)
        )
    stages.sort(key=lambda stage: (stage.measure, stage.values))
    return stages


def generalisation_check_stages(
    template: RelationSpec, config: InductionConfig
) -> list[InductionStage]:
    check = config.generalisation_check
    if check is None:
        return induction_stages(template, config)
    if not template.parameters:
        raise SpecError("generalisation checking requires at least one target parameter")
    parameter_names = {parameter.name for parameter in template.parameters}
    unknown = set(check.parameter_overrides) - parameter_names
    if unknown:
        raise SpecError(
            "generalisation_check.parameter_overrides contains unknown target "
            f"parameters: {', '.join(sorted(unknown))}"
        )
    domains = []
    for parameter in template.parameters:
        bounds = check.parameter_overrides.get(
            parameter.name,
            ParameterBounds(
                check.default_min_parameter_value,
                check.default_max_parameter_value,
            ),
        )
        domains.append(
            range(bounds.min_parameter_value, bounds.max_parameter_value + 1)
        )
    stages = []
    for parameter_values in itertools.product(*domains):
        values = tuple(int(value) for value in parameter_values)
        measure = sum(values)
        if measure < check.min_measure or measure > check.max_measure:
            continue
        target = instantiate_target(template, values)
        stages.append(InductionStage(target, values, measure))
    stages.sort(key=lambda stage: (stage.measure, stage.values))
    return stages


def dependency_alias(template: RelationSpec, stage: InductionStage) -> str:
    parts = []
    for parameter, value in zip(template.parameters, stage.values):
        encoded = f"m{abs(value)}" if value < 0 else str(value)
        parts.append(f"{parameter.name}_{encoded}")
    return template.name + "__" + "__".join(parts)


def certified_relation(
    template: RelationSpec,
    stage: InductionStage,
    candidate: str,
) -> CertifiedRelation:
    relation = replace(
        stage.target,
        name=dependency_alias(template, stage),
        display_name=template.display_name or template.name,
        description=(
            f"Previously certified instance of {template.description} "
            f"at {stage.label}."
        ),
    )
    return CertifiedRelation(stage, relation, candidate)


def used_relation_names(candidate: str, allowed_names: set[str]) -> list[str]:
    expression = parse_one(candidate)
    found: set[str] = set()

    def visit(node: SExpr) -> None:
        if isinstance(node, str):
            return
        if node and isinstance(node[0], str) and node[0] in allowed_names:
            found.add(node[0])
        for child in node[1:]:
            visit(child)

    visit(expression)
    return sorted(found)
