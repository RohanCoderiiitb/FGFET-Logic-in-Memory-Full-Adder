#!/usr/bin/env python3
"""Stage 1: digitize the TCAD reference data (black squares) and the authors'
BSIM4 fit (red line) from Fig. 2 and Fig. 4 of Kim et al., IEEE Access 2023.

Replaces the manual WebPlotDigitizer step: page 3 of the PDF is rendered at
600 dpi with pdftoppm, and each subplot is calibrated from its frame and
gridline pixel positions (measured once, listed in PLOTS below).

Usage:  python3 digitize_figures.py [path/to/paper.pdf]
Output: ../data/*.csv and ../data/digitization_check.png
"""
import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
DEFAULT_PDF = os.path.expanduser(
    "~/Downloads/Analysis_of_Logic-in-Memory_Full_Adder_Circuit_Wit.pdf")

# Page-3 pixel calibration at 600 dpi.
#   box   : plot interior (x0, x1, y0, y1) in pixels
#   x     : (pixel, value) pairs for two x reference ticks
#   y     : (pixel, value) pairs for two y reference ticks (value = log10 for log axes)
#   log   : y axis is logarithmic
#   skip  : rectangles (x0, x1, y0, y1) holding legends/labels to ignore
PLOTS = {
    "sfet_idvg_vds0p05": dict(box=(582, 1228, 776, 1246), x=((685.5, 0.5), (1120.0, 2.5)),
                              y=((812.0, -4), (1201.5, -8)), log=True,
                              skip=[(733, 1202, 1052, 1176), (890, 1202, 815, 888)]),
    "sfet_idvg_vds1":    dict(box=(1542, 2187, 776, 1246), x=((1646.5, 0.5), (2081.5, 2.5)),
                              y=((855.5, -3), (1251.0, -6)), log=True,
                              skip=[(1728, 2164, 1050, 1165), (1868, 2118, 810, 890)]),
    "vfet_idvg_vds0p05": dict(box=(582, 1227, 1546, 2015), x=((684.5, 0.5), (1119.0, 2.5)),
                              y=((1582.5, -9), (2020.0, -12)), log=True,
                              skip=[(744, 1214, 1892, 2002), (875, 1186, 1678, 1780)]),
    "vfet_idvg_vds1":    dict(box=(1541, 2184, 1546, 2015), x=((1644.5, 0.5), (2079.5, 2.5)),
                              y=((1622.5, -8), (1982.5, -11)), log=True,
                              skip=[(1702, 2172, 1892, 2002), (1890, 2136, 1690, 1792)]),
    "sfet_cgg":          dict(box=(579, 1224, 2320, 2790), x=((682.5, 0.5), (1116.5, 2.5)),
                              y=((2368.5, 2.5e-15), (2792.5, 0.5e-15)), log=False,
                              skip=[(774, 1208, 2668, 2771)]),
    "vfet_cgg":          dict(box=(1541, 2184, 2320, 2790), x=((1644.5, 0.5), (2078.5, 2.5)),
                              y=((2368.0, 7e-16), (2792.5, 3e-16)), log=False,
                              skip=[(1776, 2172, 2674, 2767)]),
    "vmn_transient_dl0p05": dict(box=(2783, 3453, 768, 1253), x=((2805.0, 0.0), (3348.5, 2.0)),
                                 y=((886.0, 1.0), (1134.0, -1.0)), log=False,
                                 skip=[(2789, 3360, 1130, 1241), (3090, 3436, 788, 875)]),
    "vmn_transient_dl1":    dict(box=(3753, 4418, 768, 1253), x=((3772.7, 0.0), (4318.0, 2.0)),
                                 y=((886.0, 1.0), (1134.0, -1.0)), log=False,
                                 skip=[(3764, 4337, 1124, 1236), (4078, 4397, 778, 864)]),
}


def render_page(pdf):
    tmp = tempfile.mkdtemp()
    subprocess.run(["pdftoppm", "-r", "600", "-f", "3", "-l", "3", "-png", pdf,
                    os.path.join(tmp, "p")], check=True)
    png = [f for f in os.listdir(tmp) if f.endswith(".png")][0]
    return np.asarray(Image.open(os.path.join(tmp, png)).convert("RGB")).astype(int)


def make_map(cal):
    (px0, vx0), (px1, vx1) = cal["x"]
    (py0, vy0), (py1, vy1) = cal["y"]
    fx = lambda p: vx0 + (p - px0) * (vx1 - vx0) / (px1 - px0)
    fy = lambda p: vy0 + (p - py0) * (vy1 - vy0) / (py1 - py0)
    if cal["log"]:
        return fx, lambda p: 10.0 ** fy(p)
    return fx, fy


def interior_mask(shape, cal):
    m = np.zeros(shape, bool)
    x0, x1, y0, y1 = cal["box"]
    m[y0:y1, x0:x1] = True
    for sx0, sx1, sy0, sy1 in cal["skip"]:
        m[sy0:sy1, sx0:sx1] = False
    return m


def find_markers(img, cal):
    """Black filled squares -> centroids. Red line pixels are allowed inside a
    square (the fitted curve is drawn over the data) so they are counted as
    'marker' pixels when surrounded by black."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    black = (r < 90) & (g < 90) & (b < 90)
    black &= interior_mask(black.shape, cal)
    black = ndimage.binary_opening(black, np.ones((5, 5)))   # drops 1-3 px dashed grid / line art
    lab, n = ndimage.label(black)
    pts = []
    for sl in ndimage.find_objects(lab):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        if 8 <= h <= 60 and 8 <= w <= 60:
            yc = 0.5 * (sl[0].start + sl[0].stop - 1)
            xc = 0.5 * (sl[1].start + sl[1].stop - 1)
            # tall blobs = squares stacked on a steep curve: split by expected size
            k = max(1, int(round(max(h, w) / 22.0)))
            if k == 1:
                pts.append((xc, yc))
            else:
                for i in range(k):
                    if h >= w:
                        pts.append((xc, sl[0].start + (i + 0.5) * h / k))
                    else:
                        pts.append((sl[1].start + (i + 0.5) * w / k, yc))
    return sorted(pts)


def find_marker_band(img, cal, npts=45):
    """Fig. 2 markers are packed so densely that they merge into one thick
    black band. Its centre line is taken column-wise (good where the curve is
    flat) and row-wise (good where it is steep), then thinned to ~npts points
    spaced evenly along the arc length in plot-normalised coordinates."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    black = (r < 90) & (g < 90) & (b < 90) & interior_mask(r.shape, cal)
    black = ndimage.binary_opening(black, np.ones((5, 5)))
    pts = []
    for x in range(black.shape[1]):
        col = np.where(black[:, x])[0]
        if 4 <= len(col) <= 40:          # a short run = band crossing, not a vertical stack
            pts.append((x, np.median(col)))
    for y in range(black.shape[0]):
        row = np.where(black[y])[0]
        if 4 <= len(row) <= 40:
            pts.append((np.median(row), y))
    pts = np.array(pts)
    x0, x1, y0, y1 = cal["box"]
    u = (pts[:, 0] - x0) / (x1 - x0)
    v = (y1 - pts[:, 1]) / (y1 - y0)
    order = np.argsort(u + 1e-3 * v)
    u, v, pts = u[order], v[order], pts[order]
    # running arc length along the curve, then take medians in equal-length bins
    s = np.r_[0, np.cumsum(np.hypot(np.diff(u), np.diff(v)))]
    edges = np.linspace(0, s[-1], npts + 1)
    out = []
    for a, c in zip(edges[:-1], edges[1:]):
        sel = (s >= a) & (s <= c)
        if sel.sum() >= 3:
            out.append((np.median(pts[sel, 0]), np.median(pts[sel, 1])))
    return out


def find_red_curve(img, cal):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    red = (r > 180) & (g < 90) & (b < 90) & interior_mask(r.shape, cal)
    xs, ys = [], []
    x0, x1 = cal["box"][:2]
    for x in range(x0, x1, 3):
        col = np.where(red[:, x])[0]
        if len(col):
            xs.append(x)
            ys.append(np.median(col))
    return np.array(xs, float), np.array(ys, float)


def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    os.makedirs(DATA, exist_ok=True)
    img = render_page(pdf)
    fig, axes = plt.subplots(4, 2, figsize=(11, 15))
    for ax, (name, cal) in zip(axes.flat, PLOTS.items()):
        fx, fy = make_map(cal)
        pts = find_markers(img, cal) if name.startswith("vmn") else find_marker_band(img, cal)
        mx = np.array([fx(p[0]) for p in pts])
        my = np.array([fy(p[1]) for p in pts])
        rx, ry = find_red_curve(img, cal)
        rx, ry = fx(rx), fy(ry)
        xlab = "t_us" if name.startswith("vmn") else "vgs_V"
        ylab = {"idvg": "ids_A_per_um", "cgg": "cgg_F_per_um", "vmn": "vmn_V"}[
            "idvg" if "idvg" in name else "cgg" if "cgg" in name else "vmn"]
        np.savetxt(os.path.join(DATA, f"{name}_tcad.csv"), np.c_[mx, my], delimiter=",",
                   header=f"{xlab},{ylab}", comments="", fmt="%.6e")
        np.savetxt(os.path.join(DATA, f"{name}_paper_bsim4.csv"), np.c_[rx, ry], delimiter=",",
                   header=f"{xlab},{ylab}", comments="", fmt="%.6e")
        ax.plot(rx, ry, "r-", lw=2, label="paper BSIM4 (red line)")
        ax.plot(mx, my, "ks", ms=4, label=f"TCAD markers ({len(mx)})")
        if cal["log"]:
            ax.set_yscale("log")
        ax.set_title(name)
        ax.grid(alpha=.3)
        ax.legend(fontsize=7)
        print(f"{name:24s} markers={len(mx):3d} red_pts={len(rx):4d}")
    fig.tight_layout()
    fig.savefig(os.path.join(DATA, "digitization_check.png"), dpi=110)


if __name__ == "__main__":
    main()
