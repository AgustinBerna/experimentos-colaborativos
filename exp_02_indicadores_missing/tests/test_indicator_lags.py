"""Pruebas sintéticas: no requieren dataset, GCP ni entrenamiento."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.fe_imputacion import (add_missing_indicator_lags,
                              build_lags_deltas_and_save, get_feature_cols)


def config():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def panel():
    # Cliente 1 no está en abril; cliente 2 cruza diciembre/enero.
    return pl.DataFrame({
        "numero_de_cliente": [1, 2, 1, 1, 2, 1],
        "foto_mes": [201905, 201901, 201901, 201903, 201812, 201902],
        "x": [50., 90., 10., 30., 80., 20.],
        "x__ausente": [0, 1, 1, 1, 0, 0],
        "clase_ternaria": ["CONTINUA"] * 6,
        "target_binario": [0] * 6,
        "target_baja2": [0] * 6,
        "partition_role": ["test", "lag_only", "lag_only", "train", "lag_only", "lag_only"],
    }).with_columns(pl.col("x__ausente").cast(pl.Int8))


class IndicatorLagTests(unittest.TestCase):
    def test_exact_calendar_months_and_client_isolation(self):
        source = panel()
        out = add_missing_indicator_lags(source, config())
        self.assertEqual(out.select(source.columns).to_dicts(), source.to_dicts())
        rows = {(r["numero_de_cliente"], r["foto_mes"]): r for r in out.to_dicts()}
        march = rows[1, 201903]
        self.assertEqual((march["x__ausente_lag1"], march["x__ausente_lag2"]), (0, 1))
        self.assertEqual((march["x__ausente_delta1"], march["x__ausente_delta2"]), (1, 0))
        may = rows[1, 201905]
        self.assertIsNone(may["x__ausente_lag1"])
        self.assertEqual(may["x__ausente_lag2"], 1)
        self.assertIsNone(may["x__ausente_delta1"])
        self.assertEqual(may["x__ausente_delta2"], -1)
        january = rows[2, 201901]
        self.assertEqual(january["x__ausente_lag1"], 0)
        self.assertIsNone(january["x__ausente_lag2"])
        self.assertIsNone(rows[1, 201901]["x__ausente_lag1"])
        self.assertEqual(out.schema["x__ausente_lag1"], pl.Int8)
        self.assertEqual(out.schema["x__ausente_delta1"], pl.Int8)

    def test_future_values_do_not_change_past(self):
        source = panel()
        changed = source.with_columns(
            pl.when(pl.col("foto_mes") >= 201905).then(1)
            .otherwise(pl.col("x__ausente")).cast(pl.Int8).alias("x__ausente")
        )
        before = add_missing_indicator_lags(source, config()).filter(pl.col("foto_mes") < 201905)
        after = add_missing_indicator_lags(changed, config()).filter(pl.col("foto_mes") < 201905)
        self.assertEqual(before.to_dicts(), after.to_dicts())

    def test_imputers_receive_only_base_features(self):
        self.assertEqual(get_feature_cols(panel(), config()), ["x"])

    def test_reject_duplicate_keys_and_existing_lags(self):
        with self.assertRaisesRegex(ValueError, "duplicadas"):
            add_missing_indicator_lags(pl.concat([panel(), panel().head(1)]), config())
        already = add_missing_indicator_lags(panel(), config())
        with self.assertRaisesRegex(ValueError, "ya existen"):
            add_missing_indicator_lags(already, config())

    def test_reject_invalid_configuration_and_null_keys(self):
        cfg = config()
        cfg["missing_indicator_deltas"] = False
        with self.assertRaises(ValueError):
            add_missing_indicator_lags(panel(), cfg)
        with self.assertRaisesRegex(ValueError, "nulos"):
            add_missing_indicator_lags(panel().with_columns(pl.lit(None).alias("foto_mes")), config())

    def test_two_lags_for_each_of_150_indicators(self):
        df = panel().drop("x__ausente").with_columns([
            pl.lit(i % 2).cast(pl.Int8).alias(f"v{i}__ausente") for i in range(150)
        ])
        out = add_missing_indicator_lags(df, config())
        added = [c for c in out.columns if c not in df.columns]
        self.assertEqual(len(added), 600)
        self.assertEqual(sum("_delta" in c for c in added), 300)
        self.assertEqual(sum("_lag" in c for c in added), 300)

    def test_prepared_partitions_keep_base_features_and_null_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            source = panel()
            build_lags_deltas_and_save(source, ["x"], work, config(), "E0")
            train = pl.read_parquet(work / "E0/prepared/train.parquet")
            self.assertEqual(train["x_lag1"].to_list(), [20.])
            self.assertEqual(train["x_lag2"].to_list(), [10.])
            self.assertEqual(train["x_delta1"].to_list(), [10.])
            self.assertEqual(train["x_delta2"].to_list(), [20.])
            test = pl.read_parquet(work / "E0/prepared/test.parquet")
            self.assertIsNone(test["x__ausente_lag1"][0])
            self.assertEqual(test["x__ausente_lag2"][0], 1)
            valid = pl.read_parquet(work / "E0/prepared/valid.parquet")
            self.assertEqual(valid.height, 0)
            self.assertEqual(valid.schema, train.schema)
            done = json.loads((work / "E0/prepared/DONE.json").read_text())
            self.assertEqual(done["missing_indicator_lag_features"], 2)
            self.assertTrue(done["missing_indicator_deltas"])
            self.assertEqual(done["missing_indicator_delta_features"], 2)

    def test_partition_and_baseline_scripts_end_to_end(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / "raw").mkdir()
            (work / "raw/DONE.json").write_text("{}")
            for month in config()["all_months"]:
                pl.DataFrame({"numero_de_cliente": [1, 2], "foto_mes": [month, month],
                              "clase_ternaria": ["CONTINUA", "CONTINUA"],
                              "x": [None if month == 201902 else 10., 20.]},
                             schema_overrides={"x": pl.Float64}).write_parquet(work / f"raw/{month}.parquet")
            for script in ["02_particionar.py", "03_imputar_baseline.py"]:
                run = subprocess.run([sys.executable, str(ROOT / script), "--work", str(work),
                                      "--config", str(ROOT / "config.json")],
                                     capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            train = pl.read_parquet(work / "E0/prepared/train.parquet")
            self.assertEqual(train.height, 12)
            march = train.filter((pl.col("numero_de_cliente") == 1) & (pl.col("foto_mes") == 201903))
            self.assertEqual(march["x__ausente_lag1"][0], 1)
            self.assertEqual(march["x__ausente_lag2"][0], 0)
            self.assertEqual(pl.read_parquet(work / "E0/prepared/valid.parquet").height, 0)
            self.assertEqual(pl.read_parquet(work / "E0/prepared/test.parquet").height, 2)

    def test_own_baseline_optimization_protocol(self):
        import run_pipeline
        cfg = config()
        run_pipeline.validate_config(cfg)
        self.assertEqual(cfg["optimization_train_months"], [201903, 201904, 201905, 201906])
        self.assertEqual(cfg["optimization_valid_month"], 201908)
        self.assertEqual(cfg["optimization_mode"], "own_E0")
        self.assertFalse((ROOT / "seleccion.json").exists())
        self.assertEqual(len(set(cfg["seeds"])), 30)
        changed = copy.deepcopy(cfg)
        changed["missing_indicator_lags"] = [1]
        with self.assertRaises(ValueError):
            run_pipeline.validate_config(changed)


if __name__ == "__main__":
    unittest.main()
