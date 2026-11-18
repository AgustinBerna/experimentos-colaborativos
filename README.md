# Experimentos colaborativos


**[Ver los dashboards en GitHub Pages](https://agustinberna.github.io/experimentos-colaborativos/)**

| Experimento | Descripción | Árboles E0 | N | Resultados |
|---|---|---:|---:|---|
| [Exp 1 · Imputación](exp_01_imputacion/) | NaN basal y siete imputaciones, incluyendo E7 con ceros | 280 | 4323 | [Ver online](https://agustinberna.github.io/experimentos-colaborativos/exp1.html) · [Descargar HTML](exp_01_imputacion/resultados/dashboard_comparativo.html) |
| [Exp 2 · Indicadores con lags y deltas](exp_02_indicadores_missing/) | Mismo que Exp1 pero agregando  indicadores de missing sus lags y delta lags; optimización propia de E0 | 361 | 4352 | [Ver online](https://agustinberna.github.io/experimentos-colaborativos/exp2-marzo-agosto.html) · [Descargar HTML](exp_02_indicadores_missing/resultados/dashboard_comparativo.html) |

Ambas corridas entrenan finalmente y ajustan imputadores con **marzo–agosto de 2019** y evalúan **octubre de 2019**, con 30 semillas comunes por método.

## Búsqueda de hiperparámetros

Metodologia: Busqueda de hiperparametros y número de envios solo con E0: entrenamiento marzo–junio y selección por AUC en agosto. El ganador E0 elige N por la meseta suavizada de ganancia de agosto. Luego cada método usa esos hiperparámetros, árboles y N de su E0. Después se realiza el entrenamiento final marzo–agosto con esa selección congelada. De esta manera lo único que cambian son los métodos de imputación dejando fijo lo demás.


## Resultados colaborativos unificados

**[Dashboard conjunto: Agustín, Micaela y Florencia](https://agustinberna.github.io/experimentos-colaborativos/consolidado.html)** · [Metodología, fuentes, CSV y reproducción](consolidado/).

Incluye 26 combinaciones de método y familia, 780 evaluaciones por semilla, gráficos con definiciones comunes y Wilcoxon pareado con Holm. Los controles repetidos se verifican y cuentan una sola vez; marzo–junio se presenta separado de marzo–agosto. Código de los forks fijado mediante submódulos. Las comparaciones de ensambles por cliente de las extensiones FF quedan pendientes de recibir sus predicciones.
