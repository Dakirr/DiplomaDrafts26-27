#!/bin/sh

set -eu

sh scripts/generate-source-manifest.sh
exec latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
