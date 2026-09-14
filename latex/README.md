# LaTeX workspace

The workspace supports Docker Desktop and Colima. Docker commands use your
active Docker context (or the `DOCKER_HOST` / `DOCKER_CONTEXT` environment
variables).

With Docker Desktop, start the application and ensure its Docker connection is
active. No Colima installation is needed.

With Colima, start the VM explicitly the first time:

```sh
make vm-start
```

This starts an `aarch64` VM using Apple's Virtualization framework and Rosetta,
with `8.8.8.8` and `1.1.1.1` as DNS servers and address-based networking
enabled. Subsequent builds automatically start Colima if the `colima` context
is selected and its daemon is unavailable.

Build `main.tex`:

```sh
make pdf
```

The result is written to `main.pdf`. The first build also creates the local
Docker image and can take several minutes. All build commands check that Docker
is available before building the image.

Start continuous rebuilding in a background container:

```sh
make start
```

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

Stop the background watch container:

```sh
make stop
```

To also stop the Colima virtual machine, run `make vm-stop`. The `vm-start` and
`vm-stop` targets are specific to Colima; with Docker Desktop, manage the engine
through the application.
