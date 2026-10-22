"""Thin ngspice batch-mode wrapper used by the fitting scripts and the tests."""
import os
import shutil
import subprocess
import tempfile

import numpy as np

NGSPICE = shutil.which("ngspice") or os.path.expanduser("~/.local/bin/ngspice")
OPENVAF = shutil.which("openvaf") or os.path.expanduser("~/.local/bin/openvaf")


def run(netlist, files=(), workdir=None, timeout=300):
    """Run `netlist` in batch mode and return {name: text} for the listed output files."""
    tmp = workdir or tempfile.mkdtemp(prefix="ngs_")
    path = os.path.join(tmp, "run.sp")
    with open(path, "w") as f:
        f.write(netlist)
    p = subprocess.run([NGSPICE, "-b", path], cwd=tmp, capture_output=True, text=True, timeout=timeout)
    out = {}
    for name in files:
        fp = os.path.join(tmp, name)
        if not os.path.exists(fp):
            raise RuntimeError(f"ngspice produced no {name}\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
        out[name] = open(fp).read()
    if workdir is None:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def load_cols(text):
    rows = [l.split() for l in text.strip().splitlines()]
    rows = [r for r in rows if r and not r[0][0].isalpha()]
    return np.array(rows, float)


def idvg(card_path, model, w, l, vds_list, vg_stop=3.0, vg_step=0.01, inst=""):
    """Id-Vg sweeps (Vs = Vb = 0). Returns vg, {vds: Id[A]}."""
    ctrl = []
    for i, vds in enumerate(vds_list):
        ctrl += [f"alter vd dc = {vds}", f"dc vg 0 {vg_stop} {vg_step}",
                 "let id = -i(vd)", f"wrdata iv{i}.txt id"]
    net = f"""* idvg
.include {card_path}
vd d 0 0.05
vg g 0 0
m1 d g 0 0 {model} w={w} l={l} {inst}
.option gmin=1e-18
.control
set wr_singlescale
{chr(10).join(ctrl)}
quit
.endc
.end
"""
    out = run(net, [f"iv{i}.txt" for i in range(len(vds_list))])
    res = {}
    for i, vds in enumerate(vds_list):
        d = load_cols(out[f"iv{i}.txt"])
        vg, res[vds] = d[:, 0], d[:, 1]
    return vg, res


def cgg(card_path, model, w, l, vgs, inst="", freq=1e6):
    """Small-signal gate capacitance Cgg = -Im(Ig)/w at Vds = Vbs = 0."""
    vlist = " ".join(f"{v:.4f}" for v in vgs)
    net = f"""* cgg
.include {card_path}
vd d 0 0
vg g 0 dc 0 ac 1
m1 d g 0 0 {model} w={w} l={l} {inst}
.control
foreach v {vlist}
  alter vg dc = $v
  ac lin 1 {freq} {freq}
  let cg = -imag(i(vg))/(2*3.141592653589793*{freq})
  echo "$v $&cg" >> cv.txt
end
quit
.endc
.end
"""
    d = load_cols(run(net, ["cv.txt"])["cv.txt"])
    return d[:, 0], d[:, 1]


def load_target(path):
    d = np.loadtxt(path, delimiter=",", skiprows=1)
    d = d[np.argsort(d[:, 0])]
    return d[:, 0], d[:, 1]
