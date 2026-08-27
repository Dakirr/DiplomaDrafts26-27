from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .sexpr import SExprError, parse_one, render


IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
SUPPORTED_SORTS = {"Point", "Int"}


class SpecError(ValueError):
    """Raised for an invalid relation input file."""


def preformat_json(text: str) -> str:
    """Make raw control characters inside JSON strings JSON-compatible.

    This permits readable multi-line SMT-LIB bodies while leaving all text
    outside strings untouched. Escaped JSON characters keep their usual
    meaning.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    output: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if not in_string:
            output.append(char)
            if char == '"':
                in_string = True
            continue

        if escaped:
            output.append(char)
            escaped = False
        elif char == "\\":
            output.append(char)
            escaped = True
        elif char == '"':
            output.append(char)
            in_string = False
        elif char == "\n":
            output.append("\\n")
        elif char == "\t":
            output.append("\\t")
        elif ord(char) < 0x20:
            output.append(f"\\u{ord(char):04x}")
        else:
            output.append(char)
    return "".join(output)


@dataclass(frozen=True)
class Argument:
    name: str
    sort: str

    @property
    def smt_names(self) -> tuple[str, ...]:
        if self.sort == "Point":
            return (f"{self.name}_x", f"{self.name}_y")
        return (self.name,)


@dataclass(frozen=True)
class Parameter:
    name: str
    sort: str
    value: int | None = None

    @property
    def is_symbolic(self) -> bool:
        return self.value is None

    @property
    def smt_value(self) -> str:
        if self.value is None:
            raise SpecError(f"symbolic parameter {self.name} has no fixed SMT value")
        if self.value >= 0:
            return str(self.value)
        return f"(- {-self.value})"


@dataclass(frozen=True)
class RelationSpec:
    name: str
    description: str
    parameters: tuple[Parameter, ...]
    parameter_constraint: str
    arguments: tuple[Argument, ...]
    body: str
    path: Path
    display_name: str | None = None

    @property
    def flattened_names(self) -> tuple[str, ...]:
        return tuple(name for arg in self.arguments for name in arg.smt_names)

    def smt_formals(self) -> str:
        return " ".join(f"({name} Int)" for name in self.flattened_names)

    def _with_fixed_parameters(self, expression: str) -> str:
        fixed = [parameter for parameter in self.parameters if not parameter.is_symbolic]
        if not fixed:
            return expression
        bindings = " ".join(
            f"({parameter.name} {parameter.smt_value})" for parameter in fixed
        )
        return f"(let ({bindings}) {expression})"

    def smt_body(self) -> str:
        return self._with_fixed_parameters(self.body)

    def smt_constraint(self) -> str:
        return self._with_fixed_parameters(self.parameter_constraint)

    def smt_call(self, logical_values: list[tuple[str, ...]] | None = None) -> str:
        parts = (
            [part for value in logical_values for part in value]
            if logical_values is not None
            else list(self.flattened_names)
        )
        return f"({self.name}{(' ' + ' '.join(parts)) if parts else ''})"

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "format_version": 1,
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    **{"name": parameter.name, "sort": parameter.sort},
                    **({"value": parameter.value} if parameter.value is not None else {}),
                }
                for parameter in self.parameters
            ],
            "parameter_constraint": self.parameter_constraint,
            "arguments": [
                {"name": argument.name, "sort": argument.sort}
                for argument in self.arguments
            ],
            "body": self.body,
        }
        if self.display_name is not None:
            result["display_name"] = self.display_name
        return result


def _identifier(value: object, field: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise SpecError(f"{field} must match {IDENTIFIER.pattern}")
    return value


def load_relation(path: Path) -> RelationSpec:
    try:
        source_text = path.read_text(encoding="utf-8")
        data = json.loads(preformat_json(source_text))
    except FileNotFoundError as error:
        raise SpecError(f"input file does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise SpecError(f"{path}: invalid JSON: {error}") from error

    if not isinstance(data, dict):
        raise SpecError(f"{path}: top-level value must be an object")
    allowed_keys = {
        "format_version",
        "name",
        "description",
        "parameters",
        "parameter_constraint",
        "arguments",
        "body",
    }
    extra_keys = set(data) - allowed_keys
    if extra_keys:
        raise SpecError(f"{path}: unknown fields: {', '.join(sorted(extra_keys))}")
    if data.get("format_version") != 1:
        raise SpecError(f"{path}: format_version must be 1")

    name = _identifier(data.get("name"), f"{path}: name")
    description = data.get("description", "")
    if not isinstance(description, str):
        raise SpecError(f"{path}: description must be a string")

    raw_parameters = data.get("parameters", [])
    if not isinstance(raw_parameters, list):
        raise SpecError(f"{path}: parameters must be an array")
    parameters: list[Parameter] = []
    seen_parameters: set[str] = set()
    for index, raw in enumerate(raw_parameters):
        if (
            not isinstance(raw, dict)
            or not {"name", "sort"}.issubset(raw)
            or set(raw) - {"name", "sort", "value"}
        ):
            raise SpecError(
                f"{path}: parameters[{index}] must contain name and sort, with optional value"
            )
        parameter_name = _identifier(
            raw["name"], f"{path}: parameters[{index}].name"
        )
        if raw["sort"] != "Int":
            raise SpecError(f"{path}: parameters[{index}].sort must be Int")
        value = raw.get("value")
        if "value" in raw and (isinstance(value, bool) or not isinstance(value, int)):
            raise SpecError(f"{path}: parameters[{index}].value must be an integer")
        if parameter_name in seen_parameters:
            raise SpecError(f"{path}: duplicate parameter {parameter_name}")
        seen_parameters.add(parameter_name)
        parameters.append(Parameter(parameter_name, "Int", value))

    parameter_constraint = data.get("parameter_constraint", "true")
    if not isinstance(parameter_constraint, str):
        raise SpecError(f"{path}: parameter_constraint must be an SMT-LIB expression")
    try:
        parameter_constraint = render(parse_one(parameter_constraint))
    except SExprError as error:
        raise SpecError(f"{path}: invalid parameter_constraint: {error}") from error

    raw_arguments = data.get("arguments")
    if not isinstance(raw_arguments, list):
        raise SpecError(f"{path}: arguments must be an array")
    arguments: list[Argument] = []
    seen_logical: set[str] = set()
    seen_smt: set[str] = set()
    for index, raw in enumerate(raw_arguments):
        if not isinstance(raw, dict) or set(raw) != {"name", "sort"}:
            raise SpecError(
                f"{path}: arguments[{index}] must contain exactly name and sort"
            )
        argument_name = _identifier(raw["name"], f"{path}: arguments[{index}].name")
        sort = raw["sort"]
        if sort not in SUPPORTED_SORTS:
            raise SpecError(
                f"{path}: arguments[{index}].sort must be Point or Int"
            )
        if argument_name in seen_logical:
            raise SpecError(f"{path}: duplicate argument {argument_name}")
        argument = Argument(argument_name, sort)
        collisions = seen_smt.intersection(argument.smt_names)
        if collisions:
            raise SpecError(
                f"{path}: flattened SMT name collision: {', '.join(collisions)}"
            )
        seen_logical.add(argument_name)
        seen_smt.update(argument.smt_names)
        arguments.append(argument)

    parameter_collisions = seen_parameters.intersection(seen_logical | seen_smt)
    if parameter_collisions:
        raise SpecError(
            f"{path}: parameter/argument name collision: "
            f"{', '.join(sorted(parameter_collisions))}"
        )

    body = data.get("body")
    if not isinstance(body, str):
        raise SpecError(f"{path}: body must be an SMT-LIB expression string")
    try:
        body = render(parse_one(body))
    except SExprError as error:
        raise SpecError(f"{path}: invalid body: {error}") from error

    return RelationSpec(
        name,
        description,
        tuple(parameters),
        parameter_constraint,
        tuple(arguments),
        body,
        path,
    )
