"""Run the three Fabric notebooks on your own machine, against the synthetic sample.

    pip install -r tools/requirements.txt
    python tools/run_local.py                 # uses synthetic-data/sample, writes to ./_local
    python tools/run_local.py --keep          # don't wipe ./_local first

The notebooks are the same files Fabric runs. When PDS_LOCAL_ROOT is set they read and write Delta tables
under that folder instead of OneLake. Nothing leaves your machine.
"""
import argparse
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
NOTEBOOKS = ["nb_01_bronze_to_silver", "nb_02_validate", "nb_03_build_gold"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default=os.path.join(REPO, "synthetic-data", "sample"))
    ap.add_argument("--root", default=os.path.join(REPO, "_local"))
    ap.add_argument("--extract", default="2026-07-15")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    if not a.keep and os.path.exists(a.root):
        shutil.rmtree(a.root)
    landing = os.path.join(a.root, "bronze", "Files", "landing", a.extract)
    if not os.path.exists(landing):
        # the x12 folder is an example of the format, not an input to the PM path
        shutil.copytree(a.sample, landing, ignore=shutil.ignore_patterns("x12"))
    os.environ["PDS_LOCAL_ROOT"] = a.root.replace("\\", "/")

    for nb in NOTEBOOKS:
        path = os.path.join(REPO, "fabric", f"{nb}.Notebook", "notebook-content.py")
        print(f"\n=== {nb}")
        t = time.time()
        code = compile(open(path, encoding="utf-8").read(), path, "exec")
        try:
            exec(code, {"__name__": "__main__"})
        except RuntimeError as e:
            print(f"\nstopped: {e}")
            sys.exit(1)
        print(f"--- {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
