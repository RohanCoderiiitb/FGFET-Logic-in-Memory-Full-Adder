* T5: 1 ms storage-mode retention of '1'
.include ../../models/fgfet_subckt.sp
VWL0 wl0 0 pwl(0 0 5e-09 0 1e-08 3 2.2e-06 3 2.205e-06 -2 0.001 -2)
VDL0 dl0 0 pwl(0 0 1.1e-06 0 1.105e-06 1 2.2e-06 1 2.205e-06 0 0.001 0)
VSL0 sl0 0 pwl(0 0 0.001 0)
X0 wl0 dl0 sl0 0 0 FGFET w_dev=1u delvto_val=0
.options method=gear reltol=1e-4 gmin=1e-15 chgtol=1e-18
.control
pre_osdi ../../models/cva_cap.osdi
tran 10n 0.001
set wr_singlescale
let isl0 = -i(vsl0)
wrdata ../results/t5_retention.txt v(x0.mn) isl0 
quit
.endc
.end
