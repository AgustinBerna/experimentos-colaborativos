# Experimentos colaborativos

Dos experimentos de imputación de valores faltantes en churn bancario, con código y resultados de las nuevas corridas.

**[Ver los dos dashboards en GitHub Pages](https://agustinberna.github.io/experimentos-colaborativos/)**

| Experimento | Descripción | Árboles E0 | N congelado | Dashboard |
|---|---|---:|---:|---|
| [Exp 1 · Imputación](exp_01_imputacion/) | NaN nativo y seis imputaciones | 280 | 4323 | [Ver online](https://agustinberna.github.io/experimentos-colaborativos/exp1.html) · [Descargar](exp_01_imputacion/resultados/dashboard_comparativo.html) |
| [Exp 2 · Indicadores de ausencia](exp_02_indicadores_missing/) | Los mismos métodos con 150 indicadores originales | 232 | 4000 | [Ver online](https://agustinberna.github.io/experimentos-colaborativos/exp2.html) · [Descargar](exp_02_indicadores_missing/resultados/dashboard_comparativo.html) |

Ambas corridas entrenan y ajustan los imputadores con **marzo–agosto de 2019**, inclusive, y evalúan **octubre de 2019**, con 30 semillas comunes por método. Conservan sus respectivas selecciones históricas; no hay nueva optimización, early stopping ni validación en agosto. En Exp2, las exclusiones se determinan con marzo–junio para conservar el esquema de variables original, aunque el entrenamiento y el ajuste de imputadores llegan a agosto.

Los nuevos paquetes de código reemplazan al pipeline histórico. En ambos experimentos, los 15 archivos de código, la configuración y la selección coinciden byte a byte con sus run_identity.json. Cada carpeta incluye los cuatro CSV de resultados, el dashboard autocontenido y un manifiesto de publicación con hashes. No se reentrenó durante esta actualización ni se verificó independientemente el hash del dataset.

Cada experimento tiene sus propios hiperparámetros, cantidad de árboles y N. La comparación entre Exp1 y Exp2 es descriptiva y no aísla causalmente el efecto de los indicadores. Los p-valores por semilla no representan tests temporales independientes. Ver metodología y ejecución en los README de cada carpeta.

## GitHub Pages

La carpeta docs contiene la portada index.html y los dashboards exp1.html y exp2.html, todos sin dependencias externas. Los enlaces anteriores dashboard_comparativo.html y dashboard_imputacion_v3.html siguen abriendo Exp1; dashboard_indicadores_v3.html abre Exp2.

El workflow de Pages publica docs al actualizar main. Si Pages no está habilitado, seleccionar **Settings → Pages → Source → GitHub Actions** una vez y ejecutar el workflow **Publicar dashboard en GitHub Pages**.
