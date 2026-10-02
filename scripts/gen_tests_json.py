#!/usr/bin/env python3
"""Generate a task's tests.json from a JUnit report produced by a gold run.

The branch id is derived from the test names themselves, so regenerating after
an unchanged run reproduces the same file.

Usage: gen_tests_json.py RESULTS_XML OUTPUT_JSON
"""

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Tests excluded from scoring, with a ProgramBench ignore-reason id. Empty here:
# every weak test found during validation was strengthened rather than ignored.
IGNORED: dict[str, list[dict[str, str]]] = {}


def main() -> None:
    results, output = Path(sys.argv[1]), Path(sys.argv[2])
    root = ET.parse(results).getroot()
    suite = root if root.tag == "testsuite" else root[0]
    names = sorted(f"{tc.get('classname')}.{tc.get('name')}" for tc in suite.iter("testcase"))
    if not names:
        raise SystemExit(f"no testcases in {results}")

    branch = hashlib.sha256("\n".join(names).encode()).hexdigest()[:12]
    output.write_text(
        json.dumps(
            {
                "branches": {
                    branch: {
                        "ignored": False,
                        "ignore_reason": "",
                        "tests": [n for n in names if n not in IGNORED],
                        "ignored_tests": [{"name": n, "reasons": r} for n, r in sorted(IGNORED.items())],
                    }
                }
            },
            indent=2,
        )
        + "\n"
    )
    print(f"{output}: branch {branch}, {len(names) - len(IGNORED)} scored, {len(IGNORED)} ignored")


if __name__ == "__main__":
    main()
