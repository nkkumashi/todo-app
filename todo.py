#!/usr/bin/env python3
"""Command-line todo app (SCRUM-5).

Supports two subcommands:
  add   Add a todo task.
  list  List all todo tasks.

Todos are persisted to a JSON file (``todos.json``) in the current
working directory so they survive between runs. Standard library only.
"""

import argparse
import json
import os
import sys

STORE = "todos.json"


def load_todos(path):
    """Return the list of todos from ``path``.

    A missing, empty, or invalid file is treated as an empty list.
    """
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def save_todos(path, todos):
    """Persist ``todos`` (a list) to ``path`` as JSON."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(todos, fh, indent=2)


def cmd_add(args):
    """Append a task and persist it."""
    todos = load_todos(STORE)
    todos.append(args.task)
    save_todos(STORE, todos)
    print(f"Added: {args.task}")


def cmd_list(_args):
    """Print a numbered list of todos, or a message when empty."""
    todos = load_todos(STORE)
    if not todos:
        print("No todos")
        return
    for i, text in enumerate(todos, start=1):
        print(f"{i}. {text}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="todo.py", description="A simple command-line todo app."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Add a todo task.")
    add_parser.add_argument("task", help="The task text to add.")
    add_parser.set_defaults(func=cmd_add)

    list_parser = subparsers.add_parser("list", help="List all todo tasks.")
    list_parser.set_defaults(func=cmd_list)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
