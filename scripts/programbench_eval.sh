#!/bin/bash
# Score a submission with ProgramBench's own `programbench eval`, rather than this
# repo's reimplementation of the harness flow.
#
# Registers the task in a throwaway copy of the ProgramBench checkout, builds the
# local test blob it expects, then runs `eval` and `info` against the task image.
#
# Usage: scripts/programbench_eval.sh SUBMISSION.tar.gz [PROGRAMBENCH_CHECKOUT]
#   With no checkout given, facebookresearch/programbench is cloned (needs network).
# Needs: docker, uv, and the task image from `scripts/build_task_image.sh`.
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
iid="mvdan__sh.9a79a44"
task="$root/tasks/$iid"
sub="$(realpath "${1:?usage: programbench_eval.sh SUBMISSION.tar.gz [CHECKOUT]}")"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

if [ -n "${2:-}" ]; then cp -r "$2" "$work/pb"; else git clone -q --depth 1 https://github.com/facebookresearch/programbench "$work/pb"; fi
uv venv -q "$work/venv"
uv pip install -q --python "$work/venv/bin/python" -e "$work/pb"

mkdir -p "$work/pb/src/programbench/data/tasks/$iid"
cp "$task/task.yaml" "$task/tests.json" "$work/pb/src/programbench/data/tasks/$iid/"

branch="$(python3 -c "import json,sys; print(next(iter(json.load(open(sys.argv[1]))['branches'])))" "$task/tests.json")"
mkdir -p "$work/blobs/$iid/tests" "$work/run/$iid"
tar czf "$work/blobs/$iid/tests/$branch.tar.gz" --exclude=__pycache__ -C "$task" eval
cp "$sub" "$work/run/$iid/submission.tar.gz"

export PROGRAMBENCH_BLOB_DIR="$work/blobs"
"$work/venv/bin/programbench" eval "$work/run" --docker-cpus "${DOCKER_CPUS:-$(nproc)}" -w 1
"$work/venv/bin/programbench" info "$work/run"
