#!/bin/sh

set -eu

manifest=.src-files.tex
temporary=.src-files.tex.tmp

{
    printf '%% Generated automatically; do not edit.\n'
    if [ -d src ]; then
        find src -type f -name '*.tex' -print \
            | LC_ALL=C sort \
            | while IFS= read -r source; do
                printf '\\input{%s}\n' "$source"
            done
    fi
} > "$temporary"

if [ -f "$manifest" ] && cmp -s "$temporary" "$manifest"; then
    rm -f "$temporary"
else
    mv "$temporary" "$manifest"
fi
