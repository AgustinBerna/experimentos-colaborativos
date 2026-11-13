# Exp3 · Indicadores, lags y deltas con optimización propia de E0

## Qué prueba

Exp3 conserva las variables e indicadores originales de Exp2 y agrega lags y deltas de 1 y 2 meses a cada indicador de ausencia. Con 150 indicadores añade 600 variables: 300 lags y 300 deltas. Los indicadores se calculan antes de imputar. Sus lags se buscan por cliente y mes calendario exacto, no por fila anterior. Si falta historia, el lag y su delta quedan null. Delta = indicador_actual − indicador_t-k: +1 empieza a faltar, −1 vuelve a estar observado, 0 no cambia.

Se conservan las exclusiones de variables de marzo–junio y los lags/deltas existentes de las variables base. Los imputadores mantienen sus configuraciones y se ajustan con marzo–agosto; los indicadores y sus derivados no pasan por ellos.

## Optimización propia del baseline E0

Esta versión no hereda la selección de Exp2. El E0 de Exp3 contiene NaN nativos, los indicadores y sus lags/deltas, igual que el esquema del resto de métodos.

1. E0 ejecuta 50 trials de Optuna, con train marzo–junio de 2019 y validación en agosto. Usa el espacio de búsqueda original de config.json, hasta 2000 árboles y early stopping de 100 rondas. Se elige por AUC binaria de agosto.
2. Con el E0 ganador se ordenan los clientes de agosto y se elige N por la meseta de ganancia suavizada con radio ±500 envíos. Octubre no elige parámetros, árboles ni N.
3. Se congela la nueva selección de E0 de Exp3 y se comparte con E1, E2, E3, E4, E5 y E06.
4. Los siete métodos se entrenan finalmente con marzo–agosto, usando los árboles elegidos y sin early stopping. Se evalúan en octubre con las mismas 30 semillas comunes.

Para la búsqueda se filtran marzo–junio y agosto del archivo E0/prepared/train.parquet; agosto no entra al fit de Optuna. valid.parquet sigue vacío por compatibilidad con el particionado final. E0 no usa imputación, por lo que la búsqueda tampoco recibe un imputador ajustado con agosto. Enero/febrero aportan historia de marzo; septiembre aporta historia de octubre; noviembre/diciembre permiten etiquetar octubre. El CSV debe contener enero–diciembre.

Las cantidades de árboles y N son resultados de esta búsqueda: no están fijadas en 232 y 4000. seleccion_exp2_referencia.json es únicamente una copia de referencia; el pipeline no la lee. La selección nueva se genera en el directorio de trabajo, E0/optimization/seleccion.json, y se congela en SELECCION_FROZEN.json antes de abrir octubre.

El estudio SQLite y los checkpoints permiten reanudar una VM Spot. Los trials completados se conservan y los modelos por semilla terminados no se vuelven a ajustar. Nunca reutilizar el work o prefijo remoto de otra versión.

## Ejecutar en GCP

Subir Exp3_indicadores_lags_deltas_optuna_GCP.zip a /home/ds/buckets/b1/exp. En la terminal:

~~~bash
mkdir -p /home/ds/exp3_lags_deltas_optuna
unzip /home/ds/buckets/b1/exp/Exp3_indicadores_lags_deltas_optuna_GCP.zip -d /home/ds/exp3_lags_deltas_optuna
tmux new-session -s exp3_optuna
~~~

Dentro de tmux, usando el mismo entorno Python/R de Exp2:

~~~bash
bash /home/ds/exp3_lags_deltas_optuna/exp_03_indicadores_lags_deltas_optuna/ejecutar_gcp.sh
~~~

El script ejecuta primero las pruebas sintéticas y luego todas las etapas de la corrida real. Las pruebas usan 2 trials y datos inventados; la corrida real usa los 50 trials configurados. Para dejarla corriendo, Ctrl+B y luego D. Volver con tmux attach -t exp3_optuna. La VM debe permanecer encendida.

Rutas predeterminadas:

- Dataset: /home/ds/buckets/b1/datasets/competencia_02_crudo.csv.gz
- Trabajo: /home/ds/exp3_indicadores_lags_deltas_optuna_run01
- Checkpoints: gs://agustinberna343_buckito2026/exp/exp3_indicadores_lags_deltas_optuna_run01

Se pueden configurar EXP3_DATA, EXP3_WORK, EXP3_REMOTE, EXP3_PYTHON y EXP3_STEP. STEP admite all (predeterminado), auditar, particionar, preparar, modelar, dashboard o estado. Para reanudar, repetir el mismo comando con idénticas rutas y archivos; para una corrida independiente, cambiar work y remote.

Para una VM nueva, instalar las dependencias fijadas de requirements.txt y los paquetes R con Rscript install_r_packages.R. Se necesita gcloud autenticado para checkpoints. En la VM ya usada para Exp2 se puede usar su entorno existente.

## Salidas y seguimiento

- E0/optimization/study.sqlite3: trials de la búsqueda propia.
- E0/optimization/split_audit.json: meses, filas y cantidad de variables usados para optimizar.
- E0/optimization/curva_ganancia_valid_e0.csv: todos los N de agosto y la ganancia suavizada.
- E0/optimization/seleccion.json y SELECCION_FROZEN.json: nueva decisión compartida.
- Cada método: prepared/indicadores_lags.json y final_fit_audit.json, con columnas y filas del entrenamiento final.
- resultados: los cuatro CSV habituales, FINALIZADO.json, dashboard_comparativo.html y lib; ZIP descargable del dashboard si existe zip en la VM.

~~~bash
tail -f /home/ds/exp3_indicadores_lags_deltas_optuna_run01/logs/main.log
~~~

La comparación con Exp2 es descriptiva: ahora también puede cambiar la selección de hiperparámetros, árboles y N, además de agregarse lags/deltas. Los p-valores del dashboard son comparaciones de cada método de Exp3 contra su E0; no son pruebas automáticas de Exp3 contra Exp2 ni tests temporales independientes.

## Validación

12 pruebas con datos sintéticos: historial exacto por mes, ausencias y cruce de año, aislamiento entre clientes, no uso de futuro, 600 variables nuevas con 150 indicadores, preparación de particiones y E0, optimización real sin test disponible, rechazo de particiones superpuestas, selección de N, herencia de selección, reajuste final marzo–agosto y reanudación sin repetir fits/trials. También se verificó la sintaxis de Python y R. No se ejecutó la corrida real de 50 trials ni se dispone aquí del dataset completo. Ver VALIDACION.json y SHA256.json.
