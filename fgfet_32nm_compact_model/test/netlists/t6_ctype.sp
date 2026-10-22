* T6: C-type (OR), delvto = 0.0 V
.include ../../fgfet_subckt.sp
VWL0 wl0 0 pwl(0 0 5e-09 0 1e-08 3 2.2e-06 3 2.205e-06 -2 2.28e-06 -2 2.285e-06 0 2.4e-06 0)
VDL0 dl0 0 pwl(0 0 1.1e-06 0 1.105e-06 0.85 2.2e-06 0.85 2.205e-06 0 2.4e-06 0)
VSL0 sl0 0 pwl(0 0 2.28e-06 0 2.285e-06 0.9 2.4e-06 0.9)
X0 wl0 dl0 sl0 0 0 FGFET w_dev=64n delvto_val=0.0
VWL1 wl1 0 pwl(0 0 5e-09 0 1e-08 3 2.2e-06 3 2.205e-06 -2 2.28e-06 -2 2.285e-06 0 2.4e-06 0)
VDL1 dl1 0 pwl(0 0 1.1e-06 0 1.105e-06 1.85 2.2e-06 1.85 2.205e-06 0 2.4e-06 0)
VSL1 sl1 0 pwl(0 0 2.28e-06 0 2.285e-06 0.9 2.4e-06 0.9)
X1 wl1 dl1 sl1 0 0 FGFET w_dev=64n delvto_val=0.0
VWL2 wl2 0 pwl(0 0 5e-09 0 1e-08 3 2.2e-06 3 2.205e-06 -2 2.28e-06 -2 2.285e-06 1.2 2.4e-06 1.2)
VDL2 dl2 0 pwl(0 0 1.1e-06 0 1.105e-06 0.85 2.2e-06 0.85 2.205e-06 0 2.4e-06 0)
VSL2 sl2 0 pwl(0 0 2.28e-06 0 2.285e-06 0.9 2.4e-06 0.9)
X2 wl2 dl2 sl2 0 0 FGFET w_dev=64n delvto_val=0.0
VWL3 wl3 0 pwl(0 0 5e-09 0 1e-08 3 2.2e-06 3 2.205e-06 -2 2.28e-06 -2 2.285e-06 1.2 2.4e-06 1.2)
VDL3 dl3 0 pwl(0 0 1.1e-06 0 1.105e-06 1.85 2.2e-06 1.85 2.205e-06 0 2.4e-06 0)
VSL3 sl3 0 pwl(0 0 2.28e-06 0 2.285e-06 0.9 2.4e-06 0.9)
X3 wl3 dl3 sl3 0 0 FGFET w_dev=64n delvto_val=0.0
.options method=gear reltol=1e-4 gmin=1e-15 chgtol=1e-18
.control
pre_osdi ../../cva_cap.osdi
tran 1n 2.4e-06
set wr_singlescale
let isl0 = -i(vsl0)
let isl1 = -i(vsl1)
let isl2 = -i(vsl2)
let isl3 = -i(vsl3)
wrdata ../results/t6_ctype.txt v(x0.mn) isl0 v(x1.mn) isl1 v(x2.mn) isl2 v(x3.mn) isl3 
quit
.endc
.end
