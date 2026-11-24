#!/usr/bin/env bash
# run_regression.sh — run the default regression; prints one PASS/FAIL line per run.
#   dv/scripts/run_regression.sh [n_random_seeds]
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
n="${1:-10}"
mkdir -p "$here/../../runs"
{
  for t in gpio_rw timer_cmp_rw timer_count; do "$here/run_sim.sh" "$t" 1; done
  for s in $(seq 1 "$n"); do "$here/run_sim.sh" random_rw "$s"; done
} | tee "$here/../../runs/regression.txt"
