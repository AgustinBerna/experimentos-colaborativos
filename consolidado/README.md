# Resultados colaborativos unificados

[Dashboard interactivo](https://agustinberna.github.io/experimentos-colaborativos/consolidado.html)

Resultados publicados de Agustín, Micaela y Florencia: **26 combinaciones método/familia, 780 evaluaciones por semilla y 294 contrastes**. No se entrenaron modelos nuevos. Cada método conserva 30 semillas comunes; los controles repetidos se verificaron contra las métricas originales y se contaron una sola vez.

## Familias

| Familia | Train final | árboles | N | Métodos únicos |
|---|---|---:|---:|---:|
| EXP1 + extensiones FF | marzo–agosto 2019 | 280 | 4323 | 13 |
| EXP2, indicadores y derivados | marzo–agosto 2019 | 361 | 4352 | 8 |
| HIST_MJ, histórico separado | marzo–junio 2019 | 280 declarados por scripts | 4323 | 5 |

Test: octubre 2019. La comparación entre familias es descriptiva: difieren entrenamiento, selección o N. El ZIP histórico de Mica contiene CSV y hay scripts publicados, pero falta una identidad completa de esa corrida; su configuración se presenta con esa limitación.

## Definiciones que no deben mezclarse

- `ZERO`: ceros directos (E7 de Agustín). `FF_ZERO`: forward fill seguido de cero (Florencia).
- `FF_IND`: forward fill e indicadores originales de ausencia (E9 del código de Mica).
- `FF_MED_POST`: forward fill y mediana aprendida de train después del forward fill (E10 de Mica).
- `FF_MED_PRE`: forward fill y mediana aprendida de los valores originales observados de train (corrida original de Florencia).
- `FF_LIMIT2ROWS`: `forward_fill(limit=2)` de Mica (E12): limita dos registros consecutivos faltantes; no garantiza dos meses calendario si hay huecos.

La incorporación posterior del control de Mica en el resumen de Florencia no constituye otra corrida independiente. Se conservaron ambas definiciones de mediana y se deduplicaron los controles coincidentes. `datos/catalogo_metodos.csv` identifica cada método por `familia::método` y registra sus alias originales.

## Estadística

Wilcoxon bilateral pareado por semilla para ganancia a N fijo y AUC binaria; `zero_method=zsplit`, `method=auto`. Las diferencias se redondean a 6 decimales para ganancia y 12 para AUC para evitar empates espurios debidos a representación flotante. Diferencias todas nulas reciben p=1. Véase [documentación de SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html).

Holm se aplica por separado a cada familia temporal, métrica y conjunto de contrastes: alternativas vs E0 (12/7/4), variantes FF vs E4 (5/0/3), y todos los pares exploratorios (78/28/10). Los tres conjuntos responden preguntas diferentes: no seleccionar retrospectivamente el ajuste que resulte menor. Los p ajustados difieren de los informes originales al ampliarse el conjunto de comparaciones. Los CSV originales se conservan sin modificación.

Las semillas comparten clientes y mes. Estos contrastes describen aleatoriedad del modelo condicionada al mismo test, no replicaciones temporales ni incertidumbre sobre nuevas cohortes. La hipótesis de simetría de las diferencias de Wilcoxon debe considerarse al interpretar el resultado; no es un test directo de diferencia de medias.

La ganancia del ensamble se calcula sobre el ranking del promedio de probabilidades: **no es la ganancia promedio de semillas**. No se adjudica significación a diferencias de ensambles mediante los tests por semilla. Para las extensiones FF falta recibir las predicciones alineadas por cliente; entonces podrá realizarse bootstrap pareado por cliente, recalculando top-N en cada remuestreo y respetando la dependencia entre métodos.

## Resultados principales

Ridge E5 en EXP2 mejora la ganancia por semilla frente a E0 (+$5,17 M de media; p Holm≈0,000117). En EXP1 su diferencia es +$1,76 M, sin evidencia concluyente con la familia ampliada (p Holm≈0,421). miceforest reduce la ganancia de EXP1 (−$5,21 M; p Holm≈0,000236).

Ninguna de las cinco extensiones FF demuestra una mejora de ganancia sobre E4 con Holm. En el ensamble de EXP1, Ridge y FF+cero alcanzan ambos $295,82 M; esa igualdad observada no es una prueba de equivalencia. FF+mediana posterior tiene la mayor AUC de ensamble de EXP1 (0,938251). EXP2 Ridge alcanza $297,22 M. Ver todas las métricas y contrastes en el dashboard y CSV.

Variantes de parámetros Ridge y reglas de negocio permanecen pendientes de resultados verificados. No se incluyen como tratamientos completados.

## Fuentes y reproducción

[Manifiesto y atribución](FUENTES.md). `fuentes/` conserva los CSV publicados; `datos/validacion.json` incluye SHA256, versiones, semillas y comprobaciones de controles. Los repositorios de Mica y Flor se vinculan también como submódulos en la raíz, fijados a commits concretos.

Desde la raíz del repositorio, con Python 3.13:

```bash
python -m pip install -r consolidado/requirements.txt
python consolidado/reproducir.py --fuentes consolidado/fuentes --out .
python -m unittest discover -s consolidado -p 'test_*.py'
```

Esto reconstruye tablas, tests, PNG/SVG y `docs/consolidado.html`, sin dataset bancario ni reentrenamiento. Plotly se reutiliza desde `e7_ceros_gcp/vendor/plotly.min.js`. No se publican datos por cliente.
