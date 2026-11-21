#!/usr/bin/env python3
"""Unified simulation and verification runner for all three FGFET Full Adders (A, B, C)
in the final/ package, sharing the exact same models in final/models/.

Matches Table 3 of Kim et al., IEEE Access 2023.
"""
import json, os, re, shutil, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FINAL_ROOT = os.path.abspath(os.path.join(HERE, ".."))
MODELS_DIR = os.path.join(FINAL_ROOT, "models")
RESULTS_DIR = os.path.join(FINAL_ROOT, "results")
SYMBOL_FILE = os.path.join(FINAL_ROOT, "FGFET.asy")
os.makedirs(RESULTS_DIR, exist_ok=True)

sys.path.insert(0, HERE)
from verify_28fet import verify as verify_28fet
import metrics as M
from ltraw import read_raw

WIN_LTSPICE = r"C:\Users\VedantM\AppData\Local\Programs\ADI\LTspice\LTspice.exe"
T_LOGIC = 2.29e-6

def _run_ltspice(args):
    if sys.platform == "win32" and os.path.exists(WIN_LTSPICE):
        subprocess.run([WIN_LTSPICE] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return
    exe = os.environ.get("LTSPICE_EXE")
    if exe and os.path.exists(exe):
        subprocess.run([exe] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return
    raise RuntimeError("LTspice executable not found.")

def sim(path):
    for _ in range(4):
        for ext in (".raw", ".log"):
            p = path[:-4] + ext
            if os.path.exists(p): os.remove(p)
        _run_ltspice(["-b", path])
        if os.path.exists(path[:-4] + ".raw"): break
    else:
        sys.exit(f"LTspice produced no raw file for {path}")
    return read_raw(path[:-4] + ".raw")

def _models_rel(text):
    m = re.search(r"\.include\s+(\S+)/cmos_32nm\.pm", text)
    assert m, "schematic has no .include of cmos_32nm.pm"
    return m.group(1)

def _prepare(text, workdir, name):
    rel = _models_rel(text)
    # Use forward slashes for LTspice compatibility
    models_abs = MODELS_DIR.replace("\\", "/")
    text = text.replace(rel, models_abs)
    shutil.copy(SYMBOL_FILE, workdir)
    path = os.path.join(workdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path

def net_text(asc_text_str, workdir):
    p = _prepare(asc_text_str, workdir, "net.asc")
    _run_ltspice(["-netlist", p])
    return open(p[:-4] + ".net", "r", encoding="utf-8").read()

def _vdd(net):
    m = re.search(r"^Vdd\s+\S+\s+0\s+([0-9.eE+-]+)\s*$", net, re.M)
    assert m, "no DC Vdd source in the schematic"
    return float(m.group(1))

def device_counts(net):
    nf = sum(1 for l in net.splitlines() if l[:1] == "M" and not l.startswith("M_VFET") and not l.startswith("M_SFET"))
    ng = sum(1 for l in net.splitlines() if l[:1] == "X" or "FGFET" in l)
    return nf, ng

# ==============================================================================
# Circuit A
# ==============================================================================
def prepare_asc_a(bit=1):
    src = open(os.path.join(FINAL_ROOT, "full_adder_atype.asc"), "r", encoding="utf-8").read()
    level = "1.9" if bit == 1 else "0.05"
    src, n = re.subn(r"(1\.105e-06 )[-0-9.eE+]+( 2\.2e-06 )[-0-9.eE+]+", lambda m: m.group(1) + level + m.group(2) + level, src)
    assert n == 1
    return src

def static_netlist_a(net, bit, vmn):
    vdd = _vdd(net)
    models_spice = MODELS_DIR.replace("\\", "/")
    L = [f"* static power A-type B={bit}",
         f".include {models_spice}/cmos_32nm.pm", f".include {models_spice}/sfet_32nm.pm", "",
         f"Vdd Vdd 0 {vdd}", f"Vmn mn 0 {vmn:.6f}", "Vst st 0 0", f"Bclk clk 0 V={vdd}*floor(V(st)/4)",
         f"Ba a 0 V={vdd}*(floor(V(st)/2)-2*floor(V(st)/4))", f"Bcin cin 0 V={vdd}*(V(st)-2*floor(V(st)/2))", ""]
    for ln in net.splitlines():
        t = ln.split(";")[0].split()
        if not t: continue
        if t[0][0] in "MC": L.append(ln.split(";")[0])
        elif t[0][0] == "X":
            par = dict(p.split("=") for p in t[7:] if "=" in p)
            L.append(f"M{t[0][2:]} {t[3]} mn {t[4]} {t[5]} sfet_nmos L=32n W={par['w_dev']} delvto={par.get('delvto_val','0')}")
    return "\n".join(L + ["", ".options gmin=1e-15 numdgt=15", ".dc Vst 0 7 1", ".end"]) + "\n"

def run_circuit_a():
    print("Simulating A-type Full Adder...")
    work = tempfile.mkdtemp(prefix="fa_final_a_")
    try:
        shutil.copy(SYMBOL_FILE, work)
        src1 = prepare_asc_a(1)
        src0 = prepare_asc_a(0)
        net = net_text(src1, work)
        vdd = _vdd(net)
        
        p1 = _prepare(src1, work, "atype_B1.asc")
        p0 = _prepare(src0, work, "atype_B0.asc")
        d1 = sim(p1); d0 = sim(p0)
        
        t = d1["time"]
        vmn1 = {k: float(np.interp(T_LOGIC, t, d1[f"v(xfg_{k}:mn)"])) for k in ("cout", "or", "sum")}
        vmn0 = {k: float(np.interp(T_LOGIC, d0["time"], d0[f"v(xfg_{k}:mn)"])) for k in ("cout", "or", "sum")}
        
        # Static
        s1_cir = os.path.join(work, "static_B1.cir")
        open(s1_cir, "w").write(static_netlist_a(net, 1, float(np.mean(list(vmn1.values())))))
        s0_cir = os.path.join(work, "static_B0.cir")
        open(s0_cir, "w").write(static_netlist_a(net, 0, float(np.mean(list(vmn0.values())))))
        s1 = sim(s1_cir); s0 = sim(s0_cir)
        st8 = [float(x) for x in -vdd * s1["i(vdd)"][:4]] + [float(x) for x in -vdd * s0["i(vdd)"][:4]]
        pst = float(np.mean(st8)) * 1e9
        
        p1_avg = M.p_avg(d1, vdd, T_LOGIC)
        p0_avg = M.p_avg(d0, vdd, T_LOGIC)
        pavg = 0.5 * (p1_avg + p0_avg)
        pdyn = (pavg - pst * 1e-9) * 1e6
        
        # A-type delay from evaluation pulse
        td = M.delay_data(d1, "cin", 9.5, vdd, T_LOGIC) * 1e12
        pdp = pdyn * td

        l1 = M.logic_check(d1, 1, vdd, T_LOGIC)
        l0 = M.logic_check(d0, 0, vdd, T_LOGIC)
        logic_ok = all(x["ok"] for x in l1 + l0)
        
        # Save compressed waves
        np.savez_compressed(os.path.join(RESULTS_DIR, "wave_A_B1.npz"), time=d1["time"], v_clk=d1["v(clk)"], v_a=d1["v(a)"], v_cin=d1["v(cin)"], v_sum=d1["v(sum)"], v_cout=d1["v(cout)"], i_vdd=d1["i(vdd)"])
        np.savez_compressed(os.path.join(RESULTS_DIR, "wave_A_B0.npz"), time=d0["time"], v_clk=d0["v(clk)"], v_a=d0["v(a)"], v_cin=d0["v(cin)"], v_sum=d0["v(sum)"], v_cout=d0["v(cout)"], i_vdd=d0["i(vdd)"])
        
        # Multi-window dynamic power analysis
        m1_act = (d1["time"] >= T_LOGIC + 2e-9) & (d1["time"] <= T_LOGIC + 8e-9)
        m0_act = (d0["time"] >= T_LOGIC + 2e-9) & (d0["time"] <= T_LOGIC + 8e-9)
        p_act = 0.5 * (np.trapezoid(-d1["i(vdd)"][m1_act], d1["time"][m1_act]) + np.trapezoid(-d0["i(vdd)"][m0_act], d0["time"][m0_act])) / 6e-9 * vdd - pst * 1e-9
        
        m1_c3 = (d1["time"] >= T_LOGIC + 4e-9) & (d1["time"] <= T_LOGIC + 6e-9)
        p_c3 = np.trapezoid(-d1["i(vdd)"][m1_c3], d1["time"][m1_c3]) / 2e-9 * vdd - pst * 1e-9
        
        return {
            "type": "A-type",
            "transistor_count": "16 FET + 3 FGFET (19 total)",
            "vdd": vdd,
            "t_plh_ps": td,
            "p_static_nW": pst,
            "p_dyn_uW": pdyn,
            "p_dyn_active_cycles_uW": p_act * 1e6,
            "p_dyn_c3_uW": p_c3 * 1e6,
            "pdp_aWs": pdp,
            "logic_ok": logic_ok,
            "vmn_read_B1": vmn1,
            "vmn_read_B0": vmn0
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ==============================================================================
# Circuit B
# ==============================================================================
def prepare_asc_b(bit=1):
    src = open(os.path.join(FINAL_ROOT, "full_adder_btype.asc"), "r", encoding="utf-8").read()
    level_b = "1.8" if bit == 1 else "0.1"
    level_nb = "0.1" if bit == 1 else "1.8"
    src, n1 = re.subn(r"(Vb b 0 PWL\(0 0 1\.1e-6 0 1\.105e-6 )[-0-9.eE+]+( 2\.2e-6 )[-0-9.eE+]+", lambda m: m.group(1) + level_b + m.group(2) + level_b, src)
    src, n2 = re.subn(r"(Vnb nb 0 PWL\(0 0 1\.1e-6 0 1\.105e-6 )[-0-9.eE+]+( 2\.2e-6 )[-0-9.eE+]+", lambda m: m.group(1) + level_nb + m.group(2) + level_nb, src)
    assert n1 == 1 and n2 == 1
    return src

def static_netlist_b(net, bit, vmn_map):
    vdd = _vdd(net)
    models_spice = MODELS_DIR.replace("\\", "/")
    vmn_val = float(np.mean(list(vmn_map.values()))) if isinstance(vmn_map, dict) else float(vmn_map)
    L = [f"* static power B-type B={bit}",
         f".include {models_spice}/cmos_32nm.pm", f".include {models_spice}/sfet_32nm.pm", "",
         f"Vdd Vdd 0 {vdd}", "Vst st 0 0", f"Bclk clk 0 V={vdd}*floor(V(st)/4)",
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
            par = dict(p.split("=") for p in t[7:] if "=" in p)
            dev_m = re.search(r"xfg_([a-z0-9_]+)", t[0].lower())
            dev_key = dev_m.group(1) if dev_m else "s1"
            v_dev = vmn_map.get(dev_key, vmn_val) if isinstance(vmn_map, dict) else vmn_val
            w_val = par.get("w_dev", "78.3n"); delvto = par.get("delvto_val", "0.9")
            L.append(f"Vmn_{dev_key} mn_{dev_key} 0 {v_dev:.6f}")
            L.append(f"M{t[0][1:]} {t[3]} mn_{dev_key} {t[4]} {t[5]} sfet_nmos L=32n W={w_val} delvto={delvto}")
    return "\n".join(L + ["", ".options gmin=1e-15 numdgt=15", ".dc Vst 0 7 1", ".end"]) + "\n"

def run_circuit_b():
    print("Simulating B-type Full Adder...")
    work = tempfile.mkdtemp(prefix="fa_final_b_")
    try:
        shutil.copy(SYMBOL_FILE, work)
        src1 = prepare_asc_b(1)
        src0 = prepare_asc_b(0)
        net = net_text(src1, work)
        vdd = _vdd(net)
        
        p1 = _prepare(src1, work, "btype_B1.asc")
        p0 = _prepare(src0, work, "btype_B0.asc")
        d1 = sim(p1); d0 = sim(p0)
        
        t = d1["time"]
        vmn1 = {k: float(np.interp(T_LOGIC, t, d1[f"v(xfg_{k}:mn)"])) for k in ("s1", "s2", "s3", "s4", "c1", "c2", "c3")}
        vmn0 = {k: float(np.interp(T_LOGIC, d0["time"], d0[f"v(xfg_{k}:mn)"])) for k in ("s1", "s2", "s3", "s4", "c1", "c2", "c3")}
        
        # Static
        s1_cir = os.path.join(work, "static_B1.cir")
        open(s1_cir, "w").write(static_netlist_b(net, 1, vmn1))
        s0_cir = os.path.join(work, "static_B0.cir")
        open(s0_cir, "w").write(static_netlist_b(net, 0, vmn0))
        s1 = sim(s1_cir); s0 = sim(s0_cir)
        st8 = [float(x) for x in -vdd * s1["i(vdd)"][:4]] + [float(x) for x in -vdd * s0["i(vdd)"][:4]]
        pst = float(np.mean(st8)) * 1e9
        
        p1_avg = M.p_avg(d1, vdd, T_LOGIC)
        p0_avg = M.p_avg(d0, vdd, T_LOGIC)
        pavg = 0.5 * (p1_avg + p0_avg)
        pdyn = (pavg - pst * 1e-9) * 1e6
        
        # B-type single-step Cout delay (B=1, A=0, Cin step)
        s_d = src1
        s_d = re.sub(r"(!Vclk clk 0 )PWL\([^)]*\)", r"\1PWL(0 0.9 2.28e-06 0.9 2.285e-06 0 2.2999e-06 0 2.29995e-06 0.9)", s_d)
        s_d = re.sub(r"(!Vcin cin 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.3005e-06 0 2.30055e-06 0.9)", s_d)
        s_d = re.sub(r"(!Vncin ncin 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.29995e-06 0.9 2.3005e-06 0.9 2.30055e-06 0)", s_d)
        s_d = re.sub(r"(!Va a 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.4e-06 0)", s_d)
        s_d = re.sub(r"(!Vna na 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.29995e-06 0.9)", s_d)
        s_d = re.sub(r"(!Vwl_a wl_a 0 )PWL\([^)]*\)", r"\1PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0)", s_d)
        s_d = re.sub(r"(!Vwl_na wl_na 0 )PWL\([^)]*\)", r"\1PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0 2.29995e-6 1.8)", s_d)
        s_d = s_d.replace("!.tran 0 3e-06 0 10p", "!.tran 0 2.31e-06 0 10p")
        p_d = _prepare(s_d, work, "delay_b.asc")
        dd = sim(p_d); tt = dd["time"]
        ti = M.cross(tt, dd["v(cin)"], vdd / 2, 2.3003e-6)
        to = M.cross(tt, dd["v(cout)"], vdd / 2, 2.3003e-6)
        td = (to - ti) * 1e12 if (ti is not None and to is not None) else None
        pdp = pdyn * td if td else None
        
        l1 = M.logic_check(d1, 1, vdd, T_LOGIC)
        l0 = M.logic_check(d0, 0, vdd, T_LOGIC)
        logic_ok = all(x["ok"] for x in l1 + l0)
        
        # Save compressed waves
        np.savez_compressed(os.path.join(RESULTS_DIR, "wave_B_B1.npz"), time=d1["time"], v_clk=d1["v(clk)"], v_a=d1["v(a)"], v_cin=d1["v(cin)"], v_sum=d1["v(sum)"], v_cout=d1["v(cout)"], i_vdd=d1["i(vdd)"])
        np.savez_compressed(os.path.join(RESULTS_DIR, "wave_B_B0.npz"), time=d0["time"], v_clk=d0["v(clk)"], v_a=d0["v(a)"], v_cin=d0["v(cin)"], v_sum=d0["v(sum)"], v_cout=d0["v(cout)"], i_vdd=d0["i(vdd)"])
        
        # Multi-window dynamic power analysis
        m1_act = (d1["time"] >= T_LOGIC + 2e-9) & (d1["time"] <= T_LOGIC + 8e-9)
        m0_act = (d0["time"] >= T_LOGIC + 2e-9) & (d0["time"] <= T_LOGIC + 8e-9)
        p_act = 0.5 * (np.trapezoid(-d1["i(vdd)"][m1_act], d1["time"][m1_act]) + np.trapezoid(-d0["i(vdd)"][m0_act], d0["time"][m0_act])) / 6e-9 * vdd - pst * 1e-9
        
        m1_c3 = (d1["time"] >= T_LOGIC + 4e-9) & (d1["time"] <= T_LOGIC + 6e-9)
        p_c3 = np.trapezoid(-d1["i(vdd)"][m1_c3], d1["time"][m1_c3]) / 2e-9 * vdd - pst * 1e-9

        return {
            "type": "B-type",
            "transistor_count": "13 FET + 7 FGFET (20 total)",
            "vdd": vdd,
            "t_plh_ps": td,
            "p_static_nW": pst,
            "p_dyn_uW": pdyn,
            "p_dyn_active_cycles_uW": p_act * 1e6,
            "p_dyn_c3_uW": p_c3 * 1e6,
            "pdp_aWs": pdp,
            "logic_ok": logic_ok,
            "vmn_read_B1": vmn1,
            "vmn_read_B0": vmn0
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)

# ==============================================================================
# Circuit C
# ==============================================================================
def prepare_asc_c(bit=1):
    src = open(os.path.join(FINAL_ROOT, "full_adder_ctype.asc"), "r", encoding="utf-8").read()
    level_b = "1.85" if bit == 1 else "0.85"
    level_nb = "0.85" if bit == 1 else "1.85"
    src, n1 = re.subn(r"(Vb b 0 PWL\(0 0 1\.1e-6 0 1\.105e-6 )[-0-9.eE+]+( 2\.2e-6 )[-0-9.eE+]+", lambda m: m.group(1) + level_b + m.group(2) + level_b, src)
    src, n2 = re.subn(r"(Vnb nb 0 PWL\(0 0 1\.1e-6 0 1\.105e-6 )[-0-9.eE+]+( 2\.2e-6 )[-0-9.eE+]+", lambda m: m.group(1) + level_nb + m.group(2) + level_nb, src)
    assert n1 == 1 and n2 == 1
    return src

def static_netlist_c(net, bit, vmn_map):
    vdd = _vdd(net)
    models_spice = MODELS_DIR.replace("\\", "/")
    vmn_val = float(np.mean(list(vmn_map.values()))) if isinstance(vmn_map, dict) else float(vmn_map)
    L = [f"* static power C-type B={bit}",
         f".include {models_spice}/cmos_32nm.pm", f".include {models_spice}/sfet_32nm.pm", "",
         f"Vdd Vdd 0 {vdd}", "Vst st 0 0", f"Bclk clk 0 V={vdd}*floor(V(st)/4)",
         f"Ba a 0 V=if(V(clk)>0.45, 1.0*(floor(V(st)/2)-2*floor(V(st)/4)), 0)",
         f"Bcin cin 0 V=if(V(clk)>0.45, 1.0*(V(st)-2*floor(V(st)/2)), 0)",
         f"Bna na 0 V=if(V(clk)>0.45, 1.0-V(a), 0)", f"Bncin ncin 0 V=if(V(clk)>0.45, 1.0-V(cin), 0)",
         f"Bwla wl_a 0 V=if(V(clk)>0.45, 1.2*V(a)/1.0, 0)", f"Bwl0 wl_0 0 V=0", ""]
    for ln in net.splitlines():
        t = ln.split(";")[0].split()
        if not t: continue
        if t[0][0] in "MC": L.append(ln.split(";")[0])
        elif t[0][0] == "X":
            dev_m = re.search(r"xfg_([a-z0-9_]+)", t[0].lower())
            dev_key = dev_m.group(1) if dev_m else "s1"
            par = dict(p.split("=") for p in t[7:] if "=" in p)
            v_dev = vmn_map.get(dev_key, vmn_val) if isinstance(vmn_map, dict) else vmn_val
            w_val = par.get("w_dev", "78.3n")
            delv_val = par.get("delvto_val", "0")
            L.append(f"Vmn_{dev_key} mn_{dev_key} 0 {v_dev:.6f}")
            L.append(f"M{dev_key} {t[3]} mn_{dev_key} {t[4]} {t[5]} sfet_nmos L=32n W={w_val} delvto={delv_val}")
    return "\n".join(L + ["", ".options gmin=1e-15 numdgt=15", ".dc Vst 0 7 1", ".end"]) + "\n"

def run_circuit_c():
    print("Simulating C-type Full Adder...")
    work = tempfile.mkdtemp(prefix="fa_final_c_")
    try:
        shutil.copy(SYMBOL_FILE, work)
        src1 = prepare_asc_c(1)
        src0 = prepare_asc_c(0)
        net = net_text(src1, work)
        vdd = _vdd(net)
        
        p1 = _prepare(src1, work, "ctype_B1.asc")
        p0 = _prepare(src0, work, "ctype_B0.asc")
        d1 = sim(p1); d0 = sim(p0)
        
        t = d1["time"]
        vmn1 = {k: float(np.interp(T_LOGIC, t, d1[f"v(xfg_{k}:mn)"])) for k in ("s1", "s2", "s3", "s4", "c1", "c2")}
        vmn0 = {k: float(np.interp(T_LOGIC, d0["time"], d0[f"v(xfg_{k}:mn)"])) for k in ("s1", "s2", "s3", "s4", "c1", "c2")}
        
        # Static
        s1_cir = os.path.join(work, "static_B1.cir")
        open(s1_cir, "w").write(static_netlist_c(net, 1, vmn1))
        s0_cir = os.path.join(work, "static_B0.cir")
        open(s0_cir, "w").write(static_netlist_c(net, 0, vmn0))
        s1 = sim(s1_cir); s0 = sim(s0_cir)
        st8 = [float(x) for x in -vdd * s1["i(vdd)"][:4]] + [float(x) for x in -vdd * s0["i(vdd)"][:4]]
        pst = float(np.mean(st8)) * 1e9
        
        p1_avg = M.p_avg(d1, vdd, T_LOGIC)
        p0_avg = M.p_avg(d0, vdd, T_LOGIC)
        pavg = 0.5 * (p1_avg + p0_avg)
        pdyn = (pavg - pst * 1e-9) * 1e6
        
        # C-type single-step Cout delay (B=1, A=0, Cin step)
        s_d = src1
        s_d = re.sub(r"(!Vclk clk 0 )PWL\([^)]*\)", r"\1PWL(0 0.9 2.28e-06 0.9 2.285e-06 0 2.2999e-06 0 2.29995e-06 0.9)", s_d)
        s_d = re.sub(r"(!Vcin cin 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.3005e-06 0 2.30055e-06 1.0)", s_d)
        s_d = re.sub(r"(!Vncin ncin 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.29995e-06 1.0 2.3005e-06 1.0 2.30055e-06 0)", s_d)
        s_d = re.sub(r"(!Va a 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.4e-06 0)", s_d)
        s_d = re.sub(r"(!Vna na 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.29995e-06 1.0)", s_d)
        s_d = re.sub(r"(!Vwl_a wl_a 0 )PWL\([^)]*\)", r"\1PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0)", s_d)
        s_d = s_d.replace("!.tran 0 3e-06 0 10p", "!.tran 0 2.31e-06 0 10p")
        p_d = _prepare(s_d, work, "delay_c.asc")
        dd = sim(p_d); tt = dd["time"]
        ti = M.cross(tt, dd["v(cin)"], 0.5, 2.3003e-6)
        to = M.cross(tt, dd["v(cout)"], vdd / 2, 2.3003e-6)
        td = (to - ti) * 1e12 if (ti is not None and to is not None) else None
        pdp = pdyn * td if td else None

        l1 = M.logic_check(d1, 1, vdd, T_LOGIC)
        l0 = M.logic_check(d0, 0, vdd, T_LOGIC)
        logic_ok = all(x["ok"] for x in l1 + l0)
        
        np.savez_compressed(os.path.join(RESULTS_DIR, "wave_C_B1.npz"), time=d1["time"], v_clk=d1["v(clk)"], v_a=d1["v(a)"], v_cin=d1["v(cin)"], v_sum=d1["v(sum)"], v_cout=d1["v(cout)"], i_vdd=d1["i(vdd)"])
        np.savez_compressed(os.path.join(RESULTS_DIR, "wave_C_B0.npz"), time=d0["time"], v_clk=d0["v(clk)"], v_a=d0["v(a)"], v_cin=d0["v(cin)"], v_sum=d0["v(sum)"], v_cout=d0["v(cout)"], i_vdd=d0["i(vdd)"])
        
        # Multi-window dynamic power analysis
        m1_act = (d1["time"] >= T_LOGIC + 2e-9) & (d1["time"] <= T_LOGIC + 8e-9)
        m0_act = (d0["time"] >= T_LOGIC + 2e-9) & (d0["time"] <= T_LOGIC + 8e-9)
        p_act = 0.5 * (np.trapezoid(-d1["i(vdd)"][m1_act], d1["time"][m1_act]) + np.trapezoid(-d0["i(vdd)"][m0_act], d0["time"][m0_act])) / 6e-9 * vdd - pst * 1e-9
        
        m1_c3 = (d1["time"] >= T_LOGIC + 4e-9) & (d1["time"] <= T_LOGIC + 6e-9)
        p_c3 = np.trapezoid(-d1["i(vdd)"][m1_c3], d1["time"][m1_c3]) / 2e-9 * vdd - pst * 1e-9

        return {
            "type": "C-type",
            "transistor_count": "15 FET + 6 FGFET (21 total)",
            "vdd": vdd,
            "t_plh_ps": td,
            "p_static_nW": pst,
            "p_dyn_uW": pdyn,
            "p_dyn_active_cycles_uW": p_act * 1e6,
            "p_dyn_c3_uW": p_c3 * 1e6,
            "pdp_aWs": pdp,
            "logic_ok": logic_ok,
            "vmn_read_B1": vmn1,
            "vmn_read_B0": vmn0
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)

def main():
    res_a = run_circuit_a()
    res_b = run_circuit_b()
    res_c = run_circuit_c()
    
    baseline = verify_28fet()
    all_res = {"28FET": baseline, "A": res_a, "B": res_b, "C": res_c}
    print("Figure 5(a):", baseline)
    with open(os.path.join(RESULTS_DIR, "metrics_final.json"), "w", encoding="utf-8") as f:
        json.dump(all_res, f, indent=2)
    
    print("\n" + "=" * 80)
    print("FINAL BENCHMARK RESULTS (ALL USING UNIFIED MODELS IN final/models/)")
    print("=" * 80)
    print(f"{'Circuit':<8} | {'T_D (ps)':<18} | {'P_static (nW)':<18} | {'P_DYN [active]':<18} | {'P_DYN [8ns]':<16} | {'Logic':<6}")
    print("-" * 90)
    
    targets = {
        "A": {"td": 43.54, "pst": 13.64, "pdyn": 1.14, "pdp": 49.64},
        "B": {"td": 41.25, "pst": 5.37,  "pdyn": 1.08, "pdp": 44.55},
        "C": {"td": 16.44, "pst": 5.55,  "pdyn": 0.93, "pdp": 15.29},
    }
    
    for k in ("A", "B", "C"):
        r = all_res[k]; tgt = targets[k]
        dev_td = (r["t_plh_ps"] - tgt["td"]) / tgt["td"] * 100
        dev_pst = (r["p_static_nW"] - tgt["pst"]) / tgt["pst"] * 100
        dev_pdyn_act = (r["p_dyn_active_cycles_uW"] - tgt["pdyn"]) / tgt["pdyn"] * 100
        dev_pdyn_8ns = (r["p_dyn_uW"] - tgt["pdyn"]) / tgt["pdyn"] * 100
        
        print(f"{k}-type    | {r['t_plh_ps']:5.2f} (tgt {tgt['td']:5.2f}, {dev_td:+5.1f}%) | {r['p_static_nW']:5.2f} (tgt {tgt['pst']:5.2f}, {dev_pst:+5.1f}%) | {r['p_dyn_active_cycles_uW']:5.2f} uW ({dev_pdyn_act:+5.1f}%) | {r['p_dyn_uW']:5.2f} uW ({dev_pdyn_8ns:+5.1f}%) | {str(r['logic_ok']):<6}")
    print("=" * 90)

if __name__ == "__main__":
    main()
