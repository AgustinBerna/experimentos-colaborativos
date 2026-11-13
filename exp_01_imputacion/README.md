# Exp 1 · Imputación de valores faltantes

## Resultados publicados

- [Ver dashboard online](https://agustinberna.github.io/experimentos-colaborativos/exp1.html).
- [Descargar dashboard autocontenido](resultados/dashboard_comparativo.html).
- [Métricas por semilla](resultados/metricas_por_semilla_test.csv) y [curvas por semilla](resultados/curvas_por_semilla_test.csv).
- [Resumen del ensamble](resultados/resumen_ensamble_test.csv) y [curvas del ensamble](resultados/curvas_ensamble_test.csv).
- [Tabla del dashboard](resultados/resumen_dashboard.csv), [identidad de la corrida](run_identity.json) y [manifiesto de publicación](resultados/manifiesto_publicacion.json).



### Métodos y particiones temporales

Se compararon siete tratamientos de valores faltantes, manteniendo las mismas particiones temporales y 30 semillas comunes de LightGBM por método:

- **E0:** tratamiento nativo de valores faltantes de LightGBM.
- **E1, E2 y E3:** imputación por media, mediana y moda, respectivamente.
- **E4:** forward fill causal por cliente, utilizando únicamente observaciones anteriores.
- **E5:** imputación iterativa mediante BayesianRidge, ajustada sobre una muestra de 60.000 filas, con 10 rondas y 25 variables vecinas.
- **E6:** imputación mediante miceforest/LightGBM, con 5 rondas, 100 iteraciones por variable y predictive mean matching con 5 donantes.

### Preparación de variables

La auditoría convirtió en faltantes los valores de las variables que presentaban 100% de ceros en un mes. Se excluyeron `tmobile_app` y `cmobile_app_trx`, sin valores observados entre enero y junio de 2019.

La imputación de variables base precedió a la generación de sus lags y deltas de orden 1 y 2. Estos lags se calcularon mediante desplazamiento de filas dentro de cada cliente, ordenadas cronológicamente. Cuando faltaban meses de un cliente, el desplazamiento no necesariamente correspondía al mes calendario inmediatamente anterior.

Exp1 no incorporó indicadores adicionales de ausencia.

Enero y febrero aportaron historia para marzo; septiembre aportó historia para octubre. Noviembre y diciembre se utilizaron para construir las etiquetas de octubre. Estos meses auxiliares no integraron el entrenamiento final.

### Búsqueda de hiperparámetros y selección de N

La búsqueda original se realizó exclusivamente sobre E0 mediante 50 trials de Optuna. Se entrenó con marzo–junio de 2019 y se seleccionó el modelo por AUC binaria en agosto, con un máximo de 2000 árboles y early stopping de 100 rondas.

Con el E0 ganador se ordenaron los clientes de agosto por probabilidad predicha, resolviendo los empates por menor identificador de cliente. Se eligió N mediante el máximo de la ganancia acumulada suavizada con una ventana de ±500 contactos. Los restantes métodos heredaron los hiperparámetros, la cantidad de árboles y N seleccionados para E0. Octubre no participó en estas decisiones.

La corrida publicada reutilizó esa selección histórica, sin repetir la búsqueda: **280 árboles y N=4323**, con AUC de validación histórica de **0,937603422**.

Los hiperparámetros seleccionados y el espacio de búsqueda se publican en `seleccion.json` y `config.json`. El código disponible de la búsqueda original no fija una semilla explícita para el muestreador de Optuna; las semillas de LightGBM sí están configuradas.

### Entrenamiento final e imputación

Una vez congelada la selección de E0, cada método se entrenó con marzo–agosto de 2019, inclusive, utilizando los 280 árboles seleccionados y sin early stopping. La evaluación se realizó en octubre de 2019.

Los imputadores de media, mediana, moda, BayesianRidge y miceforest se ajustaron con marzo–agosto y se aplicaron al resto del panel sin reajustarse con octubre. Forward fill utilizó únicamente la historia anterior disponible de cada cliente.

### Objetivo y evaluación

El objetivo binario agrupó BAJA+1 y BAJA+2 como clase positiva. La ganancia económica remuneró únicamente BAJA+2: +$1.072.500 por acierto y −$27.500 por los demás contactos.

Se reportaron métricas por semilla y para el ensamble formado por el promedio de las probabilidades de las 30 semillas. Las métricas de campaña se evaluaron al mismo N=4323 para todos los métodos.

Las comparaciones entre cada método y E0 utilizaron Wilcoxon pareado por semilla, con ajuste Holm dentro de cada métrica. Las semillas comparten clientes y mes de evaluación: los contrastes describen variación ante la aleatoriedad del modelo y no constituyen tests temporales independientes.

La comparación entre Exp1 y Exp2 es descriptiva, porque también difieren sus selecciones de hiperparámetros, cantidad de árboles y N.


## Código, ejecución y procedencia

El código de Exp1_marzo_agosto_GCP.zip reemplaza al pipeline histórico. Los **15 archivos de código, config.json y seleccion.json coinciden byte a byte** con los hashes declarados en run_identity.json. El entorno registrado es Python 3.14.4. 
[EJECUCION_PAQUETE.md](EJECUCION_PAQUETE.md) conserva el README original del ZIP y sus instrucciones de ejecución. SHA256.json es el manifiesto original del paquete: su entrada README.md corresponde al archivo archivado aquí como EJECUCION_PAQUETE.md. Los tests heredados del repositorio histórico no certifican esta variante con selección congelada.

No se publican el dataset, modelos ni predicciones individuales.
