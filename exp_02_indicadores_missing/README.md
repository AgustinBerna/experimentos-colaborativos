# Exp 2 · Imputación con indicadores de ausencia

## Resultados publicados

- [Ver dashboard online](https://agustinberna.github.io/experimentos-colaborativos/exp2.html).
- [Descargar dashboard autocontenido](resultados/dashboard_comparativo.html).
- [Métricas por semilla](resultados/metricas_por_semilla_test.csv) y [curvas por semilla](resultados/curvas_por_semilla_test.csv).
- [Resumen del ensamble](resultados/resumen_ensamble_test.csv) y [curvas del ensamble](resultados/curvas_ensamble_test.csv).
- [Tabla del dashboard](resultados/resumen_dashboard.csv), [identidad de la corrida](run_identity.json) y [manifiesto de publicación](resultados/manifiesto_publicacion.json).

## Búsqueda original de hiperparámetros

La búsqueda original de hiperparámetros se realizó con 50 trials de Optuna solo para E0, entrenando con marzo–junio de 2019 y eligiendo por AUC en la validación de agosto. Con el mejor E0 se calculó la ganancia para todos los N de agosto y se eligió la meseta suavizada. Octubre no participó. Cada método hereda los parámetros, la iteración y N de su E0.

Esta metodología se mantiene. Después de esa selección, el entrenamiento final y el ajuste de imputadores se amplían a marzo–agosto, reutilizando los hiperparámetros, árboles y N elegidos.

## Métodos y meses

Entrenamiento final e imputadores ajustados con **marzo a agosto de 2019**, inclusive. Test: **octubre de 2019**, con 30 semillas comunes por método. Se conserva la selección histórica de Exp2: **232 árboles y N=4000**. En este entrenamiento final no se repiten Optuna, early stopping ni la validación; agosto forma parte del entrenamiento final. Las métricas de seleccion.json pertenecen a la validación histórica y no a esta corrida.

E0: NaN nativo; E1: media; E2: mediana; E3: moda; E4: forward fill causal por cliente; E5: IterativeImputer/BayesianRidge (60.000 filas, 10 rondas, 25 vecinas); E06: miceforest/LightGBM (5 rondas, 100 iteraciones por variable, 5 donantes). Media, mediana, moda, Ridge y miceforest se ajustan con marzo–agosto. Forward fill usa solo la historia disponible de cada cliente. Octubre no ajusta imputadores.

La imputación de variables base precede a los lags y deltas 1 y 2. Enero/febrero aportan lags para marzo; septiembre aporta historia para octubre y noviembre/diciembre permiten etiquetar octubre. Esos meses no entran al entrenamiento.

Los 150 indicadores originales de ausencia se calculan antes de imputar, se conservan intactos y no tienen lags/deltas propios. Las exclusiones se determinan con marzo–junio para mantener el esquema de la selección histórica.

Target binario BAJA+1/BAJA+2; ganancia para BAJA+2 (+$1.072.500 por acierto; −$27.500 por los demás contactos). Wilcoxon pareado por semilla con ajuste Holm dentro de cada métrica. Las semillas comparten clientes y mes: no representan tests temporales independientes.

## Código, ejecución y procedencia

El código de Exp2_indicadores_marzo_agosto_GCP.zip reemplaza al pipeline histórico. Los **15 archivos de código, config.json y seleccion.json coinciden byte a byte** con los hashes declarados en run_identity.json. El entorno registrado es Python 3.14.4. No se verificó independientemente el hash del dataset y no se reentrenó durante esta publicación.

[EJECUCION_PAQUETE.md](EJECUCION_PAQUETE.md) conserva el README original del ZIP y sus instrucciones de ejecución. SHA256.json es el manifiesto original del paquete: su entrada README.md corresponde al archivo archivado aquí como EJECUCION_PAQUETE.md. Los tests heredados del repositorio histórico no certifican esta variante con selección congelada.

No se publican el dataset, modelos ni predicciones individuales.
