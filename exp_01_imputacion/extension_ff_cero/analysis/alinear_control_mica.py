"""Compare existing FF_ZERO runs with Mica's published, verified E10 control.

This does not train models or claim that Mica's predictions were regenerated here.
"""
from pathlib import Path
import csv
import hashlib
import json
import statistics
import numpy as np
from scipy.stats import wilcoxon

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"
ORIGINAL = BASE / "archivo_corrida_original" / "outputs"
MICA = BASE / "evidencia" / "mica"
METHODS = ["E0", "E4", "FF_ZERO", "FF_MEDIAN_MICA"]
LABELS = {"E0": "NaN nativos", "E4": "Forward fill", "FF_ZERO": "Forward fill + cero",
          "FF_MEDIAN_MICA": "FF + mediana después de FF (Mica)"}

def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))

def write(name, rows):
    with (OUT / name).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def holm(values):
    order = np.argsort(values, kind="stable")
    adjusted = np.empty(len(values))
    adjusted[order] = np.minimum(1, np.maximum.accumulate(np.asarray(values)[order] * np.arange(len(values), 0, -1)))
    return adjusted.tolist()

def main():
    local = read(ORIGINAL / "metricas_por_semilla.csv")
    mica = read(MICA / "metricas_por_semilla.csv")
    original_summary = {r["method"]: r for r in read(ORIGINAL / "resumen_florencia.csv")}
    mica_summary = {r["method"]: r for r in read(MICA / "resumen_ensamble.csv")}
    seeds = sorted(int(r["seed"]) for r in local if r["method"] == "FF_ZERO")
    assert len(seeds) == len(set(seeds)) == 30
    checks = []
    for method in ["E0", "E4"]:
        a = {int(r["seed"]): r for r in local if r["method"] == method}
        b = {int(r["seed"]): r for r in mica if r["method"] == method}
        assert sorted(a) == sorted(b) == seeds
        for metric in ["roc_auc", "pr_auc", "auc_baja2", "ap_baja2", "gain_at_n_fijo", "n_fijo_evaluado"]:
            delta = max(abs(float(a[s][metric]) - float(b[s][metric])) for s in seeds)
            assert delta <= 1e-12, (method, metric, delta)
            checks.append({"method": method, "metric": metric, "max_abs_difference": delta})
    rows = [dict(r, source="Florencia") for r in local if r["method"] in METHODS]
    median = [r for r in mica if r["method"] == "E10"]
    assert sorted(int(r["seed"]) for r in median) == seeds
    rows += [dict(r, method="FF_MEDIAN_MICA", source="Micaela_E10") for r in median]
    assert len(rows) == 120 and all(float(r["n_fijo_evaluado"]) == 4323 for r in rows)
    rows.sort(key=lambda r: (METHODS.index(r["method"]), int(r["seed"])))
    common_columns = list(mica[0]) + ["source"]
    write("metricas_por_semilla.csv", [{k: r[k] for k in common_columns} for r in rows])
    summary = []
    for method in METHODS:
        r = [x for x in rows if x["method"] == method]
        gain = [float(x["gain_at_n_fijo"]) for x in r]
        auc = [float(x["roc_auc"]) for x in r]
        ens = mica_summary["E10"] if method == "FF_MEDIAN_MICA" else original_summary[method]
        summary.append({"method": method, "label": LABELS[method], "seeds": 30,
                        "gain_mean": statistics.mean(gain), "gain_sd": statistics.stdev(gain),
                        "auc_mean": statistics.mean(auc), "auc_sd": statistics.stdev(auc),
                        "gain_ensemble": float(ens["gain_at_n_fijo"] if method == "FF_MEDIAN_MICA" else ens["gain_ensemble"]),
                        "auc_ensemble": float(ens["roc_auc"] if method == "FF_MEDIAN_MICA" else ens["auc_ensemble"]),
                        "source": "Micaela_E10" if method == "FF_MEDIAN_MICA" else "Florencia"})
    comparisons = []
    for metric in ["gain_at_n_fijo", "roc_auc"]:
        arrays = {m: np.array([float(r[metric]) for r in rows if r["method"] == m]) for m in METHODS}
        group = []
        for comparator in ["E0", "E4", "FF_MEDIAN_MICA"]:
            delta = np.round(arrays["FF_ZERO"] - arrays[comparator], 12)
            p = float(wilcoxon(delta, zero_method="zsplit", alternative="two-sided", method="auto").pvalue)
            group.append({"metric": metric, "method": "FF_ZERO", "comparator": comparator,
                          "n_pairs": 30, "delta_mean": float(delta.mean()), "delta_sd": float(delta.std(ddof=1)),
                          "delta_median": float(np.median(delta)), "wins": int((delta > 0).sum()),
                          "ties": int((delta == 0).sum()), "losses": int((delta < 0).sum()), "p_wilcoxon": p})
        for row, p in zip(group, holm([r["p_wilcoxon"] for r in group])):
            row.update(p_holm=p, significant_005=p < 0.05)
        comparisons.extend(group)
    write("resumen_florencia.csv", summary)
    write("comparaciones_pareadas.csv", comparisons)
    evidence = {"status": "aligned_existing_results", "date": "2026-11-17",
                "summary": summary, "paired_comparisons": comparisons, "reference_reproduction": checks,
                "source_commit_mica": "b4f92dc83ace1a068393c661ecf71c0e9e32d73a",
                "source_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in MICA.iterdir() if p.is_file()},
                "provenance": "90 existing local fits (E0/E4/FF_ZERO) plus 30 published Mica E10 fits. No retraining in this alignment. Mica's individual predictions were not supplied or reverified.",
                "protocol_change": "Median control changed on 2026-11-17 after viewing results to align the definition with Mica. This is a post hoc harmonized comparison, not one fixed before the original experiment.",
                "test_scope": "30 common model seeds, one fixed October cohort; not independent temporal samples.",
                "median_definition": "Fit medians on March-August training rows after causal forward fill; then fill remaining nulls before lags/deltas."}
    (OUT / "analisis_verificado.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(json.dumps({"summary": summary, "comparisons": comparisons, "baseline_checks": len(checks)}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
