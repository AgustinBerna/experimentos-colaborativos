# Exp 1 · Imputación de valores faltantes

Compara seis imputaciones con los NaN nativos de LightGBM, sin indicadores adicionales de ausencia.

## Resultados actualizados

- [Ver dashboard en GitHub Pages](https://agustinberna.github.io/experimentos-colaborativos/).
- [Dashboard autocontenido para descargar](resultados/dashboard_comparativo.html): funciona también sin conexión.
- [Métricas por semilla](resultados/metricas_por_semilla_test.csv) y [curvas por semilla](resultados/curvas_por_semilla_test.csv).
- [Resumen del ensamble](resultados/resumen_ensamble_test.csv) y [curvas del ensamble](resultados/curvas_ensamble_test.csv).
- [Tabla del dashboard](resultados/resumen_dashboard.csv), [identidad de la corrida](run_identity.json) y [manifiesto de publicación](resultados/manifiesto_publicacion.json).

Se publican los resultados suministrados, sin ejecutar nuevos entrenamientos. Las métricas y los datos de los gráficos se conservan; se integraron las dependencias locales y se muestran los siete métodos sin paginación.

## Métodos y protocolo de la corrida publicada

El entrenamiento final utiliza **marzo a agosto de 2019**, ambos inclusive. Los imputadores E1, E2, E3, E5 y E06 se ajustan con **marzo a agosto**, y aplican esos ajustes a los demás meses. Octubre no interviene en su ajuste. E4 aplica forward fill causal por cliente. La imputación de variables base precede a los lags y deltas 1 y 2; enero y febrero aportan historia para los lags de marzo.

Se reutiliza la selección histórica de Exp1: hiperparámetros E0, **280 árboles y N=4323**. No se ejecutó Optuna ni una nueva validación en esta corrida; agosto integra el entrenamiento final. El AUC de validación 0.937603422 de [seleccion.json](seleccion.json) corresponde a la selección histórica, no a una validación nueva. El test es **octubre de 2019**, con 30 semillas comunes por método.

Target binario BAJA+1/BAJA+2; ganancia solo para BAJA+2 (+$1.072.500 por acierto, −$27.500 por los demás contactos). Auditoría común de variables mes a mes: 100% ceros a null y exclusión de variables sin información en entrenamiento.

E0: NaN nativo; E1: media; E2: mediana; E3: moda; E4: forward fill causal por cliente; E5: IterativeImputer/BayesianRidge (60.000 filas, 10 rondas, 25 vecinas); E06: miceforest/LightGBM (5 rondas, 100 iteraciones por variable, 5 donantes).

Los p-valores provienen del Wilcoxon pareado por semilla con ajuste Holm dentro de cada métrica. Las semillas comparten clientes y mes: describen estabilidad ante la aleatoriedad del modelo y no 30 muestras independientes ni 30 tests temporales.

## Código y procedencia

El archivo run_identity.json recibido registra Python 3.14.4 y hashes de la corrida. Los hashes del código y de la selección difieren de los archivos históricos de este repositorio; el manifiesto detalla la comparación. No se certifica una reproducción exacta sin el código, la configuración y la selección originales de esa ejecución.

Los scripts y config.json conservados aquí corresponden al pipeline histórico: entrenamiento marzo-junio y optimización E0 con validación en agosto. No describen el entrenamiento final de los resultados actualizados. Cambiar solamente train_months incorporando agosto haría que el pipeline histórico optimizara usando un mes ya incluido en train. Para reproducir la corrida publicada hace falta su implementación con selección congelada, además del dataset; no basta con ejecutar el pipeline histórico.

No se publican dataset, modelos ni predicciones individuales.
