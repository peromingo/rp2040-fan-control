from .utils import run_cmd


def get_disk_temp(device):
    """
    Obtiene la temperatura SMART del disco.

    Usa exclusivamente el RAW_VALUE real de los atributos
    SMART 194 (Temperature_Celsius) o 190 (Airflow_Temperature_Cel).
    Ignora completamente los valores historicos dentro de parentesis.
    """
    out = run_cmd(["smartctl", "-A", device])
    if not out:
        return None

    for line in out.splitlines():
        parts = line.split()

        if not parts or parts[0] not in ("194", "190"):
            continue

        # En la salida de smartctl el RAW_VALUE aparece inmediatamente
        # antes del bloque de informacion entre parentesis.
        raw_value = None

        for index, value in enumerate(parts[1:], start=1):
            if value.startswith("("):
                if index > 0:
                    candidate = parts[index - 1]
                    try:
                        raw_value = int(candidate)
                    except ValueError:
                        raw_value = None
                break

        # Fallback para formatos sin bloque entre parentesis.
        if raw_value is None:
            try:
                raw_value = int(parts[-1])
            except (ValueError, IndexError):
                raw_value = None

        if raw_value is not None and -20 <= raw_value <= 100:
            return raw_value

    return None

def read_disk_temperature(device):
    """
    Alias explícito para la lectura de temperatura SMART.
    """

    return get_disk_temp(device)


def smart_info(device):
    """
    Devuelve la salida SMART básica del dispositivo.

    Se reserva para diagnósticos controlados.
    """

    return run_cmd([
        "smartctl",
        "-i",
        device
    ])


def smart_health(device):
    """
    Devuelve la comprobación SMART de salud del dispositivo.

    Se reserva para diagnósticos controlados.
    """

    return run_cmd([
        "smartctl",
        "-H",
        device
    ])


def smart_attributes(device):
    """
    Devuelve los atributos SMART completos.

    No debe ejecutarse en cada ciclo normal.
    """

    return run_cmd([
        "smartctl",
        "-A",
        device
    ])


def smart_full_report(device):
    """
    Devuelve el informe SMART completo.

    Debe utilizarse únicamente bajo demanda.
    """

    return run_cmd([
        "smartctl",
        "-x",
        device
    ])
