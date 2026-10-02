# Validation record — `mvdan__sh.9a79a44`

Reproduce with `scripts/validate.sh` (requires Docker).

## Correctness and fairness

Scoring follows the client's rule: flat, unweighted percentage of non-ignored tests.

| Run | What it is | Result | Required |
| --- | --- | --- | --- |
| gold (reference) | The reference binary in the task image | **112 / 112 passed** | 100% |
| gold submission (offline) | Reference source + `compile.sh`, built with the network cut | **112 / 112 passed** | 100% |
| stub-noop | Exits 0, prints nothing | **0 / 112 passed** | ~0% |
| stub-identity | Echoes stdin back unchanged; swallows flags | **0 / 112 passed** | ~0% |

Every row above was run twice: through this repo's own flow (`scripts/validate.sh`)
and through ProgramBench's real CLI (`scripts/programbench_eval.sh`, which runs
`programbench eval` then `programbench info`). Both agree; the real CLI reports no
warnings or branch errors.

The gold run establishes that no test is defective (`gold_fail`). The two stub
runs establish that no test is passable without implementing the behavior
(`dummy_pass`). The gold-submission run establishes that the task is solvable
under the real harness contract, including the offline-build rule.

`stub-identity` exists because a no-op stub is too easy a bar: a program that
returns its input unchanged passes any test whose expected output happens to
equal its input. It is the stub that actually found problems.

### What running the real harness found

My hand-rolled reproduction of the harness passed 131/131 and still missed a bug.
ProgramBench's own CLI failed the same submission with `compile_failed:
./compile.sh: go: not found`.

The harness runs every command through `bash -lc`. A login shell on Debian
re-sources `/etc/profile`, which resets `PATH` and discards the image's
`ENV PATH`, so `go` vanished from `compile.sh`. My manual runs used `bash -c`,
which honours `ENV`, and so hid it. A real agent would have hit the same wall
(and `shfmt` was affected too). The Dockerfile now symlinks the tools into
`/usr/local/bin`, and `validate.sh` uses `bash -lc` so it cannot mask this again.

Lesson: validate through the real harness, not a model of it.

### Free points removed

The client scores a flat percentage of tests, so tests that are free inflate the
number. 21 of the then-131 tests (16%) checked `--help` / `--version`, with
expected values copyable from the shipped `shfmt-help.txt` (one test per
documented option, one per option group). An agent could take 16% before
implementing any formatting. They are collapsed into two tests (`-h`/`--help`
behaviour, and `--version` shape), giving 112. Nothing was ignored or relaxed;
those tests simply did not measure anything.

### What the first pass got wrong

The initial suite scored 167 tests but leaked badly: **31 passed on stub-noop
and 61 on stub-identity**. Three families were at fault.

1. **Self-referential assertions.** Tests comparing the program against itself —
   `fmt(fmt(x)) == fmt(x)` for idempotence, `fmt(src, "-s") == fmt(src)` for
   "no change", one flag spelling against another. All are satisfied by any
   program that is merely *consistent*, including one that prints nothing.
   Fixed by asserting absolute expected values everywhere.
2. **Silent-success assertions.** `-l`, `-d` and `-w` on already-formatted input
   assert "exit 0, no output", which a no-op stub satisfies. Fixed by folding
   the formatted and unformatted cases into one test, so both halves must hold.
3. **Pass-through corpus cases.** Inputs chosen to show a construct is *kept*
   (`a | b | c`, `echo x >file 2>&1`) already equal their expected output, so
   the identity stub passes by construction. Fixed by perturbing every input's
   whitespace, so each case requires a real change while still testing that the
   construct survives.

The rewrite produced stronger tests with both stubs at zero.
No test needed to be excluded, so `ignored_tests` in `tests.json` is empty.

### Determinism

Every assertion is on stdout, stderr, exit status, or file contents. Nothing
depends on wall-clock time, the network, scheduling, locale, terminal size, or
absolute paths. `tmp_path` isolates each file-mode test. Directory walking is
asserted in lexical order, which the reference guarantees.

One deliberate exclusion: the exact `--version` string is a build stamp. The
reference binary reported `v3.14.1-0.20260929184124-9a79a445faf5` when built from
a full clone, `v3.0.0-20260929184124-9a79a445faf5` from a shallow one, and
`(devel)` from the packaged source (no `.git`) — same commit, three strings. `--version` is therefore asserted only to exit 0 with
one non-empty line. This is the `gold_fail`/golden-drift trap that a strict
assertion would have walked straight into.

## Difficulty — not yet measured

The brief's bar is *a leading model scores below 70% on average*. **That number has
not been measured.** It needs agent rollouts against the inference image, which the
authoring environment (no model API access) could not run. `difficulty: hard` in
`task.yaml` is an estimate.

### Protocol (from the client's answers)

- Frontier models only; about 8 independent runs; own Claude Code / Codex
  subscription acceptable.
- The agent receives only the executable and the user-facing docs in `agent_docs/`
  (the man page and `--help`), plus `docs/TASK.md`.
- Score = flat, unweighted percentage of non-ignored tests. No weights, no
  mandatory categories. Mean over runs must be below 70%.
- Control = no internet + source stripped from the image. Run calibration offline,
  otherwise the number is meaningless.
- The recommended baseline is the mini-swe-agent ProgramBench runner (linked from
  the ProgramBench README). It keeps the model on the host and the container on
  `--network none`, which is the cleanest way to honour "no internet". A
  subscription CLI running *inside* the container needs API reachability, which
  conflicts with that; confirm with the client before using one that way.

```bash
scripts/build_task_image.sh                          # inference image
# run each agent in it; save /workspace as <run>/mvdan__sh.9a79a44/submission.tar.gz
scripts/build_task_image.sh --eval                   # reference-free image the scorer uses
scripts/programbench_eval.sh <submission.tar.gz>     # ProgramBench's own scorer
```

### Reading the result

- **Mean above 70%**: the task is too easy. Add tests for undocumented behaviour
  that probing the binary can still find. Do not remove coverage.
- **Mean near zero**: suspect an unfair or underspecified task, not a hard one.
  Check whether the missing behaviour is inferable from `agent_docs/` or by
  probing before blaming the model.

### Known risks to the number

1. **Memorization.** shfmt is widely known, and the offline control only blocks
   downloading, not recall. A model may reproduce much of the parser and printer
   from memory, inflating the score. The compiled reference also embeds its module
   path (`go version -m`), and the program name and `--help` identify it
   regardless; this cannot realistically be hidden and the client's stated control
   does not require it. If runs come in above 70% for this reason, the levers are
   harder probe-discoverable tests, or a less well-known program.
2. **Exact diagnostic text.** Five parse-error tests assert the reference's exact
   message and position (`test_cli_errors.py`). They are discoverable by probing,
   but the space of possible messages is unbounded. The client has no public answer
   on whether undocumented-but-probeable behaviour is in scope (their Q12);
   confirm before submission, and drop or loosen these if they object.

## Provenance

Upstream `mvdan/sh` at commit `9a79a445faf5243da3c26be7d745c2cb17f27823`,
BSD 3-clause licensed. The unmodified source ships in the package at
`tasks/mvdan__sh.9a79a44/reference/src` (licence at `reference/src/LICENSE`), and
the compiled reference at `reference/bin/shfmt`. Neither is on the agent image. Not among the 201 instances in the
public ProgramBench task set.
