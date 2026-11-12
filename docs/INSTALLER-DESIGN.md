# Diseño del instalador de Unraid

Actualizado: 2026-11-12. El PLG **0.8.0-source-rc2** está publicado como prerelease y su ciclo de instalación, actualización, desinstalación y arranque tiene el alcance descrito en [VALIDATION-STATUS.md](VALIDATION-STATUS.md).

## Implementación actual

tools/build_integration_plg.py genera el instalador autocontenido a partir de src/unraid, plugin/src, plugin/scripts y las plantillas de plugin/templates. El payload incluye pyserial 3.5 fijado por SHA-256 y un manifiesto de construcción. El verificador compara archivos, permisos y bloques ejecutables con sus fuentes.

tools/prepare_update_manifest.py prepara la variante preview publicada, modificando solo nombre interno y pluginURL. La versión y los bloques ejecutables se conservan. Los prototipos plugin/rp2040-fan-control.plg.in, tools/render_unraid_plg.py y tools/build_unraid_payload.sh se mantienen como referencia histórica; no son la vía de generación de RC2.

## Rutas

| Elemento | Ruta |
| --- | --- |
| WebUI y evento startup | `/usr/local/emhttp/plugins/rp2040-fan-control/` |
| Wrapper de servicio | `/usr/local/sbin/rp2040-fan-control` |
| Auxiliar de acciones limitadas | `/usr/local/sbin/rp2040-fan-control-webui` |
| Política sudoers | `/etc/sudoers.d/rp2040-fan-control-webui` |
| Aplicación persistente y dependencia incluida | `/boot/config/plugins/rp2040-fan-control/app/` |
| Configuración y selección serie | `config.json`, `serial_port.conf` y `python-path` en la carpeta persistente del plugin |
| Logs y copias | `logs/` y `backup/` en esa carpeta |
| Estado IPC temporal | `/var/run/rp2040-fan-control/` |

El enlace estándar /var/run hacia /run se reconoce y valida. La numeración del puerto serie y los ajustes de cada instalación no forman parte del paquete público.

## Contrato de instalación y actualización

- Verificar el payload y las rutas antes de instalar; rechazar componentes simbólicos no admitidos.
- Capturar y comprobar la copia base; conservar un diario recovery-pending durante las operaciones que requieren recuperación.
- Preservar configuración local/JSON, selección serie y logs existentes; crear la configuración de ejemplo solo si falta.
- No arrancar durante una instalación manual. El servicio debe estar detenido y ENABLE ausente para actualizar una instalación existente.
- En el arranque de Unraid, permitir restaurar archivos ausentes de RAM conservando ENABLE; el evento startup decide si inicia.
- No grabar firmware, modificar /boot/config/go ni cambiar el estado del array.

## Desinstalación y recuperación

La desinstalación valida la copia base antes de parar el daemon, retira ENABLE y restaura los destinos anteriores o elimina los que el candidato había creado. Comprueba los destinos y sudoers antes de retirar el diario de recuperación. Conserva configuración, logs y copias.

Si hay recuperación pendiente, no debe borrarse el diario para forzar otra instalación. La recuperación depende de su origen y de la copia base verificada. Antes de intervenir, conserva una copia y revisa el diagnóstico del instalador de ese candidato; no ejecutes scripts de una versión distinta sobre un diario antiguo.

La limpieza manual del candidato antiguo realizada para preparar una instalación limpia es una operación de prueba separada, no el procedimiento normal de desinstalación de RC2.

## Dependencias y permisos

Python 3, smartctl y timeout deben estar disponibles en el sistema. El plugin incluye pyserial bajo app/vendor y no instala Python ni ejecuta pip sobre el sistema Unraid. Se han detectado correctamente las dependencias en el entorno de prueba; no se presupone su presencia en todos los equipos.

El wrapper ofrece check-deps, que informa del intérprete, la importación de pyserial y smartctl sin abrir el puerto del RP2040. RP2040_PYTHON permite elegir el intérprete de una invocación; python-path guarda una ruta absoluta y se lee como datos, no como código shell.

El directorio IPC nuevo usa modo 0750. Uno existente debe pertenecer a root y no permitir escritura de grupo/global. PHP utiliza un auxiliar con acciones limitadas y sudoers; no se concede escritura global para resolver el acceso.

## Pruebas y límites

Las pruebas temporales de instalación/recuperación/arranque y la CI se complementan con los ensayos manuales registrados. Instalación limpia, actualización desde Plugins y reinicio sin ENABLE están cerrados. La desinstalación/reinstalación se comprobó sobre RC2 fuente, con scripts idénticos a los de la variante publicada.

Quedan aplazadas las pruebas físicas de desconexión/reconexión del RP2040 y pérdida de fuentes térmicas. Las revisiones finales y el canal estable están en [PUBLICATION-CHECKLIST.md](PUBLICATION-CHECKLIST.md).
