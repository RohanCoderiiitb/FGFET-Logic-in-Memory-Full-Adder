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
| `scripts/fit_sfet.py` | 2.2 | Starts from PTM, sets EOT = 1.23 nm, fits 9 I–V parameters and then 7 C–V-only parameters |
| `scripts/fit_vfet.py` | 2.3 | Applies the Table I geometry, fits 10 I–V parameters and 9 C–V parameters, alternating twice |
| `scripts/fit_cva.py` | 3–4 | Fits C_VA(V) to the Fig. 4 memory-node levels under the Table II sequence. Writes the `.va`, compiles the `.osdi`, generates the subcircuit |
| `scripts/spice.py`, `fitlib.py`, `bsim4_card.py` | — | ngspice runner, bounded least-squares card fitter, and card reader/writer |

## Validation (test/results/summary.md)

18 of 20 checks pass.

| | Result |
|---|---|
| SFET Id–Vg | 0.19 decade RMS error at both V_DS (the paper's own BSIM4 fit: 0.23–0.36) |
| VFET Id–Vg | 0.09–0.11 decade RMS error (the paper's fit: 0.29–0.36) |
| Cgg–Vg | 5.0 % (SFET) and 5.8 % (VFET) RMS error; **just misses the 5 % limit** |
| Fig. 4 read-mode V_MN | −0.66 / +0.44 V against TCAD −0.58 / +0.45 V |
| Fig. 4 storage-mode V_MN | −1.52 / −1.13 V against TCAD −1.70 / −1.04 V |
| Table II read | 150 µA/µm for a stored '1', 13 pA/µm for a stored '0' |
| Floating-node charge | 0.8 mV drift over 100 storage/read cycles; 0.6 mV over 1 ms of retention |
| Adder bias schemes (Sec. III, 5–15 ns into the read) | A-type stored-bit read, B-type AND (`delvto` = 0.9) and C-type OR all work, with worst-case on/off current ratios of 10⁷–10⁸ |

## Where this departs from the guide, and why

1. **VFET current level.** The guide says I_on ≈ 2 µA/µm. The Fig. 2(b) axes actually run from 10⁻¹² to 10⁻⁸ A/µm, so
   I_on is about 1.5 nA/µm at V_DS = 0.05 V and 20 nA/µm at 1 V. That is consistent with the 0.1–0.3 µs node charging
   in Fig. 4. The SFET y-axes are also 10⁻⁸–10⁻⁴ and 10⁻⁶–10⁻³ A/µm, not the guide's ranges. All fits use the digitized
   figure data.
2. **C_VA direction is reversed.** The guide assumes C_VA is large when WL is above the node. The Fig. 4 coupling ratios
   say the opposite: about 0.2 when WL rises at initialize, but 0.36–0.6 in storage and read. The fit gives
   Cmax = 0.06 fF/µm (WL well above the node) and Cmin = 1.77 fF/µm (WL below), switching at V(WL,MN) ≈ 0.32 V.
   A multi-start fit lands on the same solution every time.
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

## Known limitations

- **Fig. 4 initialize kick** reaches 0.93 V against 0.6 V in TCAD. **Data-low storage** reaches −1.52 V against
  −1.70 V. A single tanh-shaped C_VA can't match every coupling event, because BSIM4 gives the SFET full-oxide
  accumulation capacitance when the node goes negative. The read-mode levels, which decide the logic, match to within
  0.09 V.
- **Read windows must be short.** A WL read voltage of 1.2–1.8 V (B- and C-type adders) turns the VFET on, and the
  memory node bleeds into DL = 0 V within about 100 ns (+1.59 V falls to +0.44 V). Keep reads on the nanosecond scale,
  as the paper's clocks are, or hold DL at the data value during reads.
- **Small C–V residuals.** There is a narrow capacitance spike exactly at V_GS = 0 in the VFET (about 2 aC of charge)
  and a slight bump below threshold.
- **PMOS is uncalibrated PTM.** The paper gives no PMOS data.
- **Digitizer output.** The TCAD band is a staircase of overlapping markers, which adds about 0.1 decade of noise to the
  I–V targets.
