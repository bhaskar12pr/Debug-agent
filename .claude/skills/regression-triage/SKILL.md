---
name: regression-triage
description: Group a regression's failing runs into distinct root-cause buckets before debugging any of them. Use when there are many failing tests/seeds, after a nightly regression, or when asked "what broke".
---
# Regression triage

1. Run it (if not already run): `dv/scripts/run_regression.sh [n_seeds]` -> `runs/regression.txt`
2. Bucket: `python3 -m debug_agent triage runs/` (`--json` for machine use)
3. Read the buckets, not the logs. Each bucket = one first-failure signature with
   seeds, addresses, times and numbers normalized away.
4. Sanity checks before debugging:
   - A `NO_SUMMARY` bucket means a run crashed, hung or was killed: check the
     log tail and for a missing `waves.vcd`; it is often an environment issue.
   - Two buckets whose first failures name the same instance/address are
     probably one bug; say so.
   - A run that the TB marked PASSED but has SVA `%Error`s is a FAIL: checkers
     count even when the TB's own error count is 0.
5. Order: largest bucket first, then any bucket containing a directed test
   (deterministic, easiest to reproduce).
6. Pick one representative per bucket, preferably the shortest log, and hand
   it to the root-cause skill.
