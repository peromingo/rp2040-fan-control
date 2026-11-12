# Base histórica de las fuentes y sus límites

Este documento conserva la procedencia de la recuperación inicial. El estado del paquete RC2 publicado, sus comprobaciones y sus pendientes se mantienen en [VALIDATION-STATUS.md](VALIDATION-STATUS.md) y [SOURCE-PACKAGE-REVIEW.md](SOURCE-PACKAGE-REVIEW.md).

## Firmware de referencia

firmware/rp2040/main.py contiene el firmware de referencia recuperado para revisión. Su hash público se conserva en firmware/rp2040/README.md. La instalación del plugin no lo graba en el RP2040.

## Origen del daemon

El árbol público parte de una copia adaptada: las asignaciones de discos de cada instalación se trasladaron a configuración local y las rutas se hicieron configurables. Los archivos privados originales y sus huellas no se utilizan como evidencia pública de esta publicación.

## Comparación inicial del paquete

El paquete recuperado contenía diez módulos Python. En la comparación inicial, nueve coincidían con el archivo de revisión y config.py difería por la sustitución de rutas fijas por rutas configurables. Este resultado histórico no sustituye la verificación del paquete consolidado actual.

## Estado vigente y límites

La base inicial fue el punto de partida de la consolidación. Actualmente existe un PLG fuente RC2 publicado como prerelease y pruebas de su ciclo de instalación y servicio. Esto no convierte los archivos recuperados originales ni los candidatos históricos en el artefacto actual.

Siguen pendientes los ensayos físicos de desconexión/pérdida de fuentes, la revisión final y la promoción a estable. El resumen vigente evita trasladar pendientes históricos a RC2 y limita las afirmaciones al alcance comprobado.
