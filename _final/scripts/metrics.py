"""Extract the C-type metrics of Table 3 from LTspice raw-file data (dict name -> numpy array)."""
import numpy as np
NS = 1e-9

def cross(t, y, lvl, t_from, rising=True):
    m = t >= t_from
    tt, yy = t[m], y[m]
    for i in range(len(tt) - 1):
        if (yy[i] < lvl <= yy[i + 1]) if rising else (yy[i] > lvl >= yy[i + 1]):
            return tt[i] + (lvl - yy[i]) / (yy[i + 1] - yy[i]) * (tt[i + 1] - tt[i])
    return None

def p_avg(d, vdd, t0, width=8 * NS):
    """Average supply power V_DD * mean(-I(V_DD)) over [t0, t0 + width] (includes leakage)."""
    t = d["time"]; m = (t >= t0) & (t <= t0 + width)
    return float(vdd * np.trapezoid(-d["i(vdd)"][m], t[m]) / width)

def delay_data(d, trigger, t_edge_ns, vdd, t0):
    """Propagation delay tPLH: 50 % of the rising data input (`trigger` = 'cin' or 'a') to 50 % of the rising Cout.
    `t_edge_ns` is the nominal time of the input edge relative to t0."""
    t = d["time"]; tf = t0 + (t_edge_ns - 0.2) * NS
    ti = cross(t, d["v(" + trigger + ")"], 0.5, tf); to = cross(t, d["v(cout)"], vdd / 2, tf)
    return None if (ti is None or to is None) else to - ti

def logic_check(d, bit, vdd, t0):
    """Sum / Cout at the end of the four Fig. 8 evaluate windows. A and Cin are read from the simulated waveforms."""
    t = d["time"]; chk = []
    for w in (1, 3, 5, 7):
        tt = t0 + (w + 0.95) * NS
        a = 1 if float(np.interp(tt, t, d["v(a)"])) > 0.5 else 0
        cin = 1 if float(np.interp(tt, t, d["v(cin)"])) > 0.5 else 0
        s_, c_ = float(np.interp(tt, t, d["v(sum)"])), float(np.interp(tt, t, d["v(cout)"]))
        es, ec = (a ^ bit ^ cin), int(a + bit + cin >= 2)
        chk.append({"window_ns": f"{w}-{w+1}", "A": a, "B": bit, "Cin": cin, "sum_V": s_, "cout_V": c_, "sum_exp": es, "cout_exp": ec,
                    "ok": abs(s_ - es * vdd) < 0.15 * vdd and abs(c_ - ec * vdd) < 0.15 * vdd})
    return chk
