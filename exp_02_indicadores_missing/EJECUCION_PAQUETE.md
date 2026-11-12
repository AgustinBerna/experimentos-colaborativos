# Exp2: indicadores de ausencia, entrenamiento final marzo–agosto 2019

Esta variante conserva la selección publicada del Exp2 original y amplía únicamente el entrenamiento final.
- Train final: marzo–agosto de 2019 inclusive. Test: octubre de 2019.
- Sin nueva optimización, early stopping ni selección de N.
- Mismos hiperparámetros publicados de Exp2, 232 árboles, N=4000 y 30 semillas.
- E0 (NaN), E1 (media), E2 (mediana), E3 (moda), E4 (forward fill), E5 (Ridge) y E06 (miceforest).
- Los imputadores se reajustan sobre marzo–agosto con sus algoritmos, configuraciones y semillas originales.
- Indicadores __ausente calculados antes de imputar, intactos y sin lags/deltas propios.
- El esquema de variables se conserva: exclusiones determinadas con marzo–junio, como en la selección original.
- Agosto queda en train; valid.parquet queda vacío por compatibilidad y no se lee al modelar.
- seleccion.json está intacto; sus métricas corresponden a la validación histórica de agosto del Exp2 original.

## Ejecutar en tu VM después de Exp1

Subir Exp2_indicadores_marzo_agosto_GCP.zip a /home/ds/buckets/b1/exp.
Desde una terminal, cuando finalice Exp1:

```bash
mkdir -p /home/ds/exp2_marzo_agosto
unzip -o /home/ds/buckets/b1/exp/Exp2_indicadores_marzo_agosto_GCP.zip -d /home/ds/exp2_marzo_agosto
tmux new-session -s exp2_agosto
```

Dentro de tmux:

```bash
bash /home/ds/exp2_marzo_agosto/exp_02_indicadores_missing/ejecutar_gcp.sh
```

Usa el entorno ya instalado para Exp1, el mismo dataset completo y estas rutas nuevas:
- work: /home/ds/exp2_marzo_agosto_run01
- remote: gs://agustinberna343_buckito2026/exp/exp2_marzo_agosto_run01

No reutilizar el work o prefijo de Exp1. El script ejecuta --step all, incluyendo dashboard.
Para otro equipo: instalar requirements.txt y ejecutar Rscript install_r_packages.R antes del pipeline.
Repetir el script permite reanudar checkpoints. Salir de tmux: Ctrl+B y luego D.
La VM debe seguir encendida.

## Resultados

En work/resultados: métricas y curvas por semilla y ensamble, dashboard_comparativo.html
con carpeta lib y, si existe el comando zip, dashboard_comparativo_descargar.zip.
También se publican en el prefijo remoto al completar cada etapa.
No se incluyen resultados nuevos en este paquete.

CSV completo enero–diciembre de 2019: enero/febrero alimentan lags, septiembre aporta
historia para octubre, noviembre/diciembre permiten etiquetar octubre. Estos meses
fuera de marzo–agosto no se usan para entrenar.

Fuente: AgustinBerna/experimentos-colaborativos/exp_02_indicadores_missing, main,
descargado el 11/11/2026. SOURCE_MANIFEST.json registra los SHA de los archivos originales.
Como advierte el repositorio, no se certifica por hash que su código sea el ejecutado
en la corrida histórica publicada.

