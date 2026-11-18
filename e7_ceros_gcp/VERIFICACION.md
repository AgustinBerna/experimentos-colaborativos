# Verificación local

- 7 tests: reemplazo null/NaN por cero, conservación de valores observados e
  indicadores, protocolos temporales originales, ausencia de uso del futuro,
  porcentaje ponderado por filas, ganancia y desempate por ID, Holm con siete
  alternativas y copia a GCS sólo de archivos nuevos o modificados.
- Prueba integral con datos **sintéticos**: 60 ajustes LightGBM usando las dos
  selecciones originales y sus 30 semillas, comprobación de 240 métricas por
  semilla y 8 filas de ensamble por experimento, 150 porcentajes de ausencia,
  modelos de 750/1500 variables y ZIP con verificación CRC.
- Reanudación comprobada: 60 checkpoints reutilizados, sin ejecutar nuevamente
  LightGBM y sin cambiar las predicciones. Hashes de los orígenes sin cambios.
- HTML de ambos experimentos ejecutado en Chrome: ocho métodos, siete gráficos,
  tabla completa de 150 variables; captura visual revisada.

Estas pruebas verifican el programa, **no son resultados experimentales**. Los
datos sintéticos de verificación no se incluyen en este paquete ni se publican.
La corrida sobre el dataset real debe ejecutarse en la VM.
