# Public release checklist

- [ ] Confirm authorship and permission to publish every source file.
- [x] MIT license selected and added as `LICENSE`.
- [ ] Verify the complete `fan_control` package against the active Unraid copy.
- [x] Include the verified RP2040 `main.py` readback and its hash after review.
- [ ] Confirm no real disk serials, hostnames, private paths, credentials, or logs are committed.
- [ ] Confirm the local disk configuration file is ignored by Git.
- [ ] Pin dependencies after checking the known-good deployment environment.
- [ ] Run unit and syntax tests in a disposable environment.
- [ ] Review fail-safe behavior before any deployment.
- [ ] Do not copy files over the live installation during development.


## WebUI / plugin

- [ ] Resolver permisos IPC de PHP/emhttp en Unraid objetivo sin permisos globales.
- [x] Añadir pruebas unitarias de confirmación serie con transporte simulado a nivel IPC.
- [ ] Implementar configuración persistente y controles WebUI adicionales.
- [ ] Crear y probar el `.plg` instalable completo.
- [ ] Probar instalación, actualización, servicio y desinstalación en Unraid de pruebas.


## GitHub repository preparation

- [x] Add CI workflow for Python tests plus PHP and shell syntax checks (not yet run by GitHub).
- [x] Add contribution and security guidance.
- [x] Add a privacy-conscious bug report template.
- [x] Add a manual publication runbook; no repository created and no files published.
- [ ] Review all source ownership and provenance before public publication.
- [ ] Create repository and configure a real remote URL manually.
