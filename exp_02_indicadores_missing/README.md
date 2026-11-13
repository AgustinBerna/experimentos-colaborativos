# Exp 2 · Indicadores de ausencia con lags y deltas

## Resultados de la corrida actual

- [Ver dashboard en GitHub Pages](https://agustinberna.github.io/experimentos-colaborativos/exp2-marzo-agosto.html).
- [Descargar HTML autocontenido](resultados/dashboard_comparativo.html).
- [Métricas por semilla](resultados/metricas_por_semilla_test.csv) y [curvas por semilla](resultados/curvas_por_semilla_test.csv).
- [Resumen del ensamble](resultados/resumen_ensamble_test.csv) y [curvas del ensamble](resultados/curvas_ensamble_test.csv).
- [Selección propia de E0](seleccion.json): AUC de agosto **0.9380103175**, **361 árboles**, **N=4352**.
- [Curva completa de ganancia en agosto](E0/optimization/curva_ganancia_valid_e0.csv) y [auditoría de la búsqueda](E0/optimization/split_audit.json).
- [Tabla del dashboard](resultados/resumen_dashboard.csv), [identidad original](run_identity.json) y [manifiesto de publicación](resultados/manifiesto_publicacion.json).


### Métodos y particiones temporales

Se compararon siete tratamientos de valores faltantes, manteniendo las mismas particiones temporales y 30 semillas comunes de LightGBM por método:

- **E0:** tratamiento nativo de valores faltantes de LightGBM.
- **E1, E2 y E3:** imputación por media, mediana y moda, respectivamente.
- **E4:** forward fill causal por cliente, utilizando únicamente observaciones anteriores.
- **E5:** imputación iterativa mediante BayesianRidge, ajustada sobre una muestra de 60.000 filas, con 10 rondas y 25 variables vecinas.
- **E6:** imputación mediante miceforest/LightGBM, con 5 rondas, 100 iteraciones por variable y predictive mean matching con 5 donantes.

Todos los métodos incorporaron los mismos indicadores de ausencia y sus variables temporales.

### Preparación de variables

La auditoría convirtió en faltantes los valores de las variables que presentaban 100% de ceros en un mes. Se excluyeron las variables completamente faltantes en marzo–junio de 2019. Esta regla eliminó `tmobile_app` y `cmobile_app_trx`, antes de imputar y generar indicadores o derivados.

La imputación de variables base precedió a la generación de sus lags y deltas de orden 1 y 2. Estos lags se calcularon mediante desplazamiento de filas dentro de cada cliente, ordenadas cronológicamente. Cuando faltaban meses de un cliente, el desplazamiento no necesariamente correspondía al mes calendario inmediatamente anterior.

Antes de imputar, se generaron **150 indicadores de ausencia**, uno por variable original conservada: 1 cuando el valor estaba ausente y 0 cuando estaba observado.

Se añadieron **300 lags y 300 deltas** de los indicadores, correspondientes a uno y dos meses anteriores. A diferencia de los lags de variables base, estos lags buscaron al mismo cliente en el **mes calendario exacto**. Cuando no existía ese registro histórico, el lag y su delta permanecieron nulos.

Los deltas se definieron como indicador actual menos indicador histórico: +1 indica que la variable pasó de observada a faltante; −1, que pasó de faltante a observada; y 0, que mantuvo su estado. Los indicadores y sus derivados no pasaron por los imputadores.

El esquema resultante incluyó **1500 variables predictoras**: 150 variables base, 300 lags y 300 deltas de variables base, 150 indicadores actuales, 300 lags y 300 deltas de indicadores.

Enero y febrero aportaron historia para marzo; septiembre aportó historia para octubre. Noviembre y diciembre se utilizaron para construir las etiquetas de octubre. Estos meses auxiliares no integraron el entrenamiento final.

### Búsqueda de hiperparámetros y selección de N

La búsqueda se realizó exclusivamente sobre el E0 de Exp2 mediante 50 trials de Optuna. E0 incluyó los indicadores de ausencia y sus lags y deltas, además del tratamiento nativo de faltantes.

Se entrenó con marzo–junio de 2019 y se seleccionó el modelo por AUC binaria en agosto, con un máximo de 2000 árboles y early stopping de 100 rondas. La búsqueda utilizó **506.871 filas de entrenamiento y 131.775 de validación**.

Con el E0 ganador se ordenaron los clientes de agosto por probabilidad predicha, resolviendo los empates por menor identificador de cliente. Se eligió N mediante el máximo de la ganancia acumulada suavizada con una ventana de ±500 contactos. Los restantes métodos heredaron los hiperparámetros, la cantidad de árboles y N seleccionados para E0. Octubre no participó en estas decisiones.

La selección propia de esta corrida fue de **361 árboles y N=4352**, con AUC de validación de **0,938010318**.

Los hiperparámetros seleccionados y el espacio de búsqueda se publican en `seleccion.json` y `config.json`. No se fijó una semilla explícita para el muestreador de Optuna; las semillas de LightGBM sí están configuradas. Por ello, una nueva búsqueda desde cero puede explorar otros candidatos.

### Entrenamiento final e imputación

Una vez congelada la selección de E0, cada método se entrenó con marzo–agosto de 2019, inclusive, utilizando los 361 árboles seleccionados y sin early stopping. La evaluación se realizó en octubre de 2019.

Los imputadores de media, mediana, moda, BayesianRidge y miceforest se ajustaron con marzo–agosto y se aplicaron al resto del panel sin reajustarse con octubre. Forward fill utilizó únicamente la historia anterior disponible de cada cliente.

La búsqueda utilizó solo E0, que no ajustó un imputador. Por lo tanto, los imputadores ajustados con marzo–agosto para el entrenamiento final no intervinieron en la validación de Optuna.

### Objetivo y evaluación

El objetivo binario agrupó BAJA+1 y BAJA+2 como clase positiva. La ganancia económica remuneró únicamente BAJA+2: +$1.072.500 por acierto y −$27.500 por los demás contactos.

Se reportaron métricas por semilla y para el ensamble formado por el promedio de las probabilidades de las 30 semillas. Las métricas de campaña se evaluaron al mismo N=4352 para todos los métodos.

Las comparaciones entre cada método y E0 utilizaron Wilcoxon pareado por semilla, con ajuste Holm dentro de cada métrica. Las semillas comparten clientes y mes de evaluación: los contrastes describen variación ante la aleatoriedad del modelo y no constituyen tests temporales independientes.

La comparación entre Exp1 y Exp2 es descriptiva, porque también difieren sus selecciones de hiperparámetros, cantidad de árboles y N. Las diferencias observadas no pueden atribuirse exclusivamente a los indicadores y sus derivados.

### Código, ejecución y procedencia

Los 15 archivos de código y `config.json` coinciden byte a byte con los hashes declarados en `run_identity.json`. La selección propia se publica en `seleccion.json`, junto con la curva completa de ganancia de agosto y la auditoría de la búsqueda.

El entorno registrado es Python 3.14.4. `requirements.txt` documenta las versiones previstas de las dependencias, pero `run_identity.json` no certifica las versiones realmente instaladas.

[EJECUCION_PAQUETE.md](https://github.com/AgustinBerna/experimentos-colaborativos/blob/main/exp_02_indicadores_missing/EJECUCION_PAQUETE.md) conserva las instrucciones originales del paquete. Se incluyen 12 pruebas sintéticas de preparación de variables, separación temporal, optimización, herencia de selección y reanudación.

Desde esta carpeta y con las dependencias instaladas:

~~~bash
python -m unittest discover -s tests -v
python run_pipeline.py --data /ruta/competencia_02_crudo.csv.gz --work /ruta/nueva/exp2_lags_deltas --step all
~~~

Para GCP puede agregarse --remote gs://TU_BUCKET/exp2_lags_deltas. Usar rutas nuevas; no reutilizar los checkpoints de esta corrida con código o configuración distintos. El script ejecutar_gcp.sh publica rutas predeterminadas propias de Exp2 y permite configurar EXP2_DATA, EXP2_WORK, EXP2_REMOTE, EXP2_PYTHON y EXP2_STEP.

[EJECUCION_PAQUETE.md](EJECUCION_PAQUETE.md) conserva las instrucciones originales del paquete llamado Exp3. seleccion_exp2_referencia.json conserva la selección del experimento previo únicamente como referencia: el pipeline no la lee. La selección nueva se genera en el directorio de trabajo y se congela antes de abrir octubre.

