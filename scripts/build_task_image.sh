#!/bin/bash
# Build the task image under the name and tag ProgramBench's tooling expects:
# programbench/mvdan_1776_sh.9a79a44:task_cleanroom_v6. One image serves both the
# agent run and the evaluation.
#
# In a normal environment this is just `docker build`. When the session runs
# behind an intercepting TLS proxy (Claude Code's agent proxy), the script
# additionally stages the proxy CA into the build context and runs the build on
# the host network so the in-build module and pip downloads can reach out.
set -euo pipefail

task_dir="$(cd "$(dirname "$0")/../tasks/mvdan__sh.9a79a44" && pwd)"
tag="programbench/mvdan_1776_sh.9a79a44:task_cleanroom_v6"

args=(build -t "$tag")

ca_staged=""
if [ -n "${HTTPS_PROXY:-}" ] && [ -f "${CCR_CA_BUNDLE:-/root/.ccr/ca-bundle.crt}" ]; then
  ca_staged="${task_dir}/ca/proxy-ca.crt"
  cp "${CCR_CA_BUNDLE:-/root/.ccr/ca-bundle.crt}" "$ca_staged"
  args+=(--network=host
         --build-arg "https_proxy=${HTTPS_PROXY}"
         --build-arg "HTTPS_PROXY=${HTTPS_PROXY}"
         --build-arg "no_proxy=${NO_PROXY:-}"
         --build-arg "NO_PROXY=${NO_PROXY:-}")
  echo "note: building via proxy ${HTTPS_PROXY} with staged CA" >&2
fi
trap '[ -n "$ca_staged" ] && rm -f "$ca_staged"' EXIT

docker "${args[@]}" "$task_dir"
echo "built $tag"
