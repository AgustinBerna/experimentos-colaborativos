"""Dashboard autocontenido con ocho métodos y ausencia antes de imputar."""
import base64
import html
import json
from pathlib import Path
import polars as pl

ROOT = Path(__file__).resolve().parent


def render(out, label, selected):
    out = Path(out)
    tables = {key: pl.read_csv(out / 'resultados' / file).to_dicts() for key, file in [
        ('seeds', 'metricas_por_semilla_test.csv'), ('summary', 'resumen_ensamble_test.csv'),
        ('curves', 'curvas_ensamble_test.csv'), ('missing', 'porcentaje_na_train_test.csv')]}
    tables['experiment'] = 'Exp1' if label == 'exp1' else 'Exp2'
    tables['selection'] = selected
    tables['csv'] = {name: base64.b64encode(p.read_bytes()).decode('ascii')
                     for p in sorted((out / 'resultados').glob('*.csv'))
                     if not (name := p.name).startswith('predicciones_')}
    vendor = base64.b64encode((ROOT / 'vendor/plotly.min.js').read_bytes()).decode('ascii')
    data = json.dumps(tables, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    template = (ROOT / 'dashboard_template.html').read_text(encoding='utf-8')
    document = template.replace('@@TITLE@@', html.escape(tables['experiment']))
    document = document.replace('@@VENDOR@@', vendor).replace('@@DATA@@', data)
    destination = out / f'{label}.html'
    destination.write_text(document, encoding='utf-8')
    return destination
