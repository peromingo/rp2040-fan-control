# Estado de integración WebUI / IPC

Esta versión integra el prototipo de panel y el módulo IPC en una copia de desarrollo. No es un plugin instalable ni un release.

## Incluido

- `plugin/src/usr/local/emhttp/plugins/rp2040-fan-control/RP2040FanControl.page`: registro de página en el menú Settings de Unraid.
- `plugin/.../pages/index.php`: estado del daemon, temperaturas, FAN1/FAN2 y solicitudes de modo AUTO/SILENT/TURBO.
- `src/unraid/fan_control/ipc.py`: intercambio JSON con validación de solicitud, caducidad, prevención de repetición y escritura atómica.
- `src/unraid/rp2040_fan_control_webui_dev.py`: copia de desarrollo del daemon con IPC integrado; el archivo original `rp2040_fan_control.py` permanece sin cambios.
- `tests/webui_ipc/`: pruebas unitarias IPC, carrera de publicación concurrente PHP, contrato PHP→Python, permisos de archivos, confirmación condicionada al resultado de transmisión y ciclo simulado con un serial manager falso.

## Precisión sobre las confirmaciones

La interfaz informa de que el daemon aceptó el modo y lo transmitió por serie. El firmware actual no devuelve ACK, así que no puede afirmarse que el RP2040 haya confirmado la recepción o aplicación.

## Pendiente

- Resolver y probar permisos reales del directorio `/var/run/rp2040-fan-control` para el usuario que ejecuta PHP/emhttp en la versión de Unraid de destino. No hacerlo world-writable.
- La simulación de ciclo cubre recepción → selección de modo → envío simulado → resultado IPC, pero no ejecuta la función `main()` ni el bucle completo del daemon.
- Ampliar la WebUI para configuración persistente y diagnóstico.
- Implementar el `.plg` real (instalación, actualización, gestión de servicio y desinstalación).
- Validar instalación y flujo completo en una VM o entorno de Unraid de pruebas.

No ejecutar el daemon integrado contra el hardware de producción.

## Wrapper de servicio (borrador, no instalador)

Se añade `plugin/scripts/rp2040-fan-control` como envoltorio de servicio para revisar el ciclo de vida en aislamiento. No es un `.plg` y no se instala automáticamente.

Salvaguardas del borrador:

- `start` permanece desactivado si no existe `/boot/config/plugins/rp2040-fan-control/ENABLE`.
- Rechaza la configuración ausente o con marcadores `REPLACE_WITH_`.
- Comprueba Python, `pyserial` y `smartctl` antes de iniciar.
- El directorio IPC se crea con modo `0750`; no se cambia su propietario/grupo ni se abren permisos globales.
- `stop` comprueba que el PID corresponde a este daemon y usa `SIGTERM`; no recurre a `SIGKILL` automáticamente.
- Logs y configuración local están pensados para permanecer bajo `/boot/config/plugins/rp2040-fan-control/`.

Limitaciones pendientes antes de considerar un instalador:

- Confirmar la identidad efectiva del proceso PHP/emhttp y probar lectura/escritura IPC en la versión de Unraid objetivo.
- Revisar el arranque/parada real durante instalación, actualización y apagado en una VM de pruebas.
- Definir cómo se distribuye el paquete de archivos (URL de release o paquete embebido); no se crea una URL ficticia ni un `.plg` que aparente ser instalable.
- Verificar dependencias reales disponibles en Unraid y validar la ruta serial del RP2040 con hardware de pruebas, nunca con el servidor de producción.
