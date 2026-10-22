"""Bounded least-squares fitting of BSIM4 card parameters against ngspice."""
import os
import tempfile

import numpy as np
from scipy.optimize import least_squares

from bsim4_card import write_card


class CardFitter:
    """free: list of (param, lo, hi, log_scale). Parameters are normalised to
    [0, 1] (log-spaced when log_scale) so the optimiser sees similar scales."""

    def __init__(self, name, dtype, params, free, residual_fn):
        self.name, self.dtype = name, dtype
        self.params = dict(params)
        self.free = free
        self.residual_fn = residual_fn
        self.card = os.path.join(tempfile.mkdtemp(prefix="fit_"), "card.pm")
        self.nfev = 0

    def _to_u(self, k, v, lo, hi, lg):
        return (np.log(v / lo) / np.log(hi / lo)) if lg else (v - lo) / (hi - lo)

    def _from_u(self, u, lo, hi, lg):
        return lo * (hi / lo) ** u if lg else lo + u * (hi - lo)

    def apply(self, u):
        p = dict(self.params)
        for ui, (k, lo, hi, lg) in zip(u, self.free):
            p[k] = self._from_u(ui, lo, hi, lg)
        return p

    def residual(self, u):
        self.nfev += 1
        write_card(self.card, [(self.name, self.dtype, self.apply(u), "")])
        try:
            r = self.residual_fn(self.card)
        except Exception:
            return np.full(self._nres, 10.0)
        r = np.nan_to_num(r, nan=10.0, posinf=10.0, neginf=-10.0)
        self._nres = len(r)
        return r

    def fit(self, max_nfev=300):
        u0 = []
        for k, lo, hi, lg in self.free:
            v = float(self.params[k])
            u0.append(np.clip(self._to_u(k, v, lo, hi, lg), 0.0, 1.0))
        u0 = np.array(u0)
        write_card(self.card, [(self.name, self.dtype, self.params, "")])
        r0 = self.residual_fn(self.card)
        self._nres = len(r0)
        sol = least_squares(self.residual, u0, bounds=(0, 1), diff_step=1e-3,
                            x_scale=1.0, max_nfev=max_nfev)
        self.params = self.apply(sol.x)
        rms0 = np.sqrt(np.mean(r0 ** 2))
        rms1 = np.sqrt(np.mean(sol.fun ** 2))
        print(f"  [{self.name}] {len(self.free)} params, {self.nfev} evals, rms {rms0:.4g} -> {rms1:.4g}")
        for k, lo, hi, lg in self.free:
            v = self.params[k]
            edge = " (at bound)" if np.isclose(v, lo, rtol=1e-3, atol=0) or np.isclose(v, hi, rtol=1e-3, atol=0) else ""
            print(f"      {k:8s} = {v:.5g}{edge}")
        return self.params


class TiedFitter(CardFitter):
    """Keep drain-side overlap parameters equal to the source-side ones."""
    TIES = {"cgdo": "cgso", "cgdl": "cgsl", "ckappad": "ckappas"}

    def apply(self, u):
        p = super().apply(u)
        for dst, src in self.TIES.items():
            if src in p:
                p[dst] = p[src]
        return p


def iv_residual(data_dir, prefix, w, l, floor=1e-20):
    """log10 error vs. the digitized `<prefix>_idvg_vds{0p05,1}_tcad.csv` data."""
    import spice

    targets = {vds: spice.load_target(os.path.join(data_dir, f"{prefix}_idvg_{tag}_tcad.csv"))
               for vds, tag in ((0.05, "vds0p05"), (1.0, "vds1"))}

    def fn(card):
        vg, ids = spice.idvg(card, "fitdev", w, l, list(targets))
        return np.concatenate([np.interp(x, vg, np.log10(np.abs(ids[vds]) + floor)) - np.log10(y)
                               for vds, (x, y) in targets.items()])
    return fn


def cv_residual(data_dir, prefix, w, l):
    """Relative Cgg error in % vs. `<prefix>_cgg_tcad.csv`."""
    import spice

    x, y = spice.load_target(os.path.join(data_dir, f"{prefix}_cgg_tcad.csv"))

    def fn(card):
        _, c = spice.cgg(card, "fitdev", w, l, x)
        return 100.0 * (c - y) / y
    return fn
