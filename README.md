# Control de ventiladores RP2040 SATA HAT para Unraid

Controlador y WebUI en desarrollo para regular ventiladores mediante un RP2040. El firmware no devuelve confirmaciones serie (ACK): un comando correcto confirma que el daemon ha aceptado la solicitud y completado la escritura por serie; no confirma las RPM físicas de los ventiladores.

El candidato de revisión generado desde el código fuente es **0.8.0-source-rc2**. Combina asignaciones persistentes de discos y CPU en JSON, selección del puerto serie, una WebUI con datos en directo, avisos sobre las fuentes térmicas y arranque automático opcional, con protección contra instancias duplicadas y diagnóstico del intérprete Python. No es una versión estable. El PLG y sus pruebas completadas están documentados en el resumen de validación; siguen pendientes los ensayos físicos de desconexión y pérdida de fuentes térmicas.

## Estado de pruebas y tareas

Está publicada la [prerelease v0.8.0-source-rc2](https://github.com/peromingo/rp2040-fan-control/releases/tag/v0.8.0-source-rc2). La [validación actual](docs/VALIDATION-STATUS.md) distingue resultados automáticos, comprobaciones manuales y límites.

| Prueba del PLG | Estado |
| --- | --- |
| Instalación limpia | Completada |
| Actualización RC1 → RC2 desde Plugins, conservando configuración | Completada |
| Reinicio real sin ENABLE | Completado |
| Desconexión/reconexión del RP2040 real | Aplazada |
| Pérdida de fuentes térmicas y fallback físico | Aplazada |

La revisión final y el canal estable siguen pendientes. Consulta la [lista de tareas](docs/PUBLICATION-CHECKLIST.md) y el [procedimiento de publicación](docs/GITHUB-PUBLICATION.md).

## Placas utilizadas

El montaje utiliza una Radxa X4, un Quad SATA HAT para los discos y la SATA HAT Top Board con pantalla OLED, botón y ventilador. Estas fotografías oficiales sirven como referencia para identificar cada placa.

<table>
  <tr>
    <th>Radxa X4</th>
    <th>Quad SATA HAT</th>
    <th>SATA HAT Top Board · OLED</th>
  </tr>
  <tr>
    <td align="center"><a href="https://radxa.com/products/x/x4/"><img src="https://radxa.com/x/x4/banner_radxa_x4.webp" alt="Placa Radxa X4 con RP2040 integrado" width="260"></a></td>
    <td align="center"><a href="https://wiki.radxa.com/Dual_Quad_SATA_HAT"><img src="https://wiki.radxa.com/mw/images/thumb/b/b0/Quad_sata_hat_angle.png/500px-Quad_sata_hat_angle.png" alt="Quad SATA HAT con cuatro conectores SATA" width="260"></a></td>
    <td align="center"><a href="https://wiki.radxa.com/Dual_Quad_SATA_HAT#SATA_HAT_Top_board.28Optional.29"><img src="https://wiki.radxa.com/mw/images/thumb/7/72/Sata_hat_top_board.png/500px-Sata_hat_top_board.png" alt="SATA HAT Top Board con pantalla OLED, botón y ventilador" width="260"></a></td>
  </tr>
  <tr>
    <td>Placa principal con Intel N100 y RP2040 integrado.</td>
    <td>Placa de expansión con cuatro conexiones SATA para discos.</td>
    <td>Placa superior con OLED de 0,91 pulgadas, botón físico y ventilador PWM.</td>
  </tr>
</table>

Unraid ejecuta el daemon y la WebUI. La comunicación por serie con el RP2040 permite enviar los comandos de ventilación y la información que se muestra en la OLED.

Fotografías enlazadas desde [Radxa — X4](https://radxa.com/products/x/x4/) y [Radxa Wiki — Dual/Quad SATA HAT](https://wiki.radxa.com/Dual_Quad_SATA_HAT). Las imágenes de Radxa Wiki se atribuyen a Radxa y están sujetas a [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), salvo indicación específica del fabricante.

## Pines y comunicaciones

Los GPIO siguientes son los que utiliza [el firmware incluido](firmware/rp2040/main.py). `GPIO` identifica el pin lógico del RP2040, tal como aparece en `machine.Pin(...)`. La columna X4 sigue la numeración del conector de 40 pines de la tabla oficial **v1.110**; Radxa publica otra numeración para revisiones anteriores. Comprueba la revisión de la placa antes de usar los números físicos como guía de conexión.

| Función | GPIO del RP2040 | Pin X4 de 40 pines · v1.110 | Pin Top Board · 2×5 | Uso en el proyecto |
| --- | --- | --- | --- | --- |
| Ventilador FAN1 | GPIO13 | 33 | 8 · PWM | Primera salida de control de ventilación, PWM a 25 kHz; corresponde al PWM del ventilador de la Top Board. |
| Ventilador FAN2 | GPIO19 | 32 | — | Segunda salida PWM a 25 kHz; su conexión corresponde al segundo ventilador del montaje. |
| OLED · SDA | GPIO28 | 3 | 1 · SDA | Datos de la pantalla mediante SoftI2C. |
| OLED · SCL | GPIO29 | 5 | 3 · SCL | Reloj de SoftI2C a 100 kHz. |
| OLED · reset | GPIO22 | 16 | 5 · reset | Pulso a nivel bajo y después alto para reiniciar la pantalla al arrancar. |
| Botón de la Top Board | GPIO5 | 11 | 6 · botón | Entrada con pull-up interno; pulsado a nivel bajo. |
| Control SATA · primera línea | GPIO14 | 37 | — | Línea de reset/habilitación del HAT, correspondiente a SATA 3/4 según su pinout; primera en ponerse a nivel alto. |
| Control SATA · segunda línea | GPIO24 | 22 | — | Línea de reset/habilitación del HAT, correspondiente a SATA 1/2 según su pinout; segunda en ponerse a nivel alto. |

La numeración de la Top Board corresponde a su conector de **2×5 pines**, no al conector de 40 pines de la X4. En ese conector, el fabricante identifica además el pin 2 como 3,3 V, el 4 como 5 V, el 7 y el 9 como GND y el 10 como NC. Los GPIO de la tabla son señales de control; la alimentación de los ventiladores y discos se realiza mediante los conectores de alimentación correspondientes.

El firmware configura la OLED como **128×32 píxeles**, con dirección I2C **`0x3C`**. El botón permite cambiar de página con una pulsación corta, encender/apagar la OLED con doble pulsación y solicitar el siguiente modo AUTO/SILENT/TURBO manteniéndolo pulsado al menos dos segundos.

FAN1 y FAN2 son grupos de control: las fuentes HDD/CPU que regulan cada uno se eligen en la WebUI. Conserva la secuencia SATA del firmware: ambas líneas bajas, espera de 0,2 s, GPIO14 alto, espera de 0,4 s, GPIO24 alto y estabilización de 1,5 s.

Referencias del fabricante: [GPIO de Radxa X4 y sus revisiones](https://docs.radxa.com/en/x/x4/software/gpio) y [pinout del Quad SATA HAT y la Top Board](https://wiki.radxa.com/Dual_Quad_SATA_HAT#PINOUT).

### USB, puerto serie y conexión de los discos

| Enlace | Interfaz utilizada | Identificación o configuración |
| --- | --- | --- |
| Unraid ↔ RP2040 integrado en la X4 | USB CDC de MicroPython, presentado como puerto serie virtual | `/dev/ttyACM0` u otro `/dev/ttyACM<N>`. Es preferible guardar una ruta estable `/dev/serial/by-id/...` desde la WebUI. |
| Configuración del daemon | pyserial sobre ese puerto USB | `BAUDRATE = 115200`; es el parámetro de apertura del puerto virtual, no la velocidad del enlace USB. |
| RP2040 ↔ OLED | SoftI2C | SDA GPIO28, SCL GPIO29, 100 kHz y dirección `0x3C`. |
| Quad SATA HAT ↔ sistema | USB 3 para los datos de los discos | Es un enlace de almacenamiento distinto del puerto serie USB que utiliza el daemon para el RP2040. |

El firmware recibe las tramas por `sys.stdin.buffer` y envía las solicitudes del botón por `sys.stdout`. El código actual no configura `machine.UART` ni requiere cablear pines TX/RX para ese enlace. La [documentación de Radxa](https://docs.radxa.com/en/x/x4/software/c_sdk_examples) describe las opciones USB/UART de la X4; este proyecto utiliza USB.

El selector guarda la elección en `/boot/config/plugins/rp2040-fan-control/serial_port.conf`. En automático se exige un único candidato compatible: primero se buscan rutas `by-id` hacia un `ttyACM` y después dispositivos `ttyACM` directos. Si hay varios candidatos, hay que elegir uno explícitamente. La WebUI no ofrece los puertos `ttyS`.

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

Los paquetes de integración auditfix21–24 se conservan como candidatos históricos. El candidato generado desde el código fuente sustituye su proceso de generación. El alcance de las pruebas completadas y los dos ensayos de hardware aplazados se mantiene en [VALIDATION-STATUS.md](docs/VALIDATION-STATUS.md). La comprobación de actualizaciones del canal de pruebas (`pluginURL`) se describe más abajo; el canal estable sigue pendiente. Este comando de generación no publica ninguna versión estable.

Consulta `docs/SOURCE-PACKAGE-REVIEW.md`, `docs/GITHUB-PUBLICATION.md`, `CONTRIBUTING.md` y `SECURITY.md`. La revisión de autoría, licencia y seguridad del código sigue siendo necesaria para aprobar una publicación. El firmware se incluye como referencia; generar o instalar el paquete de Unraid no lo graba en el RP2040.

Los archivos antiguos `plugin/rp2040-fan-control.plg.in`, `tools/render_unraid_plg.py` y `plugin/scripts/install-from-payload.sh` son prototipos históricos o código de referencia; no son la vía de instalación de este candidato.

## Canal de actualizaciones preview

El paquete RC2 revisado también está disponible con los metadatos de comprobación de actualizaciones en `plugin/channels/preview/`. Este es el canal de pruebas. Su `pluginURL` apunta a la propia definición mediante una URL persistente de contenido sin procesar en `source-tree-review`; conserva esa rama mientras las definiciones preview instaladas utilicen esa dirección. Todavía no hay un canal estable habilitado.

`tools/prepare_update_manifest.py` exige el SHA-256 exacto del paquete fuente revisado, añade `pluginURL` y normaliza el atributo interno `name` a `rp2040-fan-control` en la etiqueta de apertura PLUGIN. La verificación rechaza cambios en el código ejecutable, los scripts de instalación y desinstalación, la versión, el checksum o el registro de procedencia. CI compara la definición preview guardada en el repositorio con un paquete recién generado desde el código fuente. El archivo original de source-rc2 se conserva sin cambios.

La comprobación de actualizaciones no modifica el daemon en ejecución. Para instalar una actualización ofrecida, sigue siendo necesario detener el servicio y retirar ENABLE mediante el auxiliar; después de instalarla, hay que arrancarlo explícitamente. El instalador rechaza deliberadamente las actualizaciones con el servicio habilitado o en ejecución.

Las notas de la prerelease publicada, la identidad de sus archivos y los límites de validación están en [docs/releases/v0.8.0-source-rc2.md](docs/releases/v0.8.0-source-rc2.md). Un canal de versiones preliminares sirve para distribuir paquetes de pruebas revisados; no implica su promoción automática a una versión estable.
