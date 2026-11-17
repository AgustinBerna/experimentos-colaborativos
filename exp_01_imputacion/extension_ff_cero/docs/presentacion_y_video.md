# Extensión de Exp1: forward fill + cero

## FF + cero

**Pregunta.** Después de copiar el último dato conocido de cada cliente, ¿conviene completar con cero los faltantes residuales?

**Diseño.** Exp1, train marzo–agosto de 2019, test octubre, 280 árboles, N = 4.323 y 30 semillas comunes. Se compararon E0, E4, FF_ZERO y el control FF + mediana, con mediana calculada después de FF. No hubo nueva optimización.

**Resultado.** Ganancia media: E0 290,06 M, E4 291,34 M, FF_ZERO 291,42 M y FF + mediana 292,48 M. FF_ZERO mejora AUC frente a E0 y E4 (p Holm 0,000566 y 0,002076). Las diferencias de ganancia no son concluyentes (p Holm 0,116; 0,918; 0,360).

**Ensamble.** FF_ZERO logra 295,82 M, AUC 0,938077 y 377 BAJA+2. Es un resultado distinto de la ganancia media por semilla.

**Comparabilidad.** Se armonizó la definición del control: mediana de train después del forward fill. La tabla combina 90 entrenamientos locales y 30 evaluaciones publicadas del control; E0/E4 coinciden por semilla. La armonización ocurrió después de ver los resultados.

**Alcance.** Las semillas repiten el modelo sobre un mismo mes. Estos resultados no prueban una mejora estable en otros períodos. FF + cero tampoco equivale a rellenar directamente todos los faltantes con cero.

## Guion de aproximadamente un minuto

Esta extensión del experimento evaluó qué hacer con los faltantes que siguen vacíos después de forward fill. Forward fill toma el último valor conocido del mismo cliente, pero a veces no hay un dato previo para esa variable. En esos casos se completó con cero.

Se mantuvo la configuración de Exp1: entrenamiento de marzo a agosto, evaluación en octubre, 280 árboles, 4.323 contactos y las mismas 30 semillas. La ganancia media de FF + cero fue 291,42 millones, casi igual a los 291,34 millones de forward fill solo.

El AUC mejoró frente a dejar los NaN y frente a forward fill, pero la diferencia de ganancia no fue concluyente después de ajustar las comparaciones. El ensamble llegó a 295,82 millones, aunque ese único resultado no demuestra una mejora estable.

El control calcula la mediana de train después del forward fill. Se usaron 30 evaluaciones publicadas, tras comprobar la coincidencia de los baselines por semilla. La mediana alcanzó 292,48 millones, pero la diferencia con cero tampoco fue concluyente. La conclusión es que completar con cero puede mejorar el ordenamiento sin garantizar mayor ganancia.

## Sesgos y controles para el grupo

- Sesgo de confirmación: acordar comparaciones y mostrar también resultados sin mejora. En esta corrida, conservar la configuración después de observar octubre.
- Selección favorable a E0: interpretar cada familia bajo hiperparámetros elegidos para E0, no como el máximo rendimiento posible de cada imputador.
- Múltiples comparaciones: informar el ajuste de Holm y distinguir AUC de ganancia y modelos individuales de ensambles.
- Dependencia de la evaluación: las semillas comparten clientes y mes. Validar en nuevos cortes temporales antes de generalizar.

## Pendientes de la entrega

Según el cronograma compartido por el grupo el 17 de noviembre de 2026:

- Video del experimento: 23 de noviembre de 2026. Falta coordinar las intervenciones y grabarlo.
- Defensa presencial del experimento: 24 de noviembre de 2026.
- Presentación del pipeline grupal y examen oral: 10 de diciembre de 2026.
- Video individual de Michelina: 13 de diciembre de 2026.

La imputación directa con cero propuesta por Agustín es otra variante. No se la presenta como corrida terminada ni se le atribuyen resultados sin evidencia.
