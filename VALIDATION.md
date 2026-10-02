# Validation record — `mvdan__sh.9a79a44`

Reproduce with `scripts/validate.sh` (requires Docker).

## Correctness and fairness

| Run | What it is | Result | Required |
| --- | --- | --- | --- |
| gold (reference) | The reference binary in the task image | **131 / 131 passed** | 100% |
| gold submission (offline) | Upstream source + `compile.sh`, extracted into `/workspace` and built with the network cut, exactly as the harness does it | **131 / 131 passed** | 100% |
| stub-noop | Exits 0, prints nothing | **0 / 131 passed** | ~0% |
| stub-identity | Echoes stdin back unchanged; swallows flags | **0 / 131 passed** | ~0% |

The gold run establishes that no test is defective (`gold_fail`). The two stub
runs establish that no test is passable without actually implementing the
behavior (`dummy_pass`). The gold-submission run establishes that the task is
solvable under the real harness contract, including the offline-build rule.

`stub-identity` exists because a no-op stub is too easy a bar: a program that
returns its input unchanged passes any test whose expected output happens to
equal its input. It is the stub that actually found problems.

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

The rewrite brought the count to 131 stronger tests, with both stubs at zero.
No test needed to be excluded, so `ignored_tests` in `tests.json` is empty.

### Determinism

Every assertion is on stdout, stderr, exit status, or file contents. Nothing
depends on wall-clock time, the network, scheduling, locale, terminal size, or
absolute paths. `tmp_path` isolates each file-mode test. Directory walking is
asserted in lexical order, which the reference guarantees.

One deliberate exclusion: the exact `--version` string is a build stamp. The
reference binary reports `v3.14.1-0.20260929184124-9a79a445faf5` when built from
a full clone and `v3.0.0-20260929184124-9a79a445faf5` from a shallow one — same
commit, different string. `--version` is therefore asserted only to exit 0 with
one non-empty line. This is the `gold_fail`/golden-drift trap that a strict
assertion would have walked straight into.

## Difficulty — not yet measured

The brief's bar is *a leading model scores below 70% on average*. **That number
has not been measured**, because measuring it needs an agent rollout against the
inference image, which this environment cannot run.

What the task demands is a full shell parser and a canonical printer: operator
and redirect spacing, `case` clause spacing, heredoc bodies held at column 0
while the redirect indents, backslash continuations under `-bn`, comment-column
realignment and its suppression under `-kp`, dialect gating, and a narrow set of
`-s` rewrites that must not over-apply. Scored surface is bounded (no
`--to-json`, no EditorConfig), so the ceiling is reachable; the per-construct
details are where a model should lose points.

`difficulty: hard` in `task.yaml` is an estimate pending that measurement. To
measure:

```bash
scripts/build_task_image.sh                 # inference image, reference present
# run an agent in it, capture /workspace as submission.tar.gz, then:
programbench eval <run-dir>
```

## Provenance

Upstream `mvdan/sh` at commit `9a79a445faf5243da3c26be7d745c2cb17f27823`,
BSD 3-clause licensed; the licence ships in the image at
`/opt/reference/doc/LICENSE.upstream`. Not among the 201 instances in the
public ProgramBench task set.
