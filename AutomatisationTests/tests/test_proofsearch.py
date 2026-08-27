from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from proofsearch.candidate import CandidateError, compile_candidate
from proofsearch.codex_backend import CodexBackend
from proofsearch.generalisation import (
    GeneralisationVerification,
    verify_generalised_formula,
    write_generalised_formula,
)
from proofsearch.induction import (
    GeneralisationCheckConfig,
    InductionConfig,
    ParameterBounds,
    certified_relation,
    generalisation_check_stages,
    induction_stages,
    load_induction_config,
)
from proofsearch.latex import answer_filename, candidate_to_latex, write_answer_markdown
from proofsearch.runner import main
from proofsearch.sexpr import SExprError, parse_one
from proofsearch.spec import (
    Argument,
    Parameter,
    RelationSpec,
    SpecError,
    load_relation,
    preformat_json,
)
from proofsearch.verifier import validate_semantics, verify


ROOT = Path(__file__).resolve().parent.parent
R1 = load_relation(ROOT / "tests/fixtures/R_1.txt")
TARGET = load_relation(ROOT / "tests/fixtures/R_target.txt")
CORRECT = "(R1 q p)"
FIXED_R1 = load_relation(ROOT / "tests/fixtures/R_1_fixed.txt")
FIXED_TARGET = load_relation(ROOT / "tests/fixtures/R_target_fixed.txt")
FIXED_CORRECT = "(and (distinct p q) (exists ((z Point)) (and (R1 p z) (R1 z q))))"


def indexed_relation(name: str, n: int, k: int) -> RelationSpec:
    return RelationSpec(
        name=name,
        description="Test indexed relation.",
        parameters=(Parameter("n", "Int", n), Parameter("k", "Int", k)),
        parameter_constraint="true",
        arguments=(Argument("p", "Point"), Argument("q", "Point")),
        body="true",
        path=Path("test"),
    )


class SExpressionTests(unittest.TestCase):
    def test_preformats_multiline_json_strings(self) -> None:
        formatted = preformat_json('{"body": "\n  (and true true)\n"}')
        self.assertEqual(formatted, '{"body": "\\n  (and true true)\\n"}')

    def test_rejects_trailing_command(self) -> None:
        with self.assertRaises(SExprError):
            parse_one("(R1 p q) (assert false)")

    def test_rejects_comments(self) -> None:
        with self.assertRaises(SExprError):
            parse_one("(R1 p q) ; hidden text")

    def test_loads_project_multiline_inputs(self) -> None:
        source = load_relation(ROOT / "input/R_1.txt")
        target = load_relation(ROOT / "input/R_target.txt")
        self.assertEqual(source.name, "R1")
        self.assertEqual([item.name for item in target.parameters], ["n", "k"])


class CandidateTests(unittest.TestCase):
    def test_parameters_are_not_relation_arguments(self) -> None:
        self.assertEqual([(item.name, item.sort) for item in R1.parameters], [("d", "Int")])
        self.assertIsNone(R1.parameters[0].value)
        self.assertEqual([item.name for item in R1.arguments], ["p", "q"])
        self.assertEqual(R1.parameter_constraint, "(>= d 0)")

    def test_fixed_parameter_has_local_value(self) -> None:
        self.assertEqual(FIXED_R1.parameters[0].value, 1)
        self.assertIn("(let ((d 1))", FIXED_R1.smt_body())
        self.assertIn("(let ((d 2))", FIXED_TARGET.smt_body())

    def test_compiles_point_quantifier(self) -> None:
        compiled = compile_candidate("(exists ((z Point)) (R1 p z))", R1, TARGET)
        self.assertIn("(exists ((z_x Int) (z_y Int))", compiled)
        self.assertIn("(R1 p_x p_y z_x z_y)", compiled)

    def test_rejects_coordinate_access(self) -> None:
        with self.assertRaises(CandidateError):
            compile_candidate("(= p_x q_x)", R1, TARGET)

    def test_rejects_target_relation(self) -> None:
        with self.assertRaises(CandidateError):
            compile_candidate("(R_target p q)", R1, TARGET)

    def test_rejects_parameter_in_candidate(self) -> None:
        with self.assertRaises(CandidateError):
            compile_candidate("(= d 1)", R1, TARGET)

    def test_accepts_any_explicitly_available_certified_relation(self) -> None:
        predecessor = indexed_relation("R_target__n_1__k_1", 1, 1)
        compiled = compile_candidate(
            "(R_target__n_1__k_1 p q)", [R1, predecessor], TARGET
        )
        self.assertIn("(R_target__n_1__k_1", compiled)

    def test_enforces_formula_node_limit(self) -> None:
        with self.assertRaises(CandidateError):
            compile_candidate("(and true true)", R1, TARGET, max_nodes=2)


class CodexBackendTests(unittest.TestCase):
    def test_passes_per_request_reasoning_effort_to_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_path = root / "response.json"
            schema_path = root / "schema.json"
            observed_command: list[str] = []

            def run(command: list[str], **_kwargs: object) -> SimpleNamespace:
                observed_command.extend(command)
                output_path.write_text(
                    json.dumps({"candidate": "true", "explanation": "test"}),
                    encoding="utf-8",
                )
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            backend = CodexBackend(root, schema_path)
            with (
                patch("proofsearch.codex_backend.shutil.which", return_value="codex"),
                patch.object(backend, "_assert_chatgpt_auth", return_value={}),
                patch("proofsearch.codex_backend.subprocess.run", side_effect=run),
            ):
                backend.generate("prompt", output_path, reasoning_effort="low")

        option_index = observed_command.index("--config")
        self.assertEqual(
            observed_command[option_index : option_index + 2],
            ["--config", 'model_reasoning_effort="low"'],
        )


class InductionTraversalTests(unittest.TestCase):
    def test_fixed_target_values_do_not_disable_traversal(self) -> None:
        target = indexed_relation("R_target", 7, 5)
        stages = induction_stages(
            target,
            InductionConfig(max_parameter_value=7, max_measure=12),
        )
        values = {stage.values for stage in stages}
        self.assertIn((7, 5), values)
        self.assertIn((4, 7), values)
        self.assertLess(
            next(stage.measure for stage in stages if stage.values == (4, 7)),
            next(stage.measure for stage in stages if stage.values == (7, 5)),
        )

    def test_min_measure_excludes_lower_stages(self) -> None:
        target = indexed_relation("R_target", 2, 2)
        stages = induction_stages(
            target,
            InductionConfig(
                max_parameter_value=2,
                min_measure=2,
                max_measure=3,
            ),
        )
        self.assertEqual(
            [stage.values for stage in stages],
            [(0, 2), (1, 1), (2, 0), (1, 2), (2, 1)],
        )

    def test_generalisation_check_uses_named_parameter_overrides(self) -> None:
        target = indexed_relation("R_target", 2, 2)
        config = InductionConfig(
            min_measure=0,
            max_measure=0,
            generalisation_check=GeneralisationCheckConfig(
                default_min_parameter_value=0,
                default_max_parameter_value=2,
                min_measure=3,
                max_measure=3,
                parameter_overrides={
                    "n": ParameterBounds(1, 2),
                },
            ),
        )
        self.assertEqual(
            [stage.values for stage in generalisation_check_stages(target, config)],
            [(1, 2), (2, 1)],
        )

    def test_generalisation_check_rejects_unknown_parameter_override(self) -> None:
        target = indexed_relation("R_target", 2, 2)
        config = InductionConfig(
            generalisation_check=GeneralisationCheckConfig(
                default_min_parameter_value=0,
                default_max_parameter_value=1,
                min_measure=0,
                max_measure=2,
                parameter_overrides={"unknown": ParameterBounds(0, 1)},
            )
        )
        with self.assertRaisesRegex(SpecError, "unknown"):
            generalisation_check_stages(target, config)

    def test_loads_partial_named_generalisation_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "induction.txt"
            path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "generalisation_check": {
                            "default_min_parameter_value": -2,
                            "default_max_parameter_value": 7,
                            "min_measure": -1,
                            "max_measure": 4,
                            "parameter_overrides": {
                                "n": {"max_parameter_value": 3}
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            check = load_induction_config(path).generalisation_check
        self.assertIsNotNone(check)
        assert check is not None
        self.assertEqual(check.parameter_overrides["n"], ParameterBounds(-2, 3))
        self.assertEqual((check.min_measure, check.max_measure), (-1, 4))

    def test_loads_generalisation_reasoning_effort(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "induction.txt"
            path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "generalisation_reasoning_effort": "low",
                    }
                ),
                encoding="utf-8",
            )
            config = load_induction_config(path)
        self.assertEqual(config.generalisation_reasoning_effort, "low")

    def test_rejects_unknown_generalisation_reasoning_effort(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "induction.txt"
            path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "generalisation_reasoning_effort": "very-high",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SpecError, "generalisation_reasoning_effort"
            ):
                load_induction_config(path)


class LatexTests(unittest.TestCase):
    def test_fixed_parameter_answer_filename(self) -> None:
        self.assertEqual(answer_filename(FIXED_TARGET), "R_answer{2}.md")

    def test_symbolic_parameter_answer_filename(self) -> None:
        self.assertEqual(answer_filename(TARGET), "R_answer{d}.md")

    def test_renders_quantified_candidate(self) -> None:
        rendered = candidate_to_latex(
            "(exists ((z Point)) (and (R1 p z) (distinct z q)))", R1
        )
        self.assertIn(r"\exists \mathit{z}\in\mathbb{Z}^{2}", rendered)
        self.assertIn(r"\land", rendered)
        self.assertIn(r"\neq", rendered)

    def test_reconstructs_direct_predecessor_indices(self) -> None:
        target = indexed_relation("R_target", 5, 2)
        predecessor = indexed_relation("R", 4, 2)
        rendered = candidate_to_latex("(R p q)", predecessor, target)
        self.assertIn(r"_{\mathit{n}-1,\mathit{k}}", rendered)

    def test_never_swaps_parameter_identity_by_value(self) -> None:
        target = indexed_relation("R_target", 2, 5)
        predecessor = indexed_relation("R", 1, 1)
        rendered = candidate_to_latex("(R p q)", predecessor, target)
        self.assertIn(r"_{\mathit{n}-1,\mathit{k}-4}", rendered)
        self.assertNotIn(r"_{\mathit{k}-4,\mathit{n}-1}", rendered)

    def test_alias_is_rendered_as_target_family_with_fixed_parameter_order(self) -> None:
        target = indexed_relation("R_target", 2, 5)
        predecessor_stage = induction_stages(
            indexed_relation("R_target", 2, 5),
            InductionConfig(max_parameter_value=1, max_measure=2),
        )[-1]
        predecessor = certified_relation(
            target, predecessor_stage, "true"
        ).relation
        rendered = candidate_to_latex(
            f"({predecessor.name} p q)", [predecessor], target
        )
        self.assertIn(r"\mathtt{R\_target}_{\mathit{n}-1,\mathit{k}-4}", rendered)

    def test_target_filename_stays_concrete(self) -> None:
        self.assertEqual(answer_filename(indexed_relation("R_target", 5, 2)), "R_answer{5,2}.md")

    def test_writes_display_math_with_exact_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = write_answer_markdown(
                Path(temporary), FIXED_R1, FIXED_TARGET, FIXED_CORRECT
            )
            text = path.read_text(encoding="utf-8")
            self.assertEqual(path.name, "R_answer{2}.md")
            self.assertIn("$$", text)
            self.assertNotIn(r"\[", text)
            self.assertIn(FIXED_CORRECT, text)
            self.assertIn(r"\mathtt{R\_target}_{\mathit{d}}", text)
            self.assertIn(r"\mathtt{R1}_{\mathit{d}-1}", text)
            self.assertNotIn("## Explanation", text)
            self.assertNotIn("## Verification", text)

    def test_writes_unverified_generalised_formula(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            verification = GeneralisationVerification(
                verified=False,
                checked=2,
                passed=1,
                excluded=0,
                failures=(
                    {
                        "parameters": {"d": 1},
                        "message": "counterexample",
                    },
                ),
            )
            path = write_generalised_formula(
                Path(temporary),
                "(cases (when (= d 0) (R1 q p)) (else (R1 q p)))",
                7,
                verification,
                R1,
                TARGET,
            )
            text = path.read_text(encoding="utf-8")
            self.assertEqual(path.name, "generalised_formula.md")
            self.assertIn("Bounded verification did not pass", text)
            self.assertIn(r"\begin{cases}", text)
            self.assertIn("$$", text)
            self.assertNotIn(r"\[", text)


@unittest.skipUnless(shutil.which("z3"), "Z3 is not installed")
class VerifierTests(unittest.TestCase):
    def test_accepts_input_semantics(self) -> None:
        self.assertIsNone(validate_semantics(R1, TARGET))

    def test_proves_symbolic_parameter_equivalence(self) -> None:
        result = verify(CORRECT, R1, TARGET, timeout_ms=10_000)
        self.assertEqual(result.status, "verified", result.message)
        self.assertIn("(declare-const d Int)", result.query or "")
        self.assertIn("(assert (>= d 0))", result.query or "")

    def test_proves_with_different_local_fixed_values(self) -> None:
        result = verify(FIXED_CORRECT, FIXED_R1, FIXED_TARGET, timeout_ms=10_000)
        self.assertEqual(result.status, "verified", result.message)
        self.assertNotIn("(declare-const d Int)", result.query or "")
        self.assertIn("(let ((d 1))", result.query or "")
        self.assertIn("(let ((d 2))", result.query or "")

    def test_returns_counterexample_for_bad_definition(self) -> None:
        result = verify("(distinct p q)", R1, TARGET, timeout_ms=10_000)
        self.assertEqual(result.status, "counterexample", result.message)
        self.assertIsNotNone(result.counterexample)

    def test_proves_using_a_certified_relation_alias(self) -> None:
        predecessor = RelationSpec(
            name="R_previous",
            description="Certified alias.",
            parameters=R1.parameters,
            parameter_constraint=R1.parameter_constraint,
            arguments=R1.arguments,
            body=R1.body,
            path=Path("test"),
            display_name="R_target",
        )
        result = verify("(R_previous q p)", [R1, predecessor], TARGET)
        self.assertEqual(result.status, "verified", result.message)

    def test_generalisation_checks_every_selected_parameter_tuple(self) -> None:
        base = RelationSpec(
            name="Base",
            description="Test base relation.",
            parameters=(),
            parameter_constraint="true",
            arguments=(Argument("p", "Point"), Argument("q", "Point")),
            body="(= p_x q_x)",
            path=Path("test"),
        )
        family = RelationSpec(
            name="R_target",
            description="Test family.",
            parameters=(Parameter("d", "Int"),),
            parameter_constraint="true",
            arguments=base.arguments,
            body=base.body,
            path=Path("test"),
        )
        result = verify_generalised_formula(
            "(cases (when (= d 0) (Base p q)) (else (Base p q)))",
            base,
            family,
            [],
            InductionConfig(
                max_parameter_value=0,
                max_measure=0,
                generalisation_check=GeneralisationCheckConfig(
                    default_min_parameter_value=0,
                    default_max_parameter_value=0,
                    min_measure=2,
                    max_measure=4,
                    parameter_overrides={"d": ParameterBounds(2, 4)},
                ),
            ),
        )
        self.assertTrue(result.verified, result.failures)
        self.assertEqual(result.checked, 3)
        self.assertEqual(result.passed, 3)

    def test_generalisation_forbids_arithmetic_on_logical_values(self) -> None:
        result = verify_generalised_formula(
            "(= (abs (- p q)) d)",
            R1,
            TARGET,
            [],
            InductionConfig(max_parameter_value=0, max_measure=0),
        )
        self.assertFalse(result.verified)
        self.assertEqual(result.failures[0]["status"], "invalid")


@unittest.skipUnless(shutil.which("z3"), "Z3 is not installed")
class InductionRunnerTests(unittest.TestCase):
    def test_builds_certified_dag_and_saves_every_winner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_path = root / "R_1.txt"
            target_path = root / "R_target.txt"
            config_path = root / "induction.txt"
            context_path = root / "generalisation_context.json"
            output_path = root / "output"
            output_path.mkdir()
            (output_path / "old-log.json").write_text("stale", encoding="utf-8")
            (output_path / "old-run").mkdir()
            (output_path / "old-run" / "proof.smt2").write_text(
                "stale", encoding="utf-8"
            )
            source_path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "name": "Base",
                        "parameters": [],
                        "arguments": [
                            {"name": "p", "sort": "Point"},
                            {"name": "q", "sort": "Point"},
                        ],
                        "body": "(= p_x q_x)",
                    }
                ),
                encoding="utf-8",
            )
            target_path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "name": "R_target",
                        "parameters": [
                            {"name": "n", "sort": "Int", "value": 1},
                            {"name": "k", "sort": "Int", "value": 1},
                        ],
                        "arguments": [
                            {"name": "p", "sort": "Point"},
                            {"name": "q", "sort": "Point"},
                        ],
                        "body": "(= p_x q_x)",
                    }
                ),
                encoding="utf-8",
            )
            config_path.write_text(
                json.dumps(
                    {
                        "format_version": 1,
                        "min_parameter_value": 0,
                        "max_parameter_value": 1,
                        "min_measure": 0,
                        "max_measure": 1,
                        "attempts_per_step": 2,
                        "generalisation_attempts": 3,
                        "generalisation_reasoning_effort": "low",
                        "max_formula_nodes": 20,
                        "parallelism": 2,
                    }
                ),
                encoding="utf-8",
            )

            same_measure_barrier = threading.Barrier(2)
            generalisation_barrier = threading.Barrier(2)

            def generate(
                _backend,
                prompt: str,
                output_path: Path,
                *,
                schema_path: Path | None = None,
                reasoning_effort: str | None = None,
            ) -> dict[str, str]:
                if "GENERALISATION TASK" in prompt:
                    self.assertEqual(reasoning_effort, "low")
                    if "CURRENT PARALLEL ATTEMPT: 3 of 3" in prompt:
                        self.assertIn(
                            '"candidate": "(distinct p q)"', prompt
                        )
                        response = {
                            "candidate": (
                                "(cases (when (= (+ n k) 0) (Base p q)) "
                                "(else (R 0 0 p q)))"
                            ),
                            "explanation": "Observed finite pattern.",
                        }
                    else:
                        generalisation_barrier.wait(timeout=5)
                        response = {
                            "candidate": "(distinct p q)",
                            "explanation": "A deliberately failing attempt.",
                        }
                elif "R_target__n_0__k_0" in prompt:
                    self.assertIsNone(reasoning_effort)
                    same_measure_barrier.wait(timeout=5)
                    response = {
                        "candidate": "(R_target__n_0__k_0 p q)",
                        "explanation": "Use the certified predecessor.",
                    }
                else:
                    self.assertIsNone(reasoning_effort)
                    response = {
                        "candidate": "(Base p q)",
                        "explanation": "Base case.",
                    }
                output_path.write_text(json.dumps(response), encoding="utf-8")
                return response

            with patch("proofsearch.runner.CodexBackend.generate", new=generate):
                status = main(
                    [
                        "--induction",
                        "--r1",
                        str(source_path),
                        "--target",
                        str(target_path),
                        "--induction-config",
                        str(config_path),
                        "--generalisation-context",
                        str(context_path),
                        "--output-dir",
                        str(output_path),
                    ]
                )
                stale_context = json.loads(
                    context_path.read_text(encoding="utf-8")
                )
                stale_context["failed_formulas"].append(
                    {"candidate": "stale-from-previous-generalisation"}
                )
                context_path.write_text(
                    json.dumps(stale_context), encoding="utf-8"
                )
                separate_status = main(
                    [
                        "--generalise-only",
                        "--r1",
                        str(source_path),
                        "--target",
                        str(target_path),
                        "--induction-config",
                        str(config_path),
                        "--generalisation-context",
                        str(context_path),
                        "--output-dir",
                        str(output_path),
                    ]
                )
            self.assertEqual(status, 0)
            self.assertEqual(separate_status, 0)
            self.assertEqual(
                sorted(path.name for path in output_path.iterdir()),
                [
                    "R_answer{0,0}.md",
                    "R_answer{0,1}.md",
                    "R_answer{1,0}.md",
                    "generalised_formula.md",
                ],
            )
            answer = (output_path / "R_answer{1,0}.md").read_text(encoding="utf-8")
            self.assertIn(
                r"\mathtt{R\_target}_{\mathit{n}-1,\mathit{k}}",
                answer,
            )
            generalized = (output_path / "generalised_formula.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Bounded verification passed", generalized)
            learned = json.loads(context_path.read_text(encoding="utf-8"))
            self.assertEqual(
                learned["failed_formulas"][0]["candidate"], "(distinct p q)"
            )
            self.assertEqual(len(learned["failed_formulas"]), 1)
            self.assertTrue(learned["failed_formulas"][0]["failures"])


if __name__ == "__main__":
    unittest.main()
