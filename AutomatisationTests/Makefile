PYTHON ?= python3

.PHONY: run induction generalise check dry-run verify-example

run:
	$(PYTHON) run.py --induction

induction:
	$(PYTHON) run.py --induction

generalise:
	$(PYTHON) run.py --generalise-only

check:
	$(PYTHON) -m unittest discover -v

dry-run:
	$(PYTHON) run.py --dry-run

verify-example:
	$(PYTHON) run.py --r1 tests/fixtures/R_1.txt --target tests/fixtures/R_target.txt --candidate '(R1 q p)'
