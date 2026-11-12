# Revisión de correspondencia entre fuentes y paquete

Actualizado: 2026-11-12. La correspondencia del candidato fuente RC2 y su variante preview se comprueba en CI. El PLG publicado y los ensayos completados están en [VALIDATION-STATUS.md](VALIDATION-STATUS.md). Los apartados sobre auditfix24 conservan los hallazgos históricos; no describen el paquete actual.

Este informe trata el código del repositorio y los paquetes públicos, sin telemetría de instalaciones.

## Historical auditfix24 finding

The integration package is not currently a build of the main source tree. Of the 22 non-vendor payload files mapped to source locations, six match, ten differ and six have no corresponding main-tree file. The main tree also contains the safe `instance_lock.py` implementation, which is absent from the integration payload. The separate legacy daemon entry point is intentionally not included in the integration payload.

The two implementations have diverged. Neither should replace the other wholesale.

| Area | Integration candidate | Main source tree features to retain |
| --- | --- | --- |
| Configuration | JSON FAN1/FAN2 assignments, optional CPU sources and persistent serial selection | Placeholder validation and disabled initial state |
| Serial/control | Explicit port selection, refusal of ambiguous automatic selection, short-write detection, immediate maximum output on missing sources or thermal alert | Existing serial/IPC regression tests |
| WebUI/IPC | Privileged allowlisted helper, service/config controls, direct live JSON endpoint, source warnings, result-publication retry and mode finalization | Atomic command publishing and existing protocol tests |
| Instance lifecycle | Basic flock lock inside the replaceable app directory | Safe lock acquisition without truncation, stable runtime lock path |
| Service wrapper | JSON/serial configuration support | Persistent Python interpreter selection and read-only dependency diagnostics |
| Boot | Transactional startup-hook installation and canonical runtime-alias handling | Rebuild from tracked sources and dependency review |

The six candidate-only source files are the sudoers policy, startup hook, image asset, WebUI helper, `configuration.py` and `serial_port_config.py`.

## Plan histórico de consolidación

Los puntos 1–4 siguientes se implementaron en la línea fuente RC1/RC2 y tienen comprobaciones automáticas. El punto 5 se divide ahora en canal preview y actualización desde Plugins completados, y canal estable pendiente.

1. Integrate the candidate's configuration, control and WebUI features into the main source tree while retaining safe instance locking, interpreter selection and diagnostics.
2. Store the transactional installation/removal logic as reviewed source templates. Build the payload and PLG from the consolidated tree instead of modifying an earlier embedded package.
3. Check that extraction of the generated payload matches the selected source files byte for byte, with required executable modes preserved and local configuration excluded.
4. Run the IPC, lock, configuration, publication and installation/boot tests against the consolidated sources. Repeat target validation for any changes to runtime behavior.
5. Configure a stable update manifest URL (`pluginURL`) and verify the update-check/update lifecycle before publishing a stable channel.

Auditfix24 remains an integration candidate. Retaining its artifact and checksum supports inspection and reproduction of that artifact; it does not establish correspondence with the main source tree.

## Source-built candidate 0.8.0-source-rc1

The main runtime sources now include the integration configuration, helper, WebUI and thermal/serial safeguards. Safe instance locking on the stable runtime path and persistent interpreter selection/dependency diagnostics are retained. Direct POST to the standalone PHP live endpoint is rejected; mutations use the Unraid route.

`tools/build_integration_plg.py` builds from these sources and reviewed transaction templates. The official pyserial wheel is pinned by SHA-256. Verification compares all payload files/modes and both installer blocks against the sources and wheel, rejects unexpected files, and checks the deterministic archive. The app contains a source/hash manifest. This resolves source correspondence for this new candidate; historical auditfix artifacts are unchanged.

El candidato RC2 dispone de CI y ensayos manuales registrados en [VALIDATION-STATUS.md](VALIDATION-STATUS.md). El nombre histórico del PLG mantiene el registro de actualización existente. El canal preview y la actualización RC1 → RC2 desde Plugins se han verificado; el canal estable sigue pendiente.

## Source RC2 WebUI completion fix

Mode POST handling now preserves the rendered page if the enclosing Unraid shell has already sent headers. It always renders the included page and completes the form with a local GET navigation, leaving the outer response under Unraid control. The live JSON endpoint returns only the result matching the tracked request ID, allowing the confirmation message to update. Direct POST rejection remains in force. Regression tests emulate a previously emitted shell, pending-command conflicts, local return-route restrictions and result-ID isolation.

## Estado vigente de la consolidación

- [x] Fuentes consolidadas, plantillas transaccionales y generador desde el árbol real.
- [x] Bloqueo de instancia estable y diagnóstico/selección del intérprete conservados.
- [x] Correspondencia de archivos, permisos, scripts y dependencia fijada comprobada por el generador y CI.
- [x] RC2 corrige la finalización del formulario de modos y conserva los contratos del endpoint directo.
- [x] Variante preview con pluginURL y nombre interno normalizado; delta limitado a la cabecera.
- [x] Instalación limpia, actualización desde Plugins y reinicio deshabilitado cerrados con el alcance del resumen de validación.
- [ ] Ensayos físicos de desconexión y pérdida de fuentes térmicas.
- [ ] Revisión final y canal estable.

Los cambios posteriores de documentación no reconstruyen el instalador ni modifican el tag de la prerelease.
