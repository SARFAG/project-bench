"""Shared fixtures for the mvdan__sh.9a79a44 behavioral test suite.

The harness builds the submission into ``./executable`` at the workspace root
and runs these tests from that root. ``PROGRAMBENCH_EXECUTABLE`` overrides the
path so the same suite can be pointed at the gold binary during task validation.
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def executable() -> str:
    path = Path(os.environ.get("PROGRAMBENCH_EXECUTABLE", "./executable")).resolve()
    if not path.is_file():
        pytest.fail(f"executable not found at {path}")
    return str(path)


@pytest.fixture
def run(executable):
    """Invoke the program. Returns CompletedProcess with text streams."""

    def _run(*args: str, stdin: str = "", cwd=None, timeout: int = 30):
        return subprocess.run(
            [executable, *args],
            input=stdin,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )

    return _run


@pytest.fixture
def fmt(run):
    """Format `source` from stdin, asserting a clean exit, and return stdout."""

    def _fmt(source: str, *flags: str) -> str:
        p = run(*flags, stdin=source)
        assert p.returncode == 0, f"exit {p.returncode}, stderr={p.stderr!r}"
        assert p.stderr == ""
        return p.stdout

    return _fmt


@pytest.fixture
def tree(tmp_path):
    """Materialize a {relative path: content} mapping and return its root."""

    def _tree(files: dict[str, str]) -> Path:
        for rel, content in files.items():
            dest = tmp_path / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        return tmp_path

    return _tree
