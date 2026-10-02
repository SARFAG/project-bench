"""Default formatting: indentation, operator spacing, comment and blank-line handling.

Every case below changes its input, and every case also asserts that the
formatted result is a fixed point. A program that echoes its input back
unchanged therefore fails the first assertion, and one that prints nothing
fails both.
"""

import pytest

CASES = [
    ("if_oneline", "if [ x = y ]; then\necho a\nfi\n", "if [ x = y ]; then\n\techo a\nfi\n"),
    (
        "if_reflow_then_else",
        "if   [ x = y ]\nthen\n    echo a\n  else\n echo b\nfi\n",
        "if [ x = y ]; then\n\techo a\nelse\n\techo b\nfi\n",
    ),
    ("for_loop", "for i in 1 2 3; do\necho $i\ndone\n", "for i in 1 2 3; do\n\techo $i\ndone\n"),
    ("while_loop", "while read -r l; do\necho $l\ndone\n", "while read -r l; do\n\techo $l\ndone\n"),
    (
        "case_clause_spacing",
        "case $x in\na) echo a;;\nb|c) echo bc;;\n*) echo d;;\nesac\n",
        "case $x in\na) echo a ;;\nb | c) echo bc ;;\n*) echo d ;;\nesac\n",
    ),
    ("func_posix", "foo() {\necho hi\n}\n", "foo() {\n\techo hi\n}\n"),
    ("func_keyword", "function foo {\necho hi\n}\n", "function foo {\n\techo hi\n}\n"),
    ("pipeline_spacing_normalized", "a|b   |c\n", "a | b | c\n"),
    ("andor_spacing_normalized", "a&&b||c\n", "a && b || c\n"),
    ("andor_multiline_indented", "a &&\nb ||\nc\n", "a &&\n\tb ||\n\tc\n"),
    ("redirect_space_removed", "echo x > file\n", "echo x >file\n"),
    ("redirect_fd_dup_kept", "echo x > file 2>&1\n", "echo x >file 2>&1\n"),
    ("subshell_parens_tightened", "( cd /tmp && ls )\n", "(cd /tmp && ls)\n"),
    ("arith_operator_spacing", "x=$((1+2))\n", "x=$((1 + 2))\n"),
    ("quoting_preserved", "echo 'a'  \"b\"  c\n", "echo 'a' \"b\" c\n"),
    ("assignment_prefix_kept", "x=1   y=2  z=3\n", "x=1 y=2 z=3\n"),
    ("semicolon_split_to_lines", "echo a; echo b\n", "echo a\necho b\n"),
    (
        "nested_blocks_indent_per_level",
        "if true; then\nfor i in a b; do\nif false; then\necho deep\nfi\ndone\nfi\n",
        "if true; then\n\tfor i in a b; do\n\t\tif false; then\n\t\t\techo deep\n\t\tfi\n\tdone\nfi\n",
    ),
    (
        "blank_runs_collapse_to_one",
        "# top\n\n\n\necho a   # trailing\n\n\necho b\n",
        "# top\n\necho a # trailing\n\necho b\n",
    ),
    ("blank_lines_in_body_trimmed", "a() {\n\n\necho x\n\n\n}\n", "a() {\n\n\techo x\n\n}\n"),
]


@pytest.mark.parametrize(("name", "source", "expected"), CASES, ids=[c[0] for c in CASES])
def test_default_formatting_is_correct_and_stable(fmt, name, source, expected):
    assert fmt(source) == expected
    assert fmt(expected) == expected, "formatting an already-formatted program must change nothing"


def test_heredoc_body_is_not_reindented(fmt):
    """Heredoc contents are literal data: the body and terminator stay at column 0
    even when the redirect itself is indented inside a block."""
    assert fmt("if true; then\ncat   <<EOF\nhi\nEOF\nfi\n") == "if true; then\n\tcat <<EOF\nhi\nEOF\nfi\n"


def test_heredoc_at_top_level_keeps_its_body_verbatim(fmt):
    assert fmt("cat   <<EOF\nhello\nEOF\n") == "cat <<EOF\nhello\nEOF\n"


def test_trailing_comments_align_within_a_run(fmt):
    """Consecutive trailing comments are column-aligned on the widest line of the
    run, with the original padding discarded."""
    assert fmt("x=1    # a\nxyz=2  # b\n") == "x=1   # a\nxyz=2 # b\n"


def test_empty_input_yields_a_single_newline(fmt):
    assert fmt("") == "\n"


def test_trailing_newline_is_added(fmt):
    assert fmt("echo a") == "echo a\n"


def test_shebang_is_preserved_as_first_line(fmt):
    assert fmt("#!/bin/bash\nif x; then\necho a\nfi\n") == "#!/bin/bash\nif x; then\n\techo a\nfi\n"
