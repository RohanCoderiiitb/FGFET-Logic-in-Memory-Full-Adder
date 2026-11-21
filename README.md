# FGFET-Logic-in-Memory-Full-Adder

LTspice reproduction and optimization of *Analysis of Logic-in-Memory Full Adder Circuit With Floating Gate Field Effect Transistor (FGFET)* (S. Kim et al., *IEEE Access*, vol. 11, pp. 63861–63870, 2023) at the 32 nm node.

---

## Repository Structure

- [`_final/`](_final/) — **Unified & Calibrated Final Benchmark Suite**:
  - Unified model deck in `_final/models/` shared identically across all three architectures.
  - Fully calibrated schematics (`full_adder_atype.asc`, `full_adder_btype.asc`, `full_adder_ctype.asc`).
  - Comprehensive verification script `scripts/run_all_final.py` running automated transient, delay, static power, and truth-table verification.
  - See [`_final/README.md`](_final/README.md) for full physical explanations, model changes, and calibration details.
- [`fgfet_atype_fa_ltspice/`](fgfet_atype_fa_ltspice/) — **A-type Full Adder** individual schematic (`full_adder_atype.asc`), scripts, and [report](fgfet_atype_fa_ltspice/results/ATYPE_RESULTS.md).
- [`fgfet_btype_fa_ltspice/`](fgfet_btype_fa_ltspice/) — **B-type Full Adder** individual schematic (`full_adder_btype.asc`), scripts, and [report](fgfet_btype_fa_ltspice/results/BTYPE_RESULTS.md).
- [`fgfet_ctype_fa_ltspice/`](fgfet_ctype_fa_ltspice/) — **C-type Full Adder** individual schematic (`full_adder_ctype.asc`), scripts, and [report](fgfet_ctype_fa_ltspice/results/CTYPE_RESULTS.md).
- [`fgfet_32nm_compact_model/`](fgfet_32nm_compact_model/) — 32 nm BSIM4 model cards (`cmos_32nm.pm`, `sfet_32nm.pm`, `vfet_32nm.pm`) and FGFET subcircuit (`fgfet_ltspice.sub`).
- [`Extra_files/`](Extra_files/) — Reference documentation, figures, and background notes.

---

## Comparison: Paper vs. LTspice Benchmarks (A-Type, B-Type, and C-Type)

The table below summarizes the simulation results from each individual benchmark folder against the target values reported in Table 3 of Kim et al. (IEEE Access 2023):

| Metric | A-Type (Paper) | A-Type (LTspice) | A-Type Dev | B-Type (Paper) | B-Type (LTspice) | B-Type Dev | C-Type (Paper) | C-Type (LTspice) | C-Type Dev |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Transistor Count** | 19 (16 FET + 3 FGFET) | 19 (16 FET + 3 FGFET) | Exact | 20 (13 FET + 7 FGFET) | 20 (13 FET + 7 FGFET) | Exact | 21 (15 FET + 6 FGFET) | 21 (15 FET + 6 FGFET) | Exact |
| **Reduction vs. 28-FET** | 9 fewer | 9 fewer | Exact | 8 fewer | 8 fewer | Exact | 7 fewer | 7 fewer | Exact |
| **Logic Truth Table (8 states)** | Pass | Pass | Exact | Pass | Pass | Exact | Pass | Pass | Exact |
| **$V_{DD}$** | 0.9 V | 0.9 V | Exact | 0.9 V | 0.9 V | Exact | 0.9 V | 0.9 V | Exact |
| **Propagation Delay $T_D$ ($C_{\text{in}} \to C_{\text{out}}$)** | 43.54 ps | **34.27 ps** | −21.3 % | 41.25 ps | **42.94 ps** | +4.1 % | 16.44 ps | **16.44 ps** | **0.0 %** |
| **Dynamic Power $P_{\text{DYN}}$** | 1.14 µW | **1.316 µW** | +15.4 % | 1.08 µW | **0.906 µW** | −16.1 % | 0.93 µW | **0.758 µW** | −18.5 % |
| **Static Power $P_{\text{static}}$ (avg)** | 13.64 nW | **12.35 nW** | −9.5 % | 5.37 nW | **12.24 nW** | +127.9 %* | 5.55 nW | **5.58 nW** | **+0.5 %** |
| **PDP ($P_{\text{DYN}} \times T_D$)** | 49.64 aW·s | **45.09 aW·s** | −9.2 % | 44.55 aW·s | **38.92 aW·s** | −12.6 % | 15.29 aW·s | **12.46 aW·s** | −18.5 % |
| **Area (layout vs. scaled est.)** | 2.46 µm² | **2.54 µm²** | +3.4 % | 2.24 µm² | **2.68 µm²** | +19.6 % | 2.53 µm² | **2.81 µm²** | +11.2 % |

*\*Note on B-type baseline static power: The original baseline in `fgfet_btype_fa_ltspice/` used $W_p = 342\text{ nm}$ inverter PMOS, leading to excessive subthreshold leakage ($12.24\text{ nW}$). In the unified `_final/` folder, this has been resolved down to $5.48\text{ nW}$ (+2.1% error) by properly sizing PMOS off-state dimensions.*

---

## Unified Calibration in `_final/`

To resolve the remaining deviations across all three circuits while ensuring all circuits use the **exact same model files**:
- Transistor sizing and off-state subthreshold leakage were re-calibrated (reducing B-type static power to **5.48 nW** vs. paper 5.37 nW).
- C-type delay matches the paper **identically at 16.44 ps** (0.0% deviation).
- Active switching window analysis resolves dynamic power across all designs (C-type active dynamic power: **0.92 µW** vs. paper 0.93 µW, **−1.1% deviation**).

For complete technical documentation, physical analysis, and instructions to run all simulations together, refer to [`_final/README.md`](_final/README.md).
