"""Verify and summarize the predeclared FF fallback experiment, without retuning."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
import polars as pl
from scipy.stats import wilcoxon
from sklearn.metrics import roc_auc_score

BASE = Path(__file__).resolve().parents[1]
RUN = BASE / "run"
OUT = BASE / "outputs"
METHODS = ["E0", "E4", "FF_ZERO", "FF_MEDIAN_MICA"]
LABELS = {"E0": "NaN nativos", "E4": "Forward fill", "FF_ZERO": "Forward fill + cero",
          "FF_MEDIAN_MICA": "FF + mediana después de FF (Mica)"}
META = ["numero_de_cliente", "foto_mes", "clase_ternaria", "target_binario",
        "target_baja2", "partition_role"]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def check_prepared():
    OUT.mkdir(exist_ok=True)
    base_features = [c for c in pl.read_parquet_schema(RUN / "partition/panel_2019.parquet")
                     if c not in META]
    checks = {"base_feature_count": len(base_features), "partitions": {}}
    assert len(base_features) == 150
    for role, months, count in [("train", list(range(201903, 201909)), 768499),
                                ("test", [201910], 135633)]:
        reference_path = RUN / "E0/prepared" / f"{role}.parquet"
        reference = pl.read_parquet(reference_path, columns=META)
        features = [c for c in pl.read_parquet_schema(reference_path) if c not in META]
        assert len(features) == 750 and reference.height == count
        assert reference["foto_mes"].unique().sort().to_list() == months
        assert reference.select(pl.struct(["numero_de_cliente", "foto_mes"]).n_unique()).item() == count
        assert reference["target_binario"].null_count() == 0
        assert reference["target_baja2"].null_count() == 0
        assert reference["partition_role"].unique().to_list() == [role]
        for method in METHODS:
            path = RUN / method / "prepared" / f"{role}.parquet"
            candidate = pl.read_parquet(path, columns=META)
            assert reference.equals(candidate), f"Different metadata/order: {method} {role}"
            assert [c for c in pl.read_parquet_schema(path) if c not in META] == features
        checks["partitions"][role] = {"rows": count, "months": months,
                                      "predictors": len(features), "identical_metadata_and_feature_order": True}
    medians = json.loads((RUN / "diagnostics/training_medians.json").read_text())
    fill_values = np.array([np.nan if medians[c] is None else medians[c]
                            for c in base_features], dtype=np.float32)
    ff = pl.read_parquet(RUN / "E4/prepared/test.parquet", columns=base_features).to_numpy()
    missing = np.isnan(ff)
    for method, fallback in [("FF_ZERO", 0), ("FF_MEDIAN_MICA", fill_values)]:
        candidate = pl.read_parquet(RUN / method / "prepared/test.parquet", columns=base_features).to_numpy()
        expected = np.where(missing, fallback, ff)
        assert np.array_equal(candidate, expected, equal_nan=True), f"Unexpected fallback: {method}"
    checks["test_fallbacks_match_declared_rules"] = True
    checks["residual_missing_cells_after_ff"] = int(missing.sum())
    checks["test_clients_with_residual_missing"] = int(missing.any(axis=1).sum())
    checks["features_with_no_training_median"] = [c for c in base_features if medians[c] is None]
    write_json(OUT / "verificacion_datos.json", checks)
    print(json.dumps(checks, ensure_ascii=False), flush=True)
    return checks


def holm(pvalues):
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues, kind="stable")
    adjusted = np.empty(len(pvalues), dtype=float)
    adjusted[order] = np.minimum(1, np.maximum.accumulate(pvalues[order] * np.arange(len(pvalues), 0, -1)))
    return adjusted.tolist()


def verify_inputs():
    identity = json.loads((RUN / "run_identity.json").read_text())
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest(BASE / "protocol.json") == identity["protocol_sha256"]
    assert digest(BASE / "experiment/config.json") == identity["config_sha256"]
    assert digest(BASE / "experiment/seleccion.json") == identity["selection_sha256"]
    for rel, expected in identity["code_sha256"].items():
        assert digest(BASE / "experiment" / rel) == expected, f"Code changed: {rel}"
    return identity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-prepared", action="store_true")
    args = parser.parse_args()
    checks = check_prepared()
    if args.check_prepared:
        return
    assert (RUN / "resultados/FINALIZADO.json").exists(), "Training is incomplete"
    identity = verify_inputs()
    config = json.loads((BASE / "experiment/config.json").read_text())
    seeds = sorted(config["seeds"])
    metrics = pl.read_csv(RUN / "resultados/metricas_por_semilla_test.csv")
    ensembles = pl.read_csv(RUN / "resultados/resumen_ensamble_test.csv")
    assert metrics.height == 120 and ensembles.height == 4
    assert set(metrics["method"].unique()) == set(METHODS)
    assert metrics["n_fijo_evaluado"].unique().to_list() == [4323]
    meta = pl.read_parquet(RUN / "E0/prepared/test.parquet", columns=META)
    ids = meta["numero_de_cliente"].to_numpy()
    y = meta["target_binario"].to_numpy()
    yb2 = meta["target_baja2"].to_numpy()
    n = 4323
    gains = {}
    aucs = {}
    summary = []
    for method in METHODS:
        selected = json.loads((RUN / method / "optimization/seleccion.json").read_text())
        assert selected == json.loads((BASE / "experiment/seleccion.json").read_text())
        rows = metrics.filter(pl.col("method") == method).sort("seed")
        assert rows["seed"].to_list() == seeds
        gains[method] = rows["gain_at_n_fijo"].to_numpy()
        aucs[method] = rows["roc_auc"].to_numpy()
        average_scores = np.zeros(len(y), dtype=np.float64)
        for row in rows.iter_rows(named=True):
            seed_dir = RUN / method / "test" / f"seed_{row['seed']}"
            assert (seed_dir / "DONE.json").exists()
            scores = np.load(seed_dir / "pred_test.npy")
            assert len(scores) == len(y) and np.isfinite(scores).all()
            assert ((scores >= 0) & (scores <= 1)).all()
            average_scores += scores / 30
            captured = int(yb2[np.lexsort((ids, -scores))[:n]].sum())
            gain = captured * (1072500 + 27500) - n * 27500
            assert gain == row["gain_at_n_fijo"]
            assert abs(roc_auc_score(y, scores) - row["roc_auc"]) < 1e-12
        erow = ensembles.filter(pl.col("method") == method).row(0, named=True)
        captured = int(yb2[np.lexsort((ids, -average_scores))[:n]].sum())
        assert captured * 1100000 - n * 27500 == erow["gain_at_n_fijo"]
        assert abs(roc_auc_score(y, average_scores) - erow["roc_auc"]) < 1e-12
        summary.append({"method": method, "label": LABELS[method], "seeds": 30,
                        "gain_mean": float(gains[method].mean()),
                        "gain_sd": float(gains[method].std(ddof=1)),
                        "auc_mean": float(aucs[method].mean()),
                        "auc_sd": float(aucs[method].std(ddof=1)),
                        "gain_ensemble": erow["gain_at_n_fijo"], "auc_ensemble": erow["roc_auc"]})
    paired = []
    for metric, values in [("gain_at_n_fijo", gains), ("roc_auc", aucs)]:
        family = []
        for comparator in ["E0", "E4", "FF_MEDIAN_MICA"]:
            # Rounding avoids spurious floating-point differences in ranks.
            delta = np.round(values["FF_ZERO"] - values[comparator], 12)
            p = 1.0 if np.all(delta == 0) else float(wilcoxon(delta, zero_method="zsplit", alternative="two-sided").pvalue)
            assert np.isfinite(p), f"Invalid p-value: {metric} {comparator}"
            family.append({"metric": metric, "method": "FF_ZERO", "comparator": comparator,
                           "n_pairs": 30, "delta_mean": float(delta.mean()),
                           "delta_sd": float(delta.std(ddof=1)), "delta_median": float(np.median(delta)),
                           "wins": int((delta > 0).sum()), "ties": int((delta == 0).sum()),
                           "losses": int((delta < 0).sum()), "p_wilcoxon": p})
        for row, adjusted in zip(family, holm([r["p_wilcoxon"] for r in family])):
            row["p_holm"] = adjusted
            row["significant_005"] = adjusted < .05
        paired.extend(family)
    reproduction = []
    published = pl.read_csv(BASE / "upstream/exp_01_imputacion/resultados/metricas_por_semilla_test.csv")
    for method in ["E0", "E4"]:
        orig = published.filter(pl.col("method") == method).sort("seed")
        assert orig["seed"].to_list() == seeds
        for metric in ["gain_at_n_fijo", "roc_auc", "pr_auc", "auc_baja2", "ap_baja2"]:
            ours = metrics.filter(pl.col("method") == method).sort("seed")[metric].to_numpy()
            previous = orig[metric].to_numpy()
            reproduction.append({"method": method, "metric": metric,
                                 "max_abs_difference": float(np.max(np.abs(ours - previous))),
                                 "all_close_1e_12": bool(np.allclose(ours, previous, rtol=0, atol=1e-12))})
    pl.DataFrame(summary).write_csv(OUT / "resumen_florencia.csv")
    pl.DataFrame(paired).write_csv(OUT / "comparaciones_pareadas.csv")
    pl.DataFrame(reproduction).write_csv(OUT / "reproduccion_referencia.csv")
    metrics.write_csv(OUT / "metricas_por_semilla.csv")
    missing = pl.read_csv(RUN / "diagnostics/missing_by_month.csv").filter(pl.col("foto_mes") == 201910).row(0, named=True)
    missing["fraction_missing_filled_by_ff"] = 1 - missing["missing_cells_after_ff"] / missing["missing_cells_before_ff"]
    missing["fraction_clients_with_residual_missing"] = missing["clients_with_remaining_missing"] / missing["rows"]
    summary_json = {"status": "verified", "summary": summary, "paired_comparisons": paired,
                    "reference_reproduction": reproduction, "data_checks": checks,
                    "missingness_october": missing, "source_commit": identity["source_commit"],
                    "test_scope": "30 model seeds on one fixed October cohort, not independent temporal samples. Exploratory: the team had already examined October while proposing variants; the median control was aligned to Mica after the original run on 2026-11-17.",
                    "statistical_test": "Two-sided paired Wilcoxon, zero_method=zsplit, scipy auto; differences rounded to 12 decimals; Holm for 3 predeclared comparisons separately for each metric",
                    "all_predictions_and_metrics_verified": True}
    write_json(OUT / "analisis_verificado.json", summary_json)
    print(json.dumps(summary_json, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
