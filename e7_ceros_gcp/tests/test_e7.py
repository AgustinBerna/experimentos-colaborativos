import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from correr_e7 import fill_zero, missing_summary, add_tests, METHODS, Remote
from metricas import compute_curves_and_metrics


def helper(label):
    spec = importlib.util.spec_from_file_location(label, ROOT / 'referencia' / label / 'fe_imputacion.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ZeroTests(unittest.TestCase):
    def test_gcs_only_copies_new_or_changed_files(self):
        with tempfile.TemporaryDirectory() as tmp, patch('correr_e7.shutil.which', return_value='/bin/gcloud'), patch('correr_e7.subprocess.run') as cp:
            root = Path(tmp)
            p = root / 'checkpoint.json'
            p.write_text('one')
            remote = Remote(root, 'gs://bucket/exp/e7')
            remote.send(p)
            remote.send(p)
            self.assertEqual(cp.call_count, 1)
            p.write_text('two')
            remote.send(p)
            self.assertEqual(cp.call_count, 2)
            self.assertNotIn('rsync', cp.call_args.args[0])

    def test_zero_null_nan_and_observed_values(self):
        df = pl.DataFrame({'x': [None, float('nan'), 0., -4., 8.], 'x__ausente': [1, 1, 0, 0, 0]})
        result = fill_zero(df, ['x'])
        self.assertEqual(result['x'].to_list(), [0., 0., 0., -4., 8.])
        self.assertEqual(result['x__ausente'].to_list(), df['x__ausente'].to_list())

    def test_missing_percent_uses_rows_and_counts_nan_once(self):
        df = pl.DataFrame({'foto_mes': [201903, 201904, 201904, 201910], 'x': [None, float('nan'), 1., 0.]})
        result = missing_summary(df, ['x'], {'time_col': 'foto_mes', 'train_months': [201903, 201904], 'test_month': 201910}).to_dicts()[0]
        self.assertEqual(result['n_na_train'], 2)
        self.assertAlmostEqual(result['pct_na_train'], 200/3)
        self.assertEqual(result['pct_na_test'], 0)

    def test_temporal_protocol_both_experiments(self):
        # Cliente reaparece en marzo, faltando febrero. Base usa shift histórico;
        # indicador usa calendario exacto. El cero se incorpora ANTES de shift.
        for label in ['exp1', 'exp2']:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                cfg = json.loads((ROOT / 'referencia' / label / 'config.json').read_text())
                frame = pl.DataFrame({'numero_de_cliente': [1, 1, 1, 1],
                    'foto_mes': [201901, 201903, 201908, 201910], 'clase_ternaria': ['CONTINUA']*4,
                    'target_binario': [0, 0, 0, 0], 'target_baja2': [0, 0, 0, 0],
                    'partition_role': ['history', 'train', 'train', 'test'], 'x': [3., None, 5., 9.]})
                if label == 'exp2':
                    frame = frame.with_columns(pl.Series('x__ausente', [0, 1, 0, 0], dtype=pl.Int8))
                mod = helper(label)
                mod.build_lags_deltas_and_save(fill_zero(frame, ['x']), ['x'], Path(tmp), cfg, 'E7')
                train = pl.read_parquet(Path(tmp) / 'E7/prepared/train.parquet')
                march = train.filter(pl.col('foto_mes') == 201903).to_dicts()[0]
                self.assertEqual(march['x'], 0)
                self.assertEqual(march['x_lag1'], 3)
                self.assertEqual(march['x_delta1'], -3)
                self.assertIsNone(march['x_lag2'])
                if label == 'exp2':
                    self.assertEqual(march['x__ausente'], 1)
                    self.assertIsNone(march['x__ausente_lag1'])
                    self.assertIsNone(march['x__ausente_delta1'])
                    self.assertEqual(march['x__ausente_lag2'], 0)
                    self.assertEqual(march['x__ausente_delta2'], 1)

    def test_future_does_not_change_past(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = json.loads((ROOT / 'referencia/exp2/config.json').read_text())
            frame = pl.DataFrame({'numero_de_cliente': [1]*4, 'foto_mes': [201901, 201902, 201903, 201910],
                'partition_role': ['history', 'history', 'train', 'test'], 'x': [None, 2., 4., 8.],
                'x__ausente': [1, 0, 0, 0]})
            mod = helper('exp2')
            for method, data in [('A', frame), ('B', frame.with_columns(pl.when(pl.col('foto_mes') == 201910).then(900.).otherwise(pl.col('x')).alias('x')))]:
                mod.build_lags_deltas_and_save(fill_zero(data, ['x']), ['x'], Path(tmp), cfg, method)
            a = pl.read_parquet(Path(tmp) / 'A/prepared/train.parquet')
            b = pl.read_parquet(Path(tmp) / 'B/prepared/train.parquet')
            self.assertTrue(a.equals(b))

    def test_gain_ties_resolved_by_client_and_fixed_n(self):
        y = np.array([1, 0, 1, 0])
        scores = np.array([.5, .5, .5, .5])
        ids = np.array([4, 1, 2, 3])
        metrics, curves = compute_curves_and_metrics(y, y, ids, scores, 1072500, -27500, 2)
        self.assertEqual(metrics['baja2_capturadas_at_n_fijo'], 1)
        self.assertEqual(metrics['gain_at_n_fijo'], 1045000)
        self.assertEqual(curves[-1]['envios'], 2)

    def test_holm_recomputed_for_seven_alternatives(self):
        rows = [{'method': method, 'seed': seed, 'roc_auc': .7 + seed*.0001 + i*.001,
                 'gain_at_n_fijo': 1000 + seed + i*2} for i, method in enumerate(METHODS + ['E7']) for seed in range(30)]
        result = add_tests(pl.DataFrame(rows), pl.DataFrame({'method': METHODS + ['E7']}))
        self.assertEqual(result.height, 8)
        nonbaseline = result.filter(pl.col('method') != 'E0')
        for r in nonbaseline.to_dicts():
            self.assertGreaterEqual(r['p_holm_gain_vs_E0'], r['p_val_gain_vs_E0'])
            self.assertLessEqual(r['p_holm_gain_vs_E0'], 1)


if __name__ == '__main__':
    unittest.main()
