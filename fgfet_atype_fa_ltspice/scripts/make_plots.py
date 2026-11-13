#!/usr/bin/env python3
"""Plots for the report: Fig. 6(b)/(c) replica, FGFET programming sequence, rendered preview of the user's schematic (full_adder_atype.asc)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import fa, hashlib
SHA = fa.schematic_hash()

def load(bit):
    d = np.load(os.path.join(fa.RES, f"wave_B{bit}.npz"))
    assert str(d["schematic_sha256"]) == SHA, f"wave_B{bit}.npz was not produced from {os.path.basename(fa.ASC)} as it is now; run run_all.py first"
    return d
ROOT = fa.ROOT; RES = fa.RES
plt.rcParams.update({"font.size": 9, "axes.linewidth": 0.8})
COL = {"clk": "#444444", "a": "#1f77b4", "cin": "#2ca02c", "sum": "#d62728", "cout": "#9467bd"}

def fig6():
    fig, ax = plt.subplots(5, 2, figsize=(9, 7), sharex=True, sharey="row")
    for j, bit in enumerate((1, 0)):
        d = load(bit); t = (d["time"] - fa.T_LOGIC) * 1e9
        m = (t >= -0.05) & (t <= 8.0)
        for i, (k, lab) in enumerate((("clk", "CLK"), ("a", "A"), ("cin", "Cin"), ("sum", "Sum"), ("cout", "Cout"))):
            ax[i, j].plot(t[m], d[f"v({k})"][m], color=COL[k], lw=1.4)
            ax[i, j].set_ylim(-0.1, 1.05); ax[i, j].set_yticks([0, 0.9]); ax[i, j].grid(alpha=0.25)
            if j == 0: ax[i, j].set_ylabel(f"{lab} [V]")
        ax[0, j].set_title(f"B = {bit} stored in FGFET")
        ax[4, j].set_xlabel("Time [ns]"); ax[4, j].set_xticks(range(0, 9))
    fig.tight_layout(); fig.savefig(os.path.join(RES, "fig6_replica.png"), dpi=170); plt.close(fig)

def programming():
    fig, ax = plt.subplots(3, 2, figsize=(9, 6), sharex="col")
    for j, bit in enumerate((1, 0)):
        d = load(bit); t = d["time"] * 1e6
        m = t <= fa.T_LOGIC * 1e6 + 0.004
        ax[0, j].plot(t[m], d["v(wl)"][m], color="#555", label="WL")
        ax[0, j].plot(t[m], d["v(b)"][m], color="#e67e22", label="DL (= B)"); ax[0, j].legend(loc="center left", fontsize=8)
        ax[0, j].set_ylabel("V [V]"); ax[0, j].set_title(f"B = {bit}: init -> write -> storage -> read")
        for k, ls in (("cout", "-"), ("or", "--"), ("sum", ":")):
            ax[1, j].plot(t[m], d[f"v(xfg_{k}:mn)"][m], ls=ls, lw=1.4, label=f"MN of XFG_{k.upper()}")
        ax[1, j].set_ylabel("V_MN [V]"); ax[1, j].legend(fontsize=8)
        ax[2, j].plot(t[m], d["v(_cout)"][m], label="!Cout node"); ax[2, j].plot(t[m], d["v(_sum)"][m], label="!Sum node")
        ax[2, j].set_ylabel("V [V]"); ax[2, j].set_xlabel("Time [us]"); ax[2, j].legend(fontsize=8)
        for a in ax[:, j]: a.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(os.path.join(RES, "programming_sequence.png"), dpi=170); plt.close(fig)

# ------------------------------------------------------------------ schematic rendering from the .asc
SYM = {  # LINE data copied from LTspice lib/sym (nmos4 / pmos4 / voltage) and ../FGFET.asy
 "nmos4": [(48,80,48,96),(16,80,48,80),(40,48,48,48),(16,48,40,44),(16,48,40,52),(40,44,40,52),(16,8,16,24),(16,40,16,56),
           (16,72,16,88),(0,80,8,80),(8,16,8,80),(48,16,16,16),(48,0,48,16)],
 "pmos4": [(48,80,48,96),(16,80,48,80),(16,48,24,48),(48,48,24,44),(48,48,24,52),(24,44,24,52),(16,8,16,24),(16,40,16,56),
           (16,72,16,88),(0,80,8,80),(8,16,8,80),(48,16,16,16),(48,0,48,16)],
 "voltage": [(-8,36,8,36),(-8,76,8,76),(0,28,0,44),(0,96,0,88),(0,16,0,24)],
 "FGFET": [(-32,0,64,0),(64,0,64,96),(64,96,-32,96),(-32,96,-32,0),(-32,32,-16,32),(-32,64,-16,64),(48,0,48,16),(48,80,48,96),
           (48,48,64,48),(16,28,40,28),(40,28,40,68),(40,68,16,68),(16,68,16,28),(28,28,28,68)],
}
def tf(orient, x, y):
    return {"R0": (x, y), "R180": (-x, -y), "M0": (-x, y), "M180": (x, -y)}[orient]

def schematic(asc=fa.ASC, png=f"schematic_{fa.STEM}.png", xlim=(-800, 1560), ylim=(1030, -340), size=(17, 9), text_ymax=1000):
    lines = open(asc).read().splitlines()
    fig, ax = plt.subplots(figsize=size); cur = None
    SYM["cap"] = [(16, 0, 16, 24), (0, 24, 32, 24), (0, 40, 32, 40), (16, 40, 16, 64)]
    for ln in lines:                                   # wires first so symbols draw on top
        p = ln.split()
        if p and p[0] == "WIRE":
            ax.plot([int(p[1]), int(p[3])], [int(p[2]), int(p[4])], color="#1a6b1a", lw=1.3, solid_capstyle="round")
    for ln in lines:
        p = ln.split()
        if not p: continue
        if p[0] == "SYMBOL":
            cur = (p[1], int(p[2]), int(p[3]), p[4])
            for x1, y1, x2, y2 in SYM[cur[0]]:
                a = tf(cur[3], x1, y1); b = tf(cur[3], x2, y2)
                ax.plot([cur[1] + a[0], cur[1] + b[0]], [cur[2] + a[1], cur[2] + b[1]], color="#111", lw=1.2)
        elif p[0] == "SYMATTR" and p[1] == "InstName" and cur:
            x, y, o = cur[1], cur[2], cur[3]
            if cur[0] == "cap": ax.text(x + 40, y + 36, p[2], fontsize=7.5, color="#0a4d8c")
            elif o == "R180": ax.text(x + 8, y - 30, p[2], fontsize=8, color="#0a4d8c", ha="left")
            elif cur[0] == "FGFET": ax.text(x + 4, y - 10, p[2], fontsize=8, color="#0a4d8c")
            else: ax.text(x + 72, y + 40, p[2], fontsize=8, color="#0a4d8c")
        elif p[0] == "FLAG":
            x, y, n = int(p[1]), int(p[2]), p[3]
            if n == "0":
                ax.plot([x - 10, x + 10], [y, y], color="k", lw=1.2); ax.plot([x - 5, x + 5], [y + 6, y + 6], color="k", lw=1.2)
                ax.plot([x - 2, x + 2], [y + 12, y + 12], color="k", lw=1.2)
            else:
                ax.text(x, y - 10, n, fontsize=7.5, color="#b03a00", ha="center", va="bottom", fontweight="bold")
        elif p[0] == "TEXT" and not p[5].startswith("!") and int(p[2]) < text_ymax:
            txt = " ".join(p[5:]).lstrip(";")
            big = p[4] == "3"
            ax.text(int(p[1]), int(p[2]), txt, fontsize=10.5 if big else 8, color="#111" if big else "#444",
                    fontweight="bold" if big else "normal", va="center")
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.axis("off")
    fig.tight_layout(); fig.savefig(os.path.join(RES, png), dpi=130); plt.close(fig)

if __name__ == "__main__":
    fig6(); programming(); schematic()
    print("plots written")
