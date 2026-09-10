# todo-app

A small, local, single-user personal todo list CLI, implemented in Python 3.11+
using the **standard library only** (no runtime dependencies). Tasks are stored
in a single `todos.json` file in the working directory.

## Layout

- `todo.py` — persistence I/O and task business logic (public functions take the
  storage path as an argument).
- `cli.py` — argparse entry point; parses args, calls `todo.py`, formats output,
  and maps errors to exit codes.
- `test_todo.py` — `unittest` test suite.

## Install

No runtime install is required — run it directly with Python 3.11+:

```bash
python cli.py --help
```

Optionally install the console-script entry point (`todo`) and the pinned
dev/CI tooling (`black`, `ruff`, `coverage`):

```bash
python -m pip install -e ".[dev]"
```

## Usage

```bash
# Add a task
python cli.py add "buy milk"

# List all tasks (format: <id>  [status]  <text>)
python cli.py list
# 1  [open]  buy milk

# Complete a task by id
python cli.py complete 1
```

By default the store is `todos.json` in the current directory; pass
`--store <path>` to use a different file. Invalid input (empty task text, an
unknown task id) prints a clear message to stderr and exits non-zero; successful
commands exit 0. A missing or corrupt `todos.json` is treated as an empty list
rather than crashing.

## Tests

The suite uses the Python standard-library `unittest` framework (not pytest):

```bash
python -m unittest test_todo -v
```

Report-only coverage (does not gate):

```bash
python -m coverage run -m unittest test_todo && python -m coverage report -m
```

## Continuous integration

Every pull request into `main` runs a blocking GitHub Actions quality gate
(`.github/workflows/ci.yml`): `ruff check` (including the `S` security rules),
`black --check`, and the `unittest` suite must all pass before merge. Coverage
runs report-only and does not gate.
