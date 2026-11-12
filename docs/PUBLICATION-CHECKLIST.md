# Lista de pruebas y tareas de publicación

Actualizada: 2026-11-12. Estado actual: **0.8.0-source-rc2 publicada como prerelease**. Una casilla completada se limita al alcance indicado; no implica compatibilidad universal ni aprobación de una versión estable. La evidencia y los hashes públicos se resumen en [VALIDATION-STATUS.md](VALIDATION-STATUS.md).

## Implementación y paquete

- [x] Consolidar configuración JSON HDD/CPU, selección serie, WebUI y auxiliar privilegiado en el árbol fuente.
- [x] Generar el PLG instalable desde las fuentes y las plantillas revisables.
- [x] Verificar correspondencia del payload, permisos y scripts con sus fuentes.
- [x] Fijar pyserial 3.5 por SHA-256 y distribuirlo dentro del paquete.
- [x] Mantener la configuración local fuera de los archivos del payload distribuido.
- [x] Incluir el firmware de referencia y su hash sin grabarlo durante la instalación del plugin.
- [x] Implementar IPC mediante acciones limitadas del auxiliar y política sudoers, sin abrir permisos globales para PHP.

## Pruebas completadas

- [x] CI en Python 3.11 y 3.12, sintaxis PHP/shell y contratos IPC/configuración/bloqueo.
- [x] Auditoría estructural y comparación de generaciones reproducibles.
- [x] Instalación limpia del plugin RC2 publicado con estado inicial deshabilitado.
- [x] Desinstalación y reinstalación del RC2 fuente; scripts idénticos a la variante publicada.
- [x] Conservación de configuración y logs en el ciclo de reinstalación.
- [x] Arranque automático con ENABLE y reinicio real sin ENABLE.
- [x] Actualización RC1 → RC2 mediante Plugins, conservando exactamente la configuración.
- [x] Modos de ventilación, botón, OLED y comunicación serie con RP2040 en el montaje probado.
- [x] Guardado de configuración, selección serie y estado en directo de la WebUI.
- [x] Comprobador de actualizaciones y corrección del nombre interno del plugin.
- [x] Descarga de los adjuntos de la prerelease y verificación del checksum.

## Pruebas aplazadas

- [ ] Desconexión/reconexión del RP2040 real y comprobación física del comportamiento de los ventiladores.
- [ ] Pérdida parcial y total de fuentes térmicas de un grupo y comprobación del fallback físico.

## Repositorio y documentación

- [x] Repositorio y rama de trabajo publicados; CI ejecutada en GitHub.
- [x] Licencia MIT incluida, pendiente de confirmar los derechos de todos los componentes.
- [x] Guías de contribución y seguridad, plantilla de incidencias y exclusiones de archivos locales incluidas.
- [x] README en español, fotografías de referencia y tabla de pines/comunicaciones.
- [x] Documentación de validación y tareas actualizada, con históricos separados del estado actual.
- [x] Prerelease v0.8.0-source-rc2 publicada con PLG y checksum verificados.

## Revisión y promoción a estable

- [ ] Confirmar autoría, procedencia y derechos de publicación de todo el código y firmware.
- [ ] Revisar manualmente seguridad, privacidad y archivos comprometidos, además de la auditoría automática.
- [ ] Revisar compatibilidad y dependencias para las plataformas que se anuncien como soportadas.
- [ ] Completar los dos ensayos de hardware aplazados.
- [ ] Revisar la PR y decidir su integración en main.
- [ ] Definir y verificar la URL del canal estable, su versión y sus notas de publicación.

La comprobación de CI debe repetirse sobre el commit que se vaya a aprobar. Ni la prerelease ni esta lista autorizan por sí mismas una promoción a estable.
