# Control de ventiladores RP2040 SATA HAT para Unraid

Controlador y WebUI en desarrollo para regular ventiladores mediante un RP2040. El firmware no devuelve confirmaciones serie (ACK): un comando correcto confirma que el daemon ha aceptado la solicitud y completado la escritura por serie; no confirma las RPM físicas de los ventiladores.

El candidato de revisión generado desde el código fuente es **0.8.0-source-rc2**. Combina asignaciones persistentes de discos y CPU en JSON, selección del puerto serie, una WebUI con datos en directo, avisos sobre las fuentes térmicas y arranque automático opcional, con protección contra instancias duplicadas y diagnóstico del intérprete Python. No es una versión estable; la validación de este conjunto en el sistema de destino sigue en curso.

## Generar el PLG instalable para revisión

Con Python 3.11 o posterior:

```sh
python3 tools/build_integration_plg.py /tmp/rp2040-source-rc2
```

El generador descarga, si es necesario, el paquete wheel oficial de pyserial 3.5 y comprueba su SHA-256 fijado antes de empaquetarlo. Para generar el paquete sin conexión, utiliza `--wheel /path/to/pyserial-3.5-py2.py3-none-any.whl`. No se ejecuta ninguna instalación mediante pip en Unraid.

Los archivos generados incluyen el `.plg` autocontenido, su `.sha256`, `payload.tar.gz` y los scripts de instalación y desinstalación que se pueden inspeccionar. El contenido se genera directamente desde `src/unraid`, `plugin/src` y `plugin/scripts`. Las plantillas de las operaciones de instalación y reversión están en `plugin/templates`. El verificador compara cada archivo extraído, sus permisos y cada bloque del instalador con su código fuente o con el wheel de la dependencia fijada. El contenido de la aplicación incluye un `build-manifest.json`.

Se conserva deliberadamente el nombre histórico `rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg` para mantener la vía de actualización del plugin de integración existente. La versión interna identifica el candidato. No instales copias adicionales con otros nombres de archivo.

```sh
python3 tools/build_integration_plg.py /tmp/rp2040-source-rc2 \
  --wheel /path/to/pyserial-3.5-py2.py3-none-any.whl \
  --verify /tmp/rp2040-source-rc2/rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg
```

## Comprobaciones de desarrollo

Instala las dependencias de `requirements.txt` en un entorno de desarrollo. PHP CLI permite ejecutar las pruebas de integración de PHP.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/unraid \
  RP2040_TEST_WHEEL=/path/to/pyserial-3.5-py2.py3-none-any.whl \
  python3 -m unittest discover -s tests -v
python3 tools/test_boot_candidate.py /tmp/rp2040-source-rc2
```

Las pruebas utilizan sistemas de archivos temporales y operaciones simuladas del servicio y del puerto serie. No ponen en marcha el control del hardware. La integración continua (CI) ejecuta pruebas con Python 3.11 y 3.12, comprobaciones de sintaxis y protocolo PHP, auditorías del código fuente y del contenido publicable, simulaciones del ciclo de instalación y servicio, verificación del contenido frente al código fuente y comparación de generaciones reproducibles.

## Instalación, arranque y desinstalación en Unraid

La instalación manual requiere que el servicio existente esté detenido y que ENABLE esté ausente. La instalación conserva la configuración y los logs, y deja el servicio deshabilitado. El evento de arranque solo inicia el daemon si ENABLE está presente y no hay una recuperación pendiente. Durante el reinicio, el instalador puede restaurar los archivos que faltan en RAM conservando ENABLE; se rechazan las actualizaciones con el servicio habilitado cuando ya existe una instalación en ejecución. Se admite el enlace estándar `/var/run -> /run`.

Utiliza el auxiliar de la WebUI para detener el servicio antes de actualizarlo. La desinstalación restaura la copia base verificada de ese candidato, elimina ENABLE y conserva la configuración persistente, los logs y las copias de seguridad. Si falla una recuperación, se conserva `recovery-pending` para poder inspeccionarla. La primera instalación utiliza una configuración de ejemplo con marcadores que deben sustituirse antes de arrancar el servicio.

La ruta principal de la WebUI procesa los formularios que modifican el estado a través de Unraid. Se rechazan las solicitudes POST directas al endpoint PHP de datos en directo; las consultas GET directas son de solo lectura. PHP invoca un auxiliar privilegiado con acciones limitadas mediante las reglas sudoers suministradas.

## Publicación

Los paquetes de integración auditfix21–24 se conservan como candidatos históricos. El candidato generado desde el código fuente sustituye su proceso de generación; la validación de sus cambios en el sistema de destino sigue en curso. La comprobación de actualizaciones del canal de pruebas (`pluginURL`) se describe más abajo; el canal estable sigue pendiente. Este comando de generación no publica ninguna versión estable.

Consulta `docs/SOURCE-PACKAGE-REVIEW.md`, `docs/GITHUB-PUBLICATION.md`, `CONTRIBUTING.md` y `SECURITY.md`. La revisión de autoría, licencia y seguridad del código sigue siendo necesaria para aprobar una publicación. El firmware se incluye como referencia; generar o instalar el paquete de Unraid no lo graba en el RP2040.

Los archivos antiguos `plugin/rp2040-fan-control.plg.in`, `tools/render_unraid_plg.py` y `plugin/scripts/install-from-payload.sh` son prototipos históricos o código de referencia; no son la vía de instalación de este candidato.

## Canal de actualizaciones preview

El paquete RC2 revisado también está disponible con los metadatos de comprobación de actualizaciones en `plugin/channels/preview/`. Este es el canal de pruebas. Su `pluginURL` apunta a la propia definición mediante una URL persistente de contenido sin procesar en `source-tree-review`; conserva esa rama mientras las definiciones preview instaladas utilicen esa dirección. Todavía no hay un canal estable habilitado.

`tools/prepare_update_manifest.py` exige el SHA-256 exacto del paquete fuente revisado, añade `pluginURL` y normaliza el atributo interno `name` a `rp2040-fan-control` en la etiqueta de apertura PLUGIN. La verificación rechaza cambios en el código ejecutable, los scripts de instalación y desinstalación, la versión, el checksum o el registro de procedencia. CI compara la definición preview guardada en el repositorio con un paquete recién generado desde el código fuente. El archivo original de source-rc2 se conserva sin cambios.

La comprobación de actualizaciones no modifica el daemon en ejecución. Para instalar una actualización ofrecida, sigue siendo necesario detener el servicio y retirar ENABLE mediante el auxiliar; después de instalarla, hay que arrancarlo explícitamente. El instalador rechaza deliberadamente las actualizaciones con el servicio habilitado o en ejecución.

El borrador de las notas de publicación, los nombres de los archivos revisados y el procedimiento de publicación están en `docs/releases/v0.8.0-source-rc2.md`. Un canal de versiones preliminares sirve para distribuir paquetes de pruebas revisados; no implica su promoción automática a una versión estable.
