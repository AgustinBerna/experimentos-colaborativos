# Exp 2 · Indicadores de ausencia con lags y deltas

## Resultados de la corrida actual

- [Ver dashboard en GitHub Pages](https://agustinberna.github.io/experimentos-colaborativos/exp2-marzo-agosto.html).
- [Descargar HTML autocontenido](resultados/dashboard_comparativo.html).
- [Métricas por semilla](resultados/metricas_por_semilla_test.csv) y [curvas por semilla](resultados/curvas_por_semilla_test.csv).
- [Resumen del ensamble](resultados/resumen_ensamble_test.csv) y [curvas del ensamble](resultados/curvas_ensamble_test.csv).
- [Selección propia de E0](seleccion.json): AUC de agosto **0.9380103175**, **361 árboles**, **N=4352**.
- [Curva completa de ganancia en agosto](E0/optimization/curva_ganancia_valid_e0.csv) y [auditoría de la búsqueda](E0/optimization/split_audit.json).
- [Tabla del dashboard](resultados/resumen_dashboard.csv), [identidad original](run_identity.json) y [manifiesto de publicación](resultados/manifiesto_publicacion.json).

Esta corrida se llamó **Exp3 en GCP** y se publica como **Exp2 en este repositorio**, reemplazando el Exp2 anterior. Los JSON originales conservan el identificador Exp3 para mantener su trazabilidad. Los títulos del dashboard muestran Exp2. No se ejecutó entrenamiento durante la publicación.

## Indicadores y variables temporales

Se conservan los **150 indicadores de ausencia originales**, calculados antes de imputar. Se añaden sus **300 lags y 300 deltas** de 1 y 2 meses. Los lags buscan al mismo cliente en el mes calendario exacto; si no existe ese mes, tanto el lag como su delta quedan null. Delta = indicador_actual − indicador_t-k: +1 empieza a faltar, −1 vuelve a estar observado y 0 no cambia.

Los indicadores y sus derivados no pasan por los imputadores. Las variables base conservan los lags/deltas de los experimentos anteriores. E0 recibió **1500 variables**, según la auditoría de la búsqueda.

Se excluyeron **tmobile_app** y **cmobile_app_trx**, completamente vacías en marzo–junio. La exclusión precede a la generación de indicadores y derivados. Ver [variables excluidas](partition/features_excluidas.json) y [plan de indicadores](partition/indicadores_ausente.json).

## Búsqueda propia de hiperparámetros y entrenamiento final

Se mantiene la metodología de búsqueda: **50 trials de Optuna solamente sobre el baseline E0**, entrenando con **marzo–junio de 2019** y seleccionando por **AUC en agosto**. E0 incluye NaN nativos, indicadores, lags y deltas. Se usan el espacio original de búsqueda, hasta 2000 árboles y early stopping de 100 rondas. La búsqueda registrada usó 506.871 filas de entrenamiento y 131.775 de validación.

Con el E0 ganador se ordenan los clientes de agosto y se elige N por la meseta de ganancia suavizada con radio ±500 envíos. **Octubre no participa** en la búsqueda ni en la selección de N. Esta corrida tiene su propia selección; no hereda los 232 árboles ni N=4000 del Exp2 anterior.

Una vez congelados los hiperparámetros, árboles y N, todos los métodos se entrenan finalmente con **marzo–agosto**, sin early stopping, y se evalúan en **octubre** con **30 semillas comunes**. Los imputadores se ajustan con marzo–agosto para este entrenamiento final. La búsqueda usa solo E0, que no ajusta imputador; agosto no entra a su fit de Optuna.

E0: NaN nativo; E1: media; E2: mediana; E3: moda; E4: forward fill causal por cliente; E5: IterativeImputer/BayesianRidge (60.000 filas, 10 rondas, 25 vecinas); E06: miceforest/LightGBM (5 rondas, 100 iteraciones por variable, 5 donantes).

Enero/febrero aportan historia para marzo; septiembre aporta historia para octubre; noviembre/diciembre permiten etiquetar octubre. Target binario BAJA+1/BAJA+2; ganancia para BAJA+2 (+$1.072.500 por acierto; −$27.500 por los demás contactos).

Los p-valores usan Wilcoxon pareado por semilla con ajuste Holm dentro de cada métrica. Las semillas comparten el mismo test y no son tests temporales independientes. La comparación con Exp1 es descriptiva: también difieren la selección y N.

## Código, ejecución y procedencia

Los **15 archivos de código y config.json coinciden byte a byte** con run_identity.json de la corrida recibida. El entorno declara Python 3.14.4; el archivo de dependencias fija LightGBM 4.5.0 y miceforest 6.0.5, pero el manifiesto no permite verificar las versiones realmente instaladas. No se verificó independientemente el hash del dataset.

Desde esta carpeta y con las dependencias instaladas:

~~~bash
python -m unittest discover -s tests -v
python run_pipeline.py --data /ruta/competencia_02_crudo.csv.gz --work /ruta/nueva/exp2_lags_deltas --step all
~~~

Para GCP puede agregarse --remote gs://TU_BUCKET/exp2_lags_deltas. Usar rutas nuevas; no reutilizar los checkpoints de esta corrida con código o configuración distintos. El script ejecutar_gcp.sh publica rutas predeterminadas propias de Exp2 y permite configurar EXP2_DATA, EXP2_WORK, EXP2_REMOTE, EXP2_PYTHON y EXP2_STEP.

[EJECUCION_PAQUETE.md](EJECUCION_PAQUETE.md) conserva las instrucciones originales del paquete llamado Exp3. seleccion_exp2_referencia.json conserva la selección del experimento previo únicamente como referencia: el pipeline no la lee. La selección nueva se genera en el directorio de trabajo y se congela antes de abrir octubre.

Se incluyen las 12 pruebas sintéticas de esta implementación. No se publican dataset, modelos ni predicciones individuales.
