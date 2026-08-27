# Codex + Z3 relation-definition search

This program asks the locally authenticated Codex CLI to define `R_target`
using only `R1` and first-order logic. Every proposed definition is checked by
Z3. A result is accepted only when Z3 reports `unsat` for the negation of the
equivalence.

`codex exec` communicates with OpenAI, but its billing mode is determined by
the CLI sign-in method. This project uses the saved ChatGPT login, which gives
subscription access, rather than API-key usage billed through the OpenAI
Platform. See the [official authentication documentation](https://learn.chatgpt.com/codex/auth).

Before generating anything, the runner removes `OPENAI_API_KEY` and
`CODEX_API_KEY` from the child environment and requires `codex login status` to
report `Logged in using ChatGPT`. This prevents accidental usage-based API-key
billing.

## Requirements

- Python 3.10 or newer; no Python packages are required.
- Codex CLI installed and logged in. Check with `codex --version`.
- Z3 installed and available as `z3`. Check with `z3 --version`.

Confirm subscription authentication with:

```sh
codex login status
```

The required result is `Logged in using ChatGPT`. If necessary, run
`codex logout`, then `codex login`, and choose ChatGPT sign-in.

On a new machine, install and authenticate Codex according to the
[official Codex CLI documentation](https://developers.openai.com/codex/cli).
Z3 can be installed with a system package manager, for example
`brew install z3` on macOS.

## Run

Edit these files first:

- `input/R_1.txt`: the relation available to the synthesized formula.
- `input/R_target.txt`: the relation that Codex must define.

Then run:

```sh
make run
```

`make run` uses the induction-driven flow. The equivalent direct command is:

```sh
python3 run.py --induction
```

`make induction` is an explicit alias for the same flow:

```sh
make induction
```

Ordinary one-shot mode remains available with `python3 run.py`.

The default model comes from the local Codex configuration. An explicit model
can be selected with `--model MODEL`. This is still a Codex CLI invocation, not
an API call.

Useful commands:

```sh
make check
make dry-run
make generalise
python3 run.py --induction --dry-run
make verify-example
python3 run.py --help
```

`make dry-run` validates both inputs and prints the prompt without invoking
Codex or Z3. `make verify-example` bypasses Codex and checks the included example
candidate, which is useful for confirming the trusted checker works.

## Input format

Both `.txt` files use JSON with one convenience extension: string values may
contain raw newlines and tabs. A pre-formatter escapes those characters before
the standard JSON parser runs, so a long `body` can stay readable. A relation
has this form:

```json
{
  "format_version": 1,
  "name": "R1",
  "description": "Human-readable semantics.",
  "parameters": [
    {"name": "n", "sort": "Int"},
    {"name": "k", "sort": "Int"}
  ],
  "parameter_constraint": "(and (>= n 0) (>= k 0))",
  "arguments": [
    {"name": "p", "sort": "Point"},
    {"name": "q", "sort": "Point"}
  ],
  "body": "an SMT-LIB Boolean expression"
}
```

### Parameters versus arguments

They have different roles. For a family written informally as `D_(n,k)(p,q)`:

- `n` and `k` are **symbolic parameters**. Z3 considers every integer value
  satisfying the optional `parameter_constraint`.
- `p` and `q` are **arguments**. The equivalence must hold for every possible
  value of these arguments.

Arguments belong in `arguments`. Parameters belong in `parameters` and support
two forms:

```json
{"name": "n", "sort": "Int"}
```

This is symbolic. Z3 proves the result for every permitted `n`.

```json
{"name": "n", "sort": "Int", "value": 2}
```

This is fixed. Inside that relation, Z3 substitutes `n = 2`. A fixed parameter
is local to its relation, so the source and target may both call it `n` while
using different values.

Both forms are available by name inside the relation's semantic `body` and
`parameter_constraint`, but neither is passed to the relation in a candidate.

For example, Codex calls the symbolic relation as:

```text
(R1 p q)
```

It must not call it as `(R1 n k p q)` and cannot mention `n` or `k` directly in
the first-order candidate. `R1` implicitly depends on its declared symbolic
parameters.

A symbolic parameter name is global across the two files. If both files declare
symbolic `n`, they refer to the same integer. Different symbolic names denote
independent parameters. Fixed parameters are relation-local even when their
names match. The checker searches for one symbolic-parameter-and-argument
assignment that makes the equivalence false. An `unsat` result therefore proves
the equivalence universally for all symbolic assignments satisfying both files'
constraints, with fixed parameters already substituted.

Those rules describe ordinary one-shot mode. In `--induction` mode, every
target parameter position is instantiated at each selected integer tuple. This
also applies when the target parameter has a `value`, so the existing support
for a one-shot fixed target and the induction traversal can use the same target
file. Parameter names and declaration order remain fixed throughout traversal.

`parameter_constraint` is optional and defaults to `true`. For example:

```text
(and (>= n 0) (>= k 0) (>= n k))
```

The runner first checks that the combined constraints are satisfiable, preventing
an inconsistent assumption from producing a vacuous proof. Symbolic and fixed
integer parameters may be mixed in one relation.

### Arguments and semantic bodies

Supported argument sorts are `Point` and `Int`. An `Int` argument is an actual
input of the relation, not a family parameter. A point is an element of `Z^2`
and is flattened only inside semantic SMT-LIB bodies:

- `p` becomes the integer coordinates `p_x` and `p_y`.
- An `Int` argument such as `m` stays `m`.

For example, the semantic body for `D_(n,k)(p,q)` can use the symbolic parameters
`n`, `k` and the flattened point arguments as follows:

```text
(or
  (and (= (abs (- p_x q_x)) n)
       (= (abs (- p_y q_y)) k))
  (and (= (abs (- p_x q_x)) k)
       (= (abs (- p_y q_y)) n)))
```

The input `body` is the trusted semantic specification. It must be exactly one
SMT-LIB expression. It may be a raw multi-line JSON string; the pre-formatter
handles the line breaks. SMT-LIB comments, quoted symbols, strings, and trailing
commands are rejected. Z3 performs the final sort and syntax checking.

The target and source do not need to have the same argument signature. Their
relation names must be different. Within one relation, parameter and argument
names must be distinct.

## Candidate language

Codex does not write raw semantic SMT-LIB. It writes a smaller, coordinate-free
S-expression language:

```text
(and
  (distinct p q)
  (exists ((z Point))
    (and (R1 p z) (R1 z q))))
```

The allowed constructs are:

- calls to an explicitly available relation, such as `(R1 p q)`;
- `and`, `or`, `not`, `=>`, `xor`, and `iff`;
- `=` and `distinct`;
- `(exists ((z Point)) body)` and `(forall ((z Point)) body)`;
- target free arguments, bound Point variables, Boolean literals, and integer
  literals.

Several Point variables can be bound together:

```text
(exists ((z Point) (w Point)) body)
```

Candidates cannot use parameters, coordinates, arithmetic, order comparisons,
the target relation, unlisted relations, or raw SMT commands. In one-shot mode
only `R1` is available. Induction mode additionally lists the internal names of
certified smaller target instances in each stage prompt. Free `Int` arguments
and integer literals can only be passed to an available relation or compared
for equality/distinctness. Quantification is deliberately restricted to points
of `Z^2`.

## Verification loop

For each attempt the program:

1. sends both semantic specifications, the candidate grammar, and prior checker
   feedback to `codex exec`;
2. asks Codex for structured JSON containing one candidate and an explanation;
3. parses and type-checks the candidate using the restricted language;
4. expands each Point into two integer coordinates;
5. asks Z3 whether the target and candidate can differ;
6. accepts the candidate only on `unsat`;
7. otherwise sends the counterexample or error to the next Codex attempt.

`sat` means the formula is wrong and Z3 supplies a counterexample. `unknown`
means no proof was obtained; it is never accepted as success.

## Induction-driven traversal

Induction mode builds a finite certified proof DAG. It enumerates concrete
target parameter tuples in increasing measure, where the current measure is the
sum of parameter values. At a stage with measure `m`, Codex receives:

- the primitive relation from `input/R_1.txt`;
- every successfully certified target instance having measure strictly less
  than `m`;
- no failed, same-measure, or future target instance.

The restriction to strictly smaller measure makes cyclic dependency impossible
by construction. A successful instance is added to the available library only
after Z3 returns `unsat`. A failed stage is recorded and traversal continues,
but that instance cannot be used by later stages.

For example, at `n = 7, k = 5`, both `R_(n-1,k)` and `R_(k-1,n)` are eligible
smaller-measure dependencies if their concrete tuples were selected and
certified earlier. The latter is the ordered tuple `n = 4, k = 7`; it is never
reinterpreted by numerical proximity or displayed with swapped parameter
identity.

The bounds are configured in `input/induction.txt`:

```json
{
  "format_version": 1,
  "min_parameter_value": 0,
  "max_parameter_value": 6,
  "min_measure": 2,
  "max_measure": 6,
  "attempts_per_step": 5,
  "generalisation_attempts": 5,
  "generalisation_reasoning_effort": "low",
  "max_formula_nodes": 200,
  "parallelism": 6,
  "generalisation_check": {
    "default_min_parameter_value": 0,
    "default_max_parameter_value": 12,
    "min_measure": 2,
    "max_measure": 24,
    "parameter_overrides": {}
  }
}
```

- `min_parameter_value` and `max_parameter_value` define the inclusive domain
  used independently for every target parameter position.
- `min_measure` and `max_measure` are the inclusive lower and upper bounds on
  the sum of values in a selected tuple. For two parameters they select tuples
  satisfying `min_measure <= n + k <= max_measure`.
- Stages below `min_measure` are not synthesized and therefore are not available
  as certified predecessors. Keep `min_measure` at `0` when later stages should
  be allowed to build on the complete lower-measure base.
- `attempts_per_step` limits Codex retries separately at each tuple.
- `generalisation_attempts` independently limits the total number of Codex
  candidates tried for `generalised_formula.md`.
- `generalisation_reasoning_effort` controls how much reasoning Codex uses for
  generalisation requests only. Supported values are `minimal`, `low`, `medium`,
  `high`, and `xhigh`. Omit it to inherit the normal Codex configuration.
- `max_formula_nodes` limits the number of atoms and application nodes in one
  candidate syntax tree. Oversized candidates are rejected before Z3.
- `parallelism` limits concurrent stages within one measure. All stages in the
  batch see the same immutable set of strictly smaller certified predecessors.
  Their winners are published only after the entire measure finishes, so
  same-measure formulas can never depend on one another. It also limits the
  number of simultaneous generalisation attempts.

`generalisation_check` defines a separate finite domain used only when Z3 checks
`generalised_formula.md`. Its default minimum and maximum are inclusive and are
applied independently to every target parameter. `min_measure` and
`max_measure` then filter the sum of each tuple. These checking bounds do not
change which induction candidates are synthesized. If either checking measure
field is omitted, it inherits the corresponding induction measure bound.

Bounds for a named parameter can replace either or both defaults:

```json
"generalisation_check": {
  "default_min_parameter_value": 0,
  "default_max_parameter_value": 12,
  "min_measure": 2,
  "max_measure": 15,
  "parameter_overrides": {
    "n": {
      "min_parameter_value": 1,
      "max_parameter_value": 15
    },
    "k": {
      "max_parameter_value": 8
    }
  }
}
```

Here `n` uses `1..15`, while `k` inherits the default minimum and overrides only
its maximum, so it uses `0..8`. Override names must exactly match parameters in
`R_target.txt`. If `generalisation_check` is omitted, the checker retains the
older behavior and checks the tuples selected by the induction bounds and
measure range.

Command-line options override the file for one run:

```sh
python3 run.py --induction \
  --max-parameter-value 6 \
  --min-measure 2 \
  --max-measure 6 \
  --generalisation-attempts 8 \
  --max-formula-nodes 250 \
  --parallelism 4 \
  --attempts 6
```

With the current two-parameter bounds, 25 tuples are selected and there can be
up to 130 Codex requests: five attempts for each stage and up to five attempts
for the final generalisation. The separate current generalisation-check bounds
select 166 tuples for Z3 comparison. Run
`python3 run.py --induction --dry-run` to see the
tuple and maximum-request count before spending subscription capacity, then
reduce the bounds or attempts if appropriate.

Tuples that make `parameter_constraint` false are marked as excluded rather
than proved. The run exits successfully only when every other selected tuple is
certified.

This is bounded induction: it proves every selected concrete stage and checks
every dependency edge, but it does not by itself prove a theorem for all
unbounded parameter values. Raising the bounds extends the certified DAG.

## Results

Before every real run, the runner clears `output/`. A dry run does not clear it.
Winning candidates are written directly into `output/`; there are no timestamped
subdirectories.

The persistent files in `output/` are `R_answer{PARAMETERS}.md` candidates plus
the optional `generalised_formula.md` conjecture. Codex structured responses use
an automatically deleted temporary directory. SMT queries, logs, summaries,
and certificates are not saved in `output/`.

Failed generalisation formulas are cached separately in
`context/generalisation_context.json`. Each record contains the formula,
explanation, verification counts, and every parameter tuple where it failed,
including checker details and counterexamples when available. Repeated identical
formulas update their existing record. The file is cleared at the beginning of
every automatic or standalone generalisation, then passed to later batches in
that same generalisation run. It remains available for inspection after the run
but is never reused by the next run. Override its location with
`--generalisation-context PATH`.

The answer filename uses target parameter values in declaration order. Examples:

```text
R_answer{2,1}.md     fixed n = 2, k = 1
R_answer{n,k}.md     symbolic n, k
R_answer{n,1}.md     symbolic n, fixed k = 1
R_answer{}.md        target relation without parameters
```

The Markdown answer contains the displayed equivalence, exact candidate source,
and parameter modes. Induction mode calls the
same writer after every verified step, producing one `R_answer{...}.md` file per
certified target node in `output/`.

Inside the displayed formula, fixed stage values are converted back to parameter
expressions without permuting parameter identity or order. Each dependency
parameter is compared only with the target parameter having the same name, with
declaration position as a fallback. For example, at the stage `n = 2, k = 5`,
a dependency with fixed values `n = 1, k = 1` is displayed as `R_(n-1,k-4)`,
never as `R_(k-4,n-1)`. The filename remains concrete:
`R_answer{2,5}.md`.

An induction run writes one candidate for each successful stage:

```text
R_answer{2,5}.md
generalised_formula.md
```

After the verified stages finish, Codex receives the ordered list of successful
parameter tuples and their exact rendered candidate formulas. Coordinate bodies
from the trusted source and target specifications are intentionally omitted from
this prompt.

Codex must return a formula in a formal generalisation DSL, not raw LaTeX or
semantic coordinate arithmetic. It is explicitly instructed to prefer short
rules and minimise special cases, repeated clauses, iterator nesting, and
relation calls. The DSL provides:

- grouped `(cases (when PARAM_CONDITION FORMULA) ... (else FORMULA))`, with at
  most eight `when` branches to discourage concrete-tuple enumeration;
- parameter-only operations `+`, `-`, `*`, `abs`, `min`, `max`, `div`, `mod`,
  `pow`, comparisons, and parameter `ite`;
- bounded `bigand` and `bigor` iteration over parameter-index variables;
- the primitive relation such as `R1`;
- `(R INDEX_1 ... INDEX_M arg1 ... argN)` for an inductive call to a verified
  target-family instance with strictly smaller measure;
- Boolean operators, equality, distinctness, and Point quantifiers.

Parameter operations are accepted only in case guards, iteration bounds, and
the index positions of `R`. They are rejected in relation logic. Coordinate
names, arithmetic on points, unknown relations, same-measure `R`, future `R`,
and missing target instances are rejected syntactically or during
specialisation.

The checker specialises the proposed formula at every tuple selected by the
`generalisation_check` section of `input/induction.txt`, resolves its smaller
indexed `R` calls, and uses Z3 to compare it with the corresponding concrete
`R_target`. Failed bounded checks are returned to Codex for up to
`generalisation_attempts` attempts. Attempts run in batches of at most
`parallelism`; every attempt in a batch sees the same prior history. If the whole
batch fails, the next batch receives the combined complete in-memory log:
attempt numbers, candidates, explanations, verification counts, and bounded
failure feedback. Failed formulas and their complete failing-tuple lists are
also written to `context/generalisation_context.json` and included in later
batch prompts from the current run. The file is cleared when the next
generalisation starts. This context is never written to `output/`.
`generalised_formula.md` records the formal DSL, its LaTeX rendering, and whether
all selected tuples passed. Passing this finite domain is still not an unbounded
proof of the whole family. Generalisation failure does not invalidate the
separately verified stage candidates or change their induction status.

Generalisation can also be run separately after candidates already exist:

```sh
make generalise
```

or:

```sh
python3 run.py --generalise-only
```

This separate command reads the existing `R_answer{...}.md` files, writes or
replaces only `generalised_formula.md`, and does not clear `output/`, rerun
induction, or regenerate stage candidates. It does invoke Z3 to compare the
generalised formula at every tuple selected by `generalisation_check`. Wait
until an active induction run finishes before using it, so the generaliser sees
the complete candidate list.

## Verify a hand-written candidate

To test or replay a candidate without spending a Codex attempt:

```sh
python3 run.py --candidate \
  '(and (distinct p q) (exists ((z Point)) (and (R1 p z) (R1 z q))))'
```

For a long formula, put the single S-expression in a file and use:

```sh
python3 run.py --candidate-file candidate.txt
```

## Trust boundary and current limitations

Codex is untrusted: its formula is parsed, restricted, and independently checked.
The input semantic bodies, this checker, and Z3 are trusted. A bounded search is
not used as proof.

Z3 can return `unknown`, especially for heavily quantified formulas. Induction
mode maintains a finite library of verified target instances, but it does not
emit proof-assistant proof terms. `--solver-timeout-ms` limits one Z3 query;
`--codex-timeout-seconds` limits one generation request.
