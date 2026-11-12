# Experimentos colaborativos

Dos experimentos de imputación de valores faltantes en churn bancario, con código y resultados.

**[Ver el dashboard comparativo de Exp 1 en GitHub Pages](https://agustinberna.github.io/experimentos-colaborativos/)**

| Experimento | Descripción | Árboles E0 | N | Resultados |
|---|---|---:|---:|---|
| [Exp 1 · Imputación](exp_01_imputacion/) | NaN nativo y seis imputaciones | 280 | 4323 | [Ver online](https://agustinberna.github.io/experimentos-colaborativos/) · [Descargar HTML](exp_01_imputacion/resultados/dashboard_comparativo.html) |
| [Exp 2 · Indicadores de missing](exp_02_indicadores_missing/) | Los mismos métodos con 150 indicadores de ausencia | 232 | 4000 | [Descargar HTML](exp_02_indicadores_missing/resultados/dashboard_comparativo.html) · [seleccion.json](exp_02_indicadores_missing/seleccion.json) |

Exp 1 publica los nuevos resultados con entrenamiento e imputadores ajustados de **marzo a agosto de 2019**, selección histórica congelada y test en octubre, sin nueva validación. Exp 2 conserva su corrida histórica: entrenamiento marzo-junio, validación agosto y test octubre. Ambos incluyen 30 semillas por método. Como usan distintos períodos de entrenamiento y selecciones, la comparación entre experimentos es descriptiva y no aísla causalmente el efecto de los indicadores.

Cada carpeta incluye su tabla y un manifiesto con hashes. Exp 1 también contiene los cuatro CSV de resultados y run_identity.json suministrados. Se publican resultados existentes, sin nuevos entrenamientos; los README detallan el protocolo y los límites de reproducción.

## GitHub Pages

La carpeta docs contiene el dashboard autocontenido como index.html y conserva los enlaces dashboard_comparativo.html y dashboard_imputacion_v3.html. El workflow de Pages publica docs al actualizar main. Si Pages todavía no está habilitado, seleccionar **Settings → Pages → Source → GitHub Actions** una vez.
