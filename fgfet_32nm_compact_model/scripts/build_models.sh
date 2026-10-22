#!/usr/bin/env bash
# Regenerate every model file from scratch (Stages 1-4 of the replication guide).
#   ./build_models.sh [path/to/paper.pdf]
set -euo pipefail
cd "$(dirname "$0")"
echo "== Stage 1: digitize Fig. 2 / Fig. 4 ==";      python3 digitize_figures.py "$@"
echo "== Stage 2.2: SFET BSIM4 card ==";             python3 fit_sfet.py
echo "== Stage 2.3: VFET BSIM4 card ==";             python3 fit_vfet.py
echo "== Stages 3-4: C_VA Verilog-A + FGFET subckt =="; python3 fit_cva.py
