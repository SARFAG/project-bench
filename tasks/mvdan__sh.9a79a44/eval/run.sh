#!/bin/sh
# Entry point the harness invokes from the workspace root. Must leave a JUnit
# XML report at eval/results.xml regardless of test outcome.
set -u
cd "$(dirname "$0")/.."
exec python3 -m pytest eval/tests \
  -p no:cacheprovider \
  --junitxml=eval/results.xml \
  --timeout=60 --timeout-method=thread \
  -q
