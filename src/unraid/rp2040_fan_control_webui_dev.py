#!/usr/bin/env python3

# V2.5.3 - RECUPERACION REAL RP2040 / SERIAL

# ============================================================
# V2.5.0 - ROBUSTEZ RP2040 / SERIAL
# ============================================================

import os
import time
import fcntl

LOCK_FILE = os.environ.get("RP2040_LOCK_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "rp2040_fan_control.lock"))
_instance_lock = None

def acquire_instance_lock():
    global _instance_lock

    _instance_lock = open(LOCK_FILE, "w")

    try:
        fcntl.flock(_instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        _instance_lock.close()
        _instance_lock = None
        print("V3.0 ya esta en ejecucion; segunda instancia abortada.")
        return False

    _instance_lock.write("%d\n" % os.getpid())
    _instance_lock.flush()
    return True


from fan_control.disk_state import (
    read_disk_states as module_read_disk_states,
    disk_state as module_disk_state,
)

from fan_control.logger import setup_logger, log_info, log_error, log_warning
from fan_control.diagnostics import (
    format_serial_status,
    format_v28_summary,
    cycle_update,
    format_cycle_summary,
    format_smart_summary,
    format_summary,
)
from fan_control.temperature import read_temperatures as module_read_temperatures, detect_disks as module_detect_disks, unraid_id_for_identity
from fan_control.utils import (
    cpu_temperature,
    system_info,
    ram_info,
    primary_ip,
    uptime_text,
    docker_counts,
    unraid_array_info,
)
from fan_control.fan_controller import FanController
from fan_control.serial_manager import SerialManager
from fan_control.ipc import RuntimeIPC, acknowledge_transmitted_mode

BAUDRATE = 115200

# V2.5.0 - comunicacion robusta
SERIAL_RECONNECT_INTERVAL = 3
SERIAL_WATCHDOG_TIMEOUT = 6
SERIAL_ERROR_LOG_INTERVAL = 15
SUMMARY_INTERVAL = 300

# ============================================================
# DISCOS CONTROLADOS
# Identificacion persistente mediante modelo + numero de serie
# ============================================================

from fan_control.site_config_local import FAN1_DISKS, FAN2_DISKS, validate_disk_config

validate_disk_config()

ALL_DISKS = FAN1_DISKS | FAN2_DISKS

# ============================================================
# CURVA DE TEMPERATURA
# ============================================================

TEMP_MIN = 30
TEMP_MAX = 48
TEMP_ALERT = 55

# ============================================================
# V2.3.2 - ALERTAS TERMICAS
# ============================================================
HDD_WARNING_TEMP = 50
HDD_CRITICAL_TEMP = 55

CPU_WARNING_TEMP = 80
CPU_CRITICAL_TEMP = 90

THERMAL_ALERT_SECONDS = 6
THERMAL_ALERT_REPEAT_SECONDS = 30

# ============================================================
# V2.4.1 - MODOS DE VENTILACION
# ============================================================

MODE_AUTO = "AUTO"
MODE_SILENT = "SILENT"
MODE_TURBO = "TURBO"

CURRENT_MODE = MODE_AUTO

# Limite de ventilacion en modo SILENT.
SILENT_MAX_FAN = 40

MIN_FAN = 10
MAX_FAN = 100

# Subida maxima por ciclo: +15%
# Bajada maxima por ciclo: -10%
RAMP_UP = 15
RAMP_DOWN = 10

# Histéresis del objetivo del ventilador.
# Evita pequeños cambios continuos cuando la temperatura
# oscila ligeramente alrededor de un mismo punto.
FAN_HYSTERESIS = 5

UPDATE_INTERVAL = 2
SMART_INTERVAL = 10
SMART_DIAGNOSTIC_INTERVAL = 300
DISK_STATE_INTERVAL = 10

# ============================================================
# ESTADO
# ============================================================

temps = {}
disk_paths = {}

fan1_current = 40

# Objetivos anteriores utilizados por la histéresis.
fan1_target_previous = None
fan2_target_previous = None
fan2_current = 40

last_smart = 0
last_smart_diagnostic = 0

# V3.0 - diagnostico SMART (solo observacion)
smart_last_read = None
smart_disk_count = 0
smart_valid_count = 0
smart_error_count = 0

# V2.7 - gestion inteligente por tendencia termica.
# Se actualizan solamente con lecturas SMART validas.
fan1_temperature_previous = None
fan2_temperature_previous = None

# V2.8 - estadisticas diagnosticas (solo observacion)
V28_DIAGNOSTIC_INTERVAL = 60
last_v28_diagnostic = 0

# V3.0 - estadisticas de duracion de ciclo (solo diagnostico)
CYCLE_DIAG_INTERVAL = 300
last_cycle_diag = 0
last_summary = 0
cycle_min = None
cycle_max = None
cycle_sum = 0.0
cycle_count = 0

fan1_temp_min = None
fan1_temp_max = None
fan1_temp_max_disk = None

fan2_temp_min = None
fan2_temp_max = None
fan2_temp_max_disk = None

fan1_min = None
fan1_max = None
fan2_min = None
fan2_max = None

v28_intelligent_plus5_count = 0
v28_intelligent_plus10_count = 0

# V2.5.3 - diagnostico serial
SERIAL_DIAGNOSTIC_INTERVAL = 30

# Logger V3.0.
LOGGER = None

# V2.4.19 - estado fisico y estado Unraid de los discos.
disk_states = {}
unraid_disk_states = {}
last_disk_state_check = 0


# ============================================================
# COMANDOS
# ============================================================



# ============================================================
# DETECCION DE HDD
# ============================================================



# ============================================================
# V2.4.19 - ESTADO STANDBY / ACTIVIDAD
# ============================================================


def read_disk_states():
    """
    Wrapper compatible con el código V2.9/V3.0.

    Usa el módulo fan_control.disk_state y conserva
    las variables globales utilizadas por la OLED.
    """
    global disk_paths
    global disk_states
    global unraid_disk_states

    if not disk_paths:
        disk_paths = module_detect_disks(ALL_DISKS)

    states, unraid = module_read_disk_states(
        ALL_DISKS,
        disk_paths
    )

    disk_states = states
    unraid_disk_states = unraid


def disk_state(identity):
    """Estado corto para OLED: ACTIVE / STBY / ERR / UNKNOWN."""
    return module_disk_state(identity, disk_states)


# ============================================================
# TEMPERATURA POR GRUPO
# ============================================================

def group_temperature(group):

    values = []

    for identity in group:

        if identity in temps:
            values.append(temps[identity])

    if not values:
        return None

    return max(values)


# ============================================================
# CURVA
# ============================================================

THERMAL_CURVE = (
    (30, 30),
    (32, 32),
    (35, 35),
    (38, 40),
    (40, 45),
    (42, 50),
    (44, 60),
    (46, 75),
    (48, 90),
    (50, 100),
)


# V3.0 - controlador modular de ventiladores.
# Mantiene los mismos parametros del daemon original.
fan_controller = FanController(
    thermal_curve=THERMAL_CURVE,
    temp_alert=TEMP_ALERT,
    hdd_warning_temp=HDD_WARNING_TEMP,
    silent_max_fan=SILENT_MAX_FAN,
    ramp_up=RAMP_UP,
    ramp_down=RAMP_DOWN,
    fan_hysteresis=FAN_HYSTERESIS,
)



def update_v28_temperature_stats(group, temperature, fan_value):
    """Actualiza estadisticas V2.8 sin modificar ninguna logica de control."""
    global fan1_temp_min
    global fan1_temp_max
    global fan1_temp_max_disk
    global fan2_temp_min
    global fan2_temp_max
    global fan2_temp_max_disk
    global fan1_min
    global fan1_max
    global fan2_min
    global fan2_max

    if temperature is not None:
        if group == FAN1_DISKS:
            if fan1_temp_min is None or temperature < fan1_temp_min:
                fan1_temp_min = temperature

            if fan1_temp_max is None or temperature > fan1_temp_max:
                fan1_temp_max = temperature

            for identity in group:
                if temps.get(identity) == temperature:
                    fan1_temp_max_disk = disk_text(identity)
                    break

        elif group == FAN2_DISKS:
            if fan2_temp_min is None or temperature < fan2_temp_min:
                fan2_temp_min = temperature

            if fan2_temp_max is None or temperature > fan2_temp_max:
                fan2_temp_max = temperature

            for identity in group:
                if temps.get(identity) == temperature:
                    fan2_temp_max_disk = disk_text(identity)
                    break

    if group == FAN1_DISKS:
        if fan1_min is None or fan_value < fan1_min:
            fan1_min = fan_value
        if fan1_max is None or fan_value > fan1_max:
            fan1_max = fan_value

    elif group == FAN2_DISKS:
        if fan2_min is None or fan_value < fan2_min:
            fan2_min = fan_value
        if fan2_max is None or fan_value > fan2_max:
            fan2_max = fan_value


# ============================================================
# V2.7 - GESTION INTELIGENTE POR TENDENCIA TERMICA
# ============================================================









# ============================================================
# V2.4.1 - MODOS DE VENTILACION
# ============================================================



# ============================================================
# SERIAL RP2040
# ============================================================

# ============================================================
# INFORMACION OLED
# ============================================================


















def disk_text(identity):

    model, serial = identity

    names = {
        "ST500LT012-1DG142": "ST500",
        "HGST HTS541010A9E680": "HGST",
        "TOSHIBA MQ01ABF050": "TOSHIBA",
        "ST1000NX0423         00YK025D7A01874LEN": "ST1000",
        "ST1000NX0423": "ST1000",
    }

    return names.get(
        model,
        model[:8]
    )


def format_disk_status_summary():
    """Construye el estado resumido de los discos.

    Usa exclusivamente estados ya recopilados; no realiza E/S.
    """

    items = []

    for identity in sorted(ALL_DISKS, key=disk_text):
        name = disk_text(identity)
        physical = disk_state(identity)
        unraid_id = unraid_id_for_identity(identity)
        unraid = unraid_disk_states.get(unraid_id, "UNKNOWN")
        items.append("%s:%s/%s" % (name, physical, unraid))

    return " ".join(items)


def disk_temperature(identity):

    value = temps.get(identity)

    if value is None:
        return "--"

    return "%dC" % value


def storage_lines():

    lines = []

    ordered = [
        ("F1", FAN1_DISKS),
        ("F2", FAN2_DISKS),
    ]

    for fan_name, group in ordered:

        for identity in sorted(
            group,
            key=lambda x: disk_text(x)
        ):

            lines.append(
                "%s %s %s" % (
                    fan_name,
                    disk_text(identity),
                    disk_temperature(identity)
                )
            )

    return lines


def storage_page():

    t1 = group_temperature(FAN1_DISKS)
    t2 = group_temperature(FAN2_DISKS)

    l1 = "F1 %sC" % (
        "--" if t1 is None else t1
    )

    l2 = "F2 %sC" % (
        "--" if t2 is None else t2
    )

    return l1, l2


last_thermal_alert_key = None
last_thermal_alert_sent = 0

def thermal_alert():
    """
    V2.3.2 - Genera una alerta termica para el OLED.

    CRITICAL tiene prioridad sobre WARNING.
    Devuelve None si todo esta dentro de limites.
    """

    t1 = group_temperature(FAN1_DISKS)
    t2 = group_temperature(FAN2_DISKS)
    cpu = cpu_temperature()

    # --------------------------------------------------------
    # CRITICAL HDD
    # --------------------------------------------------------
    if t1 is not None and t1 >= HDD_CRITICAL_TEMP:
        return (
            "CRITICAL HDD F1",
            "TEMP %dC" % t1,
            "FAN1 100%"
        )

    if t2 is not None and t2 >= HDD_CRITICAL_TEMP:
        return (
            "CRITICAL HDD F2",
            "TEMP %dC" % t2,
            "FAN2 100%"
        )

    # --------------------------------------------------------
    # CRITICAL CPU
    # --------------------------------------------------------
    if cpu is not None and cpu >= CPU_CRITICAL_TEMP:
        return (
            "CRITICAL CPU",
            "TEMP %dC" % cpu,
            "CPU HOT!"
        )

    # --------------------------------------------------------
    # WARNING HDD
    # --------------------------------------------------------
    if t1 is not None and t1 >= HDD_WARNING_TEMP:
        return (
            "WARNING HDD F1",
            "TEMP %dC" % t1,
            "FAN1 ALERT"
        )

    if t2 is not None and t2 >= HDD_WARNING_TEMP:
        return (
            "WARNING HDD F2",
            "TEMP %dC" % t2,
            "FAN2 ALERT"
        )

    # --------------------------------------------------------
    # WARNING CPU
    # --------------------------------------------------------
    if cpu is not None and cpu >= CPU_WARNING_TEMP:
        return (
            "WARNING CPU",
            "TEMP %dC" % cpu,
            "CPU HOT!"
        )

    return None


def build_packet():

    t1 = group_temperature(FAN1_DISKS)
    t2 = group_temperature(FAN2_DISKS)

    cpu = cpu_temperature()
    ram = ram_info()
    ip = primary_ip()
    up = uptime_text()
    running, total = docker_counts()
    array = unraid_array_info()

    if ram is None:
        ram_line = "RAM --"
    else:
        used_mb, total_mb, ram_percent = ram

        ram_line = "RAM %d%% %.1f/%.1fG" % (
            ram_percent,
            used_mb / 1024.0,
            total_mb / 1024.0
        )

    cpu_line = (
        "CPU %dC" % cpu
        if cpu is not None
        else "CPU --"
    )

    # --------------------------------------------------------
    # V2.1.2 - 8 paginas OLED
    # --------------------------------------------------------

    page0 = [
        "UNRAID SYSTEM",
        system_info(),
        "FAN %d/%d" % (
            fan1_current,
            fan2_current
        )
    ]

    page1 = [
        "CPU / RAM",
        cpu_line,
        ram_line
    ]

    # Los cuatro discos se muestran individualmente.
    all_disks = []

    for identity in FAN1_DISKS:
        all_disks.append(("F1", identity))

    for identity in FAN2_DISKS:
        all_disks.append(("F2", identity))

    all_disks.sort(
        key=lambda item: disk_text(item[1])
    )

    disk_pages = []

    for index, item in enumerate(all_disks[:4]):

        fan_name, identity = item
        temp = disk_temperature(identity)

        state = disk_state(identity)
        state_line = "%s %s" % (temp, state)

        disk_pages.append([
            "HDD %d/4 %s" % (
                index + 1,
                fan_name
            ),
            disk_text(identity),
            state_line[:16]
        ])

    while len(disk_pages) < 4:
        disk_pages.append([
            "HDD %d/4" % (len(disk_pages) + 1),
            "NO CONFIGURADO",
            "--"
        ])

    page2 = disk_pages[0]
    page3 = disk_pages[1]
    page4 = disk_pages[2]
    page5 = disk_pages[3]

    page6 = [
        "DOCKER / ARRAY",
        "DOCKER %d/%d" % (
            running,
            total
        ),
        array
    ]

    ip_line = (
        "IP %s" % ip
        if ip is not None
        else "IP --"
    )

    page7 = [
        "IP / UPTIME",
        ip_line,
        up
    ]

    pages = [
        page0,
        page1,
        page2,
        page3,
        page4,
        page5,
        page6,
        page7
    ]

    encoded_pages = []

    for page in pages:

        lines = []

        for line in page:

            clean = str(line).encode(
                "ascii",
                "replace"
            ).decode("ascii")

            lines.append(
                clean[:16]
            )

        encoded_pages.append(
            "|".join(lines)
        )

    return "#".join(encoded_pages)


def v28_diagnostic():
    """Resumen periodico V2.8. Solo diagnostico, sin modificar el control."""

    message = format_v28_summary(
        fan1_temp_min,
        fan1_temp_max,
        fan1_temp_max_disk,
        fan1_min,
        fan1_max,
        fan2_temp_min,
        fan2_temp_max,
        fan2_temp_max_disk,
        fan2_min,
        fan2_max,
        v28_intelligent_plus5_count,
        v28_intelligent_plus10_count,
    )

    log_info(
        LOGGER,
        "SUMMARY",
        message
    )


def main():
    global CURRENT_MODE

    global LOGGER
    global fan1_target_previous
    global fan2_target_previous

    global temps
    global disk_paths
    global fan1_current
    global fan2_current
    global last_smart
    global last_smart_diagnostic
    global smart_last_read
    global smart_disk_count
    global smart_valid_count
    global smart_error_count
    global last_disk_state_check
    global fan1_temperature_previous
    global fan2_temperature_previous
    global v28_intelligent_plus5_count
    global v28_intelligent_plus10_count
    global last_cycle_diag
    global last_summary
    global cycle_min
    global cycle_max
    global cycle_sum
    global cycle_count

    LOGGER = setup_logger()

    # IPC web: fallo de la interfaz no debe interrumpir el control térmico.
    runtime_ipc = None
    pending_mode_request = None
    try:
        runtime_ipc = RuntimeIPC()
        runtime_ipc.ensure_runtime_dir()
    except Exception as exc:
        log_warning(LOGGER, "IPC", "IPC no disponible: %s" % exc)


    print("========================================")
    print(" RP2040 FAN CONTROL")
    print("========================================")

    serial_manager = SerialManager(
        baudrate=BAUDRATE,
        reconnect_interval=SERIAL_RECONNECT_INTERVAL,
        watchdog_timeout=SERIAL_WATCHDOG_TIMEOUT,
        error_log_interval=SERIAL_ERROR_LOG_INTERVAL,
        diagnostic_interval=SERIAL_DIAGNOSTIC_INTERVAL,
        logger=LOGGER,
        log_info=log_info,
        log_error=log_error,
        log_warning=log_warning,
        status_formatter=format_serial_status,
    )

    serial_manager.connect()

    # Arranque seguro
    fan1_current = 100
    fan2_current = 100

    serial_manager.send(
        "UNRAID SYSTEM|INICIANDO...|FANS 100"
        "#SISTEMA|SMART|LEYENDO"
        "#ALMACENAMIENTO|SMART|LEYENDO"
        "#DOCKER SYSTEM|INICIANDO|FANS 100"
        "@100,100\n"
    )

    time.sleep(3)

    # Primera lectura de estados antes de mostrar las paginas HDD.
    read_disk_states()
    last_disk_state_check = time.time()

    while True:

        cycle_started = time.perf_counter()
        now = time.time()

        # ====================================================
        # V2.5.2 - WATCHDOG RP2040 / RECUPERACION
        # ====================================================
        serial_manager.watchdog()

        # ====================================================
        # V2.5.3 - DIAGNOSTICO SERIAL
        # ====================================================
        serial_manager.diagnostic()

        # ====================================================
        # V2.8 - DIAGNOSTICO TERMICO / VENTILADORES
        # ====================================================
        global last_v28_diagnostic

        if now - last_v28_diagnostic >= V28_DIAGNOSTIC_INTERVAL:
            v28_diagnostic()
            last_v28_diagnostic = now

        # ====================================================
        # V2.4.2 - COMANDOS DE MODO DESDE RP2040
        # ====================================================
        for mode in serial_manager.read_mode_commands():

            if mode == MODE_AUTO:

                CURRENT_MODE = MODE_AUTO
                log_info(
                    LOGGER,
                    "CONTROL",
                    "MODE: AUTO"
                )

            elif mode == MODE_SILENT:

                CURRENT_MODE = MODE_SILENT
                log_info(
                    LOGGER,
                    "CONTROL",
                    "MODE: SILENT"
                )

            elif mode == MODE_TURBO:

                CURRENT_MODE = MODE_TURBO
                log_info(
                    LOGGER,
                    "CONTROL",
                    "MODE: TURBO"
                )

        # Solicitudes del panel: se aplican dentro del bucle del daemon.
        # Se procesan después de los botones físicos del RP2040, por lo que
        # una solicitud web válida tiene prioridad durante este ciclo.
        if runtime_ipc is not None:
            try:
                request = runtime_ipc.take_mode_request()
                if request is not None:
                    requested_mode = request["mode"]
                    if requested_mode in (MODE_AUTO, MODE_SILENT, MODE_TURBO):
                        CURRENT_MODE = requested_mode
                        pending_mode_request = request
                        log_info(LOGGER, "CONTROL", "MODE solicitado desde panel: %s" % CURRENT_MODE)
                    else:
                        runtime_ipc.acknowledge_mode_request(
                            request["request_id"], CURRENT_MODE, False,
                            "Modo rechazado por el daemon."
                        )
            except Exception as exc:
                # La integración web es secundaria: nunca dejar caer el bucle de ventilación.
                log_warning(LOGGER, "IPC", "Error procesando solicitud web: %s" % exc)

        # SMART cada 10 segundos
        if now - last_smart >= SMART_INTERVAL:

            disk_paths, newtemps = module_read_temperatures(ALL_DISKS)

            smart_last_read = time.time()
            smart_disk_count = len(disk_paths)
            smart_valid_count = len(newtemps)

            if now - last_smart_diagnostic >= SMART_DIAGNOSTIC_INTERVAL:
                log_info(
                    LOGGER,
                    "SMART",
                    format_smart_summary(
                        smart_disk_count,
                        smart_valid_count,
                    )
                )
                last_smart_diagnostic = now

            if newtemps:

                temps = newtemps

                # V2.8 - contar cada tendencia solo una vez por lectura SMART.
                new_fan1_temperature = group_temperature(FAN1_DISKS)
                new_fan2_temperature = group_temperature(FAN2_DISKS)

                if fan1_temperature_previous is not None and new_fan1_temperature is not None:
                    delta1 = new_fan1_temperature - fan1_temperature_previous
                    if delta1 >= 2:
                        v28_intelligent_plus10_count += 1
                    elif delta1 >= 1:
                        v28_intelligent_plus5_count += 1

                if fan2_temperature_previous is not None and new_fan2_temperature is not None:
                    delta2 = new_fan2_temperature - fan2_temperature_previous
                    if delta2 >= 2:
                        v28_intelligent_plus10_count += 1
                    elif delta2 >= 1:
                        v28_intelligent_plus5_count += 1

                # V2.9 - guardar la temperatura anterior del grupo
                # usando la lectura SMART ya calculada.
                fan1_temperature_previous = new_fan1_temperature
                fan2_temperature_previous = new_fan2_temperature

                print("Discos detectados:")

                for identity, device in disk_paths.items():

                    temp = temps.get(identity, None)

                    print(
                        "  %-8s %-20s %s = %sC" % (
                            device,
                            identity[0][:20],
                            identity[1],
                            "--" if temp is None else temp
                        )
                    )

            else:

                print(
                    "ERROR: no se han encontrado "
                    "los 4 HDD configurados"
                )

                temps = {}

            last_smart = now

        # ====================================================
        # V2.4.19 - ESTADO STANDBY / ACTIVIDAD
        # ====================================================
        if now - last_disk_state_check >= DISK_STATE_INTERVAL:
            read_disk_states()
            last_disk_state_check = now

        # FAN1
        t1 = group_temperature(FAN1_DISKS)
        raw_target1 = fan_controller.mode_temperature_to_fan(
            t1,
            CURRENT_MODE,
        )

        intelligent_target1 = fan_controller.intelligent_target(
            raw_target1,
            t1,
            fan1_temperature_previous
        )

        target1 = fan_controller.hysteresis_target(
            fan1_target_previous,
            intelligent_target1,
            t1
        )

        reason1 = fan_controller.control_reason(
            t1,
            raw_target1,
            intelligent_target1,
            target1,
            fan1_target_previous,
            fan1_temperature_previous,
            CURRENT_MODE,
        )

        if fan1_target_previous != target1:
            log_info(
                LOGGER,
                "CONTROL",
                "FAN1 objetivo: %s%% -> %s%% | temperatura=%.1fC | motivo=%s"
                % (
                    fan1_target_previous,
                    target1,
                    t1,
                    reason1,
                )
            )

        fan1_target_previous = target1

        # FAN2
        t2 = group_temperature(FAN2_DISKS)
        raw_target2 = fan_controller.mode_temperature_to_fan(
            t2,
            CURRENT_MODE,
        )

        intelligent_target2 = fan_controller.intelligent_target(
            raw_target2,
            t2,
            fan2_temperature_previous
        )

        target2 = fan_controller.hysteresis_target(
            fan2_target_previous,
            intelligent_target2,
            t2
        )

        reason2 = fan_controller.control_reason(
            t2,
            raw_target2,
            intelligent_target2,
            target2,
            fan2_target_previous,
            fan2_temperature_previous,
            CURRENT_MODE,
        )

        if fan2_target_previous != target2:
            log_info(
                LOGGER,
                "CONTROL",
                "FAN2 objetivo: %s%% -> %s%% | temperatura=%.1fC | motivo=%s"
                % (
                    fan2_target_previous,
                    target2,
                    t2,
                    reason2,
                )
            )

        fan2_target_previous = target2

        fan1_current = fan_controller.smooth(
            fan1_current,
            target1
        )

        fan2_current = fan_controller.smooth(
            fan2_current,
            target2
        )

        # V2.8 - registrar estadisticas sin alterar el control.
        update_v28_temperature_stats(
            FAN1_DISKS,
            t1,
            fan1_current
        )

        update_v28_temperature_stats(
            FAN2_DISKS,
            t2,
            fan2_current
        )

        # V3.0 - aplicar FAIL-SAFE antes de construir el paquete
        if serial_manager.fail_safe:
            fan1_current = 100
            fan2_current = 100

        packet = build_packet()

        # ========================================================
        # ========================================================
        # V2.3.2 - ALERTA TERMICA
        # ========================================================
        alert = thermal_alert()

        global last_thermal_alert_key
        global last_thermal_alert_sent

        now_alert = time.time()

        if alert is None:
            # Temperaturas normales: rearmar las alertas.
            last_thermal_alert_key = None
            last_thermal_alert_sent = 0
        else:
            alert_key = tuple(alert)
            send_alert = False

            # Nueva alerta o cambio de condicion.
            if last_thermal_alert_key != alert_key:
                send_alert = True

            # Si sigue activa, repetir como maximo cada 30 s.
            elif now_alert - last_thermal_alert_sent >= THERMAL_ALERT_REPEAT_SECONDS:
                send_alert = True

            if send_alert:
                packet += "!ALERT|%s|%s|%s" % alert
                last_thermal_alert_key = alert_key
                last_thermal_alert_sent = now_alert

        packet += "!MODE|%s" % CURRENT_MODE

        packet += "@%d,%d\n" % (
            fan1_current,
            fan2_current
        )

        tx_ok = serial_manager.send(packet)
        if not tx_ok:

            log_warning(
                LOGGER,
                "CONTROL",
                "FAIL-SAFE aplicado: FAN1=100%% FAN2=100%%"
            )

            # ====================================================
            # V2.5.0 - FAIL-SAFE
            # ====================================================
            # El daemon mantiene el estado logico a maxima
            # proteccion mientras intenta recuperar el RP2040.
            fan1_current = 100
            fan2_current = 100

        elif serial_manager.fail_safe:

            # Si la comunicacion vuelve, send_packet() ya ha
            # actualizado el estado. El siguiente ciclo vuelve
            # al control normal.
            fan1_current = 100
            fan2_current = 100

        # Confirmación de modo: solo tras una escritura serie satisfactoria.
        # El firmware actual no devuelve ACK; esto no prueba que el RP2040 procesara el paquete.
        if runtime_ipc is not None and pending_mode_request is not None:
            try:
                acknowledge_transmitted_mode(
                    runtime_ipc, pending_mode_request, CURRENT_MODE,
                    tx_ok, serial_manager.fail_safe
                )
            except Exception as exc:
                log_warning(LOGGER, "IPC", "No se pudo confirmar solicitud web: %s" % exc)
            finally:
                pending_mode_request = None

        # Snapshot para el panel. Solo contiene datos derivados del estado actual;
        # el panel no controla el puerto serie ni calcula la curva térmica.
        if runtime_ipc is not None:
            try:
                now_status = time.time()
                tx_age = (
                    round(now_status - serial_manager.last_tx_ok, 1)
                    if serial_manager.last_tx_ok else None
                )
                status = {
                    "schema_version": 1,
                    "daemon": {"state": "running", "version": "3.0-integrated-dev", "pid": os.getpid()},
                    "mode": CURRENT_MODE,
                    "fans": {
                        "fan1": {
                            "temperature_c": t1,
                            "command_percent": fan1_current,
                            "target_percent": target1,
                        },
                        "fan2": {
                            "temperature_c": t2,
                            "command_percent": fan2_current,
                            "target_percent": target2,
                        },
                    },
                    "cpu_temperature_c": cpu_temperature(),
                    "serial": {
                        "state": serial_manager.state,
                        "connected": bool(serial_manager.connected),
                        "fail_safe": bool(serial_manager.fail_safe),
                        "last_tx_age_seconds": tx_age,
                        "disconnect_count": serial_manager.disconnect_count,
                        "reconnect_count": serial_manager.reconnect_count,
                    },
                }
                runtime_ipc.publish_status(status)
            except Exception as exc:
                # Publicar estado es best-effort: nunca afecta a los ventiladores.
                log_warning(LOGGER, "IPC", "No se pudo publicar el estado: %s" % exc)

        print(
            "FAN1=%d%% FAN2=%d%% | "
            "T1=%s T2=%s" % (
                fan1_current,
                fan2_current,
                "--" if t1 is None else "%dC" % t1,
                "--" if t2 is None else "%dC" % t2
            )
        )

        time.sleep(UPDATE_INTERVAL)

        cycle_duration = time.perf_counter() - cycle_started

        cycle_min, cycle_max, cycle_sum, cycle_count = cycle_update(
            cycle_duration,
            cycle_min,
            cycle_max,
            cycle_sum,
            cycle_count,
        )

        cycle_now = time.time()
        if cycle_now - last_cycle_diag >= CYCLE_DIAG_INTERVAL:
            log_info(
                LOGGER,
                "CYCLE",
                format_cycle_summary(
                    cycle_duration,
                    cycle_min,
                    cycle_max,
                    cycle_sum,
                    cycle_count,
                )
            )
            last_cycle_diag = cycle_now

        if cycle_now - last_summary >= SUMMARY_INTERVAL:
            serial_tx_ok = (
                serial_manager.last_tx_ok > 0
                and (cycle_now - serial_manager.last_tx_ok) <= SERIAL_WATCHDOG_TIMEOUT
            )

            disk_status_text = format_disk_status_summary()

            log_info(
                LOGGER,
                "SUMMARY",
                format_summary(
                    serial_manager.state,
                    serial_manager.fail_safe,
                    serial_tx_ok,
                    serial_manager.disconnect_count,
                    serial_manager.reconnect_count,
                    fan1_current,
                    fan2_current,
                    group_temperature(FAN1_DISKS),
                    group_temperature(FAN2_DISKS),
                    smart_disk_count,
                    smart_valid_count,
                    disk_status_text,
                    cycle_min,
                    cycle_max,
                    cycle_sum,
                    cycle_count,
                    fan1_temp_min,
                    fan1_temp_max,
                    fan1_temp_max_disk,
                    fan1_min,
                    fan1_max,
                    fan2_temp_min,
                    fan2_temp_max,
                    fan2_temp_max_disk,
                    fan2_min,
                    fan2_max,
                    v28_intelligent_plus5_count,
                    v28_intelligent_plus10_count,
                )
            )

            last_summary = cycle_now


if __name__ == "__main__":
    if acquire_instance_lock():
        main()
