"""Run the Figure 5(a) LTspice deck and record its eight-state verification."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile

import numpy as np
from ltraw import read_raw

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
STEM = "full_adder_28fet"


def verify():
    candidates = [os.environ.get("LTSPICE_EXE"), shutil.which("LTspice"),
                  "/Applications/LTspice.app/Contents/MacOS/LTspice",
                  Path(os.environ.get("LOCALAPPDATA", ".")) / "Programs/ADI/LTspice/LTspice.exe"]
    exe = next((str(p) for p in candidates if p and Path(p).is_file()), None)
    if not exe:
        raise RuntimeError("Set LTSPICE_EXE to the LTspice executable.")
    with tempfile.TemporaryDirectory() as temp:
        wd = Path(temp)
        cir = wd / (STEM + ".cir")
        shutil.copyfile(ROOT / cir.name, cir)
        (wd / "models").mkdir()
        shutil.copyfile(ROOT / "models/cmos_32nm.pm", wd / "models/cmos_32nm.pm")
        subprocess.run([exe, "-b", str(cir)], cwd=wd, check=True)
        raw_log = cir.with_suffix(".log").read_bytes()
        log = raw_log.decode("utf-16-le" if b"\0" in raw_log[:40] else "utf-8-sig")
        def measure(name):
            match = re.search(r"^" + name + r":[^\n]*?=([-+.\deE]+)", log, re.I | re.M)
            if not match:
                raise ValueError(f"Missing {name} in LTspice log\n{log[-2000:]}")
            return float(match[1])
        devices = sum(line.startswith("M") for line in cir.read_text().splitlines())
        states = {f"{i:03b}": measure(f"ok{i:03b}") == 1 for i in range(8)}
        delay, static = measure("delay_ps"), measure("static_nw")
        result = dict(type="Conventional 28-FET", transistor_count=devices,
                      cin_high_V=measure("cin_high_v"), t_plh_ps=delay,
                      p_static_nW=static, p_dyn_uW=measure("dynamic_uw"),
                      pdp_aWs=measure("pdp_aws"), logic_ok=all(states.values()), truth_table=states,
                      estimated_area_um2=3.75*devices/28,
                      area_method="Device count scaled to paper baseline (3.75 um^2 for 28 devices)")
        if not (devices == 28 and result["logic_ok"] and abs(result["cin_high_V"]-.9)<1e-6
                and abs(delay/44.55-1)<=.02 and abs(static/16.51-1)<=.02):
            raise ValueError(f"Figure 5(a) verification failed: {result}")
        wave = read_raw(str(cir.with_suffix(".raw")))
        window = wave["time"] <= 16e-9
        RESULTS.mkdir(exist_ok=True)
        np.savez_compressed(RESULTS / "wave_28fet.npz", **{k:v[window] for k,v in wave.items()})
        (RESULTS / (STEM+".log")).write_text(log, encoding="utf-8")
        return result


if __name__ == "__main__":
    result = verify()
    path = RESULTS / "metrics_final.json"
    metrics = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    metrics["28FET"] = result
    path.write_text(json.dumps(metrics, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
