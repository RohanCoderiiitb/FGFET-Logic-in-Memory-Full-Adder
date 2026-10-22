* T3: Fig. 4 transient, V_DL = 0.05 V / 1.0 V
.include ../../models/fgfet_subckt.sp
VWL0 wl0 0 pwl(0 0 5e-09 0 1e-08 3 2.2e-06 3 2.205e-06 -2 2.28e-06 -2 2.285e-06 0.5 2.4e-06 0.5)
VDL0 dl0 0 pwl(0 0 1.1e-06 0 1.105e-06 0.05 2.2e-06 0.05 2.205e-06 0 2.4e-06 0)
VSL0 sl0 0 pwl(0 0 2.28e-06 0 2.285e-06 0.9 2.4e-06 0.9)
X0 wl0 dl0 sl0 0 0 FGFET w_dev=1u delvto_val=0
VWL1 wl1 0 pwl(0 0 5e-09 0 1e-08 3 2.2e-06 3 2.205e-06 -2 2.28e-06 -2 2.285e-06 0.5 2.4e-06 0.5)
VDL1 dl1 0 pwl(0 0 1.1e-06 0 1.105e-06 1 2.2e-06 1 2.205e-06 0 2.4e-06 0)
VSL1 sl1 0 pwl(0 0 2.28e-06 0 2.285e-06 0.9 2.4e-06 0.9)
X1 wl1 dl1 sl1 0 0 FGFET w_dev=1u delvto_val=0
.options method=gear reltol=1e-4 gmin=1e-15 chgtol=1e-18
.control
pre_osdi ../../models/cva_cap.osdi
tran 1n 2.4e-06
set wr_singlescale
let isl0 = -i(vsl0)
let isl1 = -i(vsl1)
wrdata ../results/t3_vmn.txt v(x0.mn) isl0 v(x1.mn) isl1 
quit
.endc
.end
