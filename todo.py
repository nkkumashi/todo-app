#!/usr/bin/env python3
"""A simple command-line todo app.

Two commands, backed by a local JSON file (``./todos.json``):

    python todo.py add "buy milk"     # add a task
    python todo.py list               # list all tasks

Tasks persist across runs. Standard library only (no third-party deps).

Implements the AI-DLC requirements for the "Command-Line Todo App" intent
(FR1-FR4, NFR1-NFR3). Exit code is 0 on success and non-zero on any error,
so the tool is scriptable and testable (NFR2).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# FR3.1 - single JSON file in the current working directory.
STORE_FILENAME = "todos.json"


class TodoError(Exception):
    """A user-facing error; the CLI turns this into a message + non-zero exit."""


def _store_path() -> str:
    return os.path.join(os.getcwd(), STORE_FILENAME)


def load_tasks(path: str) -> list[str]:
    """Return the list of task strings from ``path``.

    A missing file is treated as an empty list (FR2.3 / FR3.3). A file that
    exists but is unreadable or not valid JSON raises TodoError WITHOUT the
    caller overwriting it (FR4.1).
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise TodoError(
            f"Error: could not read task file '{path}': {exc}. "
            f"The file was left unchanged."
        ) from exc
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise TodoError(
            f"Error: task file '{path}' is not in the expected format "
            f"(a JSON list of task strings). The file was left unchanged."
        )
    return data


def save_tasks(path: str, tasks: list[str]) -> None:
    """Persist ``tasks`` to ``path`` as a JSON list (FR1.2, FR3.2)."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(tasks, handle, indent=2)
        handle.write("\n")


def add_task(task_text: str, path: str | None = None) -> str:
    """Append ``task_text`` and persist. Returns the confirmation message.

    Raises TodoError if the task text is empty/whitespace (FR1.4).
    """
    if task_text is None or not task_text.strip():
        raise TodoError(
            'Error: task text is required. Usage: todo add "<task>"'
        )
    path = path or _store_path()
    tasks = load_tasks(path)          # may raise TodoError (FR4.1)
    tasks.append(task_text)           # FR1.3 - append, don't discard
    save_tasks(path, tasks)
    return f'Added: "{task_text}"'


def format_task_list(tasks: list[str]) -> str:
    """Render tasks per FR2.2 / FR2.3."""
    if not tasks:
        return "No tasks yet."       # FR2.3
    # FR2.2 - numbered, one per line, in insertion order.
    return "\n".join(f"{i}. {text}" for i, text in enumerate(tasks, start=1))


def list_tasks(path: str | None = None) -> str:
    """Return the rendered task list (or the empty-state message)."""
    path = path or _store_path()
    tasks = load_tasks(path)          # may raise TodoError (FR4.1)
    return format_task_list(tasks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="todo",
        description="A simple command-line todo app (add and list tasks).",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="{add,list}")

    add_parser = subparsers.add_parser("add", help="Add a task.")
    add_parser.add_argument("task", help='The task text, e.g. "buy milk".')

    subparsers.add_parser("list", help="List all tasks.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code (NFR2)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return 2

    try:
        if args.command == "add":
            print(add_task(args.task))
        elif args.command == "list":
            print(list_tasks())
        else:  # pragma: no cover - argparse restricts the choices
            parser.print_help(sys.stderr)
            return 2
    except TodoError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
