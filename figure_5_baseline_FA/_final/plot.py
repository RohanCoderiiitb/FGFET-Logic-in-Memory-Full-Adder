import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def load_ltspice_txt(filepath: str) -> dict[str, np.ndarray]:
    """Read an LTspice 'Export data as text' .txt file (UTF-8, BOM, or UTF-16LE)."""
    raw = Path(filepath).read_bytes()
    if raw.startswith(b"\xff\xfe") or b"\x00" in raw[:100]:
        text = raw.decode("utf-16-le", errors="ignore")
    else:
        text = raw.decode("utf-8-sig", errors="ignore")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cols = [h.strip().lower() for h in lines[0].split()]

    rows = []
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) != len(cols):
            continue
        try:
            rows.append([float(x) for x in parts])
        except ValueError:
            continue

    arr = np.asarray(rows, dtype=np.float64)
    return {cols[i]: arr[:, i] for i in range(len(cols))}


def find_rising_crossing(t_ns: np.ndarray, v: np.ndarray, threshold: float, t_min: float) -> float:
    """Linearly interpolate the first rising crossing through `threshold` after `t_min`."""
    mask = t_ns >= t_min
    tm, vm = t_ns[mask], v[mask]
    idx = np.where((vm[:-1] < threshold) & (vm[1:] >= threshold))[0]
    if len(idx) == 0:
        raise ValueError(f"No rising crossing found at {threshold} V after {t_min} ns.")
    i = idx[0]
    frac = (threshold - vm[i]) / (vm[i + 1] - vm[i])
    return float(tm[i] + frac * (tm[i + 1] - tm[i]))


def plot_carry_transition(
    input_file: str = "full_adder_28fet.txt",
    output_file: str = "carry_transition_28fet.png",
    vdd: float = 0.9,
) -> None:
    data = load_ltspice_txt(input_file)

    required = ["time", "v(a)", "v(b)", "v(cin)", "v(cbar)", "v(sbar)", "v(cout)", "v(sum)"]
    missing = [k for k in required if k not in data]
    if missing:
        raise KeyError(
            f"Missing columns in {input_file}: {missing}.\n"
            f"Found columns: {list(data.keys())}.\n"
            "Make sure V(a), V(b), V(cin), V(cbar), V(sbar), V(cout), and V(sum) are selected when exporting."
        )

    t_ns = data["time"] * 1e9
    t_start, t_end = 4.94, 5.18
    win = (t_ns >= t_start - 0.01) & (t_ns <= t_end + 0.01)

    t = t_ns[win]
    va, vb, vcin = data["v(a)"][win], data["v(b)"][win], data["v(cin)"][win]
    vcbar, vsbar = data["v(cbar)"][win], data["v(sbar)"][win]
    vcout, vsum = data["v(cout)"][win], data["v(sum)"][win]

    vhalf = vdd / 2.0
    t_cin = find_rising_crossing(t, vcin, vhalf, t_min=4.95)
    t_cout = find_rising_crossing(t, vcout, vhalf, t_min=4.95)
    delay_ps = (t_cout - t_cin) * 1e3

    bg_color = "#f3f7fb"
    spine_color = "#526478"
    text_color = "#152536"
    grid_color = "#e1eaf2"

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "axes.edgecolor": spine_color,
        "axes.linewidth": 0.9,
        "xtick.color": spine_color,
        "ytick.color": spine_color,
    })

    fig, axes = plt.subplots(
        3, 1, figsize=(9.6, 6.6), sharex=True, gridspec_kw={"hspace": 0.22}
    )
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "Carry transition in the conventional 28-FET full adder",
        fontsize=17,
        color=text_color,
        y=0.965,
    )

    # Panel 1: Inputs
    ax = axes[0]
    ax.plot(t, va, color="#3979ba", linestyle=(0, (1.2, 4.0)), linewidth=2.0, label="A")
    ax.plot(t, vb, color="#d98121", linestyle=(0, (1.2, 4.0)), linewidth=2.0, label="B")
    ax.plot(t, vcin, color="#198760", linestyle="-", linewidth=2.2, label="Cin")
    ax.set_ylabel("Inputs (V)", fontsize=13.5, color="#000000", labelpad=8)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.03, 1.04),
        ncol=3,
        frameon=False,
        fontsize=11.5,
        markerfirst=False,
        handlelength=1.8,
        columnspacing=1.5,
        labelcolor=text_color,
    )

    # Panel 2: Internal nodes
    ax = axes[1]
    ax.plot(t, vcbar, color="#247491", linestyle="-", linewidth=2.2, label="Inverted carry")
    ax.plot(t, vsbar, color="#b33c79", linestyle=(0, (1.2, 4.0)), linewidth=2.2, label="Inverted sum")
    ax.set_ylabel("Internal nodes (V)", fontsize=13.5, color="#000000", labelpad=8)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.05, 1.04),
        ncol=2,
        frameon=False,
        fontsize=11.5,
        markerfirst=False,
        handlelength=1.8,
        columnspacing=2.2,
        labelcolor=text_color,
    )

    # Panel 3: Outputs
    ax = axes[2]
    ax.plot(t, vcout, color="#7655b7", linestyle="-", linewidth=2.2, label="Cout")
    ax.plot(t, vsum, color="#c9453e", linestyle="-", linewidth=2.2, label="Sum")
    ax.set_ylabel("Outputs (V)", fontsize=13.5, color="#000000", labelpad=8)
    ax.set_xlabel("Time (ns)", fontsize=13.5, color="#000000", labelpad=8)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(0.02, 1.04),
        ncol=2,
        frameon=False,
        fontsize=11.5,
        markerfirst=False,
        handlelength=1.8,
        columnspacing=1.5,
        labelcolor=text_color,
    )

    # Delay arrow and annotation
    ax.annotate(
        "",
        xy=(t_cout, vhalf),
        xytext=(t_cin, vhalf),
        arrowprops=dict(arrowstyle="<->", color="#3f5368", lw=1.1, shrinkA=2, shrinkB=2),
    )
    ax.text(
        t_cout + 0.015,
        vhalf + 0.05,
        f"{delay_ps:.2f} ps carry delay",
        fontsize=11.5,
        color="#23374d",
        va="bottom",
    )

    xticks = [4.96, 5.00, 5.04, 5.08, 5.12, 5.16]
    for a in axes:
        a.set_facecolor(bg_color)
        a.set_xlim(t_start, t_end)
        a.set_ylim(-0.08, 1.25)
        a.set_yticks([0, 0.45, 0.9])
        a.set_yticklabels(["0", "0.45", "0.9"], fontsize=12.5, color=text_color)
        a.set_xticks(xticks)
        a.tick_params(axis="both", length=5.5, width=0.9, pad=6)
        a.grid(True, linestyle=":", linewidth=0.6, color=grid_color)
        a.spines["top"].set_visible(False)
        a.spines["right"].set_visible(False)
        a.axvline(t_cin, color="#6d8196", linestyle=(0, (4, 5)), linewidth=0.9)
        a.axvline(t_cout, color="#6d8196", linestyle=(0, (4, 5)), linewidth=0.9)

    axes[2].set_xticklabels([f"{x:.2f}" for x in xticks], fontsize=12.5, color=text_color)

    fig.subplots_adjust(left=0.12, right=0.965, top=0.89, bottom=0.11)
    fig.savefig(output_file, dpi=300, facecolor="white")
    print(f"Saved {output_file} | Cin={t_cin:.6f} ns, Cout={t_cout:.6f} ns, Delay={delay_ps:.4f} ps")


if __name__ == "__main__":
    txt_path = sys.argv[1] if len(sys.argv) > 1 else "full_adder_28fet.txt"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "carry_transition_28fet.png"
    plot_carry_transition(txt_path, out_path)