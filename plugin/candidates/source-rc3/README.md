# Candidato 0.8.0-source-rc3

Generado desde las fuentes con `tools/build_integration_plg.py`, incluyendo pyserial
3.5 fijado por SHA-256. Conserva el nombre `rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg`
para actualizar el plugin registrado sin instalar un segundo plugin.

SHA-256 del PLG: `c47776550584061234187ee419c58c4d52353b60d3fb6062e8e325a8ead3d9f2`.

[Descargar PLG](rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg) ·
[Checksum](rp2040-fan-control-webui-integration-serial-v2-auditfix19.plg.sha256)

RC3 restaura el estado inmediatamente anterior cuando falla una instalación, sin
reutilizar para esa operación la copia histórica de desinstalación. Añade bloqueo
compartido de instalación/desinstalación y distribuye las licencias completas MIT
del proyecto y BSD de pyserial dentro del payload. Incorpora el nombre interno
normalizado y la URL del canal preview desde el constructor.

El firmware y el comportamiento del control térmico no cambian. RC2 continúa
publicado y el canal preview conserva RC2 durante la validación de este candidato.
No es una versión estable. Falta la validación manual de RC3 en Unraid.

Para actualizar, detener el daemon y dejar ENABLE ausente. Guardar previamente el
PLG registrado y la configuración. No es necesario desinstalar RC2 antes de instalar
RC3. La instalación no inicia el daemon; revisar el resultado y arrancarlo de forma
explícita. No borrar diarios recovery-pending ni mezclar instaladores de versiones.

[Plan y alcance de pruebas](../../../docs/VALIDATION-RC3.md) ·
[Diseño de recuperación](../../../docs/INSTALLER-DESIGN.md) ·
[Licencias](../../../THIRD_PARTY_NOTICES.md)
