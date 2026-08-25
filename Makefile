LATEX_DIR := latex

.DEFAULT_GOAL := pdf

.PHONY: pdf watch clean image start stop vm-start vm-stop

pdf watch clean image start stop vm-start vm-stop:
	$(MAKE) --directory="$(LATEX_DIR)" $@
