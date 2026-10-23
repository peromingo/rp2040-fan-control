def format_serial_status(
    serial_state,
    serial_connected,
    serial_fail_safe,
    serial_last_device,
    last_tx_age,
    serial_disconnect_count,
    serial_reconnect_count,
):
    """
    Construye una línea de diagnóstico del enlace serie con el RP2040.

    Esta función no modifica ningún estado ni realiza operaciones de E/S.
    """

    device = serial_last_device or "--"
    age_text = "--" if last_tx_age is None else "%.1fs" % last_tx_age

    return (
        "SERIAL: estado=%s conectado=%s fail-safe=%s "
        "puerto=%s ultimaTX=%s desconexiones=%d reconexiones=%d"
        % (
            serial_state,
            "SI" if serial_connected else "NO",
            "SI" if serial_fail_safe else "NO",
            device,
            age_text,
            serial_disconnect_count,
            serial_reconnect_count,
        )
    )


def format_v28_summary(
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
):
    """
    Construye el resumen estadístico V2.8.

    Esta función no modifica estados ni realiza operaciones de E/S.
    """

    def value_text(value, suffix=""):
        if value is None:
            return "--"
        return "%s%s" % (value, suffix)

    return (
        "V2.8 DIAG: "
        "F1 T=%s/%sC maxH=%s(%s) FAN=%s-%s%% | "
        "F2 T=%s/%sC maxH=%s(%s) FAN=%s-%s%% | "
        "ANT +5=%d +10=%d"
        % (
            value_text(fan1_temp_min),
            value_text(fan1_temp_max),
            value_text(fan1_temp_max),
            fan1_temp_max_disk or "--",
            value_text(fan1_min),
            value_text(fan1_max),
            value_text(fan2_temp_min),
            value_text(fan2_temp_max),
            value_text(fan2_temp_max),
            fan2_temp_max_disk or "--",
            value_text(fan2_min),
            value_text(fan2_max),
            v28_intelligent_plus5_count,
            v28_intelligent_plus10_count,
        )
    )



def cycle_update(duration, cycle_min, cycle_max, cycle_sum, cycle_count):
    """
    Actualiza las estadisticas de duracion de ciclo.

    No modifica estado externo ni realiza operaciones de E/S.
    Devuelve: (cycle_min, cycle_max, cycle_sum, cycle_count).
    """

    if cycle_min is None or duration < cycle_min:
        cycle_min = duration

    if cycle_max is None or duration > cycle_max:
        cycle_max = duration

    cycle_sum += duration
    cycle_count += 1

    return cycle_min, cycle_max, cycle_sum, cycle_count


def format_cycle_summary(duration, cycle_min, cycle_max, cycle_sum, cycle_count):
    """
    Construye el resumen de duracion de ciclo.

    No modifica estado ni realiza operaciones de E/S.
    """

    if duration is None:
        duration_text = "--"
    else:
        duration_text = "%.1fs" % duration

    if cycle_min is None:
        min_text = "--"
    else:
        min_text = "%.1fs" % cycle_min

    if cycle_count <= 0:
        avg_text = "--"
    else:
        avg_text = "%.1fs" % (cycle_sum / cycle_count)

    if cycle_max is None:
        max_text = "--"
    else:
        max_text = "%.1fs" % cycle_max

    return (
        "CYCLE: duracion=%s min=%s avg=%s max=%s ciclos=%d"
        % (
            duration_text,
            min_text,
            avg_text,
            max_text,
            cycle_count,
        )
    )


def format_smart_summary(smart_disk_count, smart_valid_count):
    """
    Construye el resumen diagnostico SMART.

    No modifica estado ni realiza operaciones de E/S.
    """

    return (
        "SMART: discos=%d validas=%d"
        % (
            smart_disk_count,
            smart_valid_count,
        )
    )


def format_summary(
    serial_state,
    serial_fail_safe,
    serial_tx_ok,
    serial_disconnect_count,
    serial_reconnect_count,
    fan1_current,
    fan2_current,
    fan1_temperature,
    fan2_temperature,
    smart_disk_count,
    smart_valid_count,
    disk_status_text,
    cycle_min,
    cycle_max,
    cycle_sum,
    cycle_count,
    fan1_temp_min=None,
    fan1_temp_max=None,
    fan1_temp_max_disk=None,
    fan1_min=None,
    fan1_max=None,
    fan2_temp_min=None,
    fan2_temp_max=None,
    fan2_temp_max_disk=None,
    fan2_min=None,
    fan2_max=None,
    intelligent_plus5_count=0,
    intelligent_plus10_count=0,
):
    """Construye el resumen general V3.0.

    Solo formatea datos ya recopilados.
    No modifica estado ni realiza operaciones de E/S.
    """

    def temp_text(value):
        if value is None:
            return "--"
        return "%.1fC" % value

    if cycle_min is None:
        min_text = "--"
    else:
        min_text = "%.1fs" % cycle_min

    if cycle_count <= 0:
        avg_text = "--"
    else:
        avg_text = "%.1fs" % (cycle_sum / cycle_count)

    if cycle_max is None:
        max_text = "--"
    else:
        max_text = "%.1fs" % cycle_max

    def history_temp_text(minimum, maximum, disk):
        if minimum is None and maximum is None:
            return "--"

        min_value = "--" if minimum is None else "%.1fC" % minimum
        max_value = "--" if maximum is None else "%.1fC" % maximum
        disk_text = disk or "--"

        return "%s/%s(%s)" % (min_value, max_value, disk_text)

    def history_fan_text(minimum, maximum):
        if minimum is None and maximum is None:
            return "--"

        min_value = "--" if minimum is None else "%d%%" % minimum
        max_value = "--" if maximum is None else "%d%%" % maximum

        return "%s-%s" % (min_value, max_value)

    return (
        "RP2040=%s fail-safe=%s TX=%s desconexiones=%d reconexiones=%d | "
        "FAN1=%d%% T1=%s HIST-T1=%s HIST-FAN1=%s | "
        "FAN2=%d%% T2=%s HIST-T2=%s HIST-FAN2=%s | "
        "SMART=%d/%d | DISKS=%s | "
        "TREND=+5:%d +10:%d | "
        "CYCLE=min=%s avg=%s max=%s ciclos=%d"
        % (
            serial_state,
            "SI" if serial_fail_safe else "NO",
            "OK" if serial_tx_ok else "NO",
            serial_disconnect_count,
            serial_reconnect_count,
            fan1_current,
            temp_text(fan1_temperature),
            history_temp_text(
                fan1_temp_min,
                fan1_temp_max,
                fan1_temp_max_disk,
            ),
            history_fan_text(fan1_min, fan1_max),
            fan2_current,
            temp_text(fan2_temperature),
            history_temp_text(
                fan2_temp_min,
                fan2_temp_max,
                fan2_temp_max_disk,
            ),
            history_fan_text(fan2_min, fan2_max),
            smart_disk_count,
            smart_valid_count,
            disk_status_text or "--",
            intelligent_plus5_count,
            intelligent_plus10_count,
            min_text,
            avg_text,
            max_text,
            cycle_count,
        )
    )
