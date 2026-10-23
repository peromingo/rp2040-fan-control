# RP2040 SATA HAT — Unraid fan-control daemon

Public development work copy. This is **not an installer** and must not be pointed at a live system without review.

## Source provenance

- `firmware/rp2040/main.py` is the verified RP2040 readback. Its SHA-256 is `1ad0cf8ef9a6b996bdc1c07c799d9c9c72f7aff159b1f933c3cb6ffd8a3e314f`.
- The recovered active Unraid daemon had SHA-256 `cc05574e9ae8f4ec2c9f43f83b029638d7ecc06e25c3aa4c09ac1ee6c0083a65`. The public daemon is a portable staging adaptation and is not byte-identical to that production daemon.
- The ten recovered `fan_control` module hashes were verified. The public `config.py` is intentionally adapted for configurable paths. The production daemon with real disk identities is not included.

## Before running

1. Review the source and install dependencies from `requirements.txt` (including `pyserial`) in a test environment.
2. Copy `src/unraid/fan_control/site_config.example.py` to `src/unraid/fan_control/site_config_local.py`.
3. Replace every `REPLACE_WITH_...` value with the exact disk model and serial reported by your Unraid host.
4. Keep `site_config_local.py` out of Git. It is listed in `.gitignore`.
5. Configure `RP2040_BASE_DIR`, `RP2040_LOG_DIR`, and optionally `RP2040_LOCK_FILE` for deployment.
6. Test with the daemon disconnected from the production controller first.

**Safety:** Do not start this copy on the production Unraid host yet. It has not undergone full integration testing and is not a validated replacement for the active installation.

## Initial layout

- `firmware/rp2040/main.py` — verified RP2040 firmware readback
- `src/unraid/rp2040_fan_control.py` — portable daemon staging copy
- `src/unraid/fan_control/` — Python package and example disk configuration
- `docs/` — source baseline and publication checklist
- `tests/` — portable tests

### Pruebas locales

Desde la raíz del repositorio, con Python 3 y PHP CLI (para las pruebas PHP):

```sh
PYTHONPATH=src/unraid python -m unittest discover -s tests -v
```

Las pruebas de ciclo usan un `SerialManager` simulado y directorios temporales; no abren el puerto serie ni deben ejecutarse contra el RP2040.


## WebUI / IPC (prototipo de desarrollo)

El paquete incluye una página experimental para Unraid y un adaptador IPC JSON. La página muestra estado, temperaturas y comandos FAN1/FAN2, y permite solicitar los modos AUTO/SILENT/TURBO. La confirmación solo indica que el daemon aceptó la solicitud y transmitió el paquete por serie; el firmware actual no devuelve ACK.

Esta función todavía no es instalable: falta el `.plg` real, la configuración persistente completa, validar permisos en una versión concreta de Unraid y ejecutar pruebas de integración aisladas. El daemon integrado `src/unraid/rp2040_fan_control_webui_dev.py` es exclusivamente una copia de desarrollo y no debe desplegarse en producción.


### Validación del prototipo WebUI/IPC

Las pruebas de desarrollo cubren la validación de solicitudes, la prevención de repetición, la publicación PHP concurrente, la compatibilidad del JSON PHP→Python, los permisos no world-writable y la confirmación condicionada a la transmisión serie. El workflow de GitHub Actions ejecuta estas comprobaciones en Python 3.11 y 3.12, además de validar la sintaxis PHP y Shell, auditar los archivos de publicación y comprobar la generación reproducible del paquete. Antes de integrar cambios, debe verificarse que todos los trabajos de la última ejecución relevante hayan terminado correctamente. Una CI satisfactoria no sustituye las pruebas en una VM de Unraid ni valida los permisos reales de emhttp.


### Wrapper de servicio (borrador)

Se incluye `plugin/scripts/rp2040-fan-control` para revisión del ciclo de vida, pero todavía no es un instalador Unraid. El servicio no arranca salvo que exista el marcador `ENABLE`, haya una configuración local sin marcadores de ejemplo y estén disponibles Python, `pyserial` y `smartctl`. No se deben crear ese marcador ni probar el wrapper en el Unraid de producción durante esta fase.

### Paquete de despliegue (solo revisión)

`tools/build_unraid_payload.sh` genera un archivo `*-payload.tar.gz` con la estructura prevista del payload y un SHA-256. `tools/audit_publication.py` comprueba que el árbol fuente y el payload no incluyan configuraciones locales, cachés compiladas ni artefactos de ejecución conocidos. **No es un `.plg`, no se instala con `installpkg` y no debe copiarse al Unraid de producción.** El diseño del instalador y las salvaguardas pendientes están documentados en `docs/INSTALLER-DESIGN.md`.


## Preparación para publicación

Las instrucciones para preparar el repositorio sin publicar automáticamente nada están en `docs/GITHUB-PUBLICATION.md`. El proyecto incluye un workflow de GitHub Actions para pruebas, `CONTRIBUTING.md` y `SECURITY.md`. No hay aún un `.plg` instalable ni una URL de release.

### Instalador Unraid (plantilla, no publicable aún)

`plugin/rp2040-fan-control.plg.in` y `tools/render_unraid_plg.py` preparan el descriptor de instalación. El renderizador rechaza dominios reservados de ejemplo, URLs sin HTTPS, credenciales incrustadas y checksums inválidos. El renderizador exige URLs HTTPS reales y el SHA-256 del payload; no se ha generado un `.plg` de release porque el repositorio y sus URLs aún no existen. El payload incluye un helper que preserva `site_config_local.py` y logs durante actualizaciones, crea la configuración de ejemplo solo en la primera instalación y nunca habilita el daemon automáticamente. La desinstalación propuesta conserva la configuración persistente.

**No instalar:** faltan pruebas con el plugin manager y el sistema de archivos reales de Unraid, y todavía no se han verificado los permisos PHP/emhttp para el IPC.


### Comprobación de dependencias (solo diagnóstico)

El wrapper de desarrollo acepta `check-deps` para mostrar el intérprete Python seleccionado, comprobar `pyserial` y localizar `smartctl`, sin instalar nada ni abrir el puerto serie. Si hay varios Python, se puede indicar el ejecutable mediante `RP2040_PYTHON` en una invocación manual o guardando su ruta absoluta en `/boot/config/plugins/rp2040-fan-control/python-path` (primera línea; el archivo no se ejecuta como shell). No se instala Python ni `pyserial` automáticamente. La dependencia debe prepararse y validarse primero en una VM de Unraid; véase `docs/INSTALLER-DESIGN.md`.
