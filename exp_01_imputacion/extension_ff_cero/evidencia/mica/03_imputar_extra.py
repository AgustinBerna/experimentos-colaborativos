"""03_imputar_extra.py - Métodos adicionales de tratamiento de missings (E7-E12).

Se apoya en el pipeline de Agustín (exp-colaborativos): lee partition/panel_2019.parquet
(ya auditado: ceros 100% -> NaN, sin tmobile_app/cmobile_app_trx) y escribe
<work>/<método>/prepared/{train,valid,test}.parquet con lag1/lag2/delta1/delta2
usando la misma función compartida (src.fe_imputacion). Después se evalúa con
04_modelar_evaluar.py, que reutiliza hiperparámetros y N de E0 y las 30 semillas.

Métodos (todos causales: nada de meses futuros del mismo cliente; estadísticas de
train sólo de 201903-201906):
  E7  Mediana del mes: cada NaN toma la mediana de esa variable en ese foto_mes
      (todos los clientes del mes; sin clase). Si el mes no tiene dato, mediana de train.
  E8  Cero.
  E9  Forward fill por cliente (como E4) + indicadores isnull_<var> (missing ORIGINAL,
      antes del ffill) para variables con algún NaN en train + n_nulos por fila.
  E10 Forward fill por cliente + mediana de train para lo que quede sin dato
      (clientes sin historia). E4 deja esos NaN nativos.
  E11 NaN nativo, eliminando variables con > --drop_thr de NaN en train (def. 0.5).
  E12 Forward fill acotado a --ffill_limit meses (def. 2): no arrastra datos viejos.

Uso:
  python 03_imputar_extra.py --work ./work --method E9
"""
import argparse
import json
import logging
from pathlib import Path

import polars as pl

from src.fe_imputacion import get_feature_cols, build_lags_deltas_and_save

METHODS = ["E7", "E8", "E9", "E10", "E11", "E12"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=Path("config.json"))
    ap.add_argument("--method", choices=METHODS, required=True)
    ap.add_argument("--drop_thr", type=float, default=0.5, help="E11: umbral de %% NaN en train")
    ap.add_argument("--ffill_limit", type=int, default=2, help="E12: meses máximos de arrastre")
    args = ap.parse_args()

    work = args.work.resolve()
    method = args.method
    log_path = work / "logs" / f"03_imputar_{method}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.FileHandler(log_path), logging.StreamHandler()])

    if (work / method / "prepared" / "DONE.json").exists():
        logging.info("%s ya completado.", method)
        return

    config = json.loads(args.config.read_text(encoding="utf-8"))
    id_col, time_col = config["Id_col"], config["time_col"]

    df = pl.read_parquet(work / "partition" / "panel_2019.parquet").sort([id_col, time_col])
    fcols = get_feature_cols(df, config)
    train = df.filter(pl.col("partition_role") == "train")   # estadísticas SOLO de train
    info = {"method": method}

    def ffill(frame, limit=None):
        return frame.with_columns([
            pl.col(c).forward_fill(limit=limit).over(id_col).alias(c) for c in fcols
        ])

    def train_medians(frame):
        t = frame.filter(pl.col("partition_role") == "train")
        return t.select([pl.col(c).median() for c in fcols]).row(0, named=True)

    if method == "E7":
        med = train_medians(df)
        exprs = []
        for c in fcols:
            e = pl.col(c).fill_null(pl.col(c).median().over(time_col))
            if med[c] is not None:
                e = e.fill_null(med[c])
            exprs.append(e.alias(c))
        out = df.with_columns(exprs)

    elif method == "E8":
        out = df.with_columns([pl.col(c).fill_null(0).alias(c) for c in fcols])

    elif method == "E9":
        con_nan = [c for c in fcols if train[c].null_count() > 0]
        flags = [pl.col(c).is_null().cast(pl.Int8).alias(f"isnull_{c}") for c in con_nan]
        n_nulos = pl.sum_horizontal([pl.col(c).is_null().cast(pl.Int16) for c in fcols]).alias("n_nulos")
        out = df.with_columns(flags + [n_nulos])      # missing original, ANTES del ffill
        out = ffill(out)
        info["n_indicadores"] = len(con_nan)
        logging.info("[E9] %d indicadores isnull_* + n_nulos", len(con_nan))

    elif method == "E10":
        out = ffill(df)
        med = train_medians(out)                      # mediana de train del panel ya ffill-eado
        out = out.with_columns([
            (pl.col(c).fill_null(med[c]) if med[c] is not None else pl.col(c)).alias(c)
            for c in fcols
        ])

    elif method == "E11":
        n_tr = train.height
        rate = {c: train[c].null_count() / n_tr for c in fcols}
        dropped = sorted(c for c in fcols if rate[c] > args.drop_thr)
        fcols = [c for c in fcols if c not in dropped]
        out = df.drop(dropped)
        info.update(drop_thr=args.drop_thr, n_dropped=len(dropped), dropped=dropped)
        logging.info("[E11] se eliminan %d variables con >%.0f%% NaN en train: %s",
                     len(dropped), args.drop_thr * 100, dropped)

    elif method == "E12":
        out = ffill(df, limit=args.ffill_limit)
        info["ffill_limit"] = args.ffill_limit

    (work / method).mkdir(parents=True, exist_ok=True)
    (work / method / "extra_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    build_lags_deltas_and_save(out, fcols, work, config, method=method)


if __name__ == "__main__":
    main()
