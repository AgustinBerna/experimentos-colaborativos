"""E7: cero en variables base; dos selecciones congeladas, sin Optuna ni R."""
import argparse
import gc
import hashlib
import importlib.util
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

import lightgbm as lgb
import numpy as np
import polars as pl
from scipy.stats import wilcoxon
from metricas import compute_curves_and_metrics
from dashboard import render

ROOT = Path(__file__).resolve().parent
METHODS = ['E0', 'E1', 'E2', 'E3', 'E4', 'E5', 'E06']
TABLES = ['metricas_por_semilla_test.csv', 'curvas_por_semilla_test.csv',
          'resumen_ensamble_test.csv', 'curvas_ensamble_test.csv']
META = {'numero_de_cliente', 'foto_mes', 'clase_ternaria', 'target_binario',
        'target_baja2', 'partition_role'}
KEYS = ['numero_de_cliente', 'foto_mes', 'target_binario', 'target_baja2']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def readj(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def writej(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.partial')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(path)


def helper(label):
    spec = importlib.util.spec_from_file_location('fe_' + label, ROOT / 'referencia' / label / 'fe_imputacion.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def missing_summary(frame, cols, config):
    """Conteos de celdas, antes de imputar; null y NaN cuentan una sola vez."""
    rows = {c: {'variable': c} for c in cols}
    for role, months in [('train', config['train_months']), ('test', [config['test_month']])]:
        sub = frame.filter(pl.col(config['time_col']).is_in(months))
        require(sub.height > 0, f'{role}: partición vacía')
        counts = sub.select([(pl.col(c).cast(pl.Float64).is_null() |
                              pl.col(c).cast(pl.Float64).is_nan().fill_null(False)).sum().alias(c)
                             for c in cols]).row(0, named=True)
        for c in cols:
            rows[c].update({f'n_{role}': sub.height, f'n_na_{role}': counts[c],
                            f'pct_na_{role}': 100.0 * counts[c] / sub.height})
    return pl.DataFrame(list(rows.values()))


def fill_zero(frame, cols):
    return frame.with_columns([pl.col(c).cast(pl.Float32).fill_nan(0).fill_null(0).alias(c) for c in cols])


def find_run(label, roots):
    expected = readj(ROOT / 'referencia' / label / 'seleccion.json')
    config_hash = sha(ROOT / 'referencia' / label / 'config.json')
    for root in roots:
        root = Path(root)
        candidates = {p.parent for pattern in ['run_identity.json', '*/run_identity.json', '*/*/run_identity.json']
                      for p in root.glob(pattern)} if root.is_dir() else set()
        matches = []
        for work in sorted(candidates):
            sel = work / 'E0/optimization/seleccion.json'
            if not sel.is_file():
                continue
            if (readj(work / 'run_identity.json').get('config_sha256') == config_hash
                    and readj(sel) == expected
                    and (work / 'partition/panel_2019.parquet').is_file()
                    and (work / 'resultados/resumen_ensamble_test.csv').is_file()):
                matches.append(work.resolve())
        require(len(matches) <= 1, f'{label}: hay varias corridas: {matches}. Indicar --{label} /ruta.')
        if matches:
            return matches[0]
    raise ValueError(f'No se encontró {label}. Indicar --{label} /ruta/corrida; requiere partition/panel_2019.parquet y resultados.')


class Remote:
    """Copia sólo archivos nuevos/cambiados del directorio E7; nunca rsync del origen."""
    def __init__(self, work, uri=None):
        self.work, self.uri = Path(work).resolve(), uri.rstrip('/') if uri else None
        self.cache_path = self.work / 'uploads_local.json'
        self.cache = readj(self.cache_path) if self.cache_path.exists() else {}
        self.cache = self.cache if self.cache.get('uri') == self.uri else {'uri': self.uri, 'files': {}}
        if self.uri:
            require(self.uri.startswith('gs://') and len(self.uri.split('/')) >= 5,
                    'Usar un prefijo GCS exclusivo para E7, no la raíz del bucket.')
            require(shutil.which('gcloud'), 'No se encontró gcloud')

    def send(self, *paths):
        if not self.uri:
            return
        for p in map(Path, paths):
            relative = p.resolve().relative_to(self.work).as_posix()
            digest = sha(p)
            if self.cache['files'].get(relative) == digest:
                continue
            logging.info('GCS: %s', relative)
            subprocess.run(['gcloud', 'storage', 'cp', str(p), self.uri + '/' + relative], check=True)
            self.cache['files'][relative] = digest
            writej(self.cache_path, self.cache)


def validate_source(source, label):
    config = readj(ROOT / 'referencia' / label / 'config.json')
    selected = readj(ROOT / 'referencia' / label / 'seleccion.json')
    identity = readj(source / 'run_identity.json')
    require(identity['config_sha256'] == sha(ROOT / 'referencia' / label / 'config.json'),
            f'{label}: config distinta de la publicada')
    require(readj(source / 'E0/optimization/seleccion.json') == selected,
            f'{label}: selección distinta de la publicada')
    require(identity['code_sha256']['src/fe_imputacion.py'] == sha(ROOT / 'referencia' / label / 'fe_imputacion.py'),
            f'{label}: generador de variables distinto del ejecutado originalmente')
    require(len(config['seeds']) == len(set(config['seeds'])) == 30, 'Se requieren 30 semillas comunes')
    require(config['train_months'] == list(range(201903, 201909)) and config['test_month'] == 201910,
            'Particiones inesperadas')
    seed_table = pl.read_csv(source / 'resultados' / TABLES[0])
    require(set(seed_table['method']) == set(METHODS), f'{label}: métodos de origen inesperados')
    for method in METHODS:
        rows = seed_table.filter(pl.col('method') == method)
        require(rows['seed'].to_list() == config['seeds'], f'{label}/{method}: semillas u orden distintos')
        require(rows['n_fijo_evaluado'].to_list() == [selected['n_selected_valid']] * 30,
                f'{label}/{method}: N distinto')
    return config, selected, identity


def identity_for(source, label, config, selected, original_identity, threads):
    tracked = [source / 'run_identity.json', source / 'E0/optimization/seleccion.json',
               source / 'partition/panel_2019.parquet', *[source / 'resultados' / name for name in TABLES]]
    return {'format_version': 1, 'experiment': label, 'method': 'E7',
            'source_run_identity': original_identity, 'config': config, 'selection': selected,
            'source_files_sha256': {p.relative_to(source).as_posix(): sha(p) for p in tracked},
            'code_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(ROOT.rglob('*.py'))
                            if '.venv' not in p.parts and '__pycache__' not in p.parts},
            'runtime': {'python': platform.python_version(), 'platform': platform.platform(),
                        'packages': {name: importlib.metadata.version(name) for name in
                                     ['numpy', 'polars', 'scipy', 'scikit-learn', 'lightgbm']}, 'threads': threads},
            'imputation': 'base null/NaN -> 0 before temporal features; indicators unchanged; missing history remains null',
            'new_optimization': False, 'source_run_modified': False}


def aligned(source_path, new_path, config):
    old = pl.read_parquet(source_path, columns=KEYS)
    new = pl.read_parquet(new_path, columns=KEYS)
    require(old.equals(new), f'Orden, clientes o etiquetas distintos: {new_path}')
    require(set(pl.read_parquet_schema(source_path)) == set(pl.read_parquet_schema(new_path)),
            f'Variables distintas de E0: {new_path}')
    return new


def prepare(source, out, label, config, remote):
    target = out / 'E7/prepared'
    if not (target / 'DONE.json').exists():
        logging.info('%s: leyendo panel auditado ANTES de imputación', label)
        frame = pl.read_parquet(source / 'partition/panel_2019.parquet')
        h = helper(label)
        cols = h.get_feature_cols(frame, config)
        require(len(cols) == 150, f'{label}: se esperaban 150 variables base, hay {len(cols)}')
        require(not {'tmobile_app', 'cmobile_app_trx'}.intersection(cols), 'Se encontraron variables excluidas')
        for role, months in [('train', config['train_months']), ('test', [config['test_month']])]:
            selected = frame.filter(pl.col('partition_role') == role)
            require(set(selected[config['time_col']].unique()) == set(months), f'{label}: meses incorrectos en {role}')
            require(frame.filter(pl.col(config['time_col']).is_in(months)).height == selected.height,
                    f'{label}: filas fuera de la partición {role}')
        out.joinpath('resultados').mkdir(parents=True, exist_ok=True)
        missing_summary(frame, cols, config).write_csv(out / 'resultados/porcentaje_na_train_test.csv')
        h.build_lags_deltas_and_save(fill_zero(frame, cols), cols, out, config, 'E7')
        del frame
        gc.collect()
    require((out / 'resultados/porcentaje_na_train_test.csv').is_file(), 'Falta resumen NaN; checkpoint incompleto')
    remote.send(out / 'resultados/porcentaje_na_train_test.csv')
    for role in ['train', 'test']:
        aligned(source / f'E0/prepared/{role}.parquet', target / f'{role}.parquet', config)
    return target


def load_xy(path, ordered_cols):
    df = pl.read_parquet(path)
    return (df.select(ordered_cols).to_numpy().astype(np.float32),
            df['target_binario'].to_numpy(), df['target_baja2'].to_numpy(), df['numero_de_cliente'].to_numpy())


def train(source, out, label, config, selected, threads, remote):
    prep = prepare(source, out, label, config, remote)
    # Orden de columnas idéntico al E0 original, incluso si cambian joins de Polars.
    cols = [c for c in pl.read_parquet_schema(source / 'E0/prepared/train.parquet') if c not in META]
    require(len(cols) == (750 if label == 'exp1' else 1500), f'{label}: cantidad inesperada de predictores')
    Xtr, ytr, _, _ = load_xy(prep / 'train.parquet', cols)
    Xte, yte, yb2, ids = load_xy(prep / 'test.parquet', cols)
    require(len(np.unique(ytr)) == 2 and len(np.unique(yte)) == 2, 'Se requieren ambas clases')
    require(len(np.unique(ids)) == len(ids), 'Clientes test duplicados')
    dtrain = lgb.Dataset(Xtr, label=ytr, params={'feature_pre_filter': False}, free_raw_data=False)
    # construct() utiliza num_threads antes de entrenar: evitar los 192 hilos por defecto.
    dtrain.params['num_threads'] = threads
    dtrain.construct()
    gain = config['gain']
    cut = int(selected['n_selected_valid'])
    seed_rows, curve_rows = [], []
    ensemble = np.zeros(len(ids), dtype=np.float64)
    for index, seed in enumerate(config['seeds'], 1):
        folder = out / 'E7/test' / f'seed_{seed}'
        folder.mkdir(parents=True, exist_ok=True)
        prediction = folder / 'pred_test.npy'
        marker = folder / 'DONE.json'
        if marker.exists():
            require(readj(marker)['prediction_sha256'] == sha(prediction), f'Checkpoint corrupto: {folder}')
            scores = np.load(prediction, allow_pickle=False)
            logging.info('%s: reutilizando semilla %s (%d/30)', label, seed, index)
        else:
            logging.info('%s: entrenando semilla %s (%d/30), %d árboles', label, seed, index, selected['best_iteration'])
            params = {'objective': 'binary', 'metric': 'auc', 'boosting_type': 'gbdt',
                      'feature_pre_filter': False, 'verbosity': -1, 'n_jobs': threads,
                      'seed': int(seed), 'feature_fraction_seed': int(seed) + 1,
                      'bagging_seed': int(seed) + 2, 'bagging_freq': int(config['optimization']['bagging_freq']),
                      **selected['best_params']}
            model = lgb.train(params, dtrain, num_boost_round=int(selected['best_iteration']))
            scores = model.predict(Xte, num_threads=threads)
            model.save_model(str(folder / 'modelo.txt'))
            temp = folder / 'pred_test.partial.npy'
            np.save(temp, scores)
            temp.replace(prediction)
            del model
        require(scores.shape == (len(ids),) and np.isfinite(scores).all()
                and ((scores >= 0) & (scores <= 1)).all(), f'Predicciones inválidas: {folder}')
        metrics, curves = compute_curves_and_metrics(yte, yb2, ids, scores,
                                                     gain['tp_value'], gain['fp_value'], cut)
        writej(folder / 'metrics.json', metrics)
        writej(folder / 'curves.json', curves)
        writej(marker, {'seed': seed, 'prediction_sha256': sha(prediction), 'status': 'ok'})
        # Nunca sube el dataset, parquets preparados ni los modelos al bucket.
        remote.send(prediction, folder / 'metrics.json', folder / 'curves.json', marker)
        ensemble += scores / len(config['seeds'])
        seed_rows.append({'method': 'E7', 'seed': seed, **metrics})
        curve_rows.extend({'method': 'E7', 'seed': seed, **row} for row in curves)
        logging.info('%s E7 seed=%s AUC=%.6f ganancia=%s', label, seed, metrics['roc_auc'], metrics['gain_at_n_fijo'])
    em, ec = compute_curves_and_metrics(yte, yb2, ids, ensemble, gain['tp_value'], gain['fp_value'], cut)
    # Ordinal del ID ordenado: permite emparejar con el ZIP bootstrap anterior sin publicar IDs reales.
    order = np.argsort(ids, kind='stable')
    pl.DataFrame({'cliente_id': np.arange(1, len(ids) + 1), 'foto_mes': [config['test_month']] * len(ids),
                  'target_binario': yte[order], 'target_baja2': yb2[order],
                  'prob_E7': ensemble[order]}).write_csv(out / 'resultados/predicciones_ensamble_E7.csv')
    writej(out / 'E7/final_fit_audit.json', {'method': 'E7', 'train_rows': len(ytr), 'test_rows': len(ids),
           'train_months': config['train_months'], 'test_month': config['test_month'], 'feature_count': len(cols),
           'seeds': config['seeds'], 'num_boost_round': selected['best_iteration'], 'n_selected_valid': cut,
           'early_stopping': False, 'optimization_executed': False, 'selection': selected})
    del Xtr, Xte, dtrain
    gc.collect()
    return [pl.DataFrame(seed_rows), pl.DataFrame(curve_rows),
            pl.DataFrame([{'method': 'E7', **em}]), pl.DataFrame([{'method': 'E7', **row} for row in ec])]


def add_tests(seed_table, summary):
    methods = METHODS + ['E7']
    rows = {m: {'method': m} for m in methods}
    for metric, short in [('roc_auc', 'auc'), ('gain_at_n_fijo', 'gain')]:
        ref = seed_table.filter(pl.col('method') == 'E0').sort('seed')[metric].to_numpy()
        raw, adjusted = f'p_val_{short}_vs_E0', f'p_holm_{short}_vs_E0'
        rows['E0'].update({raw: 1., adjusted: 1.})
        for m in methods[1:]:
            x = seed_table.filter(pl.col('method') == m).sort('seed')[metric].to_numpy()
            rows[m][raw] = float(wilcoxon(x, ref, zero_method='zsplit').pvalue)
        prev = 0.
        for index, m in enumerate(sorted(methods[1:], key=lambda m: rows[m][raw])):
            prev = min(1., max(prev, rows[m][raw] * (7 - index)))
            rows[m][adjusted] = prev
    return summary.drop([c for c in summary.columns if c.startswith(('p_val_', 'p_holm_'))]).join(
        pl.DataFrame(list(rows.values())), on='method', how='left', maintain_order='left')


def run_one(source, out, label, threads, remote):
    config, selected, original_identity = validate_source(source, label)
    logging.info('%s: verificando hashes de origen y congelando selección', label)
    identity = identity_for(source, label, config, selected, original_identity, threads)
    ipath = out / 'run_identity_e7.json'
    if ipath.exists():
        require(readj(ipath) == identity, f'{label}: cambió origen/código/entorno/hilos. Usar otro --work o restaurar el entorno.')
    else:
        writej(ipath, identity)
    remote.send(ipath)
    environment = out / 'entorno_reproducible.txt'
    environment.write_text('\n'.join(sorted(
        f"{dist.metadata['Name']}=={dist.version}" for dist in importlib.metadata.distributions()
        if dist.metadata['Name'])) + '\n', encoding='utf-8')
    additions = train(source, out, label, config, selected, threads, remote)
    for name, new in zip(TABLES, additions):
        old = pl.read_csv(source / 'resultados' / name)
        old = old.drop([c for c in old.columns if c.startswith(('p_val_', 'p_holm_'))])
        require(set(old['method']) == set(METHODS), f'{name}: métodos originales incompletos')
        require(set(new.columns) == set(old.columns), f'{name}: esquema incompatible')
        combined = pl.concat([old, new.select(old.columns)], how='vertical_relaxed')
        combined.write_csv(out / 'resultados' / name)
    sm = pl.read_csv(out / 'resultados' / TABLES[0])
    summary = add_tests(sm, pl.read_csv(out / 'resultados' / TABLES[2]))
    summary.write_csv(out / 'resultados' / TABLES[2])
    for name in ['config.json', 'seleccion.json']:
        shutil.copyfile(ROOT / 'referencia' / label / name, out / name)
    shutil.copyfile(source / 'run_identity.json', out / 'run_identity_origen.json')
    for relative in ['partition/features_excluidas.json', 'partition/indicadores_ausente.json',
                     'E0/optimization/split_audit.json']:
        if (source / relative).exists():
            dst = out / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, dst)
    render(out, label, selected)
    small = [p for p in out.rglob('*') if p.is_file()
             and 'prepared' not in p.parts and 'test' not in p.parts]
    remote.send(*small)
    writej(out / 'FINALIZADO.json', {'status': 'ok', 'method': 'E7', 'seeds': 30,
           'methods_in_dashboard': METHODS + ['E7'], 'optimization_executed': False,
           'wilcoxon': 'pareado por semilla; Holm 7 comparaciones por métrica; no test temporal independiente'})
    remote.send(out / 'FINALIZADO.json')


def pack(work):
    # Predicciones individuales/modelos quedan en la VM. ZIP con ensamble anónimo, CSV, HTML y procedencia.
    files = [p for label in ['exp1', 'exp2'] for p in (work / label).rglob('*')
             if p.is_file() and 'prepared' not in p.parts and 'test' not in p.parts]
    sources = [p for p in ROOT.rglob('*') if p.is_file() and '.venv' not in p.parts
               and '__pycache__' not in p.parts and p.suffix not in ['.pyc', '.zip']]
    manifest = {'files_sha256': {p.relative_to(work).as_posix(): sha(p) for p in files},
                'source_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
                'note': 'E7 adicional; no se reentrenaron E0-E06. Los CSV de predicciones tienen ordinales sin ID real.'}
    writej(work / 'manifiesto_resultados.json', manifest)
    target = work / 'resultados_E7_exp1_exp2.zip'
    temp = target.with_suffix('.partial.zip')
    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files + [work / 'manifiesto_resultados.json']:
            z.write(p, p.relative_to(work).as_posix())
        for p in sources:
            z.write(p, 'codigo_E7/' + p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(temp) as z:
        require(z.testzip() is None, 'ZIP corrupto')
    temp.replace(target)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exp1', type=Path)
    p.add_argument('--exp2', type=Path)
    p.add_argument('--buscar-en', nargs='+', type=Path, default=[Path('/home/ds'), Path('/home/ds/buckets/b1/exp')])
    p.add_argument('--work', type=Path, default=Path('/home/ds/e7_ceros_exp1_exp2_run01'))
    p.add_argument('--gcs', help='Prefijo exclusivo, ej. gs://bucket/exp/e7_ceros_exp1_exp2_run01')
    p.add_argument('--restore', action='store_true', help='Restaurar sólo checkpoints nuevos de E7 desde --gcs en work vacío')
    p.add_argument('--n-jobs', type=int, default=7)
    args = p.parse_args()
    require(lgb.__version__ == '4.5.0', 'Este protocolo fija lightgbm==4.5.0; ejecutar run_gcp.sh')
    require(args.n_jobs > 0, '--n-jobs debe ser positivo')
    work = args.work.resolve()
    sources = [v.resolve() if v else find_run(label, args.buscar_en) for label, v in [('exp1', args.exp1), ('exp2', args.exp2)]]
    require(sources[0] != sources[1], 'Exp1 y Exp2 no pueden ser la misma carpeta')
    require(not work.is_relative_to(ROOT) and not ROOT.is_relative_to(work), '--work debe quedar fuera del código')
    for source in sources:
        require(not work.is_relative_to(source) and not source.is_relative_to(work), '--work debe estar separado de las corridas originales')
        require('buckets' not in work.parts, '--work debe ser disco local de VM, no un bucket montado')
    if args.restore:
        require(args.gcs and args.gcs.startswith('gs://') and len(args.gcs.split('/')) >= 5, '--restore requiere prefijo exclusivo --gcs')
        require(not work.exists() or not any(work.iterdir()), '--restore requiere --work vacío')
        work.mkdir(parents=True, exist_ok=True)
        subprocess.run(['gcloud', 'storage', 'rsync', '--recursive', args.gcs.rstrip('/'), str(work)], check=True)
    work.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                        handlers=[logging.StreamHandler(), logging.FileHandler(work / 'main.log', encoding='utf-8')])
    logging.info('E7: 60 modelos nuevos. Exp1=%s | Exp2=%s | salida=%s', *sources, work)
    remote = Remote(work, args.gcs)
    # Validar ambos orígenes ANTES de preparar o entrenar el primero.
    identities = [validate_source(source, label)[2] for source, label in zip(sources, ['exp1', 'exp2'])]
    require(identities[0]['data_sha256'] == identities[1]['data_sha256'], 'Los experimentos usan datasets distintos')
    pop = [pl.read_parquet(source / 'E0/prepared/test.parquet', columns=KEYS).sort('numero_de_cliente') for source in sources]
    require(pop[0].equals(pop[1]), 'Exp1 y Exp2 no tienen los mismos clientes/etiquetas test')
    for source, label in zip(sources, ['exp1', 'exp2']):
        run_one(source, work / label, label, args.n_jobs, remote)
    result = pack(work)
    remote.send(work / 'manifiesto_resultados.json', result, work / 'main.log')
    logging.info('LISTO: %s (%.2f MiB). Pasar este ZIP para actualizar GitHub.', result, result.stat().st_size / 1024**2)


if __name__ == '__main__':
    main()
