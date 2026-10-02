# Sample benchmark task — rebuild `shfmt` from its binary

A single ProgramBench-style task: given only a compiled program and its
documentation, an AI agent must write a codebase from scratch that reproduces
the original's observable behavior. A hidden suite of 131 behavioral tests
scores the result.

Program under test: [`mvdan/sh`](https://github.com/mvdan/sh)'s `shfmt`, a shell
formatter, pinned at commit `9a79a445faf5243da3c26be7d745c2cb17f27823`
(BSD 3-clause).

## Why this program

- **Deterministic and pure.** Text in, text out. No network, no clocks, no TUI,
  no concurrency in the observable behavior — so no flaky tests.
- **Deep behavior over a small core.** A canonical shell formatter has to get a
  real grammar right, plus eight printer flags, five dialects and four file
  modes. Common cases are easy; the edges are not. That is where the difficulty
  comes from, rather than from volume of code or obscurity.
- **Genuine documentation.** A man page and a `--help` written for humans.
- **Clean provenance.** Permissive licence, and not one of the 201 instances in
  the public ProgramBench task set.

## Layout

```
tasks/mvdan__sh.9a79a44/
├── task.yaml          # repository, commit, language, difficulty, anti-copy hash
├── tests.json         # scored test ids, grouped into one branch
├── Dockerfile         # builds the reference, then strips the source
├── docs/TASK.md       # the agent-facing brief, including what is out of scope
├── ca/                # optional TLS trust anchors for proxied builds (empty)
└── eval/
    ├── run.sh         # harness entry point; writes eval/results.xml
    └── tests/         # the 131 behavioral tests
        ├── conftest.py
        ├── test_core_formatting.py    # default formatting (26)
        ├── test_printer_flags.py      # -i -ci -sr -bn -bl -fn -mn -kp (20)
        ├── test_parser_dialects.py    # -ln / -p / -s (29)
        ├── test_file_modes.py         # paths, -l -d -w -f (22)
        └── test_cli_errors.py         # stdin, diagnostics, exit codes (34)
scripts/
├── build_task_image.sh   # build inference or eval image
├── make_stubs.sh         # build the deliberately-wrong programs
├── gen_tests_json.py     # regenerate tests.json from a gold JUnit report
└── validate.sh           # the whole validation matrix in one command
```

## Harness contract

Taken from the ProgramBench harness rather than assumed:

- The submission is extracted into `/workspace`; its `compile.sh` must produce
  an executable at `./executable`.
- `compile.sh` runs with the network blocked, so dependencies must be vendored.
- The test branch supplies `eval/run.sh` and `eval/tests/`, is run from
  `/workspace`, and must leave a JUnit report at `eval/results.xml`.
- Test ids are `eval.tests.<module>.<test>[param]`.
- `eval_clean_hashes` in `task.yaml` is the sha256 of the reference binary; the
  harness deletes any file in a submission that matches it, so a submission
  cannot pass by shipping a copy of the reference.

Tests resolve the program under test from `PROGRAMBENCH_EXECUTABLE`, falling
back to `./executable`. That is what lets one unmodified suite run against the
reference, a stub, or a real submission.

## Build and validate

```bash
scripts/build_task_image.sh          # inference image (reference + docs present)
scripts/build_task_image.sh --eval   # eval image   (reference removed)
scripts/validate.sh                  # the validation matrix
```

Current result:

| Run | Result |
| --- | --- |
| gold (reference binary) | 131 / 131 passed |
| gold submission, built offline through `compile.sh` | 131 / 131 passed |
| stub-noop (prints nothing, exits 0) | 0 / 131 passed |
| stub-identity (echoes input unchanged) | 0 / 131 passed |

Gold at 100% means no test is defective. Both stubs at 0% mean no test can be
passed without implementing the behavior. The offline gold-submission run means
the task is solvable under the real contract.

An honest gap: the "leading model scores below 70%" bar is **not yet measured** —
that needs an agent rollout, which the authoring environment could not run.
`difficulty: hard` is an estimate. See [VALIDATION.md](VALIDATION.md) for the
reasoning, the exact command to measure it, and a write-up of the weak tests
found and fixed during authoring.

## Notes on test design

- **No self-referential assertions.** Every expectation is an absolute literal
  captured from the reference. Comparing the program against itself —
  idempotence as `fmt(fmt(x)) == fmt(x)`, or one flag spelling against another —
  is satisfied by a program that does nothing, and three such families leaked
  through the first draft. See VALIDATION.md.
- **Every input differs from its expected output.** Otherwise a passthrough
  implementation scores for free.
- **Flags assert the contrast.** Where a flag's only visible effect is to
  suppress a default rewrite (`-kp`, `-sr`, `-bl`, `-bn`), the same test asserts
  both the flag-on and flag-off results, so neither a silent nor a passthrough
  program satisfies both halves.
- **Build stamps are never asserted.** `--version` embeds the commit and varies
  with clone depth for the same commit; it is checked only for exit 0 and one
  non-empty line.
- **Scope is stated to the agent.** `docs/TASK.md` names the three subsystems
  that exist in the reference but are not scored (`--to-json`/`--from-json`,
  EditorConfig, `--detect`), so no agent budget is burnt on unscored surface.
