"""Validated persistent serial-port selection for the Unraid WebUI helper."""
from __future__ import annotations

import os
import re
import stat
import tempfile
from pathlib import Path
from typing import Any

CONFIG_PATH = Path("/boot/config/plugins/rp2040-fan-control/serial_port.conf")
_TTY_ACM = re.compile(r"^ttyACM[0-9]+$")
_PTY = re.compile(r"^pts/[0-9]+$")
_BY_ID = re.compile(r"^[A-Za-z0-9_.:+-]+$")


def _target_kind(path: Path, dev_root: Path) -> str | None:
    try:
        resolved = path.resolve(strict=True)
        relative = resolved.relative_to(dev_root).as_posix()
        if not stat.S_ISCHR(resolved.stat().st_mode):
            return None
    except (OSError, ValueError, RuntimeError):
        return None
    if _TTY_ACM.fullmatch(relative):
        return "ttyACM"
    if _PTY.fullmatch(relative):
        return "pty"
    return None


def available_ports(dev_root: str | os.PathLike[str] = "/dev") -> list[str]:
    """List only ACM devices and by-id aliases; accept PTY aliases for tests."""
    root = Path(dev_root).resolve()
    found: set[str] = set()
    by_id_dir = root / "serial" / "by-id"
    try:
        by_id = sorted(by_id_dir.iterdir())
    except OSError:
        by_id = []
    for candidate in by_id:
        if not _BY_ID.fullmatch(candidate.name) or not candidate.is_symlink():
            continue
        if _target_kind(candidate, root) == "ttyACM":
            found.add("/dev/serial/by-id/" + candidate.name)
    try:
        direct = sorted(root.glob("ttyACM*"))
    except OSError:
        direct = []
    for candidate in direct:
        if not _TTY_ACM.fullmatch(candidate.name):
            continue
        if _target_kind(candidate, root) in {"ttyACM", "pty"}:
            found.add("/dev/" + candidate.name)
    return sorted(found)


def read_selected(config_path: str | os.PathLike[str] = CONFIG_PATH) -> str:
    path = Path(config_path)
    if path.is_symlink():
        raise ValueError("serial_port.conf no puede ser un enlace simbólico.")
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "auto"
    if not stat.S_ISREG(info.st_mode) or info.st_size > 256:
        raise ValueError("serial_port.conf debe ser un archivo regular pequeño.")
    raw = path.read_text(encoding="ascii")
    if "\r" in raw or raw.count("\n") > 1:
        raise ValueError("serial_port.conf debe contener como máximo una línea.")
    value = raw[:-1] if raw.endswith("\n") else raw
    return value or "auto"


def get_config(config_path: str | os.PathLike[str] = CONFIG_PATH,
               dev_root: str | os.PathLike[str] = "/dev") -> dict[str, Any]:
    return {"selected": read_selected(config_path), "ports": available_ports(dev_root)}


def save_selected(value: Any, config_path: str | os.PathLike[str] = CONFIG_PATH,
                  dev_root: str | os.PathLike[str] = "/dev") -> str:
    if not isinstance(value, str):
        raise ValueError("Puerto serie no válido.")
    path = Path(config_path)
    if path.is_symlink():
        raise ValueError("serial_port.conf no puede ser un enlace simbólico.")
    if value == "auto":
        try:
            info = path.lstat()
        except FileNotFoundError:
            return "Selección automática guardada."
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("serial_port.conf no es un archivo regular.")
        path.unlink()
        return "Selección automática guardada."
    if value not in available_ports(dev_root):
        raise ValueError("El puerto seleccionado no está presente o no es compatible.")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".serial-port-", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return "Puerto serie guardado. El daemon debe estar detenido para aplicar la selección."
