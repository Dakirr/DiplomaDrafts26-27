#!/bin/sh

set -eu

sh scripts/generate-source-manifest.sh

monitor_sources() {
    while :; do
        sleep 1
        sh scripts/generate-source-manifest.sh
    done
}

monitor_sources &
monitor_pid=$!
trap 'kill "$monitor_pid" 2>/dev/null || true' EXIT INT TERM

latexmk -pdf -pvc -view=none -interaction=nonstopmode -halt-on-error main.tex
