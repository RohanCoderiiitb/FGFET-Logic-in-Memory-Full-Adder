#!/usr/bin/env python3
"""Sensitivity of the schematic's metrics to the FGFET device-model parameters (SFET / VFET BSIM4 cards, C_VA capacitor).
The circuit (../full_adder_atype.asc) and all sizings are untouched; each run changes parameters in a temporary copy of the model files.

  python3 fit_models.py probe        one-at-a-time perturbation of every parameter
  (import fit_models; fit_models.run({"sfet_vth0": 0.3}))   any combination

Result (see results/ATYPE_RESULTS.md section 5): the model files cannot close the gap to the paper, so they were left unchanged."""
import json, os, re, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, fa

TARGET = {"t_plh_cin_cout_ps": 43.54, "p_dyn_uW": 1.14, "p_static_avg_nW": 13.64}      # paper, Table III, A-type
MODELS = fa.models_dir()
# name -> (file, parameter, baseline); "scale" parameters are multiplied, "shift" parameters are added
PARAMS = {
    "sfet_u0":   ("sfet_32nm.pm", "u0", "scale"),     "sfet_vth0": ("sfet_32nm.pm", "vth0", "shift"),
    "sfet_vsat": ("sfet_32nm.pm", "vsat", "scale"),   "sfet_voff": ("sfet_32nm.pm", "voff", "shift"),
    "vfet_u0":   ("vfet_32nm.pm", "u0", "scale"),     "vfet_vth0": ("vfet_32nm.pm", "vth0", "shift"),
    "cva_Cmax":  ("fgfet_ltspice.sub", "cva_Cmax", "scale"), "cva_Cmin": ("fgfet_ltspice.sub", "cva_Cmin", "scale"),
    "cva_Vfb":   ("fgfet_ltspice.sub", "cva_Vfb", "shift"),  "cva_Vslp": ("fgfet_ltspice.sub", "cva_Vslp", "scale"),
}
_VAL = r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"

def base_value(name):
    f, p, _ = PARAMS[name]; txt = open(os.path.join(MODELS, f)).read()
    return float(re.search(rf"\b{p}\s*=\s*{_VAL}", txt).group(1))

def variant(changes, dest):
    """Copy the model folder to dest and apply {param name: new factor/shift}."""
    shutil.copytree(MODELS, dest, dirs_exist_ok=True)
    for name, v in changes.items():
        f, p, kind = PARAMS[name]; path = os.path.join(dest, f); txt = open(path).read()
        new = base_value(name) * v if kind == "scale" else base_value(name) + v
        txt, n = re.subn(rf"(\b{p}\s*=\s*){_VAL}", lambda m: f"{m.group(1)}{new:.8g}", txt, count=1); assert n == 1
        open(path, "w").write(txt)
    return dest

def run(changes):
    d = tempfile.mkdtemp(prefix="fa_models_")
    try:
        variant(changes, d); r = fa.measure(models=d)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    h = r["headline"]; h["vmn_B1"] = float(np.mean(list(r["B"][1]["vmn_read"].values()))); h["vmn_B0"] = float(np.mean(list(r["B"][0]["vmn_read"].values())))
    return h

def show(tag, h):
    print(f"{tag:22s} delay {h['t_plh_cin_cout_ps']:6.2f} ps  Pdyn {h['p_dyn_uW']:6.3f} uW  Pstat {h['p_static_avg_nW']:6.2f} nW  "
          f"vmn1 {h['vmn_B1']:+.3f} vmn0 {h['vmn_B0']:+.3f} logic {h['logic_ok']}", flush=True)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "probe"
    if cmd == "probe":
        rows = [("baseline", {})]
        for name, (f, p, kind) in PARAMS.items():
            step = {"scale": 1.25, "shift": 0.05}[kind]
            rows.append((f"{name} {'x' if kind=='scale' else '+'}{step}", {name: step}))
        rows += [("sfet_u0 x0.1", {"sfet_u0": 0.1}), ("sfet_vth0 +0.3", {"sfet_vth0": 0.3}),
                 ("sfet_vth0 +0.3, u0 x0.3", {"sfet_vth0": 0.3, "sfet_u0": 0.3})]
        out = []
        for tag, ch in rows:
            h = run(ch); show(tag, h); out.append({"change": tag, **{k: h[k] for k in ("t_plh_cin_cout_ps", "p_dyn_uW", "p_static_avg_nW", "vmn_B1", "vmn_B0", "logic_ok")}})
        json.dump(out, open(os.path.join(fa.RES, "model_sensitivity.json"), "w"), indent=1)
