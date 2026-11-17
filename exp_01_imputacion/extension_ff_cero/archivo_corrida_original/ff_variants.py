"""Frozen comparison: native NaN, forward fill, FF+zero, and FF+train median."""
from __future__ import annotations

import argparse
import gc
import json
import logging
from pathlib import Path

import polars as pl

from src.fe_imputacion import get_feature_cols, build_lags_deltas_and_save


def forward_fill(df: pl.DataFrame, features: list[str], id_col: str, time_col: str) -> pl.DataFrame:
    ordered = df.sort([id_col, time_col])
    return ordered.with_columns([
        pl.col(c).forward_fill().over(id_col).alias(c) for c in features
    ])


def training_medians(df: pl.DataFrame, features: list[str], time_col: str,
                     train_months: list[int]) -> dict:
    train = df.filter(pl.col(time_col).is_in(train_months))
    return train.select([pl.col(c).median().alias(c) for c in features]).row(0, named=True)


def fill_remaining(ff: pl.DataFrame, features: list[str], fallback: str,
                   medians: dict | None = None) -> pl.DataFrame:
    if fallback == "zero":
        return ff.with_columns([pl.col(c).fill_null(0).alias(c) for c in features])
    if fallback == "median":
        if medians is None:
            raise ValueError("Training medians are required")
        return ff.with_columns([
            pl.col(c).cast(pl.Float64).fill_null(float(medians[c])).alias(c)
            if medians[c] is not None else pl.col(c)
            for c in features
        ])
    raise ValueError(fallback)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(),
                                  logging.FileHandler(work / "logs/03_ff_variants.log")])
    config = json.loads(args.config.read_text())
    df = pl.read_parquet(work / "partition/panel_2019.parquet")
    features = get_feature_cols(df, config)
    id_col, time_col = config["Id_col"], config["time_col"]
    medians = training_medians(df, features, time_col, config["train_months"])
    ff = forward_fill(df, features, id_col, time_col)
    audit = work / "diagnostics"
    audit.mkdir(exist_ok=True)
    (audit / "training_medians.json").write_text(json.dumps(medians, indent=2))
    before = df.group_by(time_col).agg(
        pl.len().alias("rows"),
        pl.sum_horizontal([pl.col(c).is_null().cast(pl.UInt32) for c in features])
          .sum().alias("missing_cells_before_ff"),
    ).sort(time_col)
    after = ff.group_by(time_col).agg(
        pl.sum_horizontal([pl.col(c).is_null().cast(pl.UInt32) for c in features])
          .sum().alias("missing_cells_after_ff"),
        pl.any_horizontal([pl.col(c).is_null() for c in features])
          .sum().alias("clients_with_remaining_missing"),
    ).sort(time_col)
    before.join(after, on=time_col).write_csv(audit / "missing_by_month.csv")
    ff.filter(pl.col(time_col) == config["test_month"]).select(
        id_col, time_col,
        pl.any_horizontal([pl.col(c).is_null() for c in features])
          .alias("has_remaining_missing"),
        pl.sum_horizontal([pl.col(c).is_null().cast(pl.UInt32) for c in features])
          .alias("remaining_missing_count"),
    ).write_parquet(audit / "october_missing_groups.parquet")
    del df
    gc.collect()
    for method, fallback in [("FF_ZERO", "zero"), ("FF_MEDIAN", "median")]:
        if (work / method / "prepared/DONE.json").exists():
            logging.info("%s already prepared", method)
            continue
        logging.info("Preparing %s; fallback only on original features after FF", method)
        changed = fill_remaining(ff, features, fallback, medians)
        build_lags_deltas_and_save(changed, features, work, config, method)
        del changed
        gc.collect()
    logging.info("Both FF fallback variants prepared")


if __name__ == "__main__":
    main()
