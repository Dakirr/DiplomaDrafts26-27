from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


SExpr: TypeAlias = str | list["SExpr"]


class SExprError(ValueError):
    """Raised when text is not exactly one safe S-expression."""


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    for char in text:
        if char in ';"|':
            raise SExprError(
                "comments, strings, and quoted SMT-LIB symbols are not supported"
            )
        if char.isspace():
            flush()
        elif char in "()":
            flush()
            tokens.append(char)
        else:
            current.append(char)
    flush()
    return tokens


def parse_one(text: str) -> SExpr:
    """Parse exactly one S-expression and reject command-injection suffixes."""
    tokens = _tokenize(text)
    if not tokens:
        raise SExprError("expected one S-expression, found empty input")

    def parse_at(index: int) -> tuple[SExpr, int]:
        if index >= len(tokens):
            raise SExprError("unexpected end of input")
        token = tokens[index]
        if token == ")":
            raise SExprError("unexpected ')'")
        if token != "(":
            return token, index + 1

        result: list[SExpr] = []
        index += 1
        while True:
            if index >= len(tokens):
                raise SExprError("missing ')'")
            if tokens[index] == ")":
                if not result:
                    raise SExprError("empty lists are not valid expressions here")
                return result, index + 1
            item, index = parse_at(index)
            result.append(item)

    expression, next_index = parse_at(0)
    if next_index != len(tokens):
        raise SExprError("expected exactly one expression; trailing input is forbidden")
    return expression


def render(expression: SExpr) -> str:
    if isinstance(expression, str):
        return expression
    return "(" + " ".join(render(item) for item in expression) + ")"


def node_count(expression: SExpr) -> int:
    """Count atoms and application nodes in an S-expression."""
    if isinstance(expression, str):
        return 1
    return 1 + sum(node_count(item) for item in expression)
