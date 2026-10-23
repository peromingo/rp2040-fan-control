"""
V3.0 - Gestor de comunicacion serie con RP2040.

Extraccion conservadora de la logica serie existente
en rp2040_fan_control.py.

Responsabilidades:
- deteccion del puerto RP2040
- conexion y reconexion
- transmision de paquetes
- watchdog de comunicacion
- diagnostico periodico
- recepcion de comandos de modo

No contiene logica termica ni controla directamente CURRENT_MODE.
"""

import glob
import os
import time
import serial


MODE_AUTO = "AUTO"
MODE_SILENT = "SILENT"
MODE_TURBO = "TURBO"


class SerialManager:

    def __init__(
        self,
        baudrate,
        reconnect_interval,
        watchdog_timeout,
        error_log_interval,
        diagnostic_interval,
        logger=None,
        log_info=None,
        log_error=None,
        log_warning=None,
        status_formatter=None,
    ):
        self.baudrate = baudrate
        self.reconnect_interval = reconnect_interval
        self.watchdog_timeout = watchdog_timeout
        self.error_log_interval = error_log_interval
        self.diagnostic_interval = diagnostic_interval

        self.logger = logger
        self.log_info = log_info
        self.log_error = log_error
        self.log_warning = log_warning
        self.status_formatter = status_formatter

        self.port = None
        self.connected = False
        self.fail_safe = False
        self.rx_buffer = ""

        self.last_tx_ok = 0
        self.last_connect_attempt = 0
        self.last_error_log = 0
        self.last_diagnostic = 0

        self.state = "DISCONNECTED"
        self.last_device = None

        self.disconnect_count = 0
        self.reconnect_count = 0
        self.recovery_pending = False

    def _log_info(self, category, message):
        if self.log_info is not None:
            self.log_info(self.logger, category, message)

    def _log_error(self, category, message):
        if self.log_error is not None:
            self.log_error(self.logger, category, message)

    def _log_warning(self, category, message):
        if self.log_warning is not None:
            self.log_warning(self.logger, category, message)

    def find_port(self):
        """
        Busca primero el dispositivo estable de /dev/serial/by-id.
        Si no existe, utiliza /dev/ttyACM*.
        """

        by_id = glob.glob("/dev/serial/by-id/*")

        for device in by_id:
            try:
                real = os.path.realpath(device)

                if "ttyACM" in os.path.basename(real):
                    return device

            except Exception:
                continue

        devices = sorted(glob.glob("/dev/ttyACM*"))

        if devices:
            return devices[0]

        return None

    def mark_disconnected(self, reason=None):
        if self.port is not None:
            try:
                self.port.close()
            except Exception:
                pass

        self.port = None
        self.connected = False
        self.rx_buffer = ""
        self.state = "DISCONNECTED"

        self.disconnect_count += 1
        self.recovery_pending = True

        now = time.time()

        if (
            reason
            and
            now - self.last_error_log >= self.error_log_interval
        ):
            print(
                "RP2040 desconectado: %s | perdidas=%d"
                % (reason, self.disconnect_count)
            )
            self.last_error_log = now

    def connect(self, force=False):
        now = time.time()

        if (
            not force
            and
            now - self.last_connect_attempt < self.reconnect_interval
        ):
            return False

        self.last_connect_attempt = now

        device = self.find_port()

        if device is None:
            self.connected = False
            self.port = None
            self.state = "DISCONNECTED"
            return False

        self.state = "CONNECTING"

        try:
            if self.port:
                try:
                    self.port.close()
                except Exception:
                    pass

            self.port = serial.Serial(
                device,
                self.baudrate,
                timeout=1,
                write_timeout=2,
            )

            self.last_device = device
            self.state = "RECONNECTING"

            # Abrir el puerto no demuestra que exista comunicacion.
            # La comunicacion se valida con write + flush en send().

            self.connected = False

            self._log_info(
                "SERIAL",
                "RP2040 puerto abierto: %s" % device,
            )

            return True

        except Exception as e:
            self.port = None
            self.connected = False
            self.state = "DISCONNECTED"

            self._log_error(
                "SERIAL",
                "Error conectando RP2040: %s" % e,
            )

            return False

    def send(self, packet):
        if self.port is None:
            if not self.connect():
                self.fail_safe = True
                self.state = "FAIL-SAFE"
                return False

        try:
            self.port.write(packet.encode("ascii"))
            self.port.flush()

            was_connected = self.connected
            was_recovering = self.recovery_pending

            self.last_tx_ok = time.time()
            self.connected = True
            self.fail_safe = False
            self.state = "CONNECTED"

            if was_recovering or not was_connected:
                self.reconnect_count += 1
                self.recovery_pending = False

                self._log_info(
                    "SERIAL",
                    "RP2040 comunicacion recuperada | "
                    "reconexiones=%d"
                    % self.reconnect_count,
                )

            return True

        except Exception as e:
            self._log_error(
                "SERIAL",
                "Error transmitiendo al RP2040: %s" % e,
            )

            self.mark_disconnected(str(e))

            self.fail_safe = True
            self.state = "FAIL-SAFE"

            return False

    def watchdog(self):
        if self.last_tx_ok == 0:
            self.fail_safe = True
            self.state = "FAIL-SAFE"
            return False

        elapsed = time.time() - self.last_tx_ok

        if elapsed > self.watchdog_timeout:

            if not self.fail_safe:
                self._log_warning(
                    "SERIAL",
                    "WATCHDOG RP2040: sin comunicacion "
                    "%.1fs -> FAIL-SAFE / RECONECTANDO"
                    % elapsed,
                )

            if self.port is not None:
                try:
                    self.port.close()
                except Exception:
                    pass

            self.port = None
            self.connected = False
            self.rx_buffer = ""

            self.fail_safe = True
            self.state = "FAIL-SAFE"
            self.recovery_pending = True

            return False

        return True

    def diagnostic(self):
        now = time.time()

        if now - self.last_diagnostic < self.diagnostic_interval:
            return

        self.last_diagnostic = now

        if self.status_formatter is None:
            return

        message = self.status_formatter(
            self.state,
            self.connected,
            self.fail_safe,
            self.last_device,
            now - self.last_tx_ok if self.last_tx_ok else None,
            self.disconnect_count,
            self.reconnect_count,
        )

        self._log_info(
            "SERIAL",
            message,
        )

    def read_mode_commands(self):
        """
        Devuelve una lista de modos recibidos desde el RP2040.

        No modifica CURRENT_MODE directamente.
        """

        if self.port is None:
            return []

        try:
            waiting = self.port.in_waiting

            if waiting <= 0:
                return []

            data = self.port.read(waiting)

            if not data:
                return []

            self.rx_buffer += data.decode(
                "ascii",
                errors="ignore",
            )

            modes = []

            while "\n" in self.rx_buffer:
                line, self.rx_buffer = self.rx_buffer.split(
                    "\n",
                    1,
                )

                line = line.strip()

                if line == "!MODE|AUTO":
                    modes.append(MODE_AUTO)

                elif line == "!MODE|SILENT":
                    modes.append(MODE_SILENT)

                elif line == "!MODE|TURBO":
                    modes.append(MODE_TURBO)

            return modes

        except Exception as e:
            self.mark_disconnected(
                "RX: %s" % e
            )

            return []
