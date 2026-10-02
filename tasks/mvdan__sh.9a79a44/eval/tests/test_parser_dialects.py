"""Parser options: -ln / -p dialect selection and -s simplification.

Each dialect case asserts an absolute expected result on an input that needs
reformatting, so neither a silent nor a passthrough program scores here.
"""

import pytest

# (name, source, posix stderr, bash stdout) -- features gated behind a non-posix dialect.
GATED = [
    (
        "arrays",
        "a=(1   2)\n",
        "<standard input>:1:3: arrays are a bash/mksh/zsh feature; tried parsing as posix\n",
        "a=(1 2)\n",
    ),
    (
        "process_substitution",
        "echo <( x )\n",
        "<standard input>:1:6: `<` must be followed by a word\n",
        "echo <(x)\n",
    ),
]


@pytest.mark.parametrize(("name", "source", "stderr", "bash_out"), GATED, ids=[c[0] for c in GATED])
@pytest.mark.parametrize(("flag",), [("-p",), ("-ln=posix",), ("--language-dialect=posix",)])
def test_posix_dialect_rejects_bash_features(run, flag, name, source, stderr, bash_out):
    p = run(flag, stdin=source)
    assert (p.returncode, p.stdout, p.stderr) == (1, "", stderr)


@pytest.mark.parametrize(("name", "source", "stderr", "bash_out"), GATED, ids=[c[0] for c in GATED])
def test_bash_dialect_accepts_what_posix_rejects(run, name, source, stderr, bash_out):
    p = run("-ln=bash", stdin=source)
    assert (p.returncode, p.stdout, p.stderr) == (0, bash_out, "")


def test_posix_dialect_still_accepts_double_bracket_tests(fmt):
    """`[[ ]]` is parsed even under -ln=posix; only the features above are gated."""
    assert fmt("[[ $x ==   y ]]\n", "-ln=posix") == "[[ $x == y ]]\n"


def test_bats_dialect_parses_test_blocks(fmt):
    assert fmt('@test "x" {\ntrue\n}\n', "-ln=bats") == '@test "x" {\n\ttrue\n}\n'


def test_bash_dialect_rejects_bats_test_blocks(run):
    p = run("-ln=bash", stdin='@test "x" {\ntrue\n}\n')
    assert (p.returncode, p.stderr) == (1, "<standard input>:3:1: `}` can only be used to close a block\n")


@pytest.mark.parametrize(("dialect",), [("bash",), ("posix",), ("mksh",), ("zsh",), ("bats",)])
def test_every_documented_dialect_formats(run, dialect):
    p = run(f"-ln={dialect}", stdin="echo    a\n")
    assert (p.returncode, p.stdout, p.stderr) == (0, "echo a\n", "")


# (name, source, simplified, default) -- -s rewrites, contrasted with the default run.
SIMPLIFY = [
    ("unquote_test_operand", '[[ "$x"   ==   "y" ]]\n', '[[ $x == "y" ]]\n', '[[ "$x" == "y" ]]\n'),
    ("unquote_bare_rhs", '[[ "$x"   ==   y ]]\n', "[[ $x == y ]]\n", '[[ "$x" == y ]]\n'),
    ("drop_redundant_outer_parens", "echo $((  (1+2)  ))\n", "echo $((1 + 2))\n", "echo $(((1 + 2)))\n"),
    ("keep_meaningful_parens", "echo $(( (1+2)*3 ))\n", "echo $(((1 + 2) * 3))\n", "echo $(((1 + 2) * 3))\n"),
]


@pytest.mark.parametrize(("name", "source", "simplified", "default"), SIMPLIFY, ids=[c[0] for c in SIMPLIFY])
def test_simplify_rewrites(fmt, name, source, simplified, default):
    assert fmt(source, "-s") == simplified
    assert fmt(simplified, "-s") == simplified, "-s must be stable"


@pytest.mark.parametrize(("name", "source", "simplified", "default"), SIMPLIFY, ids=[c[0] for c in SIMPLIFY])
def test_default_run_does_not_simplify(fmt, name, source, simplified, default):
    assert fmt(source) == default


# (name, source, expected) -- inputs needing whitespace normalisation but no simplification.
UNTOUCHED_BY_SIMPLIFY = [
    ("test_builtin_quotes_kept", 'if [ "$x" = "y" ]; then\necho\nfi\n', 'if [ "$x" = "y" ]; then\n\techo\nfi\n'),
    ("quoted_param_braces_kept", 'echo    "${x}"\n', 'echo "${x}"\n'),
    ("unquoted_param_braces_kept", "echo    ${x}\n", "echo ${x}\n"),
    ("command_substitution_kept", "x=$(echo   hi)\n", "x=$(echo hi)\n"),
]


@pytest.mark.parametrize(
    ("name", "source", "expected"), UNTOUCHED_BY_SIMPLIFY, ids=[c[0] for c in UNTOUCHED_BY_SIMPLIFY]
)
def test_simplify_leaves_these_constructs_alone(fmt, name, source, expected):
    """-s is a narrow set of rewrites: it does not unquote `[` operands or strip
    `${}` braces, so these are only whitespace-normalised."""
    assert fmt(source, "-s") == expected


def test_unknown_dialect_is_a_usage_error(run):
    p = run("-ln=klingon", stdin="echo a\n")
    assert (p.returncode, p.stdout) == (2, "")
    assert p.stderr.startswith('invalid value "klingon" for flag -ln: unknown shell language variant: "klingon"\n')
    assert "usage: shfmt" in p.stderr
