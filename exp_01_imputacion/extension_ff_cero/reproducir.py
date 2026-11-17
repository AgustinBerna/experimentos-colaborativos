"""Portable entry point for the existing, unchanged experiment runner."""
import argparse
from pathlib import Path
import run_experiment

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reproducir las cuatro variantes de Florencia")
    parser.add_argument("--data", type=Path, required=True, help="competencia_02_crudo.csv.gz local")
    args = parser.parse_args()
    if not args.data.is_file():
        parser.error("El archivo indicado no existe")
    run_experiment.DATA = args.data.resolve()
    run_experiment.main()
