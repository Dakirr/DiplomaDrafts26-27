from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from .candidate import CandidateError, compile_candidate
from .spec import RelationSpec


@dataclass(frozen=True)
class VerificationResult:
    status: str
    message: str
    query: str | None = None
    compiled_candidate: str | None = None
    counterexample: str | None = None

    @property
    def verified(self) -> bool:
        return self.status == "verified"

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "message": self.message,
            "compiled_candidate": self.compiled_candidate,
            "counterexample": self.counterexample,
        }


def _definition(spec: RelationSpec) -> str:
    return f"(define-fun {spec.name} ({spec.smt_formals()}) Bool {spec.smt_body()})"


def _sources(source: RelationSpec | Sequence[RelationSpec]) -> tuple[RelationSpec, ...]:
    sources = (source,) if isinstance(source, RelationSpec) else tuple(source)
    if not sources:
        raise ValueError("at least one source relation is required")
    names = [spec.name for spec in sources]
    if len(names) != len(set(names)):
        raise ValueError("source relation names must be unique")
    return sources


def _parameter_declarations(
    source: RelationSpec | Sequence[RelationSpec], target: RelationSpec
) -> str:
    sources = _sources(source)
    parameters: dict[str, str] = {}
    for spec in (*sources, target):
        for parameter in spec.parameters:
            if not parameter.is_symbolic:
                continue
            previous_sort = parameters.get(parameter.name)
            if previous_sort is not None and previous_sort != parameter.sort:
                raise ValueError(
                    f"shared parameter {parameter.name!r} has incompatible sorts"
                )
            parameters[parameter.name] = parameter.sort

    argument_names = set(target.flattened_names)
    for spec in sources:
        argument_names.update(spec.flattened_names)
    collisions = argument_names.intersection(parameters)
    if collisions:
        raise ValueError(
            "global parameter names collide with flattened relation arguments: "
            + ", ".join(sorted(collisions))
        )
    return "\n".join(
        f"(declare-const {name} {sort})" for name, sort in parameters.items()
    )


def _constraint_assertions(
    source: RelationSpec | Sequence[RelationSpec], target: RelationSpec
) -> str:
    sources = _sources(source)
    return "\n".join(
        f"(assert {spec.smt_constraint()})"
        for spec in (*sources, target)
        if spec.parameter_constraint != "true"
    )


def build_query(
    source: RelationSpec | Sequence[RelationSpec],
    target: RelationSpec,
    compiled_candidate: str,
    timeout_ms: int,
) -> str:
    sources = _sources(source)
    if target.name in {spec.name for spec in sources}:
        raise ValueError("target relation name must differ from every source relation name")
    parameter_declarations = _parameter_declarations(source, target)
    declarations = "\n".join(
        f"(declare-const {name} Int)" for name in target.flattened_names
    )
    target_call = target.smt_call()
    return "\n".join(
        part
        for part in [
            "(set-logic ALL)",
            f"(set-option :timeout {timeout_ms})",
            parameter_declarations,
            *(_definition(spec) for spec in sources),
            _definition(target),
            _constraint_assertions(source, target),
            declarations,
            f"(assert (not (= {target_call} {compiled_candidate})))",
        ]
        if part
    ) + "\n"


def _run_z3(z3: str, script: str, wall_timeout_seconds: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [z3, "-in", "-smt2"],
        input=script,
        text=True,
        capture_output=True,
        timeout=wall_timeout_seconds,
        check=False,
    )


def _status(stdout: str) -> str | None:
    return next(
        (line.strip() for line in stdout.splitlines() if line.strip() in {"sat", "unsat", "unknown"}),
        None,
    )


def verify(
    candidate: str,
    source: RelationSpec | Sequence[RelationSpec],
    target: RelationSpec,
    *,
    timeout_ms: int = 30_000,
    z3_binary: str = "z3",
    max_formula_nodes: int | None = None,
) -> VerificationResult:
    try:
        compiled = compile_candidate(
            candidate, source, target, max_nodes=max_formula_nodes
        )
    except CandidateError as error:
        return VerificationResult("invalid", str(error))

    z3 = shutil.which(z3_binary)
    if z3 is None:
        return VerificationResult(
            "error",
            f"Z3 executable {z3_binary!r} was not found on PATH",
            compiled_candidate=compiled,
        )

    try:
        query = build_query(source, target, compiled, timeout_ms)
    except ValueError as error:
        return VerificationResult("error", str(error), compiled_candidate=compiled)
    wall_timeout = max(5.0, timeout_ms / 1000 + 5.0)
    try:
        process = _run_z3(z3, query + "(check-sat)\n", wall_timeout)
    except subprocess.TimeoutExpired:
        return VerificationResult(
            "unknown",
            "Z3 exceeded the external wall-clock timeout",
            query + "(check-sat)\n",
            compiled,
        )

    status = _status(process.stdout)
    diagnostics = "\n".join(
        value.strip() for value in (process.stdout, process.stderr) if value.strip()
    )
    replay_query = query + "(check-sat)\n"
    if status == "unsat":
        return VerificationResult(
            "verified",
            "Z3 returned unsat for the negated equivalence",
            replay_query,
            compiled,
        )
    if status == "sat":
        if target.flattened_names:
            values = " ".join(target.flattened_names)
            model_process = _run_z3(
                z3,
                query + f"(check-sat)\n(get-value ({values}))\n",
                wall_timeout,
            )
            counterexample = model_process.stdout.strip()
        else:
            counterexample = "sat (the counterexample is the empty assignment)"
        return VerificationResult(
            "counterexample",
            "the proposed formula is not equivalent to the target",
            replay_query,
            compiled,
            counterexample,
        )
    if status == "unknown":
        reason_process = _run_z3(
            z3, query + "(check-sat)\n(get-info :reason-unknown)\n", wall_timeout
        )
        reason = reason_process.stdout.strip() or diagnostics
        return VerificationResult(
            "unknown",
            f"Z3 could not decide the query: {reason}",
            replay_query,
            compiled,
        )
    return VerificationResult(
        "error",
        f"Z3 did not return sat, unsat, or unknown. Output:\n{diagnostics}",
        replay_query,
        compiled,
    )


def validate_semantics(
    source: RelationSpec | Sequence[RelationSpec],
    target: RelationSpec,
    *,
    z3_binary: str = "z3",
) -> str | None:
    """Return an error message if Z3 rejects either trusted semantic body."""
    z3 = shutil.which(z3_binary)
    if z3 is None:
        return f"Z3 executable {z3_binary!r} was not found on PATH"
    try:
        sources = _sources(source)
        if target.name in {spec.name for spec in sources}:
            return "target relation name must differ from every source relation name"
        declarations = _parameter_declarations(source, target)
    except ValueError as error:
        return str(error)
    script = "\n".join(
        part
        for part in [
            "(set-logic ALL)",
            declarations,
            *(_definition(spec) for spec in sources),
            _definition(target),
            _constraint_assertions(source, target),
            "(check-sat)",
        ]
        if part
    ) + "\n"
    try:
        process = _run_z3(z3, script, 15.0)
    except subprocess.TimeoutExpired:
        return "Z3 timed out while checking the input relation definitions"
    status = _status(process.stdout)
    if process.returncode == 0 and status == "sat":
        return None
    diagnostics = "\n".join(
        value.strip() for value in (process.stdout, process.stderr) if value.strip()
    )
    if status == "unsat":
        return "parameter constraints are inconsistent; they have no model"
    return f"Z3 rejected the input relation definitions:\n{diagnostics}"


def z3_version(z3_binary: str = "z3") -> str:
    z3 = shutil.which(z3_binary)
    if z3 is None:
        return "not found"
    process = subprocess.run(
        [z3, "--version"], text=True, capture_output=True, timeout=10, check=False
    )
    return (process.stdout or process.stderr).strip()
