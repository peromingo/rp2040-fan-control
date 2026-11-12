# Validación de 0.8.0-source-rc3

Fecha: 2026-11-13. Candidato para pruebas; RC2 sigue publicado y el canal preview
no se modifica durante la preparación de RC3.

## Cambios

- Recuperación de instalaciones mediante copia del estado inmediatamente anterior,
  independiente de la copia histórica usada al desinstalar.
- Bloqueo compartido entre instalación y desinstalación, con rechazo de operaciones
  concurrentes y de diarios pendientes de otros candidatos.
- Licencias completas MIT y BSD de pyserial dentro del payload instalado.
- Identidad `rp2040-fan-control` y URL de comprobación incluidas desde el constructor.
  El nombre del archivo PLG se conserva para actualizar el plugin ya registrado.

El firmware, el protocolo serie, las curvas térmicas, los modos de ventilación y la
configuración de cada equipo no se modifican. No se inicia el servicio durante una
instalación manual. No se graba firmware ni se modifica `/boot/config/go`.

## Comprobaciones automáticas

Las pruebas en raíz temporal ejecutan los bloques reales del paquete y comprueban:
restauración de bytes y permisos tras un fallo con copia histórica existente,
limpieza de una instalación inicial fallida, recuperación tras SIGKILL,
conservación del diario si falla la propia restauración, bloqueo de operaciones
concurrentes, rechazo de diarios ajenos y licencias instaladas completas.
Se mantienen las pruebas de arranque simulado, dependencias, IPC, configuración,
WebUI y correspondencia del payload con sus fuentes. PHP se valida en la CI Linux.

Estas pruebas no simulan la pérdida física de alimentación ni sustituyen las pruebas
en Unraid. El resultado definitivo de CI se consulta en el commit del candidato.

## Pendiente en Unraid

1. NAS de pruebas: actualizar RC2 a RC3 con el daemon detenido y ENABLE ausente;
   comparar configuración y selección serie antes/después, validar PHP y sudoers.
2. Desinstalar/reinstalar RC3, comprobando configuración y logs conservados,
   eliminación/restauración del evento startup y ausencia de recuperación pendiente.
3. Reiniciar sin ENABLE y confirmar que sigue detenido. En el equipo con RP2040,
   comprobar después el arranque habilitado, puerto serie, modos y refresco WebUI.
4. Completar las pruebas físicas aplazadas de desconexión/reconexión serie y pérdida
   de fuentes térmicas antes de declarar una versión estable.

No se deben ejecutar fallos inyectados ni SIGKILL de estas pruebas automáticas sobre
el servidor: se realizan exclusivamente en directorios temporales aislados.
