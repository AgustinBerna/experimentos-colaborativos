# Procedencia

| Autoría | Fuente conservada en la cuenta | Commit de referencia |
|---|---|---|
| Agustín | [experimentos-colaborativos](https://github.com/AgustinBerna/experimentos-colaborativos) | e1807e2285109014778874c156ae46a0173854af |
| Micaela | [experimentos-colab-mica](https://github.com/AgustinBerna/experimentos-colab-mica), fork de [micaelarr/experimentos-colab](https://github.com/micaelarr/experimentos-colab) | b4f92dc83ace1a068393c661ecf71c0e9e32d73a |
| Florencia | [experimento-colab-flor](https://github.com/AgustinBerna/experimento-colab-flor), fork de [FlorRodriguez1309/experimento-imputacion-ff-cero](https://github.com/FlorRodriguez1309/experimento-imputacion-ff-cero) | 3d911b03b401100aeb4c72b32aec36fe5e59b790 |

Los CSV fuente mantienen sus nombres y valores. No se atribuyen corridas ajenas como nuevas. La verificación de controles coincidentes cubre las diez métricas compartidas por semilla y las métricas de ensamble. Ocho duplicaciones equivalentes a 240 filas se retiraron de la tabla consolidada.

Para descargar también el código original de los forks con sus historiales:

```bash
git clone --recurse-submodules https://github.com/AgustinBerna/experimentos-colaborativos.git
```

Los submódulos fijan una versión; no se actualizan automáticamente al cambiar las ramas de los forks. La consolidación no necesita esos submódulos para reproducir los resultados agregados.
