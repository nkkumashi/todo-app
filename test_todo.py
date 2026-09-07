"""Tests for the command-line todo app.

One test per functional requirement plus the error/edge cases (FR1.4, FR2.3,
FR4.1), per NFR3. Standard library only (unittest). Each test uses an isolated
temp file so tests never touch a real ./todos.json.
"""

import json
import os
import tempfile
import unittest

import todo


class TodoStorageTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.path)  # start with the file NOT existing

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    # FR1.1 / FR1.2 / FR1.3 - add persists and appends
    def test_add_persists_task(self):
        todo.add_task("buy milk", self.path)
        self.assertEqual(todo.load_tasks(self.path), ["buy milk"])

    def test_add_appends_without_discarding(self):
        todo.add_task("buy milk", self.path)
        todo.add_task("call bank", self.path)
        self.assertEqual(todo.load_tasks(self.path), ["buy milk", "call bank"])

    # FR3.3 - add creates the file when missing
    def test_add_creates_file_when_missing(self):
        self.assertFalse(os.path.exists(self.path))
        todo.add_task("first", self.path)
        self.assertTrue(os.path.exists(self.path))

    # FR3.1 / FR3.2 - stored as a JSON list
    def test_storage_is_json_list(self):
        todo.add_task("buy milk", self.path)
        with open(self.path, encoding="utf-8") as handle:
            data = json.load(handle)
        self.assertEqual(data, ["buy milk"])

    # FR1.4 - empty task text is rejected
    def test_add_empty_text_raises(self):
        with self.assertRaises(todo.TodoError):
            todo.add_task("   ", self.path)

    # FR2.2 - populated list is numbered, one per line, insertion order
    def test_list_numbered_in_order(self):
        todo.add_task("buy milk", self.path)
        todo.add_task("call bank", self.path)
        self.assertEqual(
            todo.list_tasks(self.path), "1. buy milk\n2. call bank"
        )

    # FR2.3 - empty / missing shows friendly message
    def test_list_empty_message(self):
        self.assertEqual(todo.list_tasks(self.path), "No tasks yet.")

    # FR4.1 - corrupt file: error, and file is NOT overwritten
    def test_corrupt_file_raises_and_preserved(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write("{ this is not valid json ]")
        with self.assertRaises(todo.TodoError):
            todo.load_tasks(self.path)
        # file left unchanged
        with open(self.path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "{ this is not valid json ]")

    def test_wrong_shape_json_raises(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"not": "a list"}, handle)
        with self.assertRaises(todo.TodoError):
            todo.load_tasks(self.path)


class TodoCliTests(unittest.TestCase):
    """Exercise main() for deterministic exit codes (NFR2)."""

    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)  # so ./todos.json is isolated

    def tearDown(self):
        os.chdir(self.cwd)

    def test_cli_add_then_list(self):
        self.assertEqual(todo.main(["add", "buy milk"]), 0)
        self.assertEqual(todo.main(["list"]), 0)

    def test_cli_list_empty_exit_zero(self):
        self.assertEqual(todo.main(["list"]), 0)

    def test_cli_no_command_exit_two(self):
        self.assertEqual(todo.main([]), 2)


if __name__ == "__main__":
    unittest.main()
