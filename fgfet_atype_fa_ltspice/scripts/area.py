#!/usr/bin/env python3
"""PLACEHOLDER area estimate (not a result: see results/ATYPE_RESULTS.md section 8). Device count of ../full_adder_atype.asc scaled from the paper's conventional adder.

Area cannot come from a SPICE netlist. The only layout number the paper gives for the baseline is the conventional 28-FET adder
(3.75 um^2, 2 metal layers, ITRS 32 nm rules), so the estimate scales that by device count: every FET and every FGFET (a VFET stacked
on its SFET) is taken to occupy one conventional-FET footprint."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fa
A_CONV, N_CONV = 3.75, 28                      # paper, Fig. 9(a)
PAPER = {"A": (19, 2.46), "B": (20, 2.24), "C": (21, 2.53)}     # devices, area from Fig. 9 / Sec. III (B and C: paper circuits, for the error check)
n_fet, n_fg = fa.device_counts(fa.net_text())
est = A_CONV * (n_fet + n_fg) / N_CONV
out = {"devices_in_schematic": {"FET": n_fet, "FGFET": n_fg}, "per_device_um2": A_CONV / N_CONV, "estimate_um2": est,
       "estimate_reduction_pct": 100 * (1 - est / A_CONV), "paper_um2": PAPER["A"][1],
       "paper_reduction_pct": 100 * (1 - PAPER["A"][1] / A_CONV), "estimate_vs_paper_pct": 100 * (est / PAPER["A"][1] - 1),
       "same_method_on_paper_B_C": {k: {"estimate": A_CONV * n / N_CONV, "paper": a, "err_pct": 100 * (A_CONV * n / N_CONV / a - 1)}
                                    for k, (n, a) in PAPER.items() if k != "A"}}
json.dump(out, open(os.path.join(fa.RES, "area.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
