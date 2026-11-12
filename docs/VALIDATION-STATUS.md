# Estado de validación y tareas pendientes

Actualizado: 2026-11-12. Versión de referencia: **0.8.0-source-rc2**, publicada como [prerelease](https://github.com/peromingo/rp2040-fan-control/releases/tag/v0.8.0-source-rc2). Este documento resume el estado actual; los informes de candidatos anteriores conservan su alcance histórico.

## Alcance de la evidencia

Se distinguen las comprobaciones automáticas del repositorio y los resultados funcionales comunicados por el mantenedor durante las pruebas manuales. Estas últimas se realizaron en un entorno con RP2040 y en otro de pruebas sin RP2040. No constituyen una certificación de compatibilidad con todas las versiones de Unraid, revisiones de placa o situaciones de fallo.

Este resumen no incluye logs, capturas de los servidores, direcciones de red, nombres de equipos, identificadores de discos, PID ni hashes de configuraciones locales. Los hashes siguientes identifican exclusivamente paquetes públicos.

## Paquetes de referencia

| Paquete | SHA-256 | Alcance |
| --- | --- | --- |
| RC2 generado desde el código fuente | `1bfa566f2d378fe25831b87dae5c4753ba095c65cdfe058d007d5cbce935d273` | Base de las pruebas del candidato RC2. |
| RC2 publicado con metadatos preview | `117be7d210f87bb6041089835d142efd8455f7590edb462ace5928c27400bdfa` | PLG de la prerelease; usado en la instalación limpia y como destino de la actualización desde Plugins. |
| RC1 original | `69c17dbf3daad74054eaa5f7da914f8156f140fc252cedb0b986ea8cd4971065` | Versión anterior real utilizada para preparar el origen de la prueba de actualización. |
| RC1 adaptado para probar la actualización | `f68b683cf5bb6303ff4b2a65b9f3d4ac09ad1c5fa6e83ce8f52fbc809c00f1bd` | Conserva versión, payload y bloques ejecutables de RC1; adapta únicamente nombre interno y pluginURL. No es una release adicional. |

Nombre de archivo conservado: `rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg`. La versión se obtiene de la cabecera PLUGIN, no del nombre del archivo.

El RC2 publicado añade pluginURL y normaliza el nombre interno a `rp2040-fan-control`. El verificador comprueba que revertir solo esos metadatos restaura exactamente el RC2 fuente. Sus scripts y payload son idénticos; no se atribuye a los candidatos históricos auditfix21–24 la correspondencia del nuevo generador.

## Comprobaciones automáticas

Las ejecuciones de CI del [commit de referencia](https://github.com/peromingo/rp2040-fan-control/commit/6e25bf52dc77eed4ac4c90c7812d9b249f3a52d1) finalizaron correctamente: [ejecución de push](https://github.com/peromingo/rp2040-fan-control/actions/runs/43230283238) y [ejecución de PR](https://github.com/peromingo/rp2040-fan-control/actions/runs/43230293498). Cada matriz incluye Python 3.11 y 3.12. Las futuras revisiones deben comprobar la CI de su propio commit.

- [x] Compilación de sintaxis Python y validación de sintaxis PHP y shell.
- [x] Pruebas unitarias y contratos de configuración, bloqueo de instancia, IPC, publicación concurrente y formularios PHP.
- [x] Generación del PLG desde las fuentes y las plantillas de instalación/desinstalación.
- [x] Dependencia pyserial 3.5 fijada por SHA-256 y correspondencia de archivos y permisos del payload.
- [x] Comparación de generaciones reproducibles y auditoría estructural del árbol y del payload.
- [x] Simulaciones de instalación, recuperación y arranque en sistemas de archivos temporales.
- [x] Verificación del delta de metadatos preview y de un nombre interno válido para los selectores de Unraid.

Las simulaciones no sustituyen a un fallo físico del RP2040 ni a una revisión manual de seguridad.

## Comprobaciones manuales completadas

| Prueba | Resultado y límite |
| --- | --- |
| Instalación del candidato RC2 | Instalación completada sin arrancar el daemon ni crear ENABLE. |
| Desinstalación y reinstalación de RC2 | Reversión verificada; configuración y logs, incluidos los rotados, conservados; sin recuperación pendiente. La prueba se hizo sobre RC2 fuente, cuyos scripts son idénticos a los de la variante publicada. |
| Instalación limpia del RC2 publicado | Archivos anteriores apartados en una copia fuera del plugin; nueva copia base formada solo por entradas NEW/NEW_APP; configuración de ejemplo y servicio deshabilitado. |
| Dependencias en el entorno de prueba | Python, pyserial incluido y smartctl detectados; sintaxis PHP y sudoers correctas. No implica que Python venga instalado en cualquier Unraid. |
| Arranque con ENABLE presente | El gancho startup y un reinicio real restauraron el servicio; estado actualizado y comunicación serie disponible. |
| Reinicio con ENABLE ausente | Reinicio real confirmado por el tiempo de actividad; plugin y gancho disponibles, sin ENABLE ni proceso del daemon y sin recuperación pendiente. |
| Actualización RC1 → RC2 desde Plugins | La WebUI ofreció RC2; tras actualizar, versión y hash del PLG correctos, configuración JSON idéntica, servicio detenido y ENABLE ausente. |
| Guardado de configuración | Asignaciones HDD/CPU persistentes y selección de puerto serie comprobadas. |
| WebUI y estado en directo | Página operativa, datos actualizados mediante el endpoint PHP directo y presentación de ventiladores corregida. |
| Modos y controles físicos | AUTO/SILENT/TURBO, botón de cambio de modo y apagado/encendido de OLED comprobados funcionalmente. Sin medición de RPM ni ACK del firmware. |
| Comunicación con RP2040 real | Puerto serie abierto mediante una ruta estable, estado conectado y envío de comandos. No equivale a una prueba de desconexión física. |
| Comprobador de actualizaciones | Descarga y comparación de versión correctas; estado visual actualizado tras corregir el nombre interno con espacios. |
| Publicación | Prerelease, tag y commit revisado correctos; ambos adjuntos descargados y checksum verificado. |

La instalación limpia se refiere al plugin, no a una instalación nueva del sistema operativo. La retirada manual del candidato antiguo para preparar esa prueba no se contabiliza como validación de su desinstalador.

## Ensayos de hardware aplazados

- [ ] Desconectar y reconectar el RP2040 real: registrar detección, avisos, reconexión y comportamiento físico de los ventiladores.
- [ ] Pérdida de fuentes térmicas: comprobar una fuente ausente y un grupo sin ninguna lectura válida, incluida la salida física ordenada.

Las pruebas previas con un puerto virtual y los contratos automáticos no cierran estos dos ensayos. El watchdog y el fallback presentes en el código no se presentan como comprobados físicamente en esos escenarios.

## Pendientes para una versión estable

- [ ] Completar los dos ensayos anteriores.
- [ ] Revisar el diff completo, procedencia, autoría, licencia, seguridad y privacidad del contenido publicable.
- [ ] Completar la revisión de compatibilidad y de dependencias para las plataformas que se anuncien como soportadas.
- [ ] Revisar la PR y decidir la integración en main; la actualización de documentación no constituye una aprobación de merge.
- [ ] Definir y verificar el canal estable de actualizaciones y preparar su versión y notas de publicación.

La limpieza de candidatos y borradores antiguos es opcional. Debe conservar las referencias necesarias para reproducir o revisar las pruebas. Mientras los plugins instalados utilicen el canal preview, la rama source-tree-review debe seguir disponible.

## Límites permanentes de la interfaz actual

- El firmware no devuelve ACK: la confirmación de modo corresponde al daemon y a una escritura serie completada.
- Los porcentajes son comandos de salida; no son RPM medidas por tacómetro.
- La auditoría estructural automatizada no certifica ausencia de secretos ni derechos de publicación.

Consulta también la [lista de tareas de publicación](PUBLICATION-CHECKLIST.md), el [procedimiento de publicación](GITHUB-PUBLICATION.md) y la [revisión de correspondencia del paquete](SOURCE-PACKAGE-REVIEW.md).
