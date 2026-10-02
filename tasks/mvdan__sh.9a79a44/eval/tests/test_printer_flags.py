"""Printer options: -i, -ci, -sr, -bn, -bl, -fn, -mn, -kp.

Flag tests assert the flag-on result against an absolute expected value, and
where a flag's only visible effect is to *suppress* a default rewrite, the same
test also asserts the flag-off result, so neither a silent nor a passthrough
program can satisfy both halves.
"""

import pytest

NESTED = "if true; then\nfor i in a b; do\necho $i\ndone\nfi\n"
CASE = "case $x in\na) echo a;;\nesac\n"
FUNC = "foo() {\necho hi\n}\n"
BLOCKS = "if true; then\necho a\nfi\nfor i in 1; do\necho $i\ndone\nwhile x; do\necho y\ndone\n"


@pytest.mark.parametrize(
    ("width", "expected"),
    [
        (2, "if true; then\n  for i in a b; do\n    echo $i\n  done\nfi\n"),
        (4, "if true; then\n    for i in a b; do\n        echo $i\n    done\nfi\n"),
        (8, "if true; then\n        for i in a b; do\n                echo $i\n        done\nfi\n"),
    ],
)
def test_indent_width_uses_spaces(fmt, width, expected):
    assert fmt(NESTED, "-i", str(width)) == expected


def test_indent_zero_means_tabs(fmt):
    assert fmt(NESTED, "-i", "0") == "if true; then\n\tfor i in a b; do\n\t\techo $i\n\tdone\nfi\n"


@pytest.mark.parametrize(("flag",), [("-i=2",), ("--indent=2",)])
def test_indent_accepts_equals_and_long_forms(fmt, flag):
    assert fmt(NESTED, flag) == "if true; then\n  for i in a b; do\n    echo $i\n  done\nfi\n"


def test_glued_indent_value_is_not_a_supported_form(run):
    """Values must be separate or `=`-joined; `-i2` is an undefined flag."""
    p = run("-i2", stdin=NESTED)
    assert (p.returncode, p.stdout) == (2, "")
    assert p.stderr.startswith("flag provided but not defined: -i2\n")


def test_case_indent(fmt):
    assert fmt(CASE, "-ci") == "case $x in\n\ta) echo a ;;\nesac\n"
    assert fmt(CASE) == "case $x in\na) echo a ;;\nesac\n", "cases are flush with `case` by default"


def test_case_indent_combines_with_indent_width(fmt):
    assert fmt(CASE, "-ci", "-i", "2") == "case $x in\n  a) echo a ;;\nesac\n"


def test_space_redirects(fmt):
    assert fmt("echo x >file\n", "-sr") == "echo x > file\n"
    assert fmt("echo x > file\n") == "echo x >file\n", "the space is removed by default"


def test_space_redirects_leaves_fd_dup_alone(fmt):
    assert fmt("echo x >file 2>&1\n", "-sr") == "echo x > file 2>&1\n"


def test_binary_next_line_rewrites_continuation(fmt):
    """-bn moves the operator to the start of the next line, which requires an
    explicit backslash continuation on the preceding line."""
    assert fmt("a &&\nb\n", "-bn") == "a \\\n\t&& b\n"
    assert fmt("a &&\nb\n") == "a &&\n\tb\n", "by default the operator stays on the first line"


def test_binary_next_line_leaves_single_line_alone(fmt):
    assert fmt("a&&b&&c\n", "-bn") == "a && b && c\n"


def test_block_next_line_moves_then_and_do(fmt):
    expected = "if true\nthen\n\techo a\nfi\nfor i in 1\ndo\n\techo $i\ndone\nwhile x\ndo\n\techo y\ndone\n"
    assert fmt(BLOCKS, "-bl") == expected


def test_block_next_line_moves_function_brace(fmt):
    assert fmt(FUNC, "-bl") == "foo()\n{\n\techo hi\n}\n"
    assert fmt(FUNC) == "foo() {\n\techo hi\n}\n", "the brace stays on the signature line by default"


def test_func_next_line_is_the_deprecated_alias_for_brace_placement(fmt):
    assert fmt(FUNC, "-fn") == "foo()\n{\n\techo hi\n}\n"


def test_keep_padding_preserves_original_alignment(fmt):
    """-kp suppresses the default realignment of trailing comments, leaving the
    author's own column padding byte-for-byte."""
    source = "echo  a\nx=1    # c\nxyz=2  # d\n"
    assert fmt(source, "-kp") == source
    assert fmt(source) == "echo a\nx=1   # c\nxyz=2 # d\n", "padding is recomputed by default"


def test_minify_drops_comments_and_uses_semicolons(fmt):
    assert fmt("if true; then\n# comment\necho a\nfi\n", "-mn") == "if true;then\necho a\nfi\n"


def test_minify_removes_indentation(fmt):
    assert fmt(NESTED, "-mn") == "if true;then\nfor i in a b;do\necho $i\ndone\nfi\n"


def test_minify_implies_simplify(fmt):
    """-mn implies -s, so redundant arithmetic parens are dropped even without -s."""
    assert fmt("echo $((  (1+2)  ))\n", "-mn") == "echo $((1+2))\n"
