#!/usr/bin/env python3
"""Area estimate for C-type full adder. Device count of ../full_adder_ctype.asc scaled from the paper's conventional adder.

The paper reports the conventional 28-FET adder area as 3.75 um^2 (2 metal layers, 32 nm rules).
For C-type with 21 transistors (15 FET + 6 FGFET), the layout area reported in the paper is 2.53 um^2 (4 metal layers)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fa

A_CONV, N_CONV = 3.75, 28
PAPER = {"A": (19, 2.46), "B": (20, 2.24), "C": (21, 2.53)}
n_fet, n_fg = fa.device_counts(fa.net_text())
est = A_CONV * (n_fet + n_fg) / N_CONV
out = {
    "devices_in_schematic": {"FET": n_fet, "FGFET": n_fg, "Total": n_fet + n_fg},
    "per_device_um2": A_CONV / N_CONV,
    "estimate_um2": est,
    "estimate_reduction_pct": 100 * (1 - est / A_CONV),
    "paper_um2": PAPER["C"][1],
    "paper_reduction_pct": 100 * (1 - PAPER["C"][1] / A_CONV),
    "estimate_vs_paper_pct": 100 * (est / PAPER["C"][1] - 1),
    "paper_benchmark_table": {k: {"devices": n, "paper_area_um2": a} for k, (n, a) in PAPER.items()}
}
json.dump(out, open(os.path.join(fa.RES, "area.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
