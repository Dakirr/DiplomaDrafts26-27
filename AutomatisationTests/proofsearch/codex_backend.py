from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from collections.abc import Sequence
from pathlib import Path

from .spec import RelationSpec


class CodexError(RuntimeError):
    """Raised when the local Codex CLI cannot produce a candidate."""


def build_prompt(
    source: RelationSpec | Sequence[RelationSpec],
    target: RelationSpec,
    previous_attempts: list[dict[str, object]],
    *,
    max_formula_nodes: int | None = None,
) -> str:
    sources = (source,) if isinstance(source, RelationSpec) else tuple(source)
    if not sources:
        raise ValueError("at least one source relation is required")
    source_names = ", ".join(spec.name for spec in sources)
    source_calls = "\n".join(
        f"  - ({spec.name} {' '.join(argument.name for argument in spec.arguments)})"
        for spec in sources
    )
    size_rule = (
        f"- The candidate may contain at most {max_formula_nodes} syntax nodes "
        "(atoms plus applications).\n"
        if max_formula_nodes is not None
        else ""
    )
    history = json.dumps(previous_attempts, indent=2, ensure_ascii=False)
    return f"""You are synthesizing a first-order definition of one relation from certified relations.

Return one candidate formula that defines {target.name} using any of these available
relations: {source_names}. The final
response is constrained by a JSON schema; fill both fields and do not use Markdown.

AVAILABLE RELATION SEMANTICS (for reasoning only):
{json.dumps([spec.as_dict() for spec in sources], indent=2, ensure_ascii=False)}

TARGET RELATION SEMANTICS (the property to define):
{json.dumps(target.as_dict(), indent=2, ensure_ascii=False)}

RESTRICTED CANDIDATE LANGUAGE:
- A parameter without `value` is a symbolic meta-level integer. Z3 checks every
  assignment satisfying `parameter_constraint`; the same symbolic name in both
  files denotes the same global symbol.
- A parameter with `value` is fixed and local to that relation. Source and target
  may use the same fixed parameter name with different values.
- Parameters are not relation arguments and must not occur in the candidate.
- Free variables are exactly the logical arguments of {target.name}.
- Available relation call signatures are:
{source_calls}
  Use logical Point variables as single arguments. Do not expand points into coordinates.
- Allowed operators: and, or, not, =>, xor, iff, =, distinct.
- Quantify points as (exists ((z Point)) body) or (forall ((z Point)) body).
  Several binders may appear in the binder list.
- Integer literals and free Int arguments are allowed only as terms for equality,
  distinct, or arguments of an available relation.
- Forbidden: {target.name}, coordinate names such as p_x, arithmetic, order
  comparisons, unlisted relations, SMT commands, comments, strings, and prose
  inside the candidate.
- The candidate must be exactly one S-expression of sort Bool.
{size_rule}

The checker will expand Point variables to pairs of integers, assert the negation
of equivalence with {target.name}, and ask Z3 for satisfiability. An unsat result is
required. A bounded test or plausible explanation is not sufficient.

PREVIOUS FAILED ATTEMPTS AND CHECKER FEEDBACK:
{history if previous_attempts else "None. This is the first attempt."}

Produce a new candidate. Use the counterexamples to avoid repeating a failed formula.
"""


class CodexBackend:
    def __init__(
        self,
        project_root: Path,
        schema_path: Path,
        *,
        model: str | None = None,
        timeout_seconds: int = 900,
        codex_binary: str = "codex",
    ) -> None:
        self.project_root = project_root
        self.schema_path = schema_path
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.codex_binary = codex_binary
        self._auth_checked = False
        self._auth_lock = threading.Lock()

    @staticmethod
    def _chatgpt_environment() -> dict[str, str]:
        environment = os.environ.copy()
        # A per-process key can override cached ChatGPT authentication and cause
        # usage-based API billing. This project intentionally forbids that mode.
        environment.pop("OPENAI_API_KEY", None)
        environment.pop("CODEX_API_KEY", None)
        return environment

    def _assert_chatgpt_auth(self, codex: str) -> dict[str, str]:
        environment = self._chatgpt_environment()
        with self._auth_lock:
            if self._auth_checked:
                return environment
            status = subprocess.run(
                [codex, "login", "status"],
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
                env=environment,
            )
            diagnostics = "\n".join(
                value.strip()
                for value in (status.stdout, status.stderr)
                if value.strip()
            )
            if (
                status.returncode != 0
                or "logged in using chatgpt" not in diagnostics.lower()
            ):
                raise CodexError(
                    "this project requires subscription authentication, but "
                    "`codex login status` did not confirm 'Logged in using ChatGPT'. "
                    "Run `codex logout`, then `codex login` and choose ChatGPT sign-in. "
                    f"Status output: {diagnostics}"
                )
            self._auth_checked = True
        return environment

    def generate(
        self,
        prompt: str,
        output_path: Path,
        *,
        schema_path: Path | None = None,
        reasoning_effort: str | None = None,
    ) -> dict[str, str]:
        codex = shutil.which(self.codex_binary)
        if codex is None:
            raise CodexError(
                f"Codex executable {self.codex_binary!r} was not found on PATH"
            )
        environment = self._assert_chatgpt_auth(codex)
        command = [
            codex,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--output-schema",
            str(schema_path or self.schema_path),
            "--output-last-message",
            str(output_path),
            "--cd",
            str(self.project_root),
        ]
        if self.model:
            command.extend(["--model", self.model])
        if reasoning_effort is not None:
            command.extend(
                ["--config", f'model_reasoning_effort="{reasoning_effort}"']
            )
        command.append("-")
        try:
            process = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired as error:
            raise CodexError(
                f"Codex exceeded the {self.timeout_seconds}-second timeout"
            ) from error
        if process.returncode != 0:
            diagnostics = (process.stderr or process.stdout).strip()
            raise CodexError(f"Codex exited with code {process.returncode}: {diagnostics}")
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CodexError(f"Codex did not write valid structured JSON: {error}") from error
        if (
            not isinstance(data, dict)
            or set(data) != {"candidate", "explanation"}
            or not isinstance(data["candidate"], str)
            or not isinstance(data["explanation"], str)
        ):
            raise CodexError("Codex output did not match the candidate schema")
        return data
