"""Unit tests for the todo CLI (stdlib ``unittest``, never pytest).

Every public function in ``todo.py`` and ``cli.main`` has at least one
happy-path test and one error-path test, per the team's per-function coverage
bar. Error paths cover the three mandated fault cases: empty/whitespace task
text, unknown ``task_id``, and a missing/corrupt store treated as an empty
list.

Test isolation is mandatory: each test builds a ``todos.json`` path inside a
``tempfile.TemporaryDirectory`` created in ``setUp`` and removed in
``tearDown``. Tests never touch the real working-directory store, so they are
order-independent and non-flaky.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import cli
import todo


class TodoTestBase(unittest.TestCase):
    """Base fixture providing an isolated temporary store path."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = os.path.join(self._tmp.name, "todos.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()


class LoadTasksTests(TodoTestBase):
    def test_round_trip_returns_saved_tasks(self) -> None:
        tasks = [{"task_id": 1, "text": "buy milk", "status": "open"}]
        todo.save_tasks(self.store, tasks)
        self.assertEqual(todo.load_tasks(self.store), tasks)

    def test_missing_file_returns_empty_list(self) -> None:
        self.assertEqual(todo.load_tasks(self.store), [])

    def test_corrupt_json_returns_empty_list(self) -> None:
        with open(self.store, "w", encoding="utf-8") as handle:
            handle.write("{ this is not valid json ]")
        self.assertEqual(todo.load_tasks(self.store), [])

    def test_non_list_json_returns_empty_list(self) -> None:
        with open(self.store, "w", encoding="utf-8") as handle:
            json.dump({"task_id": 1}, handle)
        self.assertEqual(todo.load_tasks(self.store), [])


class SaveTasksTests(TodoTestBase):
    def test_atomic_round_trip(self) -> None:
        tasks = [
            {"task_id": 1, "text": "a", "status": "open"},
            {"task_id": 2, "text": "b", "status": "done"},
        ]
        todo.save_tasks(self.store, tasks)
        with open(self.store, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle), tasks)

    def test_save_leaves_no_temp_files_behind(self) -> None:
        todo.save_tasks(self.store, [])
        leftovers = [name for name in os.listdir(self._tmp.name) if name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_save_to_bad_directory_raises(self) -> None:
        bad_path = os.path.join(self._tmp.name, "no-such-dir", "todos.json")
        with self.assertRaises(OSError):
            todo.save_tasks(bad_path, [])


class AddTaskTests(TodoTestBase):
    def test_adds_task_with_open_status_and_first_id(self) -> None:
        task = todo.add_task(self.store, "buy milk")
        self.assertEqual(task, {"task_id": 1, "text": "buy milk", "status": "open"})
        self.assertEqual(todo.load_tasks(self.store), [task])

    def test_ids_are_monotonic_and_not_reused_after_complete(self) -> None:
        first = todo.add_task(self.store, "one")
        second = todo.add_task(self.store, "two")
        todo.complete_task(self.store, second["task_id"])
        third = todo.add_task(self.store, "three")
        self.assertEqual([first["task_id"], second["task_id"], third["task_id"]], [1, 2, 3])

    def test_empty_text_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            todo.add_task(self.store, "")

    def test_whitespace_only_text_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            todo.add_task(self.store, "   \t  ")


class ListTasksTests(TodoTestBase):
    def test_lists_added_tasks(self) -> None:
        todo.add_task(self.store, "one")
        todo.add_task(self.store, "two")
        tasks = todo.list_tasks(self.store)
        self.assertEqual([task["text"] for task in tasks], ["one", "two"])

    def test_empty_store_returns_empty_list(self) -> None:
        self.assertEqual(todo.list_tasks(self.store), [])


class CompleteTaskTests(TodoTestBase):
    def test_marks_task_done_and_persists(self) -> None:
        added = todo.add_task(self.store, "buy milk")
        completed = todo.complete_task(self.store, added["task_id"])
        self.assertEqual(completed["status"], "done")
        self.assertEqual(todo.load_tasks(self.store)[0]["status"], "done")

    def test_unknown_id_raises_value_error_and_leaves_store_unchanged(self) -> None:
        todo.add_task(self.store, "buy milk")
        before = todo.load_tasks(self.store)
        with self.assertRaises(ValueError):
            todo.complete_task(self.store, 999)
        self.assertEqual(todo.load_tasks(self.store), before)

    def test_already_done_is_idempotent_no_op(self) -> None:
        added = todo.add_task(self.store, "buy milk")
        todo.complete_task(self.store, added["task_id"])
        again = todo.complete_task(self.store, added["task_id"])
        self.assertEqual(again["status"], "done")
        done_count = sum(1 for t in todo.load_tasks(self.store) if t["status"] == "done")
        self.assertEqual(done_count, 1)


class CliMainTests(TodoTestBase):
    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_add_list_complete_success_returns_zero(self) -> None:
        code, out, _ = self._run(["--store", self.store, "add", "buy milk"])
        self.assertEqual(code, 0)
        self.assertIn("1", out)

        code, out, _ = self._run(["--store", self.store, "list"])
        self.assertEqual(code, 0)
        self.assertIn("buy milk", out)
        self.assertIn("[open]", out)

        code, out, _ = self._run(["--store", self.store, "complete", "1"])
        self.assertEqual(code, 0)

        _, out, _ = self._run(["--store", self.store, "list"])
        self.assertIn("[done]", out)

    def test_empty_text_returns_nonzero_and_writes_stderr(self) -> None:
        code, _, err = self._run(["--store", self.store, "add", "   "])
        self.assertNotEqual(code, 0)
        self.assertTrue(err.strip())

    def test_unknown_id_returns_nonzero_and_writes_stderr(self) -> None:
        code, _, err = self._run(["--store", self.store, "complete", "42"])
        self.assertNotEqual(code, 0)
        self.assertTrue(err.strip())


if __name__ == "__main__":
    unittest.main()
