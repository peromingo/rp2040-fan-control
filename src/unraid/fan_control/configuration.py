"""Persistent fan source configuration for the Unraid RP2040 daemon.

JSON schema v1 (stored outside the package, in the plugin configuration dir):
{
  "schema_version": 1,
  "fans": {
    "fan1": {"disks": [{"model": "...", "serial": "..."}], "use_cpu": false},
    "fan2": {"disks": [], "use_cpu": true}
  }
}

This module validates configuration only; it never changes the RP2040 firmware.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("/boot/config/plugins/rp2040-fan-control/config.json")


def config_path() -> Path:
    return Path(os.environ.get("RP2040_FAN_CONFIG", str(DEFAULT_CONFIG_PATH)))


def _identity(item: Any) -> tuple[str, str]:
    if not isinstance(item, dict):
        raise ValueError("Cada disco debe ser un objeto model/serial.")
    model, serial = item.get("model"), item.get("serial")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Modelo de disco no válido.")
    if not isinstance(serial, str) or not serial.strip():
        raise ValueError("Número de serie de disco no válido.")
    if len(model) > 160 or len(serial) > 160 or "REPLACE_WITH_" in model or "REPLACE_WITH_" in serial:
        raise ValueError("La identidad del disco contiene valores no permitidos.")
    return model.strip(), serial.strip()


def validate_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Versión de configuración no admitida.")
    fans = payload.get("fans")
    if not isinstance(fans, dict) or set(fans) != {"fan1", "fan2"}:
        raise ValueError("La configuración debe incluir FAN1 y FAN2.")
    normalized: dict[str, Any] = {"schema_version": 1, "fans": {}}
    all_disks: set[tuple[str, str]] = set()
    for key in ("fan1", "fan2"):
        entry = fans[key]
        if not isinstance(entry, dict):
            raise ValueError(f"Configuración de {key.upper()} no válida.")
        raw_disks = entry.get("disks", [])
        use_cpu = entry.get("use_cpu", False)
        if not isinstance(raw_disks, list) or not isinstance(use_cpu, bool):
            raise ValueError(f"Fuentes térmicas de {key.upper()} no válidas.")
        disks = [_identity(item) for item in raw_disks]
        if len(disks) != len(set(disks)):
            raise ValueError(f"Hay discos duplicados en {key.upper()}.")
        overlap = all_disks.intersection(disks)
        if overlap:
            raise ValueError("Un disco no puede pertenecer simultáneamente a FAN1 y FAN2.")
        all_disks.update(disks)
        if not disks and not use_cpu:
            raise ValueError(f"{key.upper()} necesita al menos un HDD o la temperatura de CPU.")
        normalized["fans"][key] = {
            "disks": [{"model": model, "serial": serial} for model, serial in disks],
            "use_cpu": use_cpu,
        }
    return normalized


def load_configuration() -> tuple[set[tuple[str, str]], set[tuple[str, str]], bool, bool]:
    """Return FAN1 disks, FAN2 disks, FAN1 CPU selection, FAN2 CPU selection."""
    path = config_path()
    if path.is_file():
        payload = validate_payload(json.loads(path.read_text(encoding="utf-8")))
        fan1 = {(d["model"], d["serial"]) for d in payload["fans"]["fan1"]["disks"]}
        fan2 = {(d["model"], d["serial"]) for d in payload["fans"]["fan2"]["disks"]}
        return fan1, fan2, payload["fans"]["fan1"]["use_cpu"], payload["fans"]["fan2"]["use_cpu"]

    # Backward-compatible fallback for existing local installations.
    from fan_control.site_config_local import FAN1_DISKS, FAN2_DISKS, validate_disk_config
    validate_disk_config()
    from fan_control import site_config_local
    use_cpu1 = getattr(site_config_local, "FAN1_USE_CPU", False)
    use_cpu2 = getattr(site_config_local, "FAN2_USE_CPU", False)
    if not isinstance(use_cpu1, bool) or not isinstance(use_cpu2, bool):
        raise RuntimeError("FAN1_USE_CPU y FAN2_USE_CPU deben ser booleanos.")
    if not FAN1_DISKS and not use_cpu1:
        raise RuntimeError("FAN1 necesita al menos un HDD o la temperatura de CPU.")
    if not FAN2_DISKS and not use_cpu2:
        raise RuntimeError("FAN2 necesita al menos un HDD o la temperatura de CPU.")
    return set(FAN1_DISKS), set(FAN2_DISKS), use_cpu1, use_cpu2


def save_configuration(payload: Any, destination: Path | None = None) -> Path:
    """Atomically persist a validated payload; caller must provide trusted permissions."""
    normalized = validate_payload(payload)
    path = destination or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".rp2040-config-", suffix=".tmp", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(normalized, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return path
