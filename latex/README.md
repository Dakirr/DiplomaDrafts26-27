# LaTeX workspace

The workspace uses Docker through Colima; Docker Desktop is not required.

Start Colima explicitly if it is not already running:

```sh
make start
```

This starts an `aarch64` VM using Apple's Virtualization framework and Rosetta,
with `8.8.8.8` and `1.1.1.1` as DNS servers and address-based networking
enabled.

Build `main.tex`:

```sh
make pdf
```

The result is written to `main.pdf`. The first build also creates the local
Docker image and can take several minutes. Colima is configured separately to
start automatically when you log in to macOS.

## Split source files

Place additional `.tex` files anywhere under `src/`. They are included in
`main.tex` automatically before the bibliography, in lexicographic path order.
Use numeric prefixes when order matters, for example:

```text
src/
├── 10-introduction.tex
├── 20-main-result.tex
└── 30-proof.tex
```

Source files should contain document content only; keep `\documentclass`, the
preamble, and `\begin{document}`/`\end{document}` in `main.tex`.

Continuously rebuild after edits:

```sh
make watch
```

The watch process also detects `.tex` files added to or removed from `src/`.

Remove generated LaTeX files:

```sh
make clean
```

When you no longer need the virtual machine, stop it with:

```sh
make stop
```
