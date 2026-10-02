#!/bin/bash
# Build the gold submission tarball: the packaged reference source, with
# dependencies vendored and a compile.sh that builds offline.
#
# This is the reference solution used by scripts/validate.sh to prove the task
# is solvable under the harness contract. It is generated rather than committed,
# so no upstream source lives in this repository.
#
# Usage: scripts/make_gold_submission.sh [OUTPUT_TARBALL]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
src="$root/tasks/mvdan__sh.9a79a44/reference/src"
out="${1:-/home/user/gold-submission.tar.gz}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

command -v go >/dev/null || { echo "error: go toolchain required to vendor dependencies" >&2; exit 1; }

mkdir -p "$work/src"
cp -r "$src/." "$work/src/"

cat > "$work/src/compile.sh" <<'EOF'
#!/bin/sh
# Builds the submission into ./executable. Runs with the network blocked, so all
# dependencies must already be vendored in the submission.
set -eu
export GOTOOLCHAIN=local
export GOFLAGS=-mod=vendor
go build -trimpath -ldflags="-s -w" -o executable ./cmd/shfmt
EOF
chmod +x "$work/src/compile.sh"

echo "vendoring dependencies" >&2
(cd "$work/src" && go mod vendor)

mkdir -p "$(dirname "$out")"
tar czf "$out" -C "$work/src" .
echo "wrote $out ($(du -h "$out" | cut -f1))" >&2
