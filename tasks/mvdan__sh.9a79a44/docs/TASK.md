# Task: rebuild `shfmt`

A compiled reference program is installed as `shfmt` (`/opt/reference/bin/shfmt`),
and its documentation is in `/opt/reference/doc/`:

| File | What it is |
| --- | --- |
| `shfmt.1.scd` | The program's man page, in scdoc source form (readable prose) |
| `shfmt-help.txt` | The program's own `--help` output |

No source code for the program is present on the image.

## What you must produce

In `/workspace`:

1. The complete source for your implementation.
2. A `compile.sh` that builds it into an executable named exactly
   `./executable` at the workspace root.

`compile.sh` runs **with the network blocked**, so vendor or inline every
dependency you need. A Go toolchain (`/usr/local/go`) and a C/C++ toolchain are
on the image; you may implement in any language the image can build.

Your `./executable` is then run against a hidden behavioral test suite that
compares its observable behavior — stdout, stderr, exit status, and the files it
writes — against the reference program's.

## Scope

The reference program is a shell formatter: it parses a shell script and prints
it back in a canonical form. Scored behavior covers:

- **Default formatting** from stdin: indentation of `if`/`for`/`while`/`case`
  and function bodies, operator and redirect spacing, arithmetic spacing,
  comment and blank-line handling, heredoc handling, statement splitting.
- **Printer flags**: `-i`, `-ci`, `-sr`, `-bn`, `-bl`, `-fn`, `-mn`, `-kp`.
- **Parser flags**: `-ln` / `-p` dialect selection (`bash`, `posix`, `mksh`,
  `zsh`, `bats`) and `-s` simplification.
- **File modes**: path arguments, `-l`, `-d`, `-w`, `-f`, the `=0`
  NUL-separated variants, recursive directory walking, and which files count as
  shell files.
- **CLI surface**: stdin handling, `--filename`, `--help`, `--version`,
  diagnostic message format, and exit statuses.

The following are present in the reference program but **not scored**, so you
need not implement them:

- `--to-json` / `--from-json` (syntax-tree serialisation)
- EditorConfig support and `--apply-ignore`
- `--detect`

Exit statuses follow the reference: `0` on success, `1` for a parse error, an
unreadable path, or a `-l`/`-d` difference, and `2` for a flag-parsing error
(which also prints the usage text).

The exact `--version` string is a build stamp and is not scored beyond exiting
`0` with one non-empty line.
