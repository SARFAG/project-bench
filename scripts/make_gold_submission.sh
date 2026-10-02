#!/bin/bash
# Build the gold submission tarball: upstream source at the pinned commit, with
# dependencies vendored and a compile.sh that builds offline.
#
# This is the reference solution used by scripts/validate.sh to prove the task
# is solvable under the harness contract. It is generated rather than committed,
# so no upstream source lives in this repository.
#
# Usage: scripts/make_gold_submission.sh [OUTPUT_TARBALL]
set -euo pipefail

repo="https://github.com/mvdan/sh"
commit="9a79a445faf5243da3c26be7d745c2cb17f27823"
out="${1:-/home/user/gold-submission.tar.gz}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

command -v go >/dev/null || { echo "error: go toolchain required to vendor dependencies" >&2; exit 1; }

echo "cloning $repo @ ${commit:0:7}" >&2
git clone --quiet --filter=blob:none "$repo" "$work/src"
git -C "$work/src" checkout --quiet --detach "$commit"
rm -rf "$work/src/.git"

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
