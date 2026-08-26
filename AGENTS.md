# Project notation and terminology

- Never change user-authored terms, names, mathematical symbols, operators,
  arrow styles, or notation unless the user explicitly asks for that specific
  change.
- Preserve distinctions between assignment, implication, logical equivalence,
  and definability exactly as written. Do not replace one with another while
  proofreading, reformatting, clarifying, or fixing compilation.
- In particular, do not replace `\leftrightharpoons` with `:=`, and do not
  replace `\longrightarrow`, `\Leftrightarrow`, or other arrows with
  `\equiv`, `\equiv_{\mathrm{def}}`, or prose equivalents.
- When notation causes a compilation error, prefer a minimal technical repair
  that preserves the rendered symbol and intended meaning. If this is not
  possible without changing notation, ask the user first.
- When reviewing a statement, report a suspected mathematical or notational
  problem instead of silently rewriting the user's notation to fix it.
- Use `$$ ... $$` for display mathematics in both Markdown and LaTeX source.
  Never introduce `\[ ... \]`.
- Do not use LaTeX notation or math delimiters in chat or console responses,
  because they are not rendered there. Write mathematical expressions in
  plain text or ASCII instead. This restriction does not apply when editing
  LaTeX source files.
- Preserve the language and terminology of the surrounding source. Do not
  silently translate, rename, normalize, or modernize them.
