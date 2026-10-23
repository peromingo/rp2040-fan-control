"""Safe runtime-file IPC adapter for the Unraid plugin.

This module is intentionally independent of the V3.0 control loop. Integrate it
only after the exported production daemon has been reviewed. Status publication
must be best-effort; it must never interrupt fan control.
"""
from __future__ import annotations

import json
import os
import re
import stat
import tempfile
import time
from pathlib import Path
from typing import Any

ALLOWED_MODES = frozenset({"AUTO", "SILENT", "TURBO"})
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,80}$")


class RuntimeIPC:
    """Publish status and consume strictly validated mode requests.

    The runtime directory should be created by the service as root-owned and
    non-world-writable. Permissions for the PHP/emhttp writer must be selected
    for the target Unraid release; do not make this directory world-writable.
    """

    def __init__(self, runtime_dir: str | os.PathLike[str] = "/var/run/rp2040-fan-control",
                 request_max_age: int = 30) -> None:
        self.runtime_dir = Path(runtime_dir)
        self.status_path = self.runtime_dir / "status.json"
        self.command_path = self.runtime_dir / "command.json"
        self.result_path = self.runtime_dir / "command-result.json"
        self.seen_path = self.runtime_dir / "seen-requests.json"
        self.request_max_age = int(request_max_age)

    def ensure_runtime_dir(self) -> None:
        # The service wrapper creates this directory as root. Re-check the
        # final path here as well, so a symlink or writable-by-others directory
        # cannot slip through between the wrapper check and daemon startup.
        self.runtime_dir.mkdir(mode=0o750, parents=True, exist_ok=True)
        try:
            info = self.runtime_dir.lstat()
        except OSError as exc:
            raise PermissionError("No se pudo inspeccionar el directorio IPC.") from exc
        if not stat.S_ISDIR(info.st_mode):
            raise PermissionError("La ruta IPC no es un directorio real; se rechaza.")
        if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise PermissionError("El directorio IPC permite escritura de grupo/otros; se rechaza.")
        if os.geteuid() == 0 and info.st_uid != 0:
            raise PermissionError("El directorio IPC existente no pertenece a root; se rechaza.")
        # Never chmod/chown an existing directory: the administrator must
        # resolve ownership/permissions explicitly. The wrapper performs the
        # same checks before launching the service.

    def _atomic_json(self, destination: Path, payload: dict[str, Any], mode: int = 0o640) -> None:
        self.ensure_runtime_dir()
        fd, tmp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp",
                                        dir=str(self.runtime_dir))
        try:
            os.fchmod(fd, mode)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp_name, destination)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def publish_status(self, status: dict[str, Any]) -> bool:
        """Atomically publish a JSON snapshot; return False on I/O/encoding errors."""
        payload = dict(status)
        payload.setdefault("schema_version", 1)
        payload.setdefault("timestamp", time.time())
        try:
            self._atomic_json(self.status_path, payload)
            return True
        except (OSError, TypeError, ValueError):
            # A web/status problem must not stop the fan-control loop.
            return False

    def _write_result(self, request_id: str | None, ok: bool, message: str,
                      applied_mode: str | None = None) -> None:
        result: dict[str, Any] = {
            "schema_version": 1,
            "request_id": request_id,
            "ok": bool(ok),
            "message": message[:240],
            "timestamp": time.time(),
        }
        if applied_mode is not None:
            result["applied_mode"] = applied_mode
        try:
            self._atomic_json(self.result_path, result)
        except (OSError, TypeError, ValueError):
            # Acknowledgement failure is reported by absence/staleness of result.
            pass

    def _load_seen_requests(self) -> dict[str, float]:
        try:
            raw = json.loads(self.seen_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return {}
            return {key: float(value) for key, value in raw.items()
                    if isinstance(key, str) and isinstance(value, (int, float))}
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return {}

    def take_mode_request(self) -> dict[str, str] | None:
        """Consume one request. Invalid/stale/replayed requests are rejected.

        Expected JSON: {"schema_version":1,"request_id":"...",
        "created_at":<unix timestamp>,"action":"set_mode","mode":"AUTO"}.
        A valid request is returned to the daemon; this method does not change
        CURRENT_MODE itself. The caller must apply it in the main control loop
        and call acknowledge_mode_request after the mode is applied.
        """
        # Atomically claim the request before reading it. A plain read()+unlink()
        # can delete a newer request if PHP replaces command.json between the two.
        processing_path = self.runtime_dir / (
            f".command.processing.{os.getpid()}.{time.time_ns()}"
        )
        try:
            os.replace(self.command_path, processing_path)
        except FileNotFoundError:
            return None
        except OSError:
            return None

        request_id: str | None = None
        try:
            if processing_path.stat().st_size > 4096:
                raise ValueError("Solicitud demasiado grande.")
            raw = processing_path.read_text(encoding="utf-8")
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError("El comando debe ser un objeto JSON.")
            candidate_id = request.get("request_id")
            if isinstance(candidate_id, str) and _REQUEST_ID.fullmatch(candidate_id):
                request_id = candidate_id
            if request.get("schema_version") != 1:
                raise ValueError("Versión de comando no admitida.")
            if not request_id:
                raise ValueError("Identificador de solicitud no válido.")
            created_at = request.get("created_at")
            if isinstance(created_at, bool) or not isinstance(created_at, (int, float)):
                raise ValueError("Marca temporal no válida.")
            age = time.time() - float(created_at)
            if age < -5 or age > self.request_max_age:
                raise ValueError("Solicitud caducada o con hora futura.")
            if request.get("action") != "set_mode":
                raise ValueError("Acción no permitida.")
            mode = request.get("mode")
            if mode not in ALLOWED_MODES:
                raise ValueError("Modo no permitido.")
            seen = self._load_seen_requests()
            # Keep a bounded replay window across daemon restarts.
            cutoff = time.time() - 300
            seen = {key: stamp for key, stamp in seen.items() if stamp >= cutoff}
            if request_id in seen:
                raise ValueError("Solicitud duplicada.")
            seen[request_id] = time.time()
            if len(seen) > 256:
                seen = dict(sorted(seen.items(), key=lambda item: item[1])[-256:])
            # If the replay guard cannot be persisted, fail closed and do not
            # apply the request. The fan-control loop itself remains unaffected.
            self._atomic_json(self.seen_path, seen)
            return {"request_id": request_id, "action": "set_mode", "mode": mode}
        except (json.JSONDecodeError, ValueError, TypeError, OSError):
            self._write_result(request_id, False, "Solicitud rechazada: formato, vigencia o modo no válido.")
            return None
        finally:
            try:
                processing_path.unlink()
            except OSError:
                pass

    def acknowledge_mode_request(self, request_id: str, applied_mode: str,
                                 ok: bool = True, message: str | None = None) -> None:
        """Publish the result after the caller has actually handled the request."""
        if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
            return
        if applied_mode not in ALLOWED_MODES and ok:
            ok = False
            message = "Modo aplicado no válido."
        self._write_result(request_id, ok,
                           message or ("Modo aplicado." if ok else "No se pudo aplicar el modo."),
                           applied_mode if ok else None)


def acknowledge_transmitted_mode(runtime_ipc: RuntimeIPC, request: dict[str, str],
                                 applied_mode: str, tx_ok: bool,
                                 fail_safe: bool) -> None:
    """Acknowledge a mode only after successful serial transmission.

    This confirms daemon acceptance and serial write only. It does not imply
    that the RP2040 received or acted on the packet; the current firmware has
    no response/ACK protocol.
    """
    request_id = request.get("request_id")
    if tx_ok and not fail_safe:
        runtime_ipc.acknowledge_mode_request(
            request_id, applied_mode, True,
            "Modo aceptado por el daemon y transmitido por serie; el firmware no devuelve ACK."
        )
    else:
        runtime_ipc.acknowledge_mode_request(
            request_id, applied_mode, False,
            "El daemon no pudo transmitir el modo por serie; se mantiene fail-safe."
        )
