# Publicación y revisión en GitHub

Actualizado: 2026-11-12.

## Estado actual

- Repositorio: peromingo/rp2040-fan-control.
- Rama de trabajo y canal preview: source-tree-review; rama predeterminada: main.
- [Prerelease v0.8.0-source-rc2](https://github.com/peromingo/rp2040-fan-control/releases/tag/v0.8.0-source-rc2) publicada con PLG y checksum descargados y verificados.
- [PR de revisión #1](https://github.com/peromingo/rp2040-fan-control/pull/1) abierta en borrador en la revisión de este documento; no se ha fusionado main.
- Código, README y documentación posteriores pueden avanzar sin cambiar el tag ni los adjuntos ya publicados.

La evidencia vigente está en [VALIDATION-STATUS.md](VALIDATION-STATUS.md). El informe de noviembre sobre auditfix21 es histórico y no define los pendientes de RC2.

## Generación y verificación

La vía actual es tools/build_integration_plg.py, no los prototipos históricos de renderizado. El generador utiliza las fuentes, las plantillas transaccionales y pyserial fijado por hash. El README contiene los comandos y la opción de wheel sin conexión.

La variante distribuida se prepara con tools/prepare_update_manifest.py: añade pluginURL y normaliza el nombre interno. Su verificación exige el hash del paquete fuente y rechaza cambios fuera de esos metadatos. Consulta [SOURCE-PACKAGE-REVIEW.md](SOURCE-PACKAGE-REVIEW.md).

CI comprueba Python 3.11/3.12, PHP/shell, contratos y simulaciones, auditoría estructural, correspondencia del payload y generaciones reproducibles. Las ejecuciones de referencia están enlazadas en el resumen de validación. Para aprobar cambios nuevos, comprueba todos los trabajos del commit correspondiente, incluidos los omitidos o cancelados.

## Pruebas del plugin cerradas

- Instalación limpia del RC2 publicado con configuración inicial y servicio deshabilitado.
- Desinstalación y reinstalación del RC2 fuente, con los mismos scripts ejecutables que la variante publicada.
- Conservación de configuración/logs y ausencia de recuperación pendiente.
- Arranque con ENABLE y reinicio real sin ENABLE.
- Actualización real RC1 → RC2 desde Plugins, conservando exactamente la configuración.
- Flujo WebUI/IPC, modos, puerto serie y comunicación con el RP2040 en el montaje probado.
- Comprobación visual de actualizaciones y verificación de los adjuntos publicados.

Estos resultados no certifican una instalación nueva del sistema operativo ni todas las versiones de Unraid. Python y smartctl siguen siendo requisitos externos; pyserial va incluido.

## Revisiones que siguen pendientes

- [ ] Revisar el diff completo contra main y la lista de archivos.
- [ ] Confirmar procedencia, autoría y derechos de publicación de fuentes, módulos recuperados y firmware.
- [ ] Revisar manualmente seguridad y privacidad; la auditoría estructural no sustituye una revisión de secretos o de contenido.
- [ ] Revisar compatibilidad y dependencias para las plataformas que se vayan a anunciar.
- [ ] Completar desconexión/reconexión del RP2040 real y pérdida de fuentes térmicas, con observación del comportamiento físico.
- [ ] Resolver hallazgos, revisar la PR y decidir su integración.
- [ ] Preparar y verificar un canal estable y sus notas de publicación.

Las exclusiones de configuración local, logs, cachés, .env y dist/ están implementadas. Su existencia y los resultados automáticos se consideran comprobados; la revisión manual final de todo el contenido sigue pendiente. La licencia MIT está incluida, pero no sustituye la confirmación de derechos de cada componente.

## Procedimiento para futuras publicaciones

1. Identificar el commit revisado y ejecutar su CI completa.
2. Generar el PLG desde sus fuentes; verificar payload, scripts y dependencia fijada.
3. Preparar los metadatos del canal elegido y comprobar su URL antes de distribuir el PLG.
4. Repetir las pruebas afectadas por cambios de comportamiento; actualizar el resumen de validación sin incluir datos privados.
5. Crear el tag en el commit revisado y adjuntar únicamente el PLG y su checksum correspondientes.
6. Usar la marca prerelease mientras no se haya aprobado la promoción a estable.
7. Descargar los adjuntos publicados y verificar hash, versión, nombre interno y URL.

No reutilices un nombre de versión para cambiar un ejecutable ya publicado. Las correcciones de documentación en la rama no deben mover el tag de RC2.

## Canal de actualizaciones

RC2 consulta plugin/channels/preview/ mediante una URL persistente en source-tree-review. Esa rama debe conservarse mientras haya instalaciones que la utilicen. main no debe convertirse implícitamente en el canal estable ni borrarse la rama preview al fusionar una PR.

Comprobar actualizaciones no inicia ni reinstala el daemon. Instalar una actualización exige detener el servicio y retirar ENABLE mediante el auxiliar. La instalación conserva los ajustes y requiere un arranque explícito posterior.

## Referencias

- [Lista de tareas](PUBLICATION-CHECKLIST.md).
- [Estado de validación y límites](VALIDATION-STATUS.md).
- [Diseño del instalador actual](INSTALLER-DESIGN.md).
- [Notas de RC2](releases/v0.8.0-source-rc2.md).
