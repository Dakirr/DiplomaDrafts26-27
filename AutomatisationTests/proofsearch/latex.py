from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .sexpr import SExpr, parse_one
from .spec import Parameter, RelationSpec


def _latex_name(name: str, *, variable: bool = False) -> str:
    escaped = (
        name.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("&", r"\&")
        .replace("$", r"\$")
    )
    command = "mathit" if variable else "mathtt"
    return f"\\{command}{{{escaped}}}"


def _parameter_latex(parameter: Parameter) -> str:
    if parameter.value is not None:
        return str(parameter.value)
    return _latex_name(parameter.name, variable=True)


def _parameter_filename_part(parameter: Parameter) -> str:
    return str(parameter.value) if parameter.value is not None else parameter.name


def relation_latex_symbol(
    spec: RelationSpec, parameter_labels: list[str] | None = None
) -> str:
    base = _latex_name(spec.display_name or spec.name)
    if not spec.parameters:
        return base
    labels = parameter_labels or [
        _parameter_latex(parameter) for parameter in spec.parameters
    ]
    indices = ",".join(labels)
    return f"{base}_{{{indices}}}"


def _offset_latex(name: str, offset: int) -> str:
    base = _latex_name(name, variable=True)
    if offset == 0:
        return base
    if offset > 0:
        return f"{base}+{offset}"
    return f"{base}-{abs(offset)}"


def _target_parameter_labels(target: RelationSpec) -> list[str]:
    # A fixed target value is the concrete stage substitution. The displayed
    # theorem uses the parameter symbol; the concrete value stays in metadata
    # and in the answer filename.
    return [_latex_name(parameter.name, variable=True) for parameter in target.parameters]


def _source_parameter_labels(
    source: RelationSpec, target: RelationSpec
) -> list[str]:
    labels: list[str] = []
    target_by_name = {parameter.name: parameter for parameter in target.parameters}
    for index, parameter in enumerate(source.parameters):
        if parameter.value is None:
            labels.append(_latex_name(parameter.name, variable=True))
            continue

        # Parameter identity is never inferred from numerical proximity. Match
        # the same name first; when names differ, preserve declared position.
        target_parameter = target_by_name.get(parameter.name)
        if target_parameter is None and index < len(target.parameters):
            target_parameter = target.parameters[index]
        if target_parameter is None or target_parameter.value is None:
            labels.append(str(parameter.value))
            continue
        labels.append(
            _offset_latex(
                target_parameter.name,
                parameter.value - target_parameter.value,
            )
        )
    return labels


def answer_filename(target: RelationSpec) -> str:
    parameters = ",".join(
        _parameter_filename_part(parameter) for parameter in target.parameters
    )
    return f"R_answer{{{parameters}}}.md"


def candidate_to_latex(
    candidate: str,
    source: RelationSpec | Sequence[RelationSpec],
    target: RelationSpec | None = None,
) -> str:
    expression = parse_one(candidate)
    sources = (source,) if isinstance(source, RelationSpec) else tuple(source)
    relation_by_name = {spec.name: spec for spec in sources}

    def render(node: SExpr) -> str:
        if isinstance(node, str):
            if node == "true":
                return r"\top"
            if node == "false":
                return r"\bot"
            if node.lstrip("-").isdigit():
                return node
            return _latex_name(node, variable=True)

        operator = node[0]
        if not isinstance(operator, str):
            raise ValueError("candidate application has a non-symbol operator")
        args = node[1:]

        if operator in {"exists", "forall"}:
            binders = args[0]
            if not isinstance(binders, list):
                raise ValueError("quantifier binders must be a list")
            quantifier = r"\exists" if operator == "exists" else r"\forall"
            rendered_binders = []
            for binder in binders:
                if not isinstance(binder, list) or not isinstance(binder[0], str):
                    raise ValueError("invalid quantifier binder")
                rendered_binders.append(
                    f"{quantifier} {_latex_name(binder[0], variable=True)}"
                    r"\in\mathbb{Z}^{2}\;"
                )
            return (
                r"\left("
                + "".join(rendered_binders)
                + render(args[1])
                + r"\right)"
            )

        rendered = [render(argument) for argument in args]
        infix = {
            "and": r"\land",
            "or": r"\lor",
            "=>": r"\longrightarrow",
            "xor": r"\mathbin{\veebar}",
            "iff": r"\Leftrightarrow",
        }
        if operator in infix:
            return r"\left(" + f" {infix[operator]} ".join(rendered) + r"\right)"
        if operator == "not":
            return r"\neg " + rendered[0]
        if operator == "=":
            return r"\left(" + " = ".join(rendered) + r"\right)"
        if operator == "distinct":
            if len(rendered) == 2:
                return rf"\left({rendered[0]} \neq {rendered[1]}\right)"
            return r"\operatorname{distinct}\left(" + ",".join(rendered) + r"\right)"

        source_spec = relation_by_name.get(operator)
        relation = (
            relation_latex_symbol(
                source_spec,
                _source_parameter_labels(source_spec, target)
                if target is not None
                else None,
            )
            if source_spec is not None
            else _latex_name(operator)
        )
        return relation + r"\left(" + ",".join(rendered) + r"\right)"

    return render(expression)


def write_answer_markdown(
    run_directory: Path,
    source: RelationSpec | Sequence[RelationSpec],
    target: RelationSpec,
    candidate: str,
) -> Path:
    path = run_directory / answer_filename(target)
    target_arguments = ",".join(
        _latex_name(argument.name, variable=True) for argument in target.arguments
    )
    target_application = (
        relation_latex_symbol(target, _target_parameter_labels(target))
        + r"\left("
        + target_arguments
        + r"\right)"
    )
    formula = candidate_to_latex(candidate, source, target)

    parameter_lines = []
    for parameter in target.parameters:
        kind = (
            f"fixed at `{parameter.value}`"
            if parameter.value is not None
            else "symbolic"
        )
        parameter_lines.append(f"- `{parameter.name}`: {kind}")
    if not parameter_lines:
        parameter_lines.append("- None")

    content = "\n".join(
        [
            f"# Verified definition of `{target.name}`",
            "",
            "## Parameters",
            "",
            *parameter_lines,
            "",
            "## Verified equivalence",
            "",
            "$$",
            f"{target_application} \\Leftrightarrow {formula}",
            "$$",
            "",
            "## Candidate source",
            "",
            "```text",
            candidate,
            "```",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return path
