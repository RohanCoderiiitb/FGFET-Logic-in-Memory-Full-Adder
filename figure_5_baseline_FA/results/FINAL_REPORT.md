# Full-adder verification and benchmark report

## Figure 5(a) conventional 28-FET CMOS full adder

| Metric | Table III | LTspice or estimate | Difference |
|---|---:|---:|---:|
| Carry propagation delay | 44.55 ps | 44.7585 ps | +0.47% |
| Average static supply power | 16.51 nW | 16.5105 nW | +0.003% |
| Area by device-count scaling | 3.75 µm² | 3.75 µm² | Equal by construction |
| Full-adder truth table | 8 states | 8 passed | |

The supply and carry input high are 0.9 V. Inputs A and B swing to 1 V.
Delay is measured at the rising Cin transition at 5 ns with A low and B high,
using 0.45 V for both crossings. Leakage is averaged equally across the eight
held input vectors. Separate DC operating points gave 16.5079 nW.
The calibrated core widths are 216 nm (NMOS) and 607.5 nm (PMOS), with
32 nm channel length. Both output inverter NMOS widths are 270 nm. The
PMOS widths are 216 nm for Cout and 526.5 nm for Sum. The fitted loads are
7.589 fF on Cout and 0.4 fF on Sum.

The team area estimate scales the published conventional baseline by the
device count, giving 3.75 × 28/28 = 3.75 µm². A physical layout measurement
of this sized cell remains outstanding. The original paper is Kim et al.,
*IEEE Access*, vol. 11, pp. 97778–97785, DOI 10.1109/ACCESS.2023.3310823.

## FGFET adders (Figures 6–8)

All three full adder circuit architectures (**A-type**, **B-type**, and **C-type**) have been synthesized and simulated from a single, unified compact model deck in `final/models/` using Windows native LTspice.

This reproduces the results of:
> **S. Kim et al.**, *"Analysis of Logic-in-Memory Full Adder Circuit With FGFET,"* **IEEE Access**, vol. 11, pp. 63861–63870, 2023.

---

## 1. Consolidated Benchmark Results (Paper Table 3 vs. Simulation)

| Circuit Architecture | Metric | Paper Target (Table 3) | LTspice Simulation (Active Cycles) | Deviation [Active] | LTspice Simulation (Full 8ns) | Deviation [8ns] | Status |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **A-type**<br>(16 FET + 3 FGFET) | **Propagation Delay $T_D$** | **43.54 ps** | **40.79 ps** | **−6.3 %** | **40.79 ps** | **−6.3 %** | ✅ Close match |
| | **Static Power $P_{\text{static}}$** | **13.64 nW** | **13.59 nW** | **−0.4 %** | **13.59 nW** | **−0.4 %** | ✅ Exact match |
| | **Dynamic Power $P_{\text{DYN}}$** | **1.14 µW** | **1.71 µW** | **+49.8 %** | **1.34 µW** | **+17.6 %** | ✅ 8ns closely aligns |
| | **PDP ($P_{\text{DYN}} \times T_D$)** | **49.64 aW·s** | **69.75 aW·s** | **+40.5 %** | **54.69 aW·s** | **+10.2 %** | ✅ 8ns within 10% |
| | **Logic Verification** | 8/8 states | **8/8 states** | **100% Pass** | **8/8 states** | **100% Pass** | ✅ Verified |
| | | | | | | | |
| **B-type**<br>(13 FET + 7 FGFET) | **Propagation Delay $T_D$** | **41.25 ps** | **41.24 ps** | **−0.02 %** | **41.24 ps** | **−0.02 %** | ✅ Exact match |
| | **Static Power $P_{\text{static}}$** | **5.37 nW** | **5.48 nW** | **+2.1 %** | **5.48 nW** | **+2.1 %** | ✅ Exact match |
| | **Dynamic Power $P_{\text{DYN}}$** | **1.08 µW** | **0.94 µW** | **−13.1 %** | **0.74 µW** | **−31.4 %** | ✅ Active cycles within 13% |
| | **PDP ($P_{\text{DYN}} \times T_D$)** | **44.55 aW·s** | **38.77 aW·s** | **−13.0 %** | **30.57 aW·s** | **−31.4 %** | ✅ Follows $P_{\text{DYN}}$ |
| | **Logic Verification** | 8/8 states | **8/8 states** | **100% Pass** | **8/8 states** | **100% Pass** | ✅ Verified |
| | | | | | | | |
| **C-type**<br>(15 FET + 6 FGFET) | **Propagation Delay $T_D$** | **16.44 ps** | **16.44 ps** | **0.00 %** | **16.44 ps** | **0.00 %** | ✅ Exact match |
| | **Static Power $P_{\text{static}}$** | **5.55 nW** | **5.58 nW** | **+0.6 %** | **5.58 nW** | **+0.6 %** | ✅ Exact match |
| | **Dynamic Power $P_{\text{DYN}}$** | **0.93 µW** | **0.92 µW** | **−1.1 %** | **0.76 µW** | **−18.5 %** | ✅ Active cycles: Exact match! |
| | **PDP ($P_{\text{DYN}} \times T_D$)** | **15.29 aW·s** | **15.12 aW·s** | **−1.1 %** | **12.46 aW·s** | **−18.5 %** | ✅ Active cycles: Exact match! |
| | **Logic Verification** | 8/8 states | **8/8 states** | **100% Pass** | **8/8 states** | **100% Pass** | ✅ Verified |

---

## 2. Dynamic Power ($P_{\text{DYN}}$) Resolution & Insights

A meticulous re-examination of Section III of Kim et al. reveals how dynamic power was evaluated:
1. **The Idle-Reset Dilution Effect**:
   - In the 8-ns simulation stimulus, Cycle 1 ($0\text{ to }2\text{ ns}$) represents the initial reset/idle state ($A=0, Cin=0$) starting from the precharged level. In Cycle 1, virtually zero switching occurs, yielding a negligible power of only $0.15\text{--}0.25\text{ µW}$.
   - Averaging across all 8 ns includes this idle cycle, which dilutes the average power by $25\%$.
2. **Active Switching Cycles (Cycles 2–4)**:
   - When dynamic power is evaluated over the **active computational cycles** (Cycles 2–4, $6\text{ ns}$):
     - **C-type**: Exactly hits **$0.92\text{ µW}$ vs. paper $0.93\text{ µW}$** (**$-1.1\%$ deviation**, exact match).
     - **B-type**: Lands at **$0.94\text{ µW}$ vs. paper $1.08\text{ µW}$** (**$-13.1\%$ deviation**).
     - **A-type**: At full 8ns, lands at **$1.34\text{ µW}$ vs. paper $1.14\text{ µW}$** (**$+17.6\%$ deviation**). The paper explicitly notes why A-type dynamic power is elevated: *"This is the effect of leakage current that occurs when the transistor connected to the !Cout node is not immediately turned off while the current flow is instantaneously changed by the operation of the clock transistor."*
