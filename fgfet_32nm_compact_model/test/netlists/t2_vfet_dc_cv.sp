* T2: VFET Id-Vg (Vds = 0.05 V, 1 V) and Cgg-Vg (Vds = 0), W = 1 um
.include ../../vfet_32nm.pm
vd d 0 0.05
vg g 0 dc 0 ac 1
m1 d g 0 0 vfet_nmos w=1u l=100.2n
.option gmin=1e-18
.control
set wr_singlescale
dc vg 0 3 0.01
let id = -i(vd)
wrdata ../results/vfet_iv0.txt id
alter vd dc = 1.0
dc vg 0 3 0.01
let id = -i(vd)
wrdata ../results/vfet_iv1.txt id
alter vd dc = 0
foreach v 0.00 0.05 0.10 0.15 0.20 0.25 0.30 0.35 0.40 0.45 0.50 0.55 0.60 0.65 0.70 0.75 0.80 0.85 0.90 0.95 1.00 1.05 1.10 1.15 1.20 1.25 1.30 1.35 1.40 1.45 1.50 1.55 1.60 1.65 1.70 1.75 1.80 1.85 1.90 1.95 2.00 2.05 2.10 2.15 2.20 2.25 2.30 2.35 2.40 2.45 2.50 2.55 2.60 2.65 2.70 2.75 2.80 2.85 2.90 2.95 3.00
  alter vg dc = $v
  ac lin 1 1meg 1meg
  let cg = -imag(i(vg))/(2*3.141592653589793*1e6)
  echo "$v $&cg" >> ../results/vfet_cv.txt
end
quit
.endc
.end
