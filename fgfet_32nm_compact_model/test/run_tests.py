#!/usr/bin/env python3
"""Validation suite for the generated FGFET model files.

Every testbench is written to test/netlists/<name>.sp (runnable on its own
with `ngspice -b <name>.sp` from that directory), raw waveforms go to
test/results/, plots to test/plots/ and a pass/fail summary to
test/results/summary.md.

  T1  SFET  Id-Vg / Cgg-Vg  vs. Fig. 2(a),(c) TCAD
  T2  VFET  Id-Vg / Cgg-Vg  vs. Fig. 2(b),(d) TCAD
  T3  FGFET memory-node transient vs. Fig. 4 (Table II sequence)
  T4  Table II read: SL current for stored '1' vs '0'
  T5  Floating-node charge conservation (100 storage/read cycles) and retention
  T6  Bias schemes of the A-, B- (AND, DELVTO = 0.9 V) and C-type (OR) adders
"""
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import spice  # noqa: E402

DATA = os.path.join(ROOT, "data")
NET = os.path.join(HERE, "netlists")
RES = os.path.join(HERE, "results")
PLOTS = os.path.join(HERE, "plots")
REL = "../../models"                 # model directory as seen from test/netlists
OSDI = f"{REL}/cva_cap.osdi"

for d in (NET, RES, PLOTS):
    os.makedirs(d, exist_ok=True)

RESULTS = []                         # (test id, check, value, limit, passed)


def check(tid, what, value, limit, ok):
    RESULTS.append((tid, what, value, limit, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {tid} {what}: {value} (limit {limit})")


def ngspice(name, body, outputs):
    path = os.path.join(NET, f"{name}.sp")
    with open(path, "w") as f:
        f.write(body)
    p = subprocess.run([spice.NGSPICE, "-b", f"{name}.sp"], cwd=NET, capture_output=True, text=True)
    out = {}
    for o in outputs:
        fp = os.path.join(RES, o)
        if not os.path.exists(fp):
            sys.exit(f"{name}: ngspice did not write {o}\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
        out[o] = spice.load_cols(open(fp).read())
    return out


def target(name):
    return spice.load_target(os.path.join(DATA, name))


# ---------------------------------------------------------------- T1 / T2
def device_test(tid, prefix, card, model, length, iv_lim, cv_lim):
    print(f"{tid}: {prefix.upper()} DC / C-V")
    for o in (f"{prefix}_iv0.txt", f"{prefix}_iv1.txt", f"{prefix}_cv.txt"):
        if os.path.exists(os.path.join(RES, o)):
            os.remove(os.path.join(RES, o))
    vlist = " ".join(f"{v:.2f}" for v in np.arange(0.0, 3.0001, 0.05))
    body = f"""* {tid}: {prefix.upper()} Id-Vg (Vds = 0.05 V, 1 V) and Cgg-Vg (Vds = 0), W = 1 um
.include {REL}/{card}
vd d 0 0.05
vg g 0 dc 0 ac 1
m1 d g 0 0 {model} w=1u l={length}
.option gmin=1e-18
.control
set wr_singlescale
dc vg 0 3 0.01
let id = -i(vd)
wrdata ../results/{prefix}_iv0.txt id
alter vd dc = 1.0
dc vg 0 3 0.01
let id = -i(vd)
wrdata ../results/{prefix}_iv1.txt id
alter vd dc = 0
foreach v {vlist}
  alter vg dc = $v
  ac lin 1 1meg 1meg
  let cg = -imag(i(vg))/(2*3.141592653589793*1e6)
  echo "$v $&cg" >> ../results/{prefix}_cv.txt
end
quit
.endc
.end
"""
    out = ngspice(f"{tid.lower()}_{prefix}_dc_cv", body, [f"{prefix}_iv0.txt", f"{prefix}_iv1.txt", f"{prefix}_cv.txt"])
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    for a, key, vds, tag in ((ax[0], f"{prefix}_iv0.txt", 0.05, "vds0p05"), (ax[1], f"{prefix}_iv1.txt", 1.0, "vds1")):
        d = out[key]
        xt, yt = target(f"{prefix}_idvg_{tag}_tcad.csv")
        xp, yp = target(f"{prefix}_idvg_{tag}_paper_bsim4.csv")
        model_at = np.interp(xt, d[:, 0], np.log10(np.abs(d[:, 1]) + 1e-20))
        rms = np.sqrt(np.mean((model_at - np.log10(yt)) ** 2))
        paper_rms = np.sqrt(np.mean((np.interp(xt, xp, np.log10(yp)) - np.log10(yt)) ** 2))
        check(tid, f"Id-Vg @Vds={vds} V rms log10 error [dec] (paper's BSIM4: {paper_rms:.3f})",
              f"{rms:.3f}", f"< {iv_lim}", rms < iv_lim)
        a.semilogy(xt, yt, "ks", ms=4, label="TCAD (Fig. 2, digitized)")
        a.semilogy(xp, yp, "r-", lw=1.2, alpha=.7, label="paper BSIM4 (digitized)")
        a.semilogy(d[:, 0], np.abs(d[:, 1]), "b-", lw=2, label="this model (ngspice)")
        a.set_ylim(yt.min() / 10, yt.max() * 3)
        a.set(xlabel="V_GS [V]", ylabel="I_DS [A/um]", title=f"{prefix.upper()} Id-Vg, V_DS = {vds} V")
        a.grid(alpha=.3, which="both")
        a.legend(fontsize=8)
    d = out[f"{prefix}_cv.txt"]
    xt, yt = target(f"{prefix}_cgg_tcad.csv")
    rel = np.sqrt(np.mean(((np.interp(xt, d[:, 0], d[:, 1]) - yt) / yt) ** 2)) * 100
    check(tid, "Cgg-Vg rms relative error [%]", f"{rel:.2f}", f"< {cv_lim}", rel < cv_lim)
    xp, yp = target(f"{prefix}_cgg_paper_bsim4.csv")
    ax[2].plot(xt, yt * 1e15, "ks", ms=4, label="TCAD")
    ax[2].plot(xp, yp * 1e15, "r-", lw=1.2, alpha=.7, label="paper BSIM4")
    ax[2].plot(d[:, 0], d[:, 1] * 1e15, "b-", lw=2, label="this model")
    ax[2].set(xlabel="V_GS [V]", ylabel="C_GG [fF/um]", title=f"{prefix.upper()} Cgg-Vg (V_DS = 0)")
    ax[2].grid(alpha=.3)
    ax[2].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, f"{tid.lower()}_{prefix}_iv_cv.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- FGFET helpers
EDGE = 5e-9


def pwl(points):
    return "pwl(" + " ".join(f"{t:.6g} {v:.6g}" for t, v in points) + ")"


def op_sources(i, vdl, vwl_read, t_write=1.1e-6, t_store=2.2e-6, t_read=2.28e-6, t_end=2.4e-6,
               vwl_write=3.0, vsl=0.9):
    """Initialize -> write -> storage -> read on FGFET #i (Table II / Sec. III)."""
    e = EDGE
    wl = pwl([(0, 0), (e, 0), (2 * e, vwl_write), (t_store, vwl_write), (t_store + e, -2),
              (t_read, -2), (t_read + e, vwl_read), (t_end, vwl_read)])
    dl = pwl([(0, 0), (t_write, 0), (t_write + e, vdl), (t_store, vdl), (t_store + e, 0), (t_end, 0)])
    sl = pwl([(0, 0), (t_read, 0), (t_read + e, vsl), (t_end, vsl)])
    return [f"VWL{i} wl{i} 0 {wl}", f"VDL{i} dl{i} 0 {dl}", f"VSL{i} sl{i} 0 {sl}"]


def fgfet_netlist(title, insts, t_end, outfile, tstep="1n", extra_save=""):
    """insts: list of (source lines, w_dev, delvto)."""
    lines = [f"* {title}", f".include {REL}/fgfet_subckt.sp"]
    vecs = []
    for i, (src, w, dv) in enumerate(insts):
        lines += src
        lines.append(f"X{i} wl{i} dl{i} sl{i} 0 0 FGFET w_dev={w} delvto_val={dv}")
        vecs += [f"v(x{i}.mn)", f"isl{i}"]
    lets = [f"let isl{i} = -i(vsl{i})" for i in range(len(insts))]
    lines += [".options method=gear reltol=1e-4 gmin=1e-15 chgtol=1e-18", ".control", f"pre_osdi {OSDI}",
              f"tran {tstep} {t_end}", "set wr_singlescale", *lets,
              f"wrdata ../results/{outfile} {' '.join(vecs)} {extra_save}", "quit", ".endc", ".end"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- T3
def test_fig4():
    print("T3: FGFET memory-node transient (Fig. 4)")
    insts = [(op_sources(i, vdl, 0.5), "1u", 0) for i, vdl in enumerate((0.05, 1.0))]
    d = ngspice("t3_fig4_transient", fgfet_netlist("T3: Fig. 4 transient, V_DL = 0.05 V / 1.0 V", insts,
                                                   2.4e-6, "t3_vmn.txt"), ["t3_vmn.txt"])["t3_vmn.txt"]
    t = d[:, 0]
    keypts = {  # read off the Fig. 4 TCAD markers
        0.05: {"storage": (2.25e-6, -1.70), "read": (2.34e-6, -0.58), "write": (2.19e-6, 0.05)},
        1.0: {"storage": (2.25e-6, -1.04), "read": (2.34e-6, 0.45), "write": (2.19e-6, 1.00)},
    }
    lim = {"write": 0.05, "storage": 0.25, "read": 0.10}
    fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
    for k, (vdl, col) in enumerate(((0.05, 1), (1.0, 3))):
        v = d[:, col]
        for mode, (tt, vt) in keypts[vdl].items():
            err = abs(np.interp(tt, t, v) - vt)
            check("T3", f"V_DL={vdl} V {mode}-mode V_MN error [V] (model {np.interp(tt, t, v):+.3f}, TCAD {vt:+.2f})",
                  f"{err:.3f}", f"< {lim[mode]}", err < lim[mode])
        tag = "dl0p05" if vdl == 0.05 else "dl1"
        xt, yt = target(f"vmn_transient_{tag}_tcad.csv")
        xp, yp = target(f"vmn_transient_{tag}_paper_bsim4.csv")
        ax[k].plot(xp, yp, "r-", lw=1.2, alpha=.6, label="paper model (digitized)")
        ax[k].plot(t * 1e6, v, "b-", lw=2, label="this model (ngspice)")
        ax[k].plot(xt, yt, "ks", ms=5, label="TCAD markers (digitized)")
        for mode, (tt, vt) in keypts[vdl].items():
            ax[k].plot(tt * 1e6, vt, "o", mfc="none", mec="g", ms=10)
        ax[k].set(xlabel="time [us]", ylabel="memory node [V]", ylim=(-2, 2), title=f"V_DL = {vdl} V")
        ax[k].grid(alpha=.3)
        ax[k].legend(fontsize=8, loc="lower left")
    ax[0].plot([], [], "o", mfc="none", mec="g", label="checked key points")
    ax[0].legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "t3_fig4_transient.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- T4
def test_read():
    print("T4: Table II read operation")
    insts = [(op_sources(i, vdl, 0.5), "1u", 0) for i, vdl in enumerate((0.05, 1.0))]
    d = ngspice("t4_read", fgfet_netlist("T4: Table II read of '0' (0.05 V) and '1' (1 V)", insts,
                                         2.4e-6, "t4_read.txt"), ["t4_read.txt"])["t4_read.txt"]
    sel = d[:, 0] > 2.33e-6
    i0, i1 = np.max(np.abs(d[sel, 2])), np.min(np.abs(d[sel, 4]))   # worst case over the read window
    check("T4", f"read current '1' [A/um] (V_MN = {np.mean(d[sel, 3]):+.3f} V)", f"{i1:.3e}", "> 1e-6", i1 > 1e-6)
    check("T4", f"read current '0' [A/um] (V_MN = {np.mean(d[sel, 1]):+.3f} V)", f"{i0:.3e}", "< 1e-9", i0 < 1e-9)
    check("T4", "I('1') / I('0')", f"{i1 / i0:.3e}", "> 1e4", i1 / i0 > 1e4)
    return d


# ---------------------------------------------------------------- T5
def test_conservation():
    print("T5: charge conservation and retention")
    e = EDGE
    # write '1', then 100 storage(-2 V)/read(+0.5 V) cycles, period 40 ns
    pts = [(0, 0), (e, 0), (2 * e, 3), (2.2e-6, 3), (2.2e-6 + e, -2)]
    t0, ncyc, per = 2.3e-6, 100, 40e-9
    for k in range(ncyc):
        a = t0 + k * per
        pts += [(a, -2), (a + e, 0.5), (a + per / 2, 0.5), (a + per / 2 + e, -2)]
    t_end = t0 + ncyc * per + 50e-9
    pts.append((t_end, -2))
    dl = pwl([(0, 0), (1.1e-6, 0), (1.1e-6 + e, 1.0), (2.2e-6, 1.0), (2.2e-6 + e, 0), (t_end, 0)])
    sl = pwl([(0, 0), (t_end, 0)])
    src = [f"VWL0 wl0 0 {pwl(pts)}", f"VDL0 dl0 0 {dl}", f"VSL0 sl0 0 {sl}"]
    d = ngspice("t5_cycles", fgfet_netlist("T5: 100 storage/read cycles after writing '1'", [(src, "1u", 0)],
                                           t_end, "t5_cycles.txt", tstep="0.5n"), ["t5_cycles.txt"])["t5_cycles.txt"]
    t, v = d[:, 0], d[:, 1]
    reads = np.array([np.interp(t0 + k * per + per / 4, t, v) for k in range(ncyc)])
    drift = (reads[-1] - reads[0]) * 1e3
    check("T5", f"V_MN drift over {ncyc} read cycles [mV] (first read {reads[0]:+.4f} V)",
          f"{drift:.3f}", "|x| < 5", abs(drift) < 5)

    # retention: write '1', hold in storage mode for 1 ms
    hold = 1e-3
    wl = pwl([(0, 0), (e, 0), (2 * e, 3), (2.2e-6, 3), (2.2e-6 + e, -2), (hold, -2)])
    dl = pwl([(0, 0), (1.1e-6, 0), (1.1e-6 + e, 1.0), (2.2e-6, 1.0), (2.2e-6 + e, 0), (hold, 0)])
    src = [f"VWL0 wl0 0 {wl}", f"VDL0 dl0 0 {dl}", f"VSL0 sl0 0 {pwl([(0, 0), (hold, 0)])}"]
    r = ngspice("t5_retention", fgfet_netlist("T5: 1 ms storage-mode retention of '1'", [(src, "1u", 0)],
                                              hold, "t5_retention.txt", tstep="10n"), ["t5_retention.txt"])["t5_retention.txt"]
    v_start = np.interp(2.25e-6, r[:, 0], r[:, 1])
    v_end = r[-1, 1]
    check("T5", f"storage-mode V_MN change over 1 ms [mV] ({v_start:+.4f} -> {v_end:+.4f} V)",
          f"{(v_end - v_start) * 1e3:.3f}", "|x| < 10", abs(v_end - v_start) < 10e-3)

    fig, ax = plt.subplots(1, 2, figsize=(13, 4.2))
    ax[0].plot(t * 1e6, v, "b-", lw=.8)
    ax[0].plot((t0 + np.arange(ncyc) * per + per / 4) * 1e6, reads, "g.", ms=3, label="read-mode samples")
    ax[0].set(xlabel="time [us]", ylabel="memory node [V]", title=f"{ncyc} storage/read cycles after writing '1'")
    ax[0].grid(alpha=.3)
    ax[0].legend(fontsize=8)
    ax[1].semilogx(r[:, 0], r[:, 1], "b-")
    ax[1].set(xlabel="time [s]", ylabel="memory node [V]", title="storage-mode retention, 1 ms")
    ax[1].grid(alpha=.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "t5_conservation_retention.png"), dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------- T6
ADDER_SCHEMES = {
    # name: (delvto, {B: V_DL}, {A: V_WL read}, expected logic(A, B))
    "A-type (memory read)": (0.0, {0: 0.05, 1: 1.9}, {1: 0.5}, lambda a, b: b),
    "B-type (AND)": (0.9, {0: 0.1, 1: 1.8}, {0: 0.0, 1: 1.8}, lambda a, b: a & b),
    "C-type (OR)": (0.0, {0: 0.85, 1: 1.85}, {0: 0.0, 1: 1.2}, lambda a, b: a | b),
}


def test_adder_biasing():
    print("T6: FGFET logic under the Sec. III adder bias schemes (w_dev = 64 nm, SL = 0.9 V, 5-15 ns read)")
    rows = []
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, (name, (dv, vdl, vwl, logic)) in zip(axes, ADDER_SCHEMES.items()):
        combos = [(a, b) for a in vwl for b in vdl]
        insts = [(op_sources(i, vdl[b], vwl[a]), "64n", dv) for i, (a, b) in enumerate(combos)]
        tag = name.split()[0].lower().replace("-", "")
        d = ngspice(f"t6_{tag}", fgfet_netlist(f"T6: {name}, delvto = {dv} V", insts, 2.4e-6, f"t6_{tag}.txt"),
                    [f"t6_{tag}.txt"])[f"t6_{tag}.txt"]
        # The adders are clocked on a ns scale (timing graphs of Figs. 6-8), so the read is
        # evaluated 5-15 ns after the WL read edge. Over longer reads a 1.2/1.8 V WL turns
        # the VFET on and bleeds the memory node into DL = 0 V within ~100 ns.
        sel = (d[:, 0] >= 2.29e-6) & (d[:, 0] <= 2.30e-6)
        on, off, labels, currents, colors = [], [], [], [], []
        for i, (a, b) in enumerate(combos):
            vmn = np.mean(d[sel, 1 + 2 * i])
            exp = logic(a, b)
            # worst case over the read window: weakest '1', leakiest '0'
            isl = np.min(np.abs(d[sel, 2 + 2 * i])) if exp else np.max(np.abs(d[sel, 2 + 2 * i]))
            (on if exp else off).append(isl)
            rows.append((name, a if len(vwl) > 1 else "-", b, vdl[b], vwl[a], vmn, isl, exp))
            labels.append(f"A={a},B={b}" if len(vwl) > 1 else f"B={b}")
            currents.append(max(isl, 1e-16))
            colors.append("tab:green" if exp else "tab:gray")
        ratio = min(on) / max(off)
        check("T6", f"{name}: min I(expected 1) / max I(expected 0)", f"{ratio:.3e}", "> 100", ratio > 100)
        ax.bar(labels, currents, color=colors)
        ax.set_yscale("log")
        ax.set(ylabel="I_SL in read [A]", title=f"{name}\n(green = expected '1')")
        ax.grid(alpha=.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "t6_adder_bias_logic.png"), dpi=120)
    plt.close(fig)
    return rows


# ---------------------------------------------------------------- report
def write_summary(adder_rows):
    npass = sum(r[4] for r in RESULTS)
    lines = ["# FGFET compact-model validation", "",
             f"**{npass} / {len(RESULTS)} checks passed.** Generated by `test/run_tests.py` "
             "(ngspice + OpenVAF OSDI).", "",
             "| Test | Check | Value | Limit | Result |", "|---|---|---|---|---|"]
    lines += [f"| {t} | {w} | {v} | {l} | {'PASS' if ok else '**FAIL**'} |" for t, w, v, l, ok in RESULTS]
    lines += ["", "## T6 detail: memory node and SL current 5-15 ns into the read (w_dev = 64 nm)", "",
              "| Scheme | A | B | V_DL write [V] | V_WL read [V] | V_MN read [V] | I_SL [A] | expected |",
              "|---|---|---|---|---|---|---|---|"]
    lines += [f"| {n} | {a} | {b} | {vd} | {vw} | {vm:+.3f} | {i:.3e} | {e} |"
              for n, a, b, vd, vw, vm, i, e in adder_rows]
    lines += ["", "## Plots", ""] + [f"![{p}](../plots/{p})" for p in sorted(os.listdir(PLOTS))]
    open(os.path.join(RES, "summary.md"), "w").write("\n".join(lines) + "\n")
    print(f"\n{npass}/{len(RESULTS)} checks passed -> test/results/summary.md")


def main():
    device_test("T1", "sfet", "sfet_32nm.pm", "sfet_nmos", "32n", iv_lim=0.25, cv_lim=5.0)
    device_test("T2", "vfet", "vfet_32nm.pm", "vfet_nmos", "100.2n", iv_lim=0.25, cv_lim=5.0)
    test_fig4()
    test_read()
    test_conservation()
    rows = test_adder_biasing()
    write_summary(rows)
    return 0 if all(r[4] for r in RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
