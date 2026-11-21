* Figure 5(a) - conventional 28-FET CMOS full adder
* Table III comparison, Kim et al., DOI 10.1109/ACCESS.2023.3310823
* Area estimate per repository: 28 * (3.75 um^2 / 28) = 3.75 um^2.
* Physical cell area requires layout extraction.
.param VSUP=0.9 VAB=1 EDGE=10p LG=32n
.param WN=216.0n WP=607.5n WNI=270.0n WPI_SUM=526.5n WPI_COUT=216.0n
.param CLOAD_SUM=0.4f CLOAD_COUT=7.589f
.temp 27

VSUPPLY vdd 0 {VSUP}
* 0-16 ns: Fig. 5(b) timing, Cin at the requested 0.9 V.
VA   a   ah PULSE(0 {VAB}  {2n-EDGE/2} {EDGE} {EDGE} {2n-EDGE} 4n 4)
VB   b   bh PULSE(0 {VAB}  {4n-EDGE/2} {EDGE} {EDGE} {4n-EDGE} 8n 2)
VCIN cin ch PULSE(0 {VSUP} {1n-EDGE/2} {EDGE} {EDGE} {1n-EDGE} 2n 8)

* After 17 ns, hold each binary vector long enough to measure leakage.
.param T0=17n HOLD=2u
VAH ah 0 PULSE(0 {VAB}  {T0+4*HOLD} {EDGE} {EDGE} {4*HOLD-EDGE} {8*HOLD})
VBH bh 0 PULSE(0 {VAB}  {T0+2*HOLD} {EDGE} {EDGE} {2*HOLD-EDGE} {4*HOLD})
VCH ch 0 PULSE(0 {VSUP} {T0+HOLD}   {EDGE} {EDGE} {HOLD-EDGE}   {2*HOLD})



CCOUT cout 0 {CLOAD_COUT}
CSUM sum 0 {CLOAD_SUM}

.options plotwinsize=0 reltol=1e-4 gmin=1e-15 numdgt=8
.save V(a) V(b) V(cin) V(sum) V(cout) V(vdd) I(VSUPPLY)
.meas tran Cin_high_V MAX V(cin) FROM=0 TO=8n
.meas tran Delay_s TRIG V(cin) VAL={VSUP/2} TD=4.5n RISE=1
+ TARG V(cout) VAL={VSUP/2} TD=4.5n RISE=1
.meas tran Delay_ps PARAM Delay_s*1e12

* Static power, averaged equally over the eight settled input vectors
.meas tran P000 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+0.8*HOLD} TO={T0+0.95*HOLD}
.meas tran P001 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+1.8*HOLD} TO={T0+1.95*HOLD}
.meas tran P100 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+4.8*HOLD} TO={T0+4.95*HOLD}
.meas tran P101 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+5.8*HOLD} TO={T0+5.95*HOLD}
.meas tran P010 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+2.8*HOLD} TO={T0+2.95*HOLD}
.meas tran P011 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+3.8*HOLD} TO={T0+3.95*HOLD}
.meas tran P110 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+6.8*HOLD} TO={T0+6.95*HOLD}
.meas tran P111 AVG (-V(vdd)*I(VSUPPLY)) FROM={T0+7.8*HOLD} TO={T0+7.95*HOLD}
.meas tran Static_nW PARAM (P000+P001+P100+P101+P010+P011+P110+P111)*1e9/8

* Mid-vector functional checks, Sum and Cout at the half-supply threshold
.meas tran OK000 FIND ((V(sum)<{VSUP/2})*(V(cout)<{VSUP/2})) AT=0.5n
.meas tran OK001 FIND ((V(sum)>{VSUP/2})*(V(cout)<{VSUP/2})) AT=1.5n
.meas tran OK100 FIND ((V(sum)>{VSUP/2})*(V(cout)<{VSUP/2})) AT=2.5n
.meas tran OK101 FIND ((V(sum)<{VSUP/2})*(V(cout)>{VSUP/2})) AT=3.5n
.meas tran OK010 FIND ((V(sum)>{VSUP/2})*(V(cout)<{VSUP/2})) AT=4.5n
.meas tran OK011 FIND ((V(sum)<{VSUP/2})*(V(cout)>{VSUP/2})) AT=5.5n
.meas tran OK110 FIND ((V(sum)<{VSUP/2})*(V(cout)>{VSUP/2})) AT=6.5n
.meas tran OK111 FIND ((V(sum)>{VSUP/2})*(V(cout)>{VSUP/2})) AT=7.5n
.meas tran Truth_pass PARAM OK000*OK001*OK100*OK101*OK010*OK011*OK110*OK111
