"""Path arguments and the file-oriented modes: -l, -d, -w, -f, directory walking."""

import pytest

UNFORMATTED = "if x; then\necho a\nfi\n"
FORMATTED = "if x; then\n\techo a\nfi\n"

# A small tree exercising extension matching, shebang detection and recursion.
TREE = {
    "bad.sh": UNFORMATTED,
    "good.sh": FORMATTED,
    "sub/nested.sh": "echo b;echo c\n",
    "noext": "#!/bin/bash\necho hi;echo there\n",
    "readme.md": "nope {{{\n",
    "plain.txt": "echo x\n",
}


def test_path_argument_formats_to_stdout(run, tree):
    root = tree({"bad.sh": UNFORMATTED})
    p = run("bad.sh", cwd=root)
    assert (p.returncode, p.stdout) == (0, FORMATTED)
    assert (root / "bad.sh").read_text() == UNFORMATTED, "stdout mode must not modify the file"


def test_list_names_only_unformatted_files_and_exits_1(run, tree):
    root = tree({"bad.sh": UNFORMATTED})
    p = run("-l", "bad.sh", cwd=root)
    assert (p.returncode, p.stdout, p.stderr) == (1, "bad.sh\n", "")


def test_list_distinguishes_formatted_from_unformatted(run, tree):
    """Both halves must hold: a stub that always prints nothing and exits 0
    satisfies the formatted case but not the unformatted one."""
    root = tree({"good.sh": FORMATTED, "bad.sh": UNFORMATTED})
    formatted = run("-l", "good.sh", cwd=root)
    assert (formatted.returncode, formatted.stdout, formatted.stderr) == (0, "", "")
    unformatted = run("-l", "bad.sh", cwd=root)
    assert (unformatted.returncode, unformatted.stdout, unformatted.stderr) == (1, "bad.sh\n", "")


def test_list_over_several_paths_reports_only_the_offenders(run, tree):
    root = tree(TREE)
    p = run("-l", "bad.sh", "good.sh", cwd=root)
    assert (p.returncode, p.stdout) == (1, "bad.sh\n")


def test_list_walks_directories_in_lexical_order(run, tree):
    root = tree(TREE)
    p = run("-l", ".", cwd=root)
    assert (p.returncode, p.stdout) == (1, "bad.sh\nnoext\nsub/nested.sh\n")


def test_list_null_separated(run, tree):
    root = tree(TREE)
    p = run("-l=0", ".", cwd=root)
    assert (p.returncode, p.stdout) == (1, "bad.sh\0noext\0sub/nested.sh\0")


def test_diff_emits_a_unified_diff_and_exits_1(run, tree):
    root = tree({"bad.sh": UNFORMATTED})
    p = run("-d", "bad.sh", cwd=root)
    expected = (
        "diff bad.sh.orig bad.sh\n"
        "--- bad.sh.orig\n"
        "+++ bad.sh\n"
        "@@ -1,3 +1,3 @@\n"
        " if x; then\n"
        "-echo a\n"
        "+\techo a\n"
        " fi\n"
    )
    assert (p.returncode, p.stdout, p.stderr) == (1, expected, "")


def test_diff_distinguishes_formatted_from_unformatted(run, tree):
    root = tree({"good.sh": FORMATTED, "bad.sh": UNFORMATTED})
    formatted = run("-d", "good.sh", cwd=root)
    assert (formatted.returncode, formatted.stdout, formatted.stderr) == (0, "", "")
    unformatted = run("-d", "bad.sh", cwd=root)
    assert unformatted.returncode == 1 and unformatted.stdout.startswith("diff bad.sh.orig bad.sh\n")


def test_diff_does_not_modify_the_file(run, tree):
    root = tree({"bad.sh": UNFORMATTED})
    assert run("-d", "bad.sh", cwd=root).returncode == 1
    assert (root / "bad.sh").read_text() == UNFORMATTED


def test_write_rewrites_in_place_and_is_silent(run, tree):
    root = tree({"bad.sh": UNFORMATTED})
    p = run("-w", "bad.sh", cwd=root)
    assert (p.returncode, p.stdout, p.stderr) == (0, "", "")
    assert (root / "bad.sh").read_text() == FORMATTED


def test_write_is_idempotent(run, tree):
    root = tree({"bad.sh": UNFORMATTED})
    assert run("-w", "bad.sh", cwd=root).returncode == 0
    assert run("-w", "bad.sh", cwd=root).returncode == 0
    assert (root / "bad.sh").read_text() == FORMATTED


def test_write_rewrites_only_what_needs_it(run, tree):
    root = tree({"good.sh": FORMATTED, "bad.sh": UNFORMATTED})
    assert run("-w", "good.sh", "bad.sh", cwd=root).returncode == 0
    assert (root / "good.sh").read_text() == FORMATTED, "already-formatted file must stay byte-identical"
    assert (root / "bad.sh").read_text() == FORMATTED, "unformatted file must be rewritten"


def test_write_over_a_directory_fixes_every_shell_file(run, tree):
    root = tree(TREE)
    assert run("-w", ".", cwd=root).returncode == 0
    assert (root / "bad.sh").read_text() == FORMATTED
    assert (root / "sub/nested.sh").read_text() == "echo b\necho c\n"
    assert (root / "noext").read_text() == "#!/bin/bash\necho hi\necho there\n"
    assert (root / "readme.md").read_text() == "nope {{{\n", "non-shell files must be left alone"
    assert (root / "plain.txt").read_text() == "echo x\n"


def test_find_lists_every_shell_file_including_formatted_ones(run, tree):
    root = tree(TREE)
    p = run("-f", ".", cwd=root)
    assert (p.returncode, p.stdout) == (0, "bad.sh\ngood.sh\nnoext\nsub/nested.sh\n")


def test_find_detects_shell_scripts_by_shebang_when_there_is_no_extension(run, tree):
    root = tree({"noext": "#!/bin/bash\necho hi\n", "plain.txt": "echo x\n"})
    p = run("-f", ".", cwd=root)
    assert (p.returncode, p.stdout) == (0, "noext\n")


def test_find_null_separated(run, tree):
    root = tree(TREE)
    p = run("-f=0", ".", cwd=root)
    assert (p.returncode, p.stdout) == (0, "bad.sh\0good.sh\0noext\0sub/nested.sh\0")


def test_find_on_an_explicit_file_echoes_it(run, tree):
    root = tree(TREE)
    p = run("-f", "bad.sh", cwd=root)
    assert (p.returncode, p.stdout) == (0, "bad.sh\n")


def test_diff_over_a_directory_concatenates_per_file_diffs(run, tree):
    root = tree(TREE)
    p = run("-d", ".", cwd=root)
    assert p.returncode == 1
    assert p.stdout.count("diff ") == 3
    assert p.stdout.startswith("diff bad.sh.orig bad.sh\n")
    assert "diff sub/nested.sh.orig sub/nested.sh\n" in p.stdout


@pytest.mark.parametrize(("flags",), [(("-l",),), (("-d",),), (("-w",),), ((),)])
def test_missing_path_is_reported_on_stderr_with_exit_1(run, tree, flags):
    root = tree({"good.sh": FORMATTED})
    p = run(*flags, "missing.sh", cwd=root)
    assert (p.returncode, p.stdout) == (1, "")
    assert p.stderr == "lstat missing.sh: no such file or directory\n"
