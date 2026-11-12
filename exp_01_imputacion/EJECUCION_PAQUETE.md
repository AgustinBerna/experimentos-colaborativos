# Exp1: entrenamiento marzo–agosto 2019

Train: 201903–201908 inclusive. Test: 201910. Agosto pasa a train; no se valida sobre agosto.
Mismos siete métodos E0–E5 y E06, 30 semillas, hiperparámetros, 280 árboles y N=4323.
Sin optimización ni early stopping. Los imputadores se ajustan al nuevo train con sus
configuraciones y semillas originales. Se mantienen las exclusiones de variables originales.
seleccion.json es la selección histórica de Exp1; sus métricas no corresponden a esta corrida.

## Ejecutar en GCP (VM Linux)

Usar el mismo entorno Python de Exp1; requirements.txt conserva las versiones originales.
Desde esta carpeta:

```bash
python -m pip install -r requirements.txt
python run_pipeline.py --data /ruta/competencia_02_crudo.csv --work /ruta/exp1_marzo_agosto --step auditar
python run_pipeline.py --data /ruta/competencia_02_crudo.csv --work /ruta/exp1_marzo_agosto --step particionar
python run_pipeline.py --data /ruta/competencia_02_crudo.csv --work /ruta/exp1_marzo_agosto --step preparar
python run_pipeline.py --data /ruta/competencia_02_crudo.csv --work /ruta/exp1_marzo_agosto --step modelar
```

Opcional: agregar --remote gs://TU_BUCKET/exp1_marzo_agosto a cada comando para checkpoints
en GCS (requiere gcloud autenticado). Usar --work y prefijo remoto NUEVOS.
Repetir comandos permite reanudar la ejecución.

El CSV debe incluir enero–diciembre: enero/febrero para lags y noviembre/diciembre
para etiquetar octubre. Septiembre aporta historia para octubre sin entrar al train.
Resultados CSV y predicciones por semilla quedan en --work con el formato original.

Dashboard opcional: instalar R, ejecutar Rscript install_r_packages.R y el pipeline
con --step dashboard. --step all incluye dashboard y requiere R.

Fuente: AgustinBerna/experimentos-colaborativos, main descargado el 11/11/2026.
No se incluyen datos ni resultados nuevos. El repositorio original advierte que no
certifica por hash la identidad de su código con la corrida publicada.

