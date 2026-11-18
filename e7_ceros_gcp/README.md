# E7: imputación por cero para Exp1 y Exp2

Este paquete agrega E7 a las dos corridas publicadas en
https://github.com/AgustinBerna/experimentos-colaborativos
(referencia: commit `27d9d941f47b3b0eeaa7c724990baf5361613ce8`).
Exp2 es la corrida que en la VM se llamó Exp3, con indicadores, lags y deltas.

## Protocolo

| Condición | Exp1 | Exp2 actual |
|---|---|---|
| Selección heredada de E0 | propia de Exp1 | propia de Exp2/Exp3 |
| Árboles fijos | 280 | 361 |
| N seleccionado en agosto | 4323 | 4352 |
| Variables | 750 | 1500 |
| Semillas | las 30 originales | las mismas 30 |
| Train final | marzo–agosto 2019 | marzo–agosto 2019 |
| Test | octubre 2019 | octubre 2019 |

No hay nueva búsqueda de hiperparámetros, selección de N ni early stopping.
Los cinco hiperparámetros ganadores se leen de `referencia/exp*/seleccion.json`.
Los config.json de referencia se conservan sin cambiar su lista histórica de métodos.

E7 reemplaza null y NaN por **0 en las 150 variables base**, después de la
auditoría original y antes de generar sus lags/deltas. Conserva los ceros y
otros valores observados. No ajusta ningún imputador y no usa información
futura para decidir los reemplazos.

Se reutilizan literalmente los generadores de variables de cada corrida:
los lags base usan desplazamiento de filas por cliente; en Exp2 los indicadores
usan mes calendario exacto. **La falta de historia para un lag sigue siendo null**;
no se rellena con cero una segunda vez después de generar lags. Los 150
indicadores originales y sus 600 derivados de Exp2 se conservan y no se imputan.
`tmobile_app` y `cmobile_app_trx` continúan excluidas.

Se fija LightGBM **4.5.0** en un entorno virtual separado. Esto es la versión
exigida por el paquete; no prueba qué versión estaba efectivamente instalada
en las corridas anteriores, que no registraron todas sus dependencias.
La nueva identidad guarda Python, plataforma y versiones instaladas. Se usa
CPU con 7 hilos por defecto. No se requieren miceforest, Optuna ni R para E7.
`entorno_reproducible.txt` registra también las dependencias efectivamente
instaladas. En una VM nueva, conservar la versión de Python e instalar ese
archivo con `.venv/bin/python -m pip install -r /ruta/entorno_reproducible.txt`
antes de reanudar si las versiones disponibles cambiaron.

## Archivos de origen necesarios en la VM

Las dos carpetas completas de trabajo de las corridas anteriores, con:

- `run_identity.json`.
- `E0/optimization/seleccion.json`.
- `partition/panel_2019.parquet` auditado y sin imputar.
- `E0/prepared/train.parquet` y `E0/prepared/test.parquet`.
- Los cuatro CSV originales en `resultados/`.

El programa busca una corrida inequívoca de cada experimento a poca profundidad
en `/home/ds` y `/home/ds/buckets/b1/exp`. Prefiere una copia local completa.
Valida hashes de configuración y del generador, selección exacta, semillas,
meses, columnas y alineación de clientes/etiquetas antes de evaluar E7.
No modifica esos archivos ni reentrena E0–E6.

## Ejecutar en GCP

Subir `E7_ceros_GCP.zip` a `/home/ds` usando JupyterLab. En una terminal:

```bash
cd /home/ds
python3 -m zipfile -e E7_ceros_GCP.zip e7_ceros_codigo
tmux new -s e7_ceros
```

Dentro de tmux:

```bash
bash /home/ds/e7_ceros_codigo/E7_ceros_GCP/run_gcp.sh \
  --gcs gs://agustinberna343_buckito2026/exp/e7_ceros_exp1_exp2_run01
```

El script crea su propio `.venv`, instala dependencias y ejecuta los tests antes
de la corrida. No cambia `/home/ds/.venv`. Si la creación de venv no está disponible
en el Python elegido, usar otro intérprete con `E7_PYTHON=/ruta/python3 bash ...`.
Trabajar en disco local; la generación de variables de Exp2 requiere bastante
RAM y espacio, por lo que conviene usar la VM de 96 GB de las corridas anteriores.

Si la búsqueda no encuentra una carpeta única, indicar las rutas concretas:

```bash
bash /home/ds/e7_ceros_codigo/E7_ceros_GCP/run_gcp.sh \
  --exp1 /RUTA/REAL/DE/LA/CORRIDA/EXP1 \
  --exp2 /home/ds/exp3_indicadores_lags_deltas_optuna_run01 \
  --gcs gs://agustinberna343_buckito2026/exp/e7_ceros_exp1_exp2_run01
```

`--exp1` apunta a la **carpeta de trabajo con resultados**, no al código ni al ZIP.
La ruta de Exp1 no se inventa: se busca por su identidad y selección publicadas.
Se puede omitir `--gcs` para ejecutar y guardar únicamente en disco local.

Separarse de tmux sin detener: `Ctrl+B`, después `D`. Volver:
`tmux attach -t e7_ceros`. Ver el avance desde otra terminal:

```bash
tail -f /home/ds/e7_ceros_exp1_exp2_run01/main.log
```

## Reanudar

Con el disco local conservado, ejecutar el mismo comando. Verifica identidad,
archivos y predicciones y reutiliza las semillas completadas. No cambiar código,
selecciones, hilos o versiones a mitad de una corrida.

Si se perdió el directorio de trabajo local y se guardaron checkpoints en GCS:

```bash
bash /home/ds/e7_ceros_codigo/E7_ceros_GCP/run_gcp.sh \
  --restore \
  --gcs gs://agustinberna343_buckito2026/exp/e7_ceros_exp1_exp2_run01
```

`--restore` exige que `--work` (por defecto `/home/ds/e7_ceros_exp1_exp2_run01`)
esté vacío o no exista. Los archivos originales de Exp1/Exp2 también deben
seguir disponibles. Sólo restaura el prefijo nuevo de E7. Los parquets preparados
de E7 se reconstruyen localmente; sus predicciones terminadas no se reentrenan.
Se guarda cada predicción y su marcador al terminar cada semilla. No hay rsync
de las corridas antiguas ni subida de sus datasets. Tras restaurar un disco nuevo
puede volver a copiar los checkpoints pequeños de E7 para reparar subidas.

## Dashboard y faltantes

Se generan `exp1/exp1.html` y `exp2/exp2.html`, autocontenidos, con los ocho
métodos. El panel de variables rotas se reemplaza por porcentaje de NaN por
variable: tabla completa con buscador, comparación train/test y barras de las
20 variables con más ausencia. No requiere conexión a librerías externas.

`porcentaje_na_train_test.csv` cuenta null y NaN antes de imputar, sobre las 150
variables base conservadas y todas las filas de train marzo–agosto y test octubre.
Se calcula `100 * faltantes / filas`, no el promedio simple de porcentajes
mensuales. No incluye indicadores ni lags/deltas. La auditoría previa se conserva.

La ganancia del ensamble se calcula sobre el promedio de las 30 probabilidades.
Los CSV incluyen métricas individuales y ensamble. Se recalculan Wilcoxon pareado
por semilla y Holm para **siete** alternativas frente a E0, por métrica. Los
p-valores describen variación entre semillas y no prueban generalización temporal
ni significación de la ganancia del ensamble.

## Archivo para devolver y actualizar GitHub

Al finalizar se imprime `LISTO` y se obtiene:

```text
/home/ds/e7_ceros_exp1_exp2_run01/resultados_E7_exp1_exp2.zip
```

Con `--gcs` también queda en:

```text
gs://agustinberna343_buckito2026/exp/e7_ceros_exp1_exp2_run01/resultados_E7_exp1_exp2.zip
```

Descargar y pasar **ese ZIP**. Incluye ambos HTML, cuatro CSV comparativos por
experimento (240 filas de métricas por semilla y 8 de ensamble), porcentajes de
NaN, selección, configuración, auditoría, hashes y código. Incluye probabilidades
del ensamble E7 con ordinales anónimos de clientes compatibles con el ZIP anterior
de bootstrap; esas predicciones son para el análisis y **no para publicarlas
automáticamente en GitHub**. Los modelos y predicciones individuales quedan
en la VM; los npy individuales de E7 también se respaldan en GCS si se indicó.

La actualización pública se hace con los resultados reales después de esta
corrida. Este paquete no contiene resultados de E7 sobre el dataset real.
