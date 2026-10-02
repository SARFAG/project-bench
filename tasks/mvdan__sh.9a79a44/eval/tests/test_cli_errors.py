"""CLI surface: stdin handling, diagnostics, and exit codes.

Exit-code contract observed from the reference program:
  0  success (including --help and --version)
  1  a runtime problem: parse error, unreadable path, or a -l/-d difference
  2  a flag-parsing problem, which also prints the usage text
"""

import pytest

PARSE_ERRORS = [
    ("then_without_body", "if true; then\n", "<standard input>:1:10: `then` must be followed by a statement list\n"),
    ("unclosed_quote", "echo 'abc\n", "<standard input>:1:6: reached EOF without closing quote `'`\n"),
    ("stray_closing_brace", "}\n", "<standard input>:1:1: `}` can only be used to close a block\n"),
    (
        "paren_in_command",
        "echo )\n",
        "<standard input>:1:6: a command can only contain words and redirects; encountered `)`\n",
    ),
    (
        "bad_param_expansion_operator",
        "echo ${x\n",
        '<standard input>:1:9: not a valid parameter expansion operator: "\\n"\n',
    ),
    (
        "unclosed_param_expansion",
        "echo ${x y\n",
        "<standard input>:1:9: not a valid parameter expansion operator: ` `\n",
    ),
]


@pytest.mark.parametrize(("name", "source", "stderr"), PARSE_ERRORS, ids=[c[0] for c in PARSE_ERRORS])
def test_parse_errors_report_position_on_stderr_and_exit_1(run, name, source, stderr):
    p = run(stdin=source)
    assert (p.returncode, p.stdout, p.stderr) == (1, "", stderr)


def test_unterminated_heredoc_is_accepted_and_terminated(run):
    """The parser tolerates a heredoc that runs to EOF and the printer emits the
    missing terminator rather than failing."""
    p = run(stdin="cat <<EOF\nhi\n")
    assert (p.returncode, p.stdout, p.stderr) == (0, "cat <<EOF\nhi\nEOF\n", "")


def test_no_arguments_reads_stdin(fmt):
    assert fmt("echo a;echo b\n") == "echo a\necho b\n"


def test_dash_reads_stdin(run):
    p = run("-", stdin="echo a;echo b\n")
    assert (p.returncode, p.stdout) == (0, "echo a\necho b\n")


def test_filename_replaces_standard_input_in_diagnostics(run):
    p = run("--filename=x.sh", stdin="if true; then\n")
    assert (p.returncode, p.stderr) == (1, "x.sh:1:10: `then` must be followed by a statement list\n")


def test_filename_is_rejected_alongside_a_path_argument(run, tree):
    root = tree({"a.sh": "echo a\n"})
    p = run("--filename=x.sh", "a.sh", cwd=root)
    assert (p.returncode, p.stdout, p.stderr) == (1, "", "-filename can only be used with stdin\n")


@pytest.mark.parametrize(("flag",), [("-h",), ("--help",)])
def test_help_goes_to_stderr_and_exits_0(run, flag):
    p = run(flag)
    assert (p.returncode, p.stdout) == (0, "")
    assert p.stderr.startswith("usage: shfmt [flags] [path ...]\n")


@pytest.mark.parametrize(
    ("section",),
    [("Parser options:",), ("Printer options:",), ("Utilities:",)],
)
def test_help_documents_each_option_group(run, section):
    assert section in run("--help").stderr


@pytest.mark.parametrize(
    ("option",),
    [
        ("--version",),
        ("--list",),
        ("--write",),
        ("--diff",),
        ("--filename",),
        ("--language-dialect",),
        ("--simplify",),
        ("--indent",),
        ("--binary-next-line",),
        ("--case-indent",),
        ("--space-redirects",),
        ("--keep-padding",),
        ("--block-next-line",),
        ("--minify",),
        ("--find",),
    ],
)
def test_help_lists_every_supported_long_option(run, option):
    assert option in run("--help").stderr


def test_version_exits_0_with_a_single_nonempty_line(run):
    """The exact version string is a build stamp and is deliberately not asserted."""
    p = run("--version")
    assert p.returncode == 0
    assert p.stdout.strip() != ""
    assert len(p.stdout.strip().splitlines()) == 1


def test_undefined_flag_exits_2_with_usage(run):
    p = run("--nope", stdin="echo a\n")
    assert (p.returncode, p.stdout) == (2, "")
    assert p.stderr.startswith("flag provided but not defined: -nope\n")
    assert "usage: shfmt" in p.stderr


def test_non_numeric_indent_exits_2_with_usage(run):
    p = run("-i=-1", stdin="echo a\n")
    assert (p.returncode, p.stdout) == (2, "")
    assert p.stderr.startswith('invalid value "-1" for flag -i: parse error\n')
    assert "usage: shfmt" in p.stderr
