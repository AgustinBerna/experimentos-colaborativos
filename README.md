# Experimentos colaborativos

Experimentos de imputación de valores faltantes en churn bancario, con código, configuración y resultados de cada corrida.

**[Ver los dashboards en GitHub Pages](https://agustinberna.github.io/experimentos-colaborativos/)**

| Experimento | Descripción | Árboles E0 | N | Resultados |
|---|---|---:|---:|---|
| [Exp 1 · Imputación](exp_01_imputacion/) | NaN nativo y seis imputaciones | 280 | 4323 | [Ver online](https://agustinberna.github.io/experimentos-colaborativos/exp1.html) · [Descargar HTML](exp_01_imputacion/resultados/dashboard_comparativo.html) |
| [Exp 2 · Indicadores con lags y deltas](exp_02_indicadores_missing/) | 150 indicadores originales + 300 lags + 300 deltas; optimización propia de E0 | 361 | 4352 | [Ver online](https://agustinberna.github.io/experimentos-colaborativos/exp2-marzo-agosto.html) · [Descargar HTML](exp_02_indicadores_missing/resultados/dashboard_comparativo.html) |

Ambas corridas entrenan finalmente y ajustan imputadores con **marzo–agosto de 2019** y evalúan **octubre de 2019**, con 30 semillas comunes por método.

## Búsqueda de hiperparámetros

La metodología se conserva: 50 trials de Optuna solo para E0, entrenamiento marzo–junio y selección por AUC en agosto. El ganador E0 elige N por la meseta suavizada de ganancia de agosto; octubre no participa. Cada método hereda hiperparámetros, árboles y N de su E0. Después se realiza el entrenamiento final marzo–agosto con esa selección congelada.

Exp1 reutiliza su selección histórica. El Exp2 actual realiza su **propia optimización** e incorpora lags y deltas mensuales de los indicadores. Esta corrida se llamó Exp3 en GCP y reemplaza aquí al Exp2 anterior. Los archivos originales de identidad y selección conservan ese identificador para trazabilidad.

Los experimentos tienen sus propias selecciones y N: la comparación es descriptiva y no aísla causalmente el efecto de los indicadores. Los p-valores por semilla no representan tests temporales independientes. Los README detallan metodología, ejecución y procedencia.

Cada carpeta incluye resultados CSV, dashboard autocontenido y manifiesto con hashes. En ambas corridas publicadas, el código y la configuración coinciden con las identidades suministradas. No se reentrenó al publicar los resultados.

## GitHub Pages

La portada está en docs/index.html. Exp1 se mantiene en exp1.html; Exp2 en exp2-marzo-agosto.html, con los alias exp2.html y dashboard_indicadores_v3.html. El workflow de Pages publica docs al actualizar main.
