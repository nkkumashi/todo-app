"""Command-line entry point for the todo CLI.

This module is a thin boundary layer (NFR4): it parses arguments, calls into
``todo.py`` for all business logic and persistence, formats output for the
terminal, and maps exceptions to process exit codes. It contains no task logic
and no JSON parsing of its own.

Subcommands::

    todo add <text>          add a new task
    todo list                list all tasks
    todo complete <task_id>  mark a task done

The default storage path is ``todos.json`` in the current working directory;
the logic functions in ``todo.py`` accept the path as an argument, so tests
drive :func:`main` with an isolated path instead.
"""

from __future__ import annotations

import argparse
import sys

import todo

DEFAULT_STORE = "todos.json"


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with the add/list/complete subcommands."""
    parser = argparse.ArgumentParser(prog="todo", description="A small personal todo list.")
    parser.add_argument(
        "--store",
        default=DEFAULT_STORE,
        help=f"Path to the JSON task store (default: {DEFAULT_STORE}).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a new task.")
    add_parser.add_argument("text", help="The task description.")

    subparsers.add_parser("list", help="List all tasks.")

    complete_parser = subparsers.add_parser("complete", help="Mark a task as done.")
    complete_parser.add_argument("task_id", type=int, help="The id of the task to complete.")

    return parser


def _format_task_line(task: dict) -> str:
    """Format one task as a list line, e.g. ``1  [open]  buy milk``."""
    return f"{task['task_id']}  [{task['status']}]  {task['text']}"


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code.

    Returns 0 on success. On a ``ValueError`` from the logic layer (empty task
    text, unknown ``task_id``) or any other command failure, prints a clear
    message to stderr and returns a non-zero code. ``argv`` defaults to
    ``sys.argv[1:]`` when not supplied so tests can inject arguments directly.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "add":
            task = todo.add_task(args.store, args.text)
            print(f"Added task {task['task_id']}: {task['text']}")
        elif args.command == "list":
            tasks = todo.list_tasks(args.store)
            if not tasks:
                print("No tasks.")
            else:
                for task in tasks:
                    print(_format_task_line(task))
        elif args.command == "complete":
            task = todo.complete_task(args.store, args.task_id)
            print(f"Completed task {task['task_id']}: {task['text']}")
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
