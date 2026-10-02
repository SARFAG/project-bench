#!/usr/bin/env python3
"""Score calibration runs the way `programbench info` does, then report the mean.

Reads <run_dir>/<instance>/<instance>.eval.json for each run directory, drops the
branches and tests the task marks as ignored, and prints one line per run plus the
mean against the 70% bar. Run it with the ProgramBench virtualenv's python.

Usage: score_runs.py RUN_DIR [RUN_DIR ...]
"""

import statistics
import sys
from pathlib import Path

from programbench.eval.eval import EvaluationResult
from programbench.eval.eval_batch import InstanceEvalSummary
from programbench.utils.load_data import get_active_branches, get_ignored_tests, load_all_instances

BAR = 70.0

instances = {i["instance_id"]: i for i in load_all_instances(include_tests=True)}
scores: list[float] = []
for run in map(Path, sys.argv[1:]):
    paths = sorted(run.glob("*/*.eval.json"))
    if not paths:
        print(f"{run.name:12} no eval.json (run did not finish, or was not evaluated)")
        continue
    for p in paths:
        result = EvaluationResult.model_validate_json(p.read_text())
        inst = instances[p.parent.name]
        result = result.for_branches(get_active_branches(inst)).without_ignored(get_ignored_tests(inst))
        s = InstanceEvalSummary.from_eval_result(p.parent.name, result)
        note = f"  [{s.error_code}: scored as 0]" if s.error_code else ""
        print(f"{run.name:12} {s.n_resolved:4}/{s.n_tests:<4} tests = {100 * s.n_resolved / max(s.n_tests, 1):5.1f}%{note}")
        scores.append(100 * s.n_resolved / max(s.n_tests, 1))

if scores:
    mean = statistics.mean(scores)
    sd = statistics.stdev(scores) if len(scores) > 1 else 0.0
    print(f"\n{len(scores)} runs: mean {mean:.1f}%  sd {sd:.1f}  min {min(scores):.1f}  max {max(scores):.1f}")
    print(f"bar: mean < {BAR:.0f}%  ->  {'MET' if mean < BAR else 'NOT MET'}")
