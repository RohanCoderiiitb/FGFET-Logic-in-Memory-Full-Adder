# FGFET-Logic-in-Memory-Full-Adder

LTspice reproduction of *Analysis of Logic-in-Memory Full Adder Circuit With Floating Gate Field Effect Transistor (FGFET)* (S. Kim et al., *IEEE Access*, 2023) at the 32 nm node.

## Repository Structure

- [`fgfet_32nm_compact_model/`](fgfet_32nm_compact_model/) — 32 nm BSIM4 model cards (`cmos_32nm.pm`, `sfet_32nm.pm`, `vfet_32nm.pm`) and FGFET subcircuit (`fgfet_ltspice.sub`)
- [`fgfet_atype_fa_ltspice/`](fgfet_atype_fa_ltspice/) — **A-type Full Adder** LTspice schematic (`full_adder_atype.asc`), scripts, and [full report](fgfet_atype_fa_ltspice/results/ATYPE_RESULTS.md)
- [`fgfet_btype_fa_ltspice/`](fgfet_btype_fa_ltspice/) — **B-type Full Adder** LTspice schematic (`full_adder_btype.asc`), scripts, and [full report](fgfet_btype_fa_ltspice/results/BTYPE_RESULTS.md)

---

## Comparison: Paper vs. LTspice (A-Type & B-Type)

| Metric | A-Type (Paper) | A-Type (LTspice) | A-Type Deviation | B-Type (Paper) | B-Type (LTspice) | B-Type Deviation |
|---|---|---|---|---|---|---|
| **Transistor count** | 19 (16 FET + 3 FGFET) | 19 (16 FET + 3 FGFET) | exact | 20 (13 FET + 7 FGFET) | 20 (13 FET + 7 FGFET) | exact |
| **Reduction vs. 28-FET** | 9 fewer | 9 fewer | exact | 8 fewer | 8 fewer | exact |
| **Logic truth table (8 states)** | Pass | Pass | exact | Pass | Pass | exact |
| **$V_{DD}$** | 0.9 V | 0.9 V | exact | 0.9 V | 0.9 V | exact |
| **Propagation delay $t_{\text{PLH}}$ ($C_{\text{in}} \to C_{\text{out}}$)** | 43.54 ps | **34.27 ps** | −21.3 % | 41.25 ps | **42.94 ps** | +4.1 % |
| **Dynamic power $P_{\text{dyn}}$** | 1.14 µW | **1.316 µW** | +15.4 % | 1.08 µW | **0.906 µW** | −16.1 % |
| **Static power $P_{\text{static}}$ (avg)** | 13.64 nW | **12.35 nW** | −9.5 % | 5.37 nW (text: 5.40 nW) | **12.24 nW** | +128 % (342 nm inv PMOS) |
| **PDP ($P_{\text{dyn}} \times t_p$)** | 49.64 aW·s | **45.09 aW·s** | −9.2 % | 44.55 aW·s | **38.92 aW·s** | −12.6 % |
| **Area (layout vs. scaled est.)** | 2.46 µm² (−34.4 %) | **2.54 µm²** (−32.1 % est.) | +3.4 % | 2.24 µm² (−40.3 %) | **2.68 µm²** (−28.6 % est.) | +19.6 % |

*Note: Layout areas in LTspice are device-count-scaled estimates from the paper's 28-FET conventional full adder (`3.75 µm² / 28 × N`). Full details, waveforms, and methodology are in [`fgfet_atype_fa_ltspice/results/ATYPE_RESULTS.md`](fgfet_atype_fa_ltspice/results/ATYPE_RESULTS.md) and [`fgfet_btype_fa_ltspice/results/BTYPE_RESULTS.md`](fgfet_btype_fa_ltspice/results/BTYPE_RESULTS.md).*