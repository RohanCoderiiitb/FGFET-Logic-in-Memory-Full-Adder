#!/usr/bin/env python3
"""Measure the A-type metrics from the schematic ../full_adder_atype.asc and write results/metrics.json + results/wave_B*.npz.

Protocol (standard SPICE characterisation, see results/ATYPE_RESULTS.md section 4):
  * propagation delay t_PLH: 50 % of the rising data input (Cin, or A) -> 50 % of the rising Cout
  * P_avg   : mean(V_DD * I_DD) over the 8 ns Fig. 6 window, B = 1 and B = 0 runs averaged (all 8 A,B,Cin combinations)
  * P_static: DC operating point, all 8 (A, B, Cin) combinations, CLK = 0, memory node at its stored read level
  * P_dyn   : P_avg - P_static ;  PDP = P_dyn * t_p ;  E_cycle = P_dyn * T_clk
All circuit information comes from the schematic (see fa.py)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, fa

def main():
    out, waves = fa.measure(keep_waves=True)
    sha = fa.schematic_hash()
    out["schematic"] = {"file": os.path.basename(fa.ASC), "sha256": sha}
    for bit in (1, 0):
        d = waves[bit]; t = d["time"]
        keep = ((t >= 2.284e-6) | (np.arange(len(t)) % 100 == 0)) & (t <= 2.31e-6)     # thin the 10 ps programming samples; full resolution from the read edge on
        d = {k: v[keep] for k, v in d.items()}
        np.savez_compressed(os.path.join(fa.RES, f"wave_B{bit}.npz"),
                            schematic_sha256=sha, **{k: d[k] for k in ("time", "v(clk)", "v(a)", "v(cin)", "v(sum)", "v(cout)", "v(_cout)", "v(_sum)",
                                                  "v(wl)", "v(b)", "v(xfg_cout:mn)", "v(xfg_or:mn)", "v(xfg_sum:mn)", "i(vdd)")})
    json.dump(out, open(os.path.join(fa.RES, "metrics.json"), "w"), indent=1)
    print(json.dumps(out["headline"], indent=1))
    print("delay cases (B, step input, other input = value -> t_PLH ps | Cout before/after V):")
    for c in out["delay_cases"]:
        t = "no Cout rise" if c["t_plh_ps"] is None else f"{c['t_plh_ps']:.2f}"
        print(f"  B={c['B']} {c['step_input']}: {c['other_input']}={c['other_value']} -> {t} | {c['cout_before_V']:.3f}/{c['cout_after_V']:.3f} (expect Cout={c['cout_expected']})")
    for b in (1, 0):
        print(f"B{b} logic ok:", all(x["ok"] for x in out["B"][b]["logic"]), {k: round(v, 3) for k, v in out["B"][b]["vmn_read"].items()})

if __name__ == "__main__":
    main()
