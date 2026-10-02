#!/bin/bash
# Full task validation. Reports the pass rate of:
#   gold       -- the reference binary shipped in the image, which must score 100%
#   submission -- the gold submission built offline from the packaged source
#   stub-*     -- deliberately wrong programs, which must score ~0%
#
# Every command runs through `bash -lc`, as the ProgramBench harness does: a login
# shell resets PATH, which an `ENV PATH` image would otherwise hide.
#
# Usage: scripts/validate.sh   (build the image first: scripts/build_task_image.sh)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
task="$root/tasks/mvdan__sh.9a79a44"
img="programbench/mvdan_1776_sh.9a79a44:task_cleanroom_v6"
stubs="${STUB_DIR:-/home/user/stubs}"
sub="${GOLD_SUBMISSION:-/home/user/gold-submission.tar.gz}"

"$root/scripts/make_stubs.sh" "$stubs" >/dev/null
[ -f "$sub" ] || "$root/scripts/make_gold_submission.sh" "$sub"

run_suite() {  # run_suite EXECUTABLE_PATH [extra docker args...]
  local exe="$1"; shift
  docker run --rm --network none -v "$task/eval:/workspace/eval:ro" "$@" "$img" \
    bash -lc "cd /workspace && PROGRAMBENCH_EXECUTABLE='$exe' pytest eval/tests -q -p no:cacheprovider 2>&1 | tail -1"
}

printf '%-26s %s\n' "RUN" "RESULT"
printf '%-26s %s\n' "gold (./executable)" "$(run_suite /workspace/executable)"
for s in noop identity; do
  printf '%-26s %s\n' "stub-$s" "$(run_suite /stub -v "$stubs/stub-$s:/stub:ro")"
done

# The gold submission goes through the real contract: wipe the workspace, extract,
# offline compile.sh, run.
printf '%-26s ' "gold submission (offline)"
docker run --rm --network none -v "$sub:/in/submission.tar.gz:ro" -v "$task/eval:/in/eval:ro" "$img" \
  bash -lc 'set -e; cd /workspace && rm -rf /workspace/* /workspace/.[!.]* && tar xzf /in/submission.tar.gz \
    && rm -f ./executable && ./compile.sh >/dev/null 2>&1 && cp -r /in/eval /workspace/eval \
    && pytest eval/tests -q -p no:cacheprovider 2>&1 | tail -1'
