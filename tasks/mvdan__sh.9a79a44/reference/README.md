# Reference program

Not visible to the benchmark agent beyond the compiled binary.

- `src/` — source of `shfmt` from [mvdan/sh](https://github.com/mvdan/sh) at commit
  `9a79a445faf5243da3c26be7d745c2cb17f27823` (BSD 3-clause, see `src/LICENSE`),
  exported with `git archive`. The only omissions are upstream's `CLAUDE.md` and
  `AGENTS.md` (AI-assistant instructions, not source); nothing that is compiled
  was altered.
- `bin/shfmt` — the compiled reference executable, extracted from the task image.
  Its sha256 is `eval_clean_hashes` in `../task.yaml`.

Rebuild from source with `scripts/build_task_image.sh`; the Dockerfile builds `src/`
with `CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" ./cmd/shfmt`.
