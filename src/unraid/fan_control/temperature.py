import re

from .utils import run_cmd
from .smart import get_disk_temp


def get_candidate_disks():
    """
    Busca discos rotacionales reales.

    ROTA=1
    TYPE=disk

    No se utilizan dispositivos /dev/sdX fijos.
    """

    out = run_cmd([
        "lsblk",
        "-d",
        "-n",
        "-o",
        "NAME,ROTA,TYPE"
    ])

    result = []

    for line in out.splitlines():
        parts = line.split()

        if len(parts) < 3:
            continue

        name, rota, dtype = parts[0], parts[1], parts[2]

        if rota == "1" and dtype == "disk":
            result.append("/dev/" + name)

    return result


def get_disk_identity(device):
    """
    Devuelve una tupla (modelo, serial), o None.
    """

    out = run_cmd([
        "smartctl",
        "-i",
        device
    ])

    model = None
    serial = None

    for line in out.splitlines():

        if line.startswith("Device Model:"):
            model = line.split(":", 1)[1].strip()

        elif line.startswith("Serial Number:"):
            serial = line.split(":", 1)[1].strip()

    if model and serial:
        return model, serial

    return None


def detect_disks(all_disks):
    """
    Detecta los discos conocidos por modelo + serial.

    all_disks debe ser un conjunto de tuplas:
    {
        (modelo, serial),
        ...
    }
    """

    found = {}

    for device in get_candidate_disks():

        identity = get_disk_identity(device)

        if identity is None:
            continue

        if identity in all_disks:
            found[identity] = device

    return found


def read_temperatures(all_disks):
    """
    Detecta los discos conocidos y devuelve:

    {
        (modelo, serial): temperatura,
        ...
    }
    """

    disk_paths = detect_disks(all_disks)
    result = {}

    for identity, device in disk_paths.items():

        temp = get_disk_temp(device)

        if temp is not None and -20 <= temp <= 100:
            result[identity] = temp

    return disk_paths, result


def group_temperature(group, temperatures):
    """
    Devuelve la temperatura máxima de un grupo de discos.

    Si no hay temperaturas válidas, devuelve None.
    """

    values = []

    for identity in group:

        if identity in temperatures:
            values.append(temperatures[identity])

    if not values:
        return None

    return max(values)


def normalize_model(model):
    """
    Normaliza espacios consecutivos del modelo para formar
    identificadores compatibles con Unraid.
    """

    return re.sub(r"\s+", "_", model.strip())


def unraid_id_for_identity(identity):
    """
    Convierte (modelo, serial) al formato diskId de Unraid.
    """

    model, serial = identity

    return normalize_model(model) + "_" + serial
