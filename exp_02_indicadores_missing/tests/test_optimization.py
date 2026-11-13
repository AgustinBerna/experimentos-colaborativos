"""Búsqueda/reajuste/reanudación reales sobre clientes sintéticos pequeños."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import optuna
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("exp3_model", ROOT / "04_modelar_evaluar.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def smoke_config():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    config["methods"] = ["E0", "E1"]
    config["gain"]["smoothing_radius_n"] = 2
    config["optimization"].update(trials=2, num_boost_round=12, early_stopping_rounds=3)
    config["optimization"]["search_space"] = {
        "num_leaves": [3, 6], "learning_rate": [.05, .15],
        "min_data_in_leaf": [3, 6], "feature_fraction": [.8, 1.],
        "bagging_fraction": [.8, 1.],
    }
    return config


def fixture(work, config):
    for method in config["methods"]:
        directory = work / method / "prepared"
        directory.mkdir(parents=True)
        frames = []
        for month in config["train_months"]:
            size = 40
            yb2 = (np.arange(size) % 10 == 0).astype(np.int8)
            y = np.maximum((np.arange(size) % 4 == 0).astype(np.int8), yb2)
            x = y + np.random.default_rng(month).normal(0, .4, size)
            x[::13] = np.nan if method == "E0" else 0.
            frames.append(pl.DataFrame({
                "numero_de_cliente": np.arange(size) + 1000, "foto_mes": [month] * size,
                "clase_ternaria": ["BAJA+2" if b else "BAJA+1" if t else "CONTINUA"
                                    for b, t in zip(yb2, y)],
                "target_binario": y, "target_baja2": yb2, "partition_role": ["train"] * size,
                "x": x, "x__ausente": (np.arange(size) % 13 == 0).astype(np.int8),
                "x__ausente_lag1": np.zeros(size, dtype=np.int8),
                "x__ausente_lag2": np.ones(size, dtype=np.int8),
                "x__ausente_delta1": (np.arange(size) % 13 == 0).astype(np.int8),
                "x__ausente_delta2": (np.arange(size) % 13 == 0).astype(np.int8) - 1,
            }))
        pl.concat(frames).write_parquet(directory / "train.parquet")
        # No se necesita valid.parquet ni test.parquet para optimizar E0.
        (directory / "DONE.json").write_text("{}")


class OptimizationTests(unittest.TestCase):
    def test_real_search_without_test_then_shared_refit_and_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            config = smoke_config()
            fixture(work, config)
            best = model.optimize_baseline(work, config, n_jobs=1)
            self.assertEqual(best["source_experiment"], "Exp3")
            self.assertGreater(best["best_iteration"], 0)
            self.assertLessEqual(best["best_iteration"], 12)
            self.assertLessEqual(best["n_selected_valid"], 40)
            self.assertFalse((work / "E0/prepared/test.parquet").exists())
            audit = json.loads((work / "E0/optimization/split_audit.json").read_text())
            self.assertEqual((audit["train_rows"], audit["valid_rows"]), (160, 40))
            self.assertEqual(audit["train_months"], [201903, 201904, 201905, 201906])
            self.assertEqual(audit["valid_month"], 201908)
            self.assertFalse(audit["test_read_during_optimization"])
            curve = pl.read_csv(work / "E0/optimization/curva_ganancia_valid_e0.csv")
            self.assertEqual(curve.height, 41)
            self.assertAlmostEqual(curve["ganancia_suavizada"][best["n_selected_valid"]],
                                   best["gain_valid_smoothed_at_n"])
            for method in config["methods"]:
                directory = work / method / "prepared"
                test = pl.read_parquet(directory / "train.parquet").filter(pl.col("foto_mes") == 201908)
                test.with_columns(pl.lit(201910).alias("foto_mes"),
                                  pl.lit("test").alias("partition_role")).write_parquet(directory / "test.parquet")
            cp = work / "smoke_config.json"
            cp.write_text(json.dumps(config))
            command = [sys.executable, str(ROOT / "04_modelar_evaluar.py"), "--work", str(work),
                       "--config", str(cp), "--n_jobs", "1"]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            selected = json.loads((work / "SELECCION_FROZEN.json").read_text())
            self.assertEqual(best, selected)
            self.assertEqual(best, json.loads((work / "E1/optimization/seleccion.json").read_text()))
            for method in config["methods"]:
                final = json.loads((work / method / "final_fit_audit.json").read_text())
                self.assertEqual(final["train_rows"], 240)
                self.assertEqual(final["train_months"], config["train_months"])
                self.assertEqual(final["num_boost_round"], best["best_iteration"])
                self.assertFalse(final["early_stopping_in_final_fit"])
            metrics = pl.read_csv(work / "resultados/metricas_por_semilla_test.csv")
            self.assertEqual(metrics.height, 60)
            self.assertEqual(metrics["n_fijo_evaluado"].unique().to_list(), [best["n_selected_valid"]])
            prediction = work / "E0/test" / f"seed_{config['seeds'][0]}" / "pred_test.npy"
            prediction_mtime = prediction.stat().st_mtime_ns
            selection_bytes = (work / "E0/optimization/seleccion.json").read_bytes()
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(prediction.stat().st_mtime_ns, prediction_mtime)
            self.assertEqual((work / "E0/optimization/seleccion.json").read_bytes(), selection_bytes)
            storage = optuna.storages.RDBStorage(url=f"sqlite:///{work / 'E0/optimization/study.sqlite3'}")
            try:
                study = optuna.load_study(study_name="lgbm_E0", storage=storage)
                self.assertEqual(sum(t.state == optuna.trial.TrialState.COMPLETE for t in study.trials), 2)
            finally:
                storage.remove_session()
                storage.engine.dispose()

    def test_invalid_overlap_rejected_before_fitting(self):
        config = smoke_config()
        config["optimization_train_months"].append(201908)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "no puede entrar"):
                model.optimize_baseline(Path(temporary), config, 1)

    def test_incomplete_checkpoint_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            directory = work / "E0/optimization"
            directory.mkdir(parents=True)
            (directory / "DONE.json").write_text("{}")
            with self.assertRaisesRegex(RuntimeError, "incompleto"):
                model.optimize_baseline(work, smoke_config(), 1)


if __name__ == "__main__":
    unittest.main()
