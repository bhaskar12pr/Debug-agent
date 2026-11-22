#!/usr/bin/env bash
# run_sim.sh — build (once) and run one test of SOC_VERIF's soc_top with Verilator.
#
#   dv/scripts/run_sim.sh <test> [seed] [extra plusargs...]
#
# Output: runs/<test>_s<seed>/{sim.log,waves.vcd}
# Env:    SOC_VERIF  path to the SOC_VERIF checkout (default: ../SOC_VERIF or ../soc_verif)
#         SIM_DEBUG=1 to enable [DBG] transaction trace lines in the checkers
set -euo pipefail
here="$(cd "$(dirname "$0")/../.." && pwd)"
test="${1:?usage: run_sim.sh <test> [seed] [plusargs...]}"; seed="${2:-1}"; shift $(( $# >= 2 ? 2 : 1 ))

soc="${SOC_VERIF:-}"
if [[ -z "$soc" ]]; then
  for c in "$here/../SOC_VERIF" "$here/../soc_verif"; do [[ -d "$c/rtl" ]] && soc="$c" && break; done
fi
[[ -d "$soc/rtl" ]] || { echo "SOC_VERIF checkout not found; set SOC_VERIF=/path/to/SOC_VERIF" >&2; exit 2; }

defines=(); objdir="$here/build/obj_dir"
if [[ "${SIM_DEBUG:-0}" == 1 ]]; then defines+=(+define+SIM_DEBUG); objdir="$here/build/obj_dir_dbg"; fi

if [[ ! -x "$objdir/Vtb_soc_top" ]]; then
  mapfile -t rtl < <(find "$soc/rtl/ip" -name '*.sv' | sort)
  verilator --binary --timing --assert --trace -Wno-fatal -Wno-lint -Wno-style \
    -Wno-PINCONNECTEMPTY -Wno-MULTIDRIVEN -Wno-LATCH -Wno-COMBDLY \
    --top-module tb_soc_top --Mdir "$objdir" -o Vtb_soc_top "${defines[@]}" \
    "${rtl[@]}" "$soc/rtl/soc_top/soc_top.sv" \
    "$here/dv/sva/apb_protocol_checker.sv" "$here/dv/sva/soc_decode_checker.sv" \
    "$here/dv/sva/soc_binds.sv" "$here/dv/tb/tb_soc_top.sv" > "$here/build/verilator_build.log" 2>&1 \
    || { tail -30 "$here/build/verilator_build.log" >&2; exit 3; }
fi

out="$here/runs/${test}_s${seed}"; mkdir -p "$out"
cd "$out"
# error+limit keeps the sim running past the first $error, like a commercial simulator.
"$objdir/Vtb_soc_top" +TEST="$test" +SEED="$seed" +WAVES +verilator+error+limit+1000 \
  +verilator+seed+"$seed" "$@" > sim.log 2>&1 || true
# A run fails if the TB says so, OR any checker/simulator error appears in the log
# (an SVA failure is a real failure even when the TB's own error count is 0).
if grep -qE '^TEST .* PASSED' sim.log && ! grep -qE '^UVM_(ERROR|FATAL) [^:]|%Error|%Fatal' sim.log; then
  echo "PASS $test seed=$seed $out"
else
  echo "FAIL $test seed=$seed $out"
fi
