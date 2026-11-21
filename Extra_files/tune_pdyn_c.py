import sys, os, re, tempfile, shutil
import numpy as np

sys.path.insert(0, r"fgfet_ctype_fa_ltspice\scripts")
import fa as fa_c, metrics as M

asc_c = open(r"final\full_adder_ctype.asc").read()

# Let's test varying C_internal vs C_output for C-type:
# C1 (_sum), C3 (_cout) are internal
# C2 (sum), C4 (cout) are output
print("=== C-TYPE DYNAMIC POWER TUNING ===")
print(f"{'C_int':>8} {'C_out':>8} | {'TD(ps)':>7} {'Pstat(nW)':>10} {'Pdyn(uW)':>9} {'PDP(aWs)':>9} {'Logic':>6}")
print("-" * 65)

for c_int in [2.5e-16, 2.7e-16, 3.0e-16, 3.2e-16]:
    for c_out in [3.0e-16, 4.0e-16, 5.0e-16, 6.0e-16, 7.0e-16]:
        src = asc_c
        # Replace C1 and C3
        src = re.sub(r"(SYMATTR InstName C1\nSYMATTR Value )[-0-9.eE+]+", rf"\g<1>{c_int:.2e}", src)
        src = re.sub(r"(SYMATTR InstName C3\nSYMATTR Value )[-0-9.eE+]+", rf"\g<1>{c_int:.2e}", src)
        # Replace C2 and C4
        src = re.sub(r"(SYMATTR InstName C2\nSYMATTR Value )[-0-9.eE+]+", rf"\g<1>{c_out:.2e}", src)
        src = re.sub(r"(SYMATTR InstName C4\nSYMATTR Value )[-0-9.eE+]+", rf"\g<1>{c_out:.2e}", src)
        
        # Quick measure
        work = tempfile.mkdtemp(prefix="test_c_")
        try:
            shutil.copy(r"final\FGFET.asy", work)
            p1 = fa_c._prepare(fa_c.asc_text(1, True, src), work, "c1.asc", models=os.path.abspath(r"final\models"))
            p0 = fa_c._prepare(fa_c.asc_text(0, True, src), work, "c0.asc", models=os.path.abspath(r"final\models"))
            d1 = fa_c.sim(p1); d0 = fa_c.sim(p0)
            
            vdd = 0.9
            # Delay
            s_d = fa_c.asc_text(1, True, src)
            s_d = re.sub(r"(!Vclk clk 0 )PWL\([^)]*\)", r"\1PWL(0 0.9 2.28e-06 0.9 2.285e-06 0 2.2999e-06 0 2.29995e-06 0.9)", s_d)
            s_d = re.sub(r"(!Vcin cin 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.3005e-06 0 2.30055e-06 1.0)", s_d)
            s_d = re.sub(r"(!Vncin ncin 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.29995e-06 1.0 2.3005e-06 1.0 2.30055e-06 0)", s_d)
            s_d = re.sub(r"(!Va a 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.4e-06 0)", s_d)
            s_d = re.sub(r"(!Vna na 0 )PWL\([^)]*\)", r"\1PWL(0 0 2.29995e-06 1.0)", s_d)
            s_d = re.sub(r"(!Vwl_a wl_a 0 )PWL\([^)]*\)", r"\1PWL(0 3 1.1e-6 3 2.2e-6 3 2.205e-6 -2 2.28e-6 -2 2.285e-6 0)", s_d)
            s_d = s_d.replace("!.tran 0 3e-06 0 10p", "!.tran 0 2.31e-06 0 10p")
            p_d = fa_c._prepare(s_d, work, "delay_c.asc", models=os.path.abspath(r"final\models"))
            dd = fa_c.sim(p_d); tt = dd["time"]
            ti = M.cross(tt, dd["v(cin)"], 0.5, 2.3003e-6)
            to = M.cross(tt, dd["v(cout)"], vdd / 2, 2.3003e-6)
            td = (to - ti) * 1e12 if (ti and to) else None
            
            p1_avg = M.p_avg(d1, vdd, fa_c.T_LOGIC)
            p0_avg = M.p_avg(d0, vdd, fa_c.T_LOGIC)
            pavg = 0.5 * (p1_avg + p0_avg)
            pst = 5.58e-9 # known static
            pdyn = (pavg - pst) * 1e6
            pdp = pdyn * td if td else None
            
            l1 = M.logic_check(d1, 1, vdd, fa_c.T_LOGIC)
            l0 = M.logic_check(d0, 0, vdd, fa_c.T_LOGIC)
            ok = all(x["ok"] for x in l1 + l0)
            
            print(f"{c_int*1e15:7.2f}f {c_out*1e15:7.2f}f | {td:7.2f} {pst*1e9:10.2f} {pdyn:9.3f} {pdp:9.2f} {str(ok):>6}")
        finally:
            shutil.rmtree(work, ignore_errors=True)
