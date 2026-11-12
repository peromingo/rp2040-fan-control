# Estado de integración WebUI / IPC

Actualizado: 2026-11-12. La integración forma parte del **PLG instalable 0.8.0-source-rc2**, publicado como prerelease. El prototipo que describía la primera versión de este documento ha sido sustituido por el paquete generado desde el árbol fuente.

## Implementado

- Registro de la página mediante RP2040FanControl.page y render de pages/index.php dentro de Unraid.
- Estado del servicio y controles de inicio, parada y reinicio.
- Configuración persistente JSON de grupos HDD/CPU y selección del puerto serie antes del arranque.
- Estado del controlador, temperaturas, avisos de fuentes y valores de comando/objetivo de FAN1 y FAN2.
- Modos AUTO, SILENT y TURBO, con confirmación asociada al identificador de la solicitud.
- Consulta periódica de solo lectura al endpoint PHP directo con rp2040_live=1.
- Auxiliar privilegiado de acciones limitadas y reglas sudoers; PHP no necesita escritura global en el directorio IPC.
- Validación de solicitudes, caducidad, prevención de repetición y publicación atómica mediante fan_control/ipc.py.

## Correcciones verificadas

- El campo operation evita el conflicto del nombre action con el tratamiento de formularios de Unraid.
- La finalización del POST de modo respeta el render de la página contenedora y evita la página en blanco.
- El sondeo usa la ruta PHP del plugin: la ruta Settings puede devolver la página HTML de Unraid en lugar de JSON.
- El nombre interno rp2040-fan-control evita los espacios que impedían actualizar la celda de estado de Plugins.

Los modos, la configuración y el estado en directo se comprobaron manualmente. Las pruebas automáticas cubren contratos PHP/Python, concurrencia, permisos, aislamiento de solicitudes y resultados de transmisión; consulta el alcance de la [validación actual](VALIDATION-STATUS.md).

## Permisos y servicio

El wrapper crea el directorio IPC con modo 0750 y rechaza permisos de escritura de grupo/globales o propietario inesperado en un directorio existente. El acceso de la WebUI se realiza mediante el auxiliar y sudoers. La ausencia o caducidad del estado deshabilita los controles de modo.

El servicio valida configuración, Python, pyserial y smartctl antes de iniciar. El intérprete puede seleccionarse mediante python-path o RP2040_PYTHON. La parada comprueba que el PID corresponde al daemon y utiliza SIGTERM; no fuerza SIGKILL automáticamente.

La instalación manual exige servicio detenido y ENABLE ausente. Tras un reinicio, el evento startup solo inicia si ENABLE está presente. Ambos estados de arranque se han comprobado mediante reinicios reales.

## Precisión de las confirmaciones

La interfaz confirma aceptación por el daemon y escritura serie completada. El firmware actual no devuelve ACK; no se confirma recepción/aplicación por el RP2040 ni se miden RPM. Las simulaciones de transporte no prueban el comportamiento físico en una desconexión.

## Pendientes

- Ensayos reales de desconexión/reconexión del RP2040 y pérdida de fuentes térmicas.
- Revisión final de seguridad, compatibilidad y procedencia antes de promover a estable.

Las tareas ya completadas de instalador, configuración persistente y permisos funcionales dejan de figurar como desarrollo pendiente. La [lista de publicación](PUBLICATION-CHECKLIST.md) y [VALIDATION-STATUS.md](VALIDATION-STATUS.md) recogen el trabajo restante.
