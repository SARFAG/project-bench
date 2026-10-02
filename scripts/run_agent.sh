#!/bin/bash
# Difficulty calibration: N independent agent runs against the task image, scored
# with ProgramBench's own evaluator, then reported as a mean against the 70% bar.
#
# Each run uses the ProgramBench mini-swe-agent configuration unchanged (prompt,
# 1000-step limit, 6h wall limit, `--network none`, `--user agent`, no ptrace),
# except for CPU/memory, which are capped to what this machine has.
#
# Usage:
#   MODEL=<litellm model name> [RUNS=8] [PARALLEL=1] scripts/run_agent.sh
#
# Needs: docker, uv, the task image (scripts/build_task_image.sh), and the model's
# API key in the environment (e.g. ANTHROPIC_API_KEY). Re-running resumes: a run
# whose submission.tar.gz already exists is skipped.
#
# Optional: OUT (default ./calibration), CPUS, MEMORY (default 16g),
#   COST_LIMIT (USD per run; unset = the official 0 = unlimited),
#   PROGRAMBENCH_SRC (local checkout; otherwise cloned),
#   EXTRA_CONFIG (an extra mini-swe-agent config; used by the self-test).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
iid="mvdan__sh.9a79a44"
task="$root/tasks/$iid"
img="programbench/mvdan_1776_sh.9a79a44:task_cleanroom_v6"
: "${MODEL:?set MODEL to a litellm model name, e.g. MODEL=anthropic/<model-id>}"
runs="${RUNS:-8}"; parallel="${PARALLEL:-1}"
out="$(realpath -m "${OUT:-$root/calibration}")"
cpus="${CPUS:-$(( $(nproc) > 20 ? 20 : $(nproc) ))}"

docker image inspect "$img" >/dev/null 2>&1 || { echo "build the image first: scripts/build_task_image.sh" >&2; exit 1; }
mkdir -p "$out"

if [ ! -d "$out/programbench" ]; then
  if [ -n "${PROGRAMBENCH_SRC:-}" ]; then cp -r "$PROGRAMBENCH_SRC" "$out/programbench"
  else git clone -q --depth 1 https://github.com/facebookresearch/programbench "$out/programbench"; fi
fi
[ -d "$out/venv" ] || uv venv -q "$out/venv"
uv pip install -q --python "$out/venv/bin/python" mini-swe-agent -e "$out/programbench"

# Register the task, and build the local test blob `programbench eval` reads.
tdir="$out/programbench/src/programbench/data/tasks/$iid"
mkdir -p "$tdir" && cp "$task/task.yaml" "$task/tests.json" "$tdir/"
branch="$(python3 -c "import json,sys; print(next(iter(json.load(open(sys.argv[1]))['branches'])))" "$task/tests.json")"
rm -rf "$out/blobs" && mkdir -p "$out/blobs/$iid/tests"
tar czf "$out/blobs/$iid/tests/$branch.tar.gz" --exclude=__pycache__ -C "$task" eval

# The official run_args, with CPU/memory adjusted (lists are replaced, not merged).
python3 - "$out/local.yaml" "$cpus" "${MEMORY:-16g}" "${COST_LIMIT:-}" <<'PY'
import sys, yaml
path, cpus, mem, cost = sys.argv[1:]
cfg = {"environment": {"run_args": ["--rm", "--network", "none", "--cpus", cpus, "--memory", mem,
                                    "--memory-swap", mem, "--user", "agent", "--cap-drop", "SYS_PTRACE"]}}
if cost:
    cfg["agent"] = {"cost_limit": float(cost)}
open(path, "w").write(yaml.safe_dump(cfg))
PY

mswea="$out/venv/lib/python$("$out/venv/bin/python" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')/site-packages/minisweagent"
configs=(-c "$mswea/config/benchmarks/programbench.yaml" -c "$out/local.yaml")
[ -n "${EXTRA_CONFIG:-}" ] && configs+=(-c "$EXTRA_CONFIG")

# litellm may not know a new model's price; do not let that abort a run. (This also
# disables cost accounting, so COST_LIMIT has no effect unless prices are known.)
export MSWEA_COST_TRACKING="${MSWEA_COST_TRACKING:-ignore_errors}" MSWEA_SILENT_STARTUP=1
export PROGRAMBENCH_BLOB_DIR="$out/blobs"

run_one() {
  local i="$1"
  "$out/venv/bin/mini-extra" programbench "${configs[@]}" -m "$MODEL" --filter "^${iid}\$" -o "$out/run-$i" -w 1 \
    > "$out/run-$i.log" 2>&1 || echo "run $i exited non-zero; see $out/run-$i.log" >&2
}
echo "running $runs run(s), $parallel at a time, model=$MODEL, cpus=$cpus/run"
for i in $(seq 1 "$runs"); do
  run_one "$i" &
  while [ "$(jobs -rp | wc -l)" -ge "$parallel" ]; do wait -n || true; done
done
wait

for i in $(seq 1 "$runs"); do
  [ -f "$out/run-$i/$iid/submission.tar.gz" ] || continue
  "$out/venv/bin/programbench" eval "$out/run-$i" --docker-cpus "$cpus" -w 1 >/dev/null 2>&1 || true
done
"$out/venv/bin/python" "$root/scripts/score_runs.py" $(for i in $(seq 1 "$runs"); do echo "$out/run-$i"; done)
