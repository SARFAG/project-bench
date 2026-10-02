# Sample benchmark task — rebuild `shfmt` from its binary

A single ProgramBench-style task: given only a compiled program and its
documentation, an AI agent must write a codebase from scratch that reproduces
the original's observable behavior. A hidden suite of 112 behavioral tests
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
├── Dockerfile         # builds reference/src, then strips the source
├── docs/TASK.md       # reviewer-facing description of the workspace and scored scope
├── agent_docs/        # the ONLY documentation the agent sees (man page + --help)
├── reference/
│   ├── src/           # reference source at the pinned commit (BSD-3), unmodified
│   └── bin/shfmt      # compiled reference executable; sha256 = eval_clean_hashes
├── ca/                # optional TLS trust anchors for proxied builds (empty)
└── eval/
    ├── run.sh         # harness entry point; writes eval/results.xml
    └── tests/         # the 112 behavioral tests
        ├── conftest.py
        ├── test_core_formatting.py    # default formatting (26)
        ├── test_printer_flags.py      # -i -ci -sr -bn -bl -fn -mn -kp (20)
        ├── test_parser_dialects.py    # -ln / -p / -s (29)
        ├── test_file_modes.py         # paths, -l -d -w -f (22)
        └── test_cli_errors.py         # stdin, diagnostics, exit codes (15)
scripts/
├── build_task_image.sh   # build the task image (programbench/...:task_cleanroom_v6)
├── run_agent.sh          # N independent agent runs + scoring (difficulty calibration)
├── score_runs.py         # per-run and mean score, as `programbench info` computes it
├── make_stubs.sh         # build the deliberately-wrong programs
├── make_gold_submission.sh  # build the reference solution tarball from reference/src
├── gen_tests_json.py     # regenerate tests.json from a gold JUnit report
├── validate.sh           # the validation matrix, run through this repo's own flow
└── programbench_eval.sh  # the same submissions scored by ProgramBench's real CLI
```

## Image contract (what the official agent runner requires)

Learned by running the real mini-swe-agent ProgramBench runner against the image
rather than assumed. The image must have:

- a user named `agent` (the runner starts containers with `--user agent`);
- the reference at `/workspace/executable` and docs under `/workspace/docs`, because
  the agent prompt says "the executable is located at `./executable`";
- `/workspace` as a git repository the agent can commit into;
- `git config --system safe.directory '*'`, because the harness unpacks and builds the
  submission as root while the repository is owned by `agent`; without it `go build`
  fails VCS stamping at evaluation even though it worked for the agent.

## Harness contract

Taken from the ProgramBench harness rather than assumed:

- The submission is extracted into `/workspace`; its `compile.sh` must produce
  an executable at `./executable`.
- `compile.sh` runs with the network blocked, so dependencies must be vendored.
- The test branch supplies `eval/run.sh` and `eval/tests/`, is run from
  `/workspace`, and must leave a JUnit report at `eval/results.xml`.
- Test ids are `eval.tests.<module>.<test>[param]`.
- Every command runs through `bash -lc`, a *login* shell. On Debian that re-sources
  `/etc/profile` and resets `PATH`, discarding the image's `ENV PATH`. Tools the
  build needs must therefore sit on the default login `PATH`; the Dockerfile
  symlinks `go` into `/usr/local/bin`.
- `eval_clean_hashes` in `task.yaml` is the sha256 of the reference binary; the
  harness deletes any file in a submission that matches it, so a submission
  cannot pass by shipping a copy of the reference.

Tests resolve the program under test from `PROGRAMBENCH_EXECUTABLE`, falling
back to `./executable`. That is what lets one unmodified suite run against the
reference, a stub, or a real submission.

## Build and validate

```bash
scripts/build_task_image.sh          # the task image; serves the agent run and the evaluation
scripts/validate.sh                  # the validation matrix
scripts/programbench_eval.sh SUBMISSION.tar.gz   # score with ProgramBench's real CLI
```

Current result, scored two independent ways (this repo's flow, and ProgramBench's own
`programbench eval` + `info`):

| Run | Result |
| --- | --- |
| gold (reference binary) | 112 / 112 passed |
| gold submission, built offline through `compile.sh` | 112 / 112 passed, both scorers |
| stub-noop (prints nothing, exits 0) | 0 / 112 passed, both scorers |
| stub-identity (echoes input unchanged) | 0 / 112 passed, both scorers |

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
- **Scope is not stated to the agent.** The official agent prompt is generic and the
  workspace holds only the binary and `docs/`, so the agent is *not* told that
  `--to-json`/`--from-json`, EditorConfig and `--detect` are unscored (they are in
  the man page). That costs it effort, not points, and is inherent to the benchmark;
  `docs/TASK.md` records the scope for reviewers only.
