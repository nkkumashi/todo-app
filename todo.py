"""Persistence I/O and task business logic for the todo CLI.

This module owns everything that touches the JSON store and the task data
model. It has no knowledge of argument parsing, output formatting, or process
exit codes -- that boundary lives in ``cli.py`` (NFR4). Every public function
accepts the storage ``path`` as an argument so callers (including tests) can
supply an isolated location instead of the working-directory ``todos.json``.

A task is a plain ``dict`` with exactly these keys, in this order:

    task_id (int)   monotonically increasing, never reused
    text    (str)   non-empty
    status  (str)   "open" | "done"

The store is a single JSON file containing a list of such task dicts. A missing
or corrupt store is treated as an empty task list rather than an error, so a
first run or a hand-damaged file degrades gracefully instead of crashing.
"""

from __future__ import annotations

import json
import os
import tempfile

STATUS_OPEN = "open"
STATUS_DONE = "done"


def load_tasks(path: str) -> list[dict]:
    """Return the list of tasks stored at ``path``.

    A missing or corrupt store is treated as an empty task list: only
    ``FileNotFoundError``, ``json.JSONDecodeError``, and ``OSError`` are
    caught (never a bare ``except``), so genuine programming errors still
    surface. A store whose top-level JSON is not a list is also treated as
    empty rather than propagating a malformed shape downstream.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def save_tasks(path: str, tasks: list[dict]) -> None:
    """Persist ``tasks`` to ``path`` atomically.

    The list is written to a temporary file in the same directory and then
    moved onto the target path with ``os.replace``. On POSIX and Windows this
    replacement is atomic, so a reader never observes a half-written store and
    an interrupted write leaves the previous store intact.
    """
    directory = os.path.dirname(os.path.abspath(path))
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".todos-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(tasks, handle, indent=2)
            handle.write("\n")
        os.replace(temp_path, path)
    except OSError:
        # Clean up the temp file if the replace never happened; then re-raise
        # so the failure is loud rather than silently swallowed.
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def add_task(path: str, text: str) -> dict:
    """Create a new open task with ``text`` and persist it.

    ``text`` must contain non-whitespace characters; empty or whitespace-only
    input raises ``ValueError``. The new ``task_id`` is ``max(existing ids) + 1``
    so ids are monotonically increasing and never reused, even after tasks are
    completed. Returns the created task dict.
    """
    if not text or not text.strip():
        raise ValueError("Task text must not be empty.")

    tasks = load_tasks(path)
    next_id = max((task["task_id"] for task in tasks), default=0) + 1
    task = {"task_id": next_id, "text": text, "status": STATUS_OPEN}
    tasks.append(task)
    save_tasks(path, tasks)
    return task


def list_tasks(path: str) -> list[dict]:
    """Return all tasks in the store, tolerating a missing/corrupt store.

    This is a thin, intention-revealing wrapper over :func:`load_tasks`; both
    return ``[]`` when the store is absent or unreadable.
    """
    return load_tasks(path)


def complete_task(path: str, task_id: int) -> dict:
    """Mark the task with ``task_id`` as done and persist the change.

    Completing an already-done task is an idempotent no-op success that returns
    the unchanged task. An unknown ``task_id`` raises ``ValueError`` and leaves
    the store untouched. Returns the (now or already) completed task dict.
    """
    tasks = load_tasks(path)
    for task in tasks:
        if task["task_id"] == task_id:
            if task["status"] == STATUS_DONE:
                return task
            task["status"] = STATUS_DONE
            save_tasks(path, tasks)
            return task
    raise ValueError(f"No task found with task_id {task_id}.")
