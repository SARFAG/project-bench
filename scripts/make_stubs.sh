#!/bin/sh
# Build the two stub "implementations" used to check that the test suite
# actually discriminates: a no-op binary and an identity (passthrough) binary.
set -eu
out="${1:?usage: make_stubs.sh OUTDIR}"
mkdir -p "$out"

cat > "$out/stub-noop" <<'EOF'
#!/bin/sh
# Does nothing at all: no output, always succeeds.
exit 0
EOF

cat > "$out/stub-identity" <<'EOF'
#!/bin/sh
# Plausible-but-wrong: echoes stdin back unchanged, so any test whose input is
# already formatted would pass. Flags are swallowed; paths are cat'ed.
args=""
for a in "$@"; do
  case "$a" in
    -*) ;;
    *) args="$args $a" ;;
  esac
done
if [ -n "$args" ]; then
  # shellcheck disable=SC2086
  cat $args 2>/dev/null || exit 1
else
  cat
fi
EOF

chmod +x "$out/stub-noop" "$out/stub-identity"
echo "wrote $out/stub-noop $out/stub-identity"
