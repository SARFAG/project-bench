#!/bin/bash
# Full task validation. Builds both images, then reports the pass rate of:
#   gold      -- the reference program, which must score 100%
#   submission-- the gold submission built offline from vendored source
#   stub-*    -- deliberately wrong programs, which must score ~0%
#
# Usage: scripts/validate.sh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
task="$root/tasks/mvdan__sh.9a79a44"
eval_img="mvdan_1776_sh.9a79a44:eval_v1"
task_img="mvdan_1776_sh.9a79a44:task_cleanroom_v1"
stubs="${STUB_DIR:-/home/user/stubs}"
sub="${GOLD_SUBMISSION:-/home/user/gold-submission.tar.gz}"

"$root/scripts/make_stubs.sh" "$stubs" >/dev/null
[ -f "$sub" ] || "$root/scripts/make_gold_submission.sh" "$sub"

run_suite() {  # run_suite IMAGE EXECUTABLE_PATH [extra docker args...]
  local img="$1" exe="$2"; shift 2
  docker run --rm --network none -v "$task/eval:/workspace/eval:ro" "$@" "$img" \
    bash -c "cd /workspace && PROGRAMBENCH_EXECUTABLE='$exe' pytest eval/tests -q -p no:cacheprovider 2>&1 | tail -1"
}

printf '%-26s %s\n' "RUN" "RESULT"
printf '%-26s %s\n' "gold (reference)" "$(run_suite "$task_img" /opt/reference/bin/shfmt)"
for s in noop identity; do
  printf '%-26s %s\n' "stub-$s" "$(run_suite "$eval_img" /stub -v "$stubs/stub-$s:/stub:ro")"
done

# The gold submission goes through the real contract: extract, offline compile.sh, run.
printf '%-26s ' "gold submission (offline)"
docker run --rm --network none -v "$sub:/in/submission.tar.gz:ro" -v "$task/eval:/in/eval:ro" "$eval_img" \
  bash -c 'set -e; cd /workspace && tar xzf /in/submission.tar.gz && rm -f ./executable \
    && ./compile.sh >/dev/null 2>&1 && cp -r /in/eval /workspace/eval \
    && pytest eval/tests -q -p no:cacheprovider 2>&1 | tail -1'
