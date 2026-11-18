"""Funci?n de evaluaci?n copiada sin cambios del Exp2 publicado."""
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score

def compute_curves_and_metrics(y_bin: np.ndarray, y_baja2: np.ndarray, ids: np.ndarray, scores: np.ndarray, tp_val: float, fp_val: float, cut_n: int):
    """Evalúa octubre al N elegido en E0/201908; no optimiza N sobre test."""
    if not 0 <= cut_n <= len(scores):
        raise ValueError(f"N congelado fuera de la población de test: {cut_n}")
    roc_auc = float(roc_auc_score(y_bin, scores))
    pr_auc = float(average_precision_score(y_bin, scores))
    auc_baja2 = float(roc_auc_score(y_baja2, scores))
    ap_baja2 = float(average_precision_score(y_baja2, scores))

    # Un score empatado se resuelve siempre por menor ID de cliente.
    order = np.lexsort((ids, -scores))
    y_b2_sorted = y_baja2[order]

    # Ganancia económica sobre BAJA+2
    gains = np.where(y_b2_sorted == 1, tp_val, fp_val)
    cum_gain = np.cumsum(gains)
    gain_at_cut = float(cum_gain[cut_n - 1]) if cut_n else 0.0

    # Lift y recall se refieren a BAJA+2, la clase que remunera la campaña.
    base_rate = float(np.mean(y_baja2))
    captured = int(np.sum(y_b2_sorted[:cut_n]))
    precision_at_cut = captured / cut_n if cut_n else 0.0
    recall_at_cut = captured / int(np.sum(y_baja2)) if np.sum(y_baja2) else 0.0
    lift_at_cut = precision_at_cut / base_rate if base_rate > 0 else 0.0

    # Puntos para el dashboard: hasta el mismo N, incluyendo siempre N exacto.
    grid = np.unique(np.r_[np.arange(250, cut_n + 1, 250), cut_n]) if cut_n else np.array([0], dtype=int)
    cum_pos = np.cumsum(y_b2_sorted)
    total_pos = max(1, int(np.sum(y_baja2)))

    curve_rows = []
    for k in grid:
        if k == 0:
            curve_rows.append({"envios": 0, "ganancia": 0.0, "precision": 0.0,
                               "recall": 0.0, "lift": 0.0})
            continue
        idx = k - 1
        prec_k = float(cum_pos[idx] / k)
        rec_k = float(cum_pos[idx] / total_pos)
        lift_k = prec_k / base_rate if base_rate > 0 else 0.0
        curve_rows.append({
            "envios": int(k),
            "ganancia": float(cum_gain[idx]),
            "precision": prec_k,
            "recall": rec_k,
            "lift": lift_k
        })

    metrics = {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "auc_baja2": auc_baja2,
        "ap_baja2": ap_baja2,
        "n_fijo_evaluado": int(cut_n),
        "gain_at_n_fijo": gain_at_cut,
        "lift_at_n_fijo": lift_at_cut,
        "recall_baja2_at_n_fijo": recall_at_cut,
        "precision_baja2_at_n_fijo": precision_at_cut,
        "baja2_capturadas_at_n_fijo": captured,
    }
    return metrics, curve_rows
