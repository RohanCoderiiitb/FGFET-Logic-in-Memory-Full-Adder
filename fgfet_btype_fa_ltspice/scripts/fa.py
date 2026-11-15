"""Single entry point to the circuit: everything (metrics, plots, static power, area, model fitting) starts from the schematic
../full_adder_atype.asc. Nothing in this package defines a circuit of its own.

  net_text()        LTspice's own netlist of the .asc (View > SPICE Netlist), the authoritative circuit description
  run_copy()        LTspice run on a temporary copy of the schematic (only B, .save and the model-file location may differ)
  static_netlist()  DC-leakage netlist derived from that netlist (FGFET -> its SFET with the memory node pinned)
  measure()         all metrics from B = 1 / B = 0 runs of the schematic
"""
import os, re, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import numpy as np
import metrics as M
from ltraw import read_raw

ASC = os.path.abspath(os.environ.get("FA_ASC") or os.path.join(ROOT, "full_adder_btype.asc"))   # schematic under test (env FA_ASC)
STEM = os.path.splitext(os.path.basename(ASC))[0]
RES = os.path.join(ROOT, "results") if STEM == "full_adder_btype" else os.path.join(ROOT, "results", STEM)
os.makedirs(RES, exist_ok=True)
SYMBOL = os.path.join(ROOT, "FGFET.asy")
APP = "/Applications/LTspice.app/Contents/SharedSupport/ltspice"
EXTRA_SAVE = " V(wl) V(b)"          # only addition to the schematic's .save (the programming plot needs WL and DL)
T_LOGIC = 2.29e-6                   # analysis window: 5 ns after WL reaches the read level (checked against the schematic below)

def _wine(args):
    # FA_WINEPREFIX: a private copy of the Wine bottle, so batch runs never share a Wine server with the LTspice GUI
    env = dict(os.environ, WINEPREFIX=os.environ.get("FA_WINEPREFIX") or os.path.expanduser("~/Library/Application Support/LTspice/Bottles/ltspice"),
               DYLD_FALLBACK_LIBRARY_PATH=f"{APP}/lib")
    subprocess.run([f"{APP}/LTspice/wine", "C:\\Program Files\\ADI\\LTspice\\LTspice.exe"] + args,
                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _models_rel(text):
    m = re.search(r"\.include\s+(\S+)/cmos_32nm\.pm", text)
    assert m, "schematic has no .include of cmos_32nm.pm"
    return m.group(1)

def models_dir(text=None):
    """Absolute path of the model-file folder that the schematic's .include lines point to."""
    text = text or open(ASC).read()
    return os.path.abspath(os.path.join(os.path.dirname(ASC), _models_rel(text)))

def _prepare(text, workdir, name, models=None):
    rel = _models_rel(text)
    text = text.replace(rel, models or models_dir(text))
    shutil.copy(SYMBOL, workdir)
    path = os.path.join(workdir, name); open(path, "w").write(text); return path

def sim(path):
    for _ in range(4):
        for ext in (".raw", ".log"):
            if os.path.exists(path[:-4] + ext): os.remove(path[:-4] + ext)
        _wine(["-b", "Z:" + path])
        if os.path.exists(path[:-4] + ".raw"): break
    else:
        sys.exit(f"LTspice produced no raw file for {path}")
    return read_raw(path[:-4] + ".raw")

def asc_text(bit=1, save_extra=True, src=None):
    """The schematic's text (or `src`, a modified copy of it) with B = bit (the Vb write level, whatever value the file holds)
    and, optionally, V(wl) V(b) appended to .save (unless already there)."""
    src = src or open(ASC).read()
    level_b = "1.8" if bit == 1 else "0.1"
    level_nb = "0.1" if bit == 1 else "1.8"
    src, n1 = re.subn(r"(Vb b 0 PWL\(0 0 1\.1e-6 0 1\.105e-6 )[-0-9.eE+]+( 2\.2e-6 )[-0-9.eE+]+", lambda m: m.group(1) + level_b + m.group(2) + level_b, src)
    src, n2 = re.subn(r"(Vnb nb 0 PWL\(0 0 1\.1e-6 0 1\.105e-6 )[-0-9.eE+]+( 2\.2e-6 )[-0-9.eE+]+", lambda m: m.group(1) + level_nb + m.group(2) + level_nb, src)
    assert n1 == 1 and n2 == 1, "expected the Vb and Vnb write-level patterns in the schematic"
    if save_extra:
        src = "\n".join(l.rstrip() + EXTRA_SAVE if (l.startswith("TEXT") and "!.save" in l and "V(wl)" not in l) else l for l in src.split("\n"))
    return src

def schematic_hash():
    """SHA-256 of the schematic's circuit: LTspice's netlist without comments, .save and the Vb line, so toggling B or the .save list
    in the GUI does not change it, while any change to devices, sizes, nets or the other sources does."""
    import hashlib
    keep = sorted(l.strip() for l in net_text().splitlines() if l.strip() and l[0] not in "*." and not l.startswith("Vb "))
    keep += sorted(l.strip() for l in net_text().splitlines() if l.startswith((".tran", ".options", ".include")))
    return hashlib.sha256("\n".join(keep).encode()).hexdigest()

def net_text(workdir=None, models=None, src=None):
    """LTspice's netlist of the schematic."""
    own = workdir is None; workdir = workdir or tempfile.mkdtemp(prefix="fa_net_")
    p = _prepare(asc_text(1, False, src), workdir, "net.asc", models)
    _wine(["-netlist", "Z:" + p]); t = open(p[:-4] + ".net").read()
    if own: shutil.rmtree(workdir, ignore_errors=True)
    return t

def _vdd(net):
    m = re.search(r"^Vdd\s+\S+\s+0\s+([0-9.eE+-]+)\s*$", net, re.M); assert m, "no DC Vdd source in the schematic"
    return float(m.group(1))

def check_stimulus(net):
    """The analysis windows below assume this stimulus; fail loudly if the schematic's sources no longer match it."""
    wl = re.search(r"^Vwl\s+wl\s+0\s+PWL\((.*)\)", net, re.M).group(1).split()
    assert abs(float(wl[-2]) - 2.285e-6) < 1e-12 and float(wl[-1]) == 0.5, "WL read edge is no longer at 2.285 us / 0.5 V"
    assert "2.29103e-06 0.9" in re.search(r"^Vclk.*$", net, re.M).group(0), "CLK pulse timing changed"

def static_netlist(net, bit, vmn_map, models=None):
    """DC leakage of all 8 (CLK, A, Cin) states from the schematic's own netlist: every FGFET becomes its sense FET with the
    memory node pinned at its stored read level vmn; sources are replaced by DC states (st = 4 CLK + 2 A + Cin)."""
    vdd = _vdd(net); models = models or models_dir()
    vmn_val = float(np.mean(list(vmn_map.values()))) if isinstance(vmn_map, dict) else float(vmn_map)
    L = [f"* static power, B={bit}, memory node pinned at {vmn_val:.4f} V (derived from the schematic netlist)",
         f".include {models}/cmos_32nm.pm", f".include {models}/sfet_32nm.pm", "",
         f"Vdd Vdd 0 {vdd}", f"Vmn mn 0 {vmn_val:.6f}", "Vst st 0 0", f"Bclk clk 0 V={vdd}*floor(V(st)/4)",
         f"Ba a 0 V=if(V(clk)>0.45, {vdd}*(floor(V(st)/2)-2*floor(V(st)/4)), 0)",
         f"Bcin cin 0 V=if(V(clk)>0.45, {vdd}*(V(st)-2*floor(V(st)/2)), 0)",
         f"Bna na 0 V=if(V(clk)>0.45, {vdd}-V(a), 0)", f"Bncin ncin 0 V=if(V(clk)>0.45, {vdd}-V(cin), 0)",
         f"Bwla wl_a 0 V=if(V(clk)>0.45, 2*V(a), 0)", f"Bwlna wl_na 0 V=if(V(clk)>0.45, 2*({vdd}-V(a)), 0)",
         f"Bwl1 wl_1 0 V=if(V(clk)>0.45, 1.8, 0)", ""]
    for ln in net.splitlines():
        t = ln.split(";")[0].split()
        if not t: continue
        if t[0][0] in "MC": L.append(ln.split(";")[0])
        elif t[0][0] == "X":
            assert t[6] == "FGFET", ln
            par = dict(p.split("=") for p in t[7:] if "=" in p)
            dev_key = t[0][4:].lower() if len(t[0]) > 4 else "s1"
            v_dev = vmn_map.get(dev_key, vmn_val) if isinstance(vmn_map, dict) else vmn_val
            L.append(f"Vmn_{dev_key} mn_{dev_key} 0 {v_dev:.6f}")
            L.append(f"M{t[0][2:]} {t[3]} mn_{dev_key} {t[4]} {t[5]} sfet_nmos L=32n W={par['w_dev']} delvto={par.get('delvto_val','0')}")
    return "\n".join(L + ["", ".options gmin=1e-15 numdgt=15", ".dc Vst 0 7 1", ".end"]) + "\n"

def device_counts(net):
    nf = sum(1 for l in net.splitlines() if l[:1] == "M"); ng = sum(1 for l in net.splitlines() if l[:1] == "X")
    return nf, ng

def _set_source(src, name, node, pwl):
    new, n = re.subn(rf"(!{name} {node} 0 )PWL\([^)]*\)", lambda m: m.group(1) + pwl, src); assert n == 1, f"source {name} not found"
    return new

def delay_sweep(models, work, vdd, t_trig=2.3005e-6):
    """t_PLH for every input case with a possible Cout 0 -> 1 transition, for both stored bits.
    A data input (Cin or A) rises 0 -> 1 with CLK already high (evaluate), the other data input held at 0 or 1, B stored as 0 or 1.
    Returns a list of cases; 't_plh_ps' is None when Cout has no rising transition (it stays at its level)."""
    out = []
    for bit in (0, 1):
        for trig, other in (("cin", "a"), ("a", "cin")):
            for oval in (0, 1):
                s = asc_text(bit, True)
                s = _set_source(s, "Vclk", "clk", "PWL(0 0.9 2.28e-06 0.9 2.285e-06 0 2.2999e-06 0 2.29995e-06 0.9)")
                if trig == "cin":
                    s = _set_source(s, "Vcin", "cin", "PWL(0 0 2.3005e-06 0 2.30055e-06 0.9)")
                    s = _set_source(s, "Vncin", "ncin", "PWL(0 0 2.29995e-06 0.9 2.3005e-06 0.9 2.30055e-06 0)")
                    s = _set_source(s, "Va", "a", "PWL(0 0 2.29995e-06 0.9)" if oval else "PWL(0 0 2.4e-06 0)")
                    s = _set_source(s, "Vna", "na", "PWL(0 0 2.4e-06 0)" if oval else "PWL(0 0 2.29995e-06 0.9)")
                    s = _set_source(s, "Vwl_a", "wl_a", "PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0 2.29995e-6 1.8)" if oval else "PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0)")
                    s = _set_source(s, "Vwl_na", "wl_na", "PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0)" if oval else "PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0 2.29995e-6 1.8)")
                else: # trig == "a"
                    s = _set_source(s, "Va", "a", "PWL(0 0 2.3005e-6 0 2.30055e-6 0.9)")
                    s = _set_source(s, "Vna", "na", "PWL(0 0 2.29995e-6 0.9 2.3005e-6 0.9 2.30055e-6 0)")
                    s = _set_source(s, "Vcin", "cin", "PWL(0 0 2.29995e-6 0.9)" if oval else "PWL(0 0 2.4e-06 0)")
                    s = _set_source(s, "Vncin", "ncin", "PWL(0 0 2.4e-06 0)" if oval else "PWL(0 0 2.29995e-6 0.9)")
                    s = _set_source(s, "Vwl_a", "wl_a", "PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0 2.3005e-6 0 2.30055e-6 1.8)")
                    s = _set_source(s, "Vwl_na", "wl_na", "PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0 2.29995e-6 1.8 2.3005e-6 1.8 2.30055e-6 0)")
                s = s.replace("!.tran 0 3e-06 0 10p", "!.tran 0 2.31e-06 0 10p"); assert "2.31e-06" in s
                d = sim(_prepare(s, work, f"delay_B{bit}_{trig}_{other}{oval}.asc", models)); t = d["time"]
                # (A, Cin) after the step
                a_ = 1 if trig == "a" else oval; c_ = 1 if trig == "cin" else oval
                before = float(np.interp(t_trig - 0.2e-9, t, d["v(cout)"])); after = float(np.interp(t_trig + 1.0e-9, t, d["v(cout)"]))
                ti = M.cross(t, d["v(" + trig + ")"], vdd / 2, t_trig - 0.2e-9)
                to = M.cross(t, d["v(cout)"], vdd / 2, t_trig - 0.2e-9)
                rises = before < vdd / 2 <= after
                out.append({"B": bit, "step_input": trig, "other_input": other, "other_value": oval,
                            "A_after": a_, "Cin_after": c_, "cout_expected": int(a_ + bit + c_ >= 2),
                            "cout_before_V": before, "cout_after_V": after,
                            "t_plh_ps": (to - ti) * 1e12 if (rises and ti is not None and to is not None) else None})
    return out

def measure(models=None, keep_waves=False, src=None):
    """Run B=1 and B=0 on the schematic (+ static DC) and return all metrics. `models`: alternative model-file folder."""
    work = tempfile.mkdtemp(prefix="fa_atype_")
    try:
        net = net_text(work, models, src); check_stimulus(net); vdd = _vdd(net)
        out = {"vdd": vdd, "n_fet": device_counts(net)[0], "n_fgfet": device_counts(net)[1], "B": {}}
        waves = {}
        for bit in (1, 0):
            d = waves[bit] = sim(_prepare(asc_text(bit, True, src), work, f"{STEM}_B{bit}.asc", models)); t = d["time"]
            vmn = {k: float(np.interp(T_LOGIC, t, d[f"v(xfg_{k}:mn)"])) for k in ("s1", "s2", "s3", "s4", "c1", "c2", "c3")}
            logic = M.logic_check(d, bit, vdd, T_LOGIC)
            per = [{"A": c["A"], "B": bit, "Cin": c["Cin"],
                    "p_avg_W": M.p_avg(d, vdd, T_LOGIC + (int(c["window_ns"].split("-")[0]) - 1) * 1e-9, 2e-9)} for c in logic]   # precharge + evaluate period of each combination
            out["B"][bit] = {"p_avg_W": M.p_avg(d, vdd, T_LOGIC), "p_avg_per_combo": per, "logic": logic, "vmn_read": vmn}
            s = sim(_write(work, f"static_B{bit}.cir", static_netlist(net, bit, vmn, models)))
            out["B"][bit]["static_states_W"] = [float(x) for x in -vdd * s["i(vdd)"]]
            out["B"][bit]["static_table"] = [{"CLK": 0, "A": (k >> 1) & 1, "B": bit, "Cin": k & 1, "p_static_W": float(-vdd * s["i(vdd)"][k])} for k in range(4)]   # state index = 4 CLK + 2 A + Cin
        out["delay_cases"] = delay_sweep(models, work, vdd)
        c_cin = [c["t_plh_ps"] for c in out["delay_cases"] if c["B"] == 1 and c["step_input"] == "cin" and c["other_value"] == 0 and c["t_plh_ps"] is not None]
        c_a = [c["t_plh_ps"] for c in out["delay_cases"] if c["B"] == 1 and c["step_input"] == "a" and c["other_value"] == 0 and c["t_plh_ps"] is not None]
        tp = (c_cin[0] * 1e-12) if c_cin else None
        out["t_plh_cin_cout_s"] = tp
        out["t_plh_a_cout_s"] = (c_a[0] * 1e-12) if c_a else None
        st8 = out["B"][1]["static_states_W"][:4] + out["B"][0]["static_states_W"][:4]
        p_avg = 0.5 * (out["B"][1]["p_avg_W"] + out["B"][0]["p_avg_W"]); p_st = float(np.mean(st8))
        out["headline"] = {"t_plh_cin_cout_ps": None if tp is None else tp * 1e12,
            "t_plh_a_cout_ps": None if out["t_plh_a_cout_s"] is None else out["t_plh_a_cout_s"] * 1e12,
            "t_worst_ps": None if (tp is None or out["t_plh_a_cout_s"] is None) else max(tp, out["t_plh_a_cout_s"]) * 1e12,
            "t_phl": "undefined (dynamic logic: Cout only resets on CLK)",
            "p_avg_uW": p_avg * 1e6, "p_avg_B1_uW": out["B"][1]["p_avg_W"] * 1e6, "p_avg_B0_uW": out["B"][0]["p_avg_W"] * 1e6,
            "p_static_avg_nW": p_st * 1e9, "p_static_max_nW": float(np.max(st8)) * 1e9, "p_dyn_uW": (p_avg - p_st) * 1e6,
            "e_cycle_fJ": (p_avg - p_st) * 2e-9 * 1e15, "pdp_aJ": None if tp is None else (p_avg - p_st) * tp * 1e18,
            "n_fet": out["n_fet"], "n_fgfet": out["n_fgfet"],
            "logic_ok": all(x["ok"] for b in (1, 0) for x in out["B"][b]["logic"])}
        return (out, waves) if keep_waves else out
    finally:
        shutil.rmtree(work, ignore_errors=True)

def _write(work, name, text):
    p = os.path.join(work, name); open(p, "w").write(text); return p
