"""Run the agreed experiment locally, with immutable inputs and resumable stages."""
from pathlib import Path
import datetime
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys

BASE = Path(__file__).resolve().parent
CODE = BASE / "experiment"
WORK = BASE / "run"
DATA = BASE / "data" / "competencia_02_crudo.csv.gz"
CONFIG = CODE / "config.json"
METHODS = ["E0", "E4", "FF_ZERO", "FF_MEDIAN_MICA"]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    WORK.mkdir(exist_ok=True)
    (WORK / "logs").mkdir(exist_ok=True)
    env = os.environ.copy()
    for name in ["PIPELINE_REMOTE_URI", "PIPELINE_WORK_DIR"]:
        env.pop(name, None)
    env.update({"OMP_NUM_THREADS": "7", "POLARS_MAX_THREADS": "7",
                "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1"})
    identity = {
        "dataset": str(DATA), "dataset_sha256": digest(DATA),
        "protocol_sha256": digest(BASE / "protocol.json"),
        "source_commit": "27d9d941f47b3b0eeaa7c724990baf5361613ce8",
        "code_sha256": {str(p.relative_to(CODE)): digest(p)
                         for p in sorted(CODE.rglob("*.py"))},
        "config_sha256": digest(CONFIG),
        "selection_sha256": digest(CODE / "seleccion.json"),
        "python": sys.version,
        "dependencies": {name: importlib.metadata.version(name) for name in
                         ["numpy", "polars", "pyarrow", "lightgbm", "scikit-learn", "scipy"]},
        "threads": 7, "methods": METHODS,
    }
    identity_path = WORK / "run_identity.json"
    if identity_path.exists() and json.loads(identity_path.read_text()) != identity:
        raise RuntimeError("Run inputs or environment changed; do not reuse old checkpoints")
    identity_path.write_text(json.dumps(identity, indent=2))
    common = ["--work", str(WORK), "--config", str(CONFIG)]
    stages = [
        ("tests", ["-m", "unittest", "test_ff_variants", "-v"]),
        ("auditar", ["01_auditar.py", *common, "--data", str(DATA)]),
        ("particionar", ["02_particionar.py", *common]),
        ("preparar_E0", ["03_imputar_baseline.py", *common]),
        ("preparar_E4", ["03_imputar_temporal.py", *common]),
        ("preparar_variantes", ["ff_variants.py", *common]),
        ("modelar", ["04_modelar_evaluar.py", *common, "--methods", *METHODS, "--n_jobs", "7"]),
    ]
    status = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "completed_stages": [], "status": "running"}
    status_path = WORK / "progress.json"
    with (WORK / "logs/execution.log").open("a", buffering=1) as log:
        for name, command in stages:
            status.update(stage=name, updated_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
            status_path.write_text(json.dumps(status, indent=2))
            print(f"STAGE_START {name}", flush=True)
            log.write(f"\nSTAGE_START {name}\n")
            process = subprocess.Popen([sys.executable, "-u", *command], cwd=CODE, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, bufsize=1)
            for line in process.stdout:
                log.write(line)
                print(line, end="", flush=True)
            returncode = process.wait()
            if returncode:
                status.update(status="failed", returncode=returncode)
                status_path.write_text(json.dumps(status, indent=2))
                raise RuntimeError(f"Stage {name} failed with exit code {returncode}")
            status["completed_stages"].append(name)
            print(f"STAGE_DONE {name}", flush=True)
        status.update(status="complete", stage="complete",
                      completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        status_path.write_text(json.dumps(status, indent=2))
        print("EXPERIMENT_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
