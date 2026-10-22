# 32 nm FGFET compact model (BSIM4 + Verilog-A)

A reconstruction of the FGFET compact model from S. Kim et al., *Analysis of Logic-in-Memory Full Adder Circuit
With Floating Gate Field Effect Transistor (FGFET)*, IEEE Access 2023. It follows Stages 1–4 of
`fgfet_compact_model_full_adder_replication_guide.md` using only open-source tools (guide option A).

## Model files

All model files live in `models/`. Keep `fgfet_subckt.sp` next to the `.pm` cards, because it includes them by relative path.

| File | Contents |
|---|---|
| `models/sfet_32nm.pm` | `sfet_nmos`: the FGFET's sense transistor, fitted to Fig. 2(a),(c) |
| `models/vfet_32nm.pm` | `vfet_nmos`: the vertical access transistor, fitted to Fig. 2(b),(d) |
| `models/cva_cap.va` / `models/cva_cap.osdi` | Verilog-A source and compiled OSDI library for the WL–memory-node coupling capacitor C_VA |
| `models/fgfet_subckt.sp` | `FGFET` subcircuit (Fig. 1(c)). It includes the two cards above and the fitted `cva_fgfet` model |
| `models/cmos_32nm.pm` | `nmos_32nm` (same fit as the SFET, with PTM GIDL kept) and `pmos_32nm` (unmodified PTM). For the conventional-CMOS parts of the adders |
| `models/ptm_32nm_hp_base.pm` | The PTM 32 nm HP starting card |
| `data/` | TCAD data and the paper's own BSIM4 curves, digitized from Fig. 2 and Fig. 4 (`digitization_check.png` shows them) |

## Using the model

```spice
.include /path/to/fgfet_32nm_compact_model/models/fgfet_subckt.sp
.options gmin=1e-15 chgtol=1e-18          $ required, see "Simulator settings"
X1 wl dl sl ss 0 FGFET w_dev=64n delvto_val=0    $ delvto_val=0.9 for the B-type adder
.control
pre_osdi /path/to/fgfet_32nm_compact_model/models/cva_cap.osdi
...
.endc
```

Pins are `WL DL SL SS B`. The memory node is `x1.mn`.

### Simulator settings

The memory node floats, and holds only a few femtocoulombs per µm, so two ngspice defaults break it:

- `gmin` defaults to 1e-12 S and is placed across every BSIM4 junction, including the VFET's junction on the memory
  node. That leaks a stored value away in microseconds (250 mV in 1 ms). With `gmin=1e-15` the drift is 0.6 mV in 1 ms.
- `chgtol` defaults to 1e-14 C, which is more than the node's total charge. Integration error then drifts the node by
  about 30 µV per WL cycle; with `chgtol=1e-18` that drops below 10 µV per cycle.

## Toolchain

- ngspice 44.2, built from source with `--enable-osdi` and installed to `~/.local` (no root needed).
- OpenVAF 23.5.0, the statically linked build, linked as `~/.local/bin/openvaf`. OpenVAF-Reloaded needs libLLVM 18,
  which isn't installed on this machine.
- Python 3 with numpy, scipy, matplotlib and Pillow, plus `pdftoppm` (poppler-utils).

ngspice runs `version = 4.0` BSIM4 cards on its BSIM4v5 code.

## Rebuilding and testing

```bash
scripts/build_models.sh [path/to/paper.pdf]   # digitize -> fit SFET -> fit VFET -> fit C_VA, ~1 min
python3 test/run_tests.py                     # ~5 s; writes test/plots, test/results/summary.md
```

| Script | Stage | What it does |
|---|---|---|
| `scripts/digitize_figures.py` | 1 | Renders PDF page 3 at 600 dpi and extracts the black TCAD markers and red BSIM4 curves, with axes calibrated from each plot's frame and gridlines. Replaces manual WebPlotDigitizer work |
| `scripts/fit_sfet.py` | 2.2 | Starts from PTM, sets EOT = 1.23 nm, fits 9 I–V parameters and 8 C–V parameters (including `k1`, bounded by Table I), alternating twice |
| `scripts/fit_vfet.py` | 2.3 | Applies the Table I geometry (with `capmod=1`), fits 10 I–V parameters and 8 C–V parameters, alternating twice |
| `scripts/fit_cva.py` | 3–4 | Fits C_VA(V) to the Fig. 4 memory-node levels under the Table II sequence (best of 6 deterministic starts). Writes the `.va`, compiles the `.osdi`, generates the subcircuit |
| `scripts/spice.py`, `fitlib.py`, `bsim4_card.py` | — | ngspice runner, bounded least-squares card fitter, and card reader/writer |

## Validation (test/results/summary.md)

All 20 checks pass.

| | Result |
|---|---|
| SFET Id–Vg | 0.19 decade RMS error at both V_DS (the paper's own BSIM4 fit: 0.23–0.36) |
| VFET Id–Vg | 0.09–0.11 decade RMS error (the paper's fit: 0.29–0.36) |
| Cgg–Vg | 4.7 % (SFET) and 2.5 % (VFET) RMS error (the paper's fit: 21.6 % and 6.0 %) |
| Fig. 4 read-mode V_MN | −0.64 / +0.44 V against TCAD −0.58 / +0.45 V |
| Fig. 4 storage-mode V_MN | −1.53 / −1.13 V against TCAD −1.70 / −1.04 V |
| Fig. 4 initialize kick (not a test check) | 0.97 V peak against the TCAD marker at 0.60 V |
| Table II read | 157 µA/µm for a stored '1', 15 pA/µm for a stored '0' |
| Floating-node charge | 0.1 mV drift over 100 storage/read cycles; 0.6 mV over 1 ms of retention |
| Adder bias schemes (Sec. III, 5–15 ns into the read) | A-type stored-bit read, B-type AND (`delvto` = 0.9) and C-type OR all work, with worst-case on/off current ratios of 10⁷–10⁸ |

## Where this departs from the guide, and why

1. **VFET current level.** The guide says I_on ≈ 2 µA/µm. The Fig. 2(b) axes actually run from 10⁻¹² to 10⁻⁸ A/µm, so
   I_on is about 1.5 nA/µm at V_DS = 0.05 V and 20 nA/µm at 1 V. That is consistent with the 0.1–0.3 µs node charging
   in Fig. 4. The SFET y-axes are also 10⁻⁸–10⁻⁴ and 10⁻⁶–10⁻³ A/µm, not the guide's ranges. All fits use the digitized
   figure data.
2. **C_VA direction is reversed.** The guide assumes C_VA is large when WL is above the node. The Fig. 4 coupling ratios
   say the opposite: about 0.2 when WL rises at initialize, but 0.36–0.6 in storage and read. The fit gives
   Cmax = 0.085 fF/µm (WL well above the node) and Cmin = 1.81 fF/µm (WL below), switching at V(WL,MN) ≈ 0.34 V.
3. **GIDL is off in `sfet_nmos` (`agidl=0`).** Fig. 2 never drives V_GS below 0, so it doesn't constrain GIDL. With PTM
   values, a stored '0' (gate at −0.65 V, drain at 0.9 V) draws 1 µA/µm of GIDL. The paper credits the Si₃N₄ barrier
   with suppressing GIDL and says a stored '0' conducts no current. `nmos_32nm` keeps the PTM GIDL so the conventional
   28FET adder stays conventional.
4. **SFET and VFET gate tunnelling are off (`igcmod=igbmod=0`).** BSIM4 would compute SFET tunnelling from the 1.23 nm
   EOT, but the physical high-k stack is 3.7 nm. The VFET has 10 nm of SiO₂.
5. **VFET short-channel terms.** With an intrinsic channel, BSIM4's depletion width is about 1 µm. With PTM's
   `dsub=0.1` that multiplies DIBL by about 300 and pushed Vth to −1.9 V at V_DS = 1 V. The card uses `dvt0=0` and
   `dsub=1`, which fits a wrap-gated 100 nm pillar.
6. **SFET C–V length.** TCAD Cgg reaches 2.45 fF/µm, about 3× what a 32 nm (12.6 nm effective length) gate can
   produce. The card uses `dlc` ≈ −25 nm, which affects only C–V; I–V is unchanged.
7. **SFET `k1` comes from Table I, not PTM.** PTM's `k1 = 0.4` corresponds to its 4.1e18 cm⁻³ halo doping and holds the
   sub-threshold Cgg flat through a large depletion term, missing the TCAD rise from 0.53 to 0.74 fF/µm over
   0.18–0.32 V. Table I gives the SFET substrate as 1e16–1.8e17 cm⁻³, i.e. `k1` = √(2qε_Si·N)/C_ox ∈ [0.021, 0.087].
   Fitted inside that range: `k1` = 0.063 (N ≈ 9e16 cm⁻³). C–V error drops from 5.0 % to 4.7 %; I–V is unchanged.
8. **VFET uses `capmod=1`.** `capmod=2` adds bulk-MOSFET charge-centroid and surface-potential (ΔΦ) corrections that
   assume a doped body. With the undoped pillar's `k1` ≈ 0, ΔΦ blows up and distorts the moderate-inversion C–V. The fit
   was stuck at about 5.8 % with `noff` and `moin` pinned at their bounds, and freeing `k1` did not help. `capmod=1`
   keeps the same weak-inversion form without those corrections: 2.5 %, with I–V unchanged. `noff` ≤ 4 is consistent
   with the TCAD onset slope, noff·n ≈ 3.4–3.9 between 0.70 and 0.95 V. A wider `noff` bound fits better but only by
   bending the strong-inversion region, so it is not used.

## Known limitations

- **Fig. 4 initialize kick** reaches 0.97 V against 0.6 V in TCAD. **Data-low storage** reaches −1.53 V against
  −1.70 V. No single-valued C_VA(V(WL,MN)) can fix these. The node's charge is conserved across each coupling edge, so
  each edge fixes ∫C_VA dv between its start and end voltage. With C_VA removed and the node forced along the TCAD
  levels, the other elements need these amounts:

  | Edge | ∫C_VA dv required |
  |---|---|
  | Initialize, v = 0 → 2.4 V | **−0.10 fC**: impossible for C ≥ 0. The VFET's turn-on coupling alone already overshoots 0.6 V |
  | Storage-high minus read-high | +0.57 fC over 0.05–2.0 V, which contradicts the initialize edge |

  The best non-negative C(v) of *any* shape still misses three edges by 0.18–0.24 fC, using an unphysical 35 fF/µm
  spike. A physical (monotone) MOS-capacitor shape misses by 0.3–1.0 fC, and the tanh is already in that class.
  A physics-based accumulation/deep-depletion form collapses to the same step.

  Weighting the kick more heavily lowers it, but only by breaking the stored-'1' read level:

  | Kick weight | Kick | Read-high V_MN (TCAD 0.45 V) |
  |---|---|---|
  | 0.5 (used) | 0.97 V | 0.44 V |
  | 1 | 0.82 V | 0.55 V (fails the 0.1 V check) |
  | 4 | 0.72 V | 0.63 V |

  The kick bottoms out at about 0.72 V. Storage-low stays at −1.49 to −1.53 V under every weighting. Both gaps come
  from the BSIM4 SFET/VFET charge functions, not from C_VA. The fit therefore keeps the logic-critical read levels
  accurate (within 0.06 V).
- **Read windows must be short.** A WL read voltage of 1.2–1.8 V (B- and C-type adders) turns the VFET on, and the
  memory node bleeds into DL = 0 V within about 100 ns (+1.59 V falls to +0.44 V). Keep reads on the nanosecond scale,
  as the paper's clocks are, or hold DL at the data value during reads.
- **VFET below V_GS = 0 is unconstrained.** Fig. 2(d) stops at 0 V. Below it the VFET accumulates (Cgb ≈ 0.35 fF/µm
  to the body), which a floating undoped pillar physically cannot do. That charge goes to substrate/GND, so it only
  adds about 20 aF of load per 64 nm FGFET on the word line and does not couple into the memory node. It also produces
  the jump in Cgg at exactly V_GS = 0. The VFET's strong-inversion Cgg plateau is about 4 % low (0.67 vs 0.70 fF/µm),
  because `capmod=1` has no charge-centroid term.
- **PMOS is uncalibrated PTM.** The paper gives no PMOS data.
- **Digitizer output.** The TCAD band is a staircase of overlapping markers, which adds about 0.1 decade of noise to the
  I–V targets.
