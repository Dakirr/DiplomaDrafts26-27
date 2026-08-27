from __future__ import annotations

import argparse
import concurrent.futures
import itertools
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from .codex_backend import CodexBackend, CodexError, build_prompt
from .induction import (
    CertifiedRelation,
    InductionConfig,
    InductionStage,
    certified_relation,
    generalisation_check_stages,
    induction_stages,
    load_induction_config,
)
from .generalisation import (
    GeneralisationVerification,
    build_generalisation_prompt,
    load_candidate_outputs,
    record_failed_generalisation,
    reset_generalisation_context,
    verify_generalised_formula,
    write_generalised_formula,
)
from .latex import write_answer_markdown
from .spec import RelationSpec, SpecError, load_relation
from .verifier import validate_semantics, verify


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _prepare_output_directory(root: Path) -> Path:
    """Return an empty result directory, refusing broad destructive targets."""
    if root.exists() and root.is_symlink():
        raise ValueError("--output-dir must not be a symbolic link")
    resolved = root.expanduser().resolve()
    broad_targets = {
        Path("/").resolve(),
        Path("/tmp").resolve(),
        Path("/private/tmp").resolve(),
        Path.home().resolve(),
        PROJECT_ROOT.resolve(),
        *PROJECT_ROOT.resolve().parents,
    }
    if resolved in broad_targets:
        raise ValueError(f"refusing to clear broad output directory: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    for child in resolved.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    return resolved


def _generate_generalised_formula(
    source: RelationSpec,
    target_template: RelationSpec,
    config: InductionConfig,
    output_directory: Path,
    backend: CodexBackend,
    raw_output_path: Path,
    context_path: Path,
    *,
    timeout_ms: int,
    z3_binary: str,
) -> Path:
    observations = load_candidate_outputs(output_directory, target_template)
    if not observations:
        raise ValueError(
            f"no R_answer{{...}}.md candidates found in {output_directory}"
        )
    check_stages = generalisation_check_stages(target_template, config)
    if not check_stages:
        raise ValueError("generalisation-check bounds select no parameter tuples")
    print(
        f"Generalisation check domain: {len(check_stages)} parameter tuple(s)"
    )
    persistent_context = reset_generalisation_context(
        context_path, source, target_template
    )
    history: list[dict[str, object]] = []
    response: dict[str, str] | None = None
    verification = None
    last_generation_error: str | None = None

    def run_attempt(
        attempt: int, prompt: str
    ) -> tuple[dict[str, str], GeneralisationVerification]:
        attempt_output_path = raw_output_path.with_name(
            f"{raw_output_path.stem}-attempt-{attempt:02d}"
            f"{raw_output_path.suffix}"
        )
        attempt_response = backend.generate(
            prompt,
            attempt_output_path,
            schema_path=PROJECT_ROOT / "schemas/generalised_formula.schema.json",
            reasoning_effort=config.generalisation_reasoning_effort,
        )
        attempt_verification = verify_generalised_formula(
            attempt_response["candidate"],
            source,
            target_template,
            observations,
            config,
            timeout_ms=timeout_ms,
            z3_binary=z3_binary,
        )
        return attempt_response, attempt_verification

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=config.parallelism,
        thread_name_prefix="generalisation-attempt",
    ) as executor:
        for batch_start in range(
            1, config.generalisation_attempts + 1, config.parallelism
        ):
            batch_attempts = list(
                range(
                    batch_start,
                    min(
                        batch_start + config.parallelism,
                        config.generalisation_attempts + 1,
                    ),
                )
            )
            prompt_snapshot = build_generalisation_prompt(
                source,
                target_template,
                observations,
                config,
                history,
                persistent_context["failed_formulas"],
            )
            print(
                f"Generalisation attempts {batch_attempts[0]}-"
                f"{batch_attempts[-1]}/{config.generalisation_attempts}: running "
                f"{len(batch_attempts)} in parallel..."
            )
            futures = {
                attempt: executor.submit(
                    run_attempt,
                    attempt,
                    prompt_snapshot
                    + f"\nCURRENT PARALLEL ATTEMPT: {attempt} of "
                    f"{config.generalisation_attempts}.\n",
                )
                for attempt in batch_attempts
            }
            verified_outcome: (
                tuple[dict[str, str], GeneralisationVerification] | None
            ) = None
            for attempt in batch_attempts:
                try:
                    attempt_response, attempt_verification = futures[attempt].result()
                except CodexError as error:
                    last_generation_error = str(error)
                    history.append(
                        {"attempt": attempt, "generation_error": str(error)}
                    )
                    print(f"Generalisation attempt {attempt}: Codex error — {error}")
                    continue
                print(
                    f"Generalisation attempt {attempt}: bounded check "
                    f"{attempt_verification.passed}/"
                    f"{attempt_verification.checked} tuple(s) passed"
                )
                history.append(
                    {
                        "attempt": attempt,
                        "candidate": attempt_response["candidate"],
                        "explanation": attempt_response["explanation"],
                        "bounded_verification": attempt_verification.feedback(),
                    }
                )
                if not attempt_verification.verified:
                    persistent_context = record_failed_generalisation(
                        context_path,
                        persistent_context,
                        candidate=attempt_response["candidate"],
                        explanation=attempt_response["explanation"],
                        verification=attempt_verification,
                    )
                response = attempt_response
                verification = attempt_verification
                if attempt_verification.verified and verified_outcome is None:
                    verified_outcome = (attempt_response, attempt_verification)
            if verified_outcome is not None:
                response, verification = verified_outcome
                break
    if response is None or verification is None:
        raise CodexError(last_generation_error or "all generalisation attempts failed")
    return write_generalised_formula(
        output_directory,
        response["candidate"],
        len(observations),
        verification,
        source,
        target_template,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ask local Codex for a relation definition and verify it with Z3."
    )
    parser.add_argument("--r1", type=Path, default=PROJECT_ROOT / "input/R_1.txt")
    parser.add_argument(
        "--target", type=Path, default=PROJECT_ROOT / "input/R_target.txt"
    )
    parser.add_argument(
        "--attempts",
        type=int,
        help="Codex attempts (per induction step in induction mode).",
    )
    parser.add_argument(
        "--model",
        help="Codex model override. By default the local Codex configuration chooses.",
    )
    parser.add_argument("--solver-timeout-ms", type=int, default=30_000)
    parser.add_argument("--codex-timeout-seconds", type=int, default=900)
    parser.add_argument("--z3", default="z3", help="Z3 executable name or path")
    parser.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "output"
    )
    parser.add_argument(
        "--candidate",
        help="Verify this candidate directly without invoking Codex.",
    )
    parser.add_argument(
        "--candidate-file",
        type=Path,
        help="Verify a candidate expression read from a file without invoking Codex.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the first Codex prompt without running anything.",
    )
    parser.add_argument(
        "--induction",
        action="store_true",
        help="Prove concrete target instances in increasing parameter measure.",
    )
    parser.add_argument(
        "--generalise-only",
        action="store_true",
        help="Generate generalised_formula.md from existing output candidates only.",
    )
    parser.add_argument(
        "--induction-config",
        type=Path,
        default=PROJECT_ROOT / "input/induction.txt",
    )
    parser.add_argument(
        "--generalisation-context",
        type=Path,
        default=PROJECT_ROOT / "context/generalisation_context.json",
        help="Persistent failed-formula context passed to generalisation attempts.",
    )
    parser.add_argument("--min-parameter-value", type=int)
    parser.add_argument("--max-parameter-value", type=int)
    parser.add_argument("--min-measure", type=int)
    parser.add_argument("--max-measure", type=int)
    parser.add_argument(
        "--generalisation-attempts",
        type=int,
        help="Codex attempts for the final generalisation step.",
    )
    parser.add_argument("--max-formula-nodes", type=int)
    parser.add_argument("--parallelism", type=int)
    return parser


def _induction_config(args: argparse.Namespace) -> InductionConfig:
    config = load_induction_config(args.induction_config)
    overrides = {
        "min_parameter_value": args.min_parameter_value,
        "max_parameter_value": args.max_parameter_value,
        "min_measure": args.min_measure,
        "max_measure": args.max_measure,
        "attempts_per_step": args.attempts,
        "generalisation_attempts": args.generalisation_attempts,
        "max_formula_nodes": args.max_formula_nodes,
        "parallelism": args.parallelism,
    }
    config = replace(
        config,
        **{name: value for name, value in overrides.items() if value is not None},
    )
    if config.min_parameter_value < 0:
        raise SpecError("min_parameter_value must be nonnegative")
    if config.max_parameter_value < config.min_parameter_value:
        raise SpecError(
            "max_parameter_value must be at least min_parameter_value"
        )
    if config.min_measure < 0:
        raise SpecError("min_measure must be nonnegative")
    if config.max_measure < config.min_measure:
        raise SpecError("max_measure must be at least min_measure")
    if config.attempts_per_step < 1:
        raise SpecError("attempts_per_step must be positive")
    if config.generalisation_attempts < 1:
        raise SpecError("generalisation_attempts must be positive")
    if config.max_formula_nodes < 1:
        raise SpecError("max_formula_nodes must be positive")
    if config.parallelism < 1:
        raise SpecError("parallelism must be positive")
    return config


def _run_induction(
    args: argparse.Namespace,
    source: RelationSpec,
    target_template: RelationSpec,
    config: InductionConfig,
    direct_candidate: str | None,
) -> int:
    try:
        stages = induction_stages(target_template, config)
    except SpecError as error:
        print(f"input error: {error}", file=sys.stderr)
        return 2
    if not stages:
        print("input error: induction bounds select no parameter tuples", file=sys.stderr)
        return 2

    if args.dry_run:
        generalisation_count = (
            0
            if direct_candidate is not None
            else len(generalisation_check_stages(target_template, config))
        )
        request_count = (
            0
            if direct_candidate is not None
            else len(stages) * config.attempts_per_step
            + config.generalisation_attempts
        )
        print(
            f"Induction dry run: {len(stages)} tuple(s), at most "
            f"{request_count} Codex request(s), including generalisation."
        )
        if direct_candidate is None:
            print(
                f"Generalisation check dry run: {generalisation_count} "
                "tuple(s) will be compared with R_target by Z3."
            )
        print(
            build_prompt(
                [source],
                stages[0].target,
                [],
                max_formula_nodes=config.max_formula_nodes,
            )
        )
        return 0

    run_directory = args.output_dir
    request_count = (
        0
        if direct_candidate is not None
        else len(stages) * config.attempts_per_step
        + config.generalisation_attempts
    )
    print(f"Results: {run_directory}")
    print(
        f"Induction: {len(stages)} tuple(s), "
        f"{config.min_measure} <= measure <= {config.max_measure}, "
        f"formula nodes <= {config.max_formula_nodes}, "
        f"at most {request_count} Codex request(s) "
        "including generalisation"
    )

    backend = None
    if direct_candidate is None:
        backend = CodexBackend(
            PROJECT_ROOT,
            PROJECT_ROOT / "schemas/candidate.schema.json",
            model=args.model,
            timeout_seconds=args.codex_timeout_seconds,
        )

    certified: list[CertifiedRelation] = []
    failed = False
    with tempfile.TemporaryDirectory(prefix="proofsearch-codex-") as temporary:
        temporary_directory = Path(temporary)
        numbered_stages = list(enumerate(stages, 1))

        def run_stage(
            item: tuple[int, object],
            available_sources: list[RelationSpec],
        ) -> dict[str, object]:
            stage_number, raw_stage = item
            stage = raw_stage
            assert isinstance(stage, InductionStage)
            label = f"Stage {stage_number}/{len(stages)} {stage.label}"
            semantic_error = validate_semantics(
                available_sources, stage.target, z3_binary=args.z3
            )
            if semantic_error is not None:
                if semantic_error.startswith("parameter constraints are inconsistent"):
                    print(f"{label}: excluded by parameter_constraint")
                    return {"status": "excluded", "stage": stage}
                print(f"{label}: input error: {semantic_error}", file=sys.stderr)
                return {
                    "status": "error",
                    "stage": stage,
                    "message": semantic_error,
                }

            history: list[dict[str, object]] = []
            attempts = 1 if direct_candidate is not None else config.attempts_per_step
            for attempt in range(1, attempts + 1):
                if direct_candidate is not None:
                    response = {
                        "candidate": direct_candidate,
                        "explanation": "Supplied directly.",
                    }
                else:
                    assert backend is not None
                    print(f"{label}: attempt {attempt}/{attempts}, asking Codex...")
                    raw_output_path = temporary_directory / (
                        f"codex-{stage_number}-{attempt:02d}.json"
                    )
                    try:
                        response = backend.generate(
                            build_prompt(
                                available_sources,
                                stage.target,
                                history,
                                max_formula_nodes=config.max_formula_nodes,
                            ),
                            raw_output_path,
                        )
                    except CodexError as error:
                        print(f"{label}: Codex error: {error}", file=sys.stderr)
                        return {
                            "status": "error",
                            "stage": stage,
                            "message": str(error),
                        }

                result = verify(
                    response["candidate"],
                    available_sources,
                    stage.target,
                    timeout_ms=args.solver_timeout_ms,
                    z3_binary=args.z3,
                    max_formula_nodes=config.max_formula_nodes,
                )
                print(f"{label}: {result.status} — {result.message}")
                if result.verified:
                    return {
                        "status": "verified",
                        "stage": stage,
                        "response": response,
                        "sources": available_sources,
                    }
                history.append(
                    {
                        "candidate": response["candidate"],
                        "status": result.status,
                        "checker_message": result.message,
                        "counterexample": result.counterexample,
                    }
                )
            return {"status": "failed", "stage": stage}

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=config.parallelism,
            thread_name_prefix="proof-stage",
        ) as executor:
            for measure, grouped in itertools.groupby(
                numbered_stages, key=lambda item: item[1].measure
            ):
                batch = list(grouped)
                available_sources = [source] + [item.relation for item in certified]
                workers = min(config.parallelism, len(batch))
                print(
                    f"Measure {measure}: running {len(batch)} stage(s) with "
                    f"{workers} worker(s); {len(certified)} lower-measure "
                    "predecessor(s) available"
                )
                futures = [
                    executor.submit(run_stage, item, available_sources)
                    for item in batch
                ]
                outcomes = [future.result() for future in futures]
                for outcome in outcomes:
                    status = outcome["status"]
                    if status == "excluded":
                        continue
                    if status != "verified":
                        failed = True
                        continue
                    stage = outcome["stage"]
                    response = outcome["response"]
                    sources = outcome["sources"]
                    assert isinstance(stage, InductionStage)
                    assert isinstance(response, dict)
                    assert isinstance(sources, list)
                    candidate = response["candidate"]
                    assert isinstance(candidate, str)
                    answer_path = write_answer_markdown(
                        run_directory,
                        sources,
                        stage.target,
                        candidate,
                    )
                    certified.append(
                        certified_relation(target_template, stage, candidate)
                    )
                    print(f"Saved candidate: {answer_path.name}")

        if certified and direct_candidate is None:
            assert backend is not None
            print("Generalisation: asking Codex to infer a whole-family formula...")
            raw_output_path = temporary_directory / "generalised-formula.json"
            try:
                generalised_path = _generate_generalised_formula(
                    source,
                    target_template,
                    config,
                    run_directory,
                    backend,
                    raw_output_path,
                    args.generalisation_context,
                    timeout_ms=args.solver_timeout_ms,
                    z3_binary=args.z3,
                )
                print(f"Saved generalised conjecture: {generalised_path.name}")
            except (CodexError, OSError, ValueError) as error:
                print(
                    f"Generalisation warning: {error}. "
                    "Verified induction candidates remain valid.",
                    file=sys.stderr,
                )

    print(f"Saved {len(certified)} winning candidate(s) to {run_directory}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.attempts is not None and args.attempts < 1:
        print("error: --attempts must be positive", file=sys.stderr)
        return 2
    if args.solver_timeout_ms < 1 or args.codex_timeout_seconds < 1:
        print("error: timeouts must be positive", file=sys.stderr)
        return 2
    if args.candidate is not None and args.candidate_file is not None:
        print("error: use only one of --candidate and --candidate-file", file=sys.stderr)
        return 2
    if args.generalise_only and args.induction:
        print(
            "error: --generalise-only cannot be combined with --induction",
            file=sys.stderr,
        )
        return 2
    if args.generalise_only and (
        args.dry_run or args.candidate is not None or args.candidate_file is not None
    ):
        print(
            "error: --generalise-only cannot be combined with dry-run or candidate options",
            file=sys.stderr,
        )
        return 2

    try:
        source = load_relation(args.r1)
        target = load_relation(args.target)
    except SpecError as error:
        print(f"input error: {error}", file=sys.stderr)
        return 2
    if source.name == target.name:
        print("input error: source and target relation names must differ", file=sys.stderr)
        return 2

    if args.generalise_only:
        try:
            config = _induction_config(args)
        except SpecError as error:
            print(f"input error: {error}", file=sys.stderr)
            return 2
        output_directory = args.output_dir.expanduser().resolve()
        if not output_directory.is_dir():
            print(
                f"output error: directory does not exist: {output_directory}",
                file=sys.stderr,
            )
            return 2
        backend = CodexBackend(
            PROJECT_ROOT,
            PROJECT_ROOT / "schemas/candidate.schema.json",
            model=args.model,
            timeout_seconds=args.codex_timeout_seconds,
        )
        with tempfile.TemporaryDirectory(prefix="proofsearch-generalisation-") as temporary:
            try:
                path = _generate_generalised_formula(
                    source,
                    target,
                    config,
                    output_directory,
                    backend,
                    Path(temporary) / "generalised-formula.json",
                    args.generalisation_context,
                    timeout_ms=args.solver_timeout_ms,
                    z3_binary=args.z3,
                )
            except (CodexError, OSError, ValueError) as error:
                print(f"generalisation error: {error}", file=sys.stderr)
                return 2
        print(f"Saved generalised conjecture: {path}")
        return 0

    direct_candidate = args.candidate
    if args.candidate_file is not None:
        try:
            direct_candidate = args.candidate_file.read_text(encoding="utf-8").strip()
        except OSError as error:
            print(f"candidate file error: {error}", file=sys.stderr)
            return 2

    if args.induction:
        try:
            config = _induction_config(args)
        except SpecError as error:
            print(f"input error: {error}", file=sys.stderr)
            return 2
        if direct_candidate is None:
            try:
                check_stages = generalisation_check_stages(target, config)
            except ValueError as error:
                print(f"input error: {error}", file=sys.stderr)
                return 2
            if not check_stages:
                print(
                    "input error: generalisation-check bounds select no "
                    "parameter tuples",
                    file=sys.stderr,
                )
                return 2
        if not args.dry_run:
            try:
                args.output_dir = _prepare_output_directory(args.output_dir)
            except (OSError, ValueError) as error:
                print(f"output error: {error}", file=sys.stderr)
                return 2
        return _run_induction(args, source, target, config, direct_candidate)

    if args.dry_run:
        print(build_prompt(source, target, []))
        return 0

    try:
        output_directory = _prepare_output_directory(args.output_dir)
    except (OSError, ValueError) as error:
        print(f"output error: {error}", file=sys.stderr)
        return 2

    semantic_error = validate_semantics(source, target, z3_binary=args.z3)
    if semantic_error is not None:
        print(f"input error: {semantic_error}", file=sys.stderr)
        return 2

    attempts = args.attempts if args.attempts is not None else 5

    print(f"Results: {output_directory}")

    if direct_candidate is not None:
        response = {"candidate": direct_candidate, "explanation": "Supplied directly."}
        result = verify(
            direct_candidate,
            source,
            target,
            timeout_ms=args.solver_timeout_ms,
            z3_binary=args.z3,
        )
        print(f"Verification: {result.status} — {result.message}")
        if result.verified:
            answer_path = write_answer_markdown(
                output_directory,
                source,
                target,
                response["candidate"],
            )
            print(f"Saved candidate: {answer_path}")
            return 0
        if result.counterexample:
            print(f"Counterexample:\n{result.counterexample}")
        return 1

    backend = CodexBackend(
        PROJECT_ROOT,
        PROJECT_ROOT / "schemas/candidate.schema.json",
        model=args.model,
        timeout_seconds=args.codex_timeout_seconds,
    )
    history: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="proofsearch-codex-") as temporary:
        temporary_directory = Path(temporary)
        for attempt in range(1, attempts + 1):
            print(f"Attempt {attempt}/{attempts}: asking Codex...")
            raw_output_path = temporary_directory / f"codex-{attempt:02d}.json"
            try:
                response = backend.generate(
                    build_prompt(source, target, history), raw_output_path
                )
            except CodexError as error:
                print(f"Codex error: {error}", file=sys.stderr)
                return 2

            print(f"Candidate: {response['candidate']}")
            result = verify(
                response["candidate"],
                source,
                target,
                timeout_ms=args.solver_timeout_ms,
                z3_binary=args.z3,
            )
            print(f"Verification: {result.status} — {result.message}")
            if result.verified:
                answer_path = write_answer_markdown(
                    output_directory,
                    source,
                    target,
                    response["candidate"],
                )
                print(f"Saved candidate: {answer_path}")
                return 0

            history.append(
                {
                    "candidate": response["candidate"],
                    "status": result.status,
                    "checker_message": result.message,
                    "counterexample": result.counterexample,
                }
            )

    print("No candidate was verified.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
