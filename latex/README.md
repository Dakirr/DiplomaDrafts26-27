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

Continuously rebuild after edits:

```sh
make watch
```

Remove generated LaTeX files:

```sh
make clean
```

When you no longer need the virtual machine, stop it with:

```sh
make stop
```
