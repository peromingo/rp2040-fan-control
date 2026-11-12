from .utils import run_cmd
from .temperature import unraid_id_for_identity


def get_disk_power_state(device):
    """
    Consulta el estado físico con hdparm -C.
    No provoca spin-up ni spin-down.
    """

    try:
        out = run_cmd(
            ["hdparm", "-C", device],
            timeout=3
        )

        low = out.lower()

        if "standby" in low:
            return "STBY"

        if "active/idle" in low or "active" in low:
            return "ACTIVE"

        return "UNKNOWN"

    except Exception:
        return "UNKNOWN"


def read_unraid_disk_states():
    """
    Lee rdevId/rdevStatus desde mdcmd status,
    emparejando los datos por índice.
    """

    result = {}

    try:
        out = run_cmd(
            ["mdcmd", "status"],
            timeout=3
        )

        entries = {}

        for line in out.splitlines():

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            value = value.strip()

            if key.startswith("rdevId."):
                idx = key.split(".", 1)[1]
                entries.setdefault(idx, {})["id"] = value

            elif key.startswith("rdevStatus."):
                idx = key.split(".", 1)[1]
                entries.setdefault(idx, {})["status"] = value

        for entry in entries.values():

            disk_id = entry.get("id", "")
            status = entry.get("status", "")

            if not disk_id:
                continue

            if status == "DISK_OK":
                result[disk_id] = "OK"

            elif status == "DISK_NP_DSBL":
                result[disk_id] = "DISABLED"

            elif status == "DISK_NP":
                result[disk_id] = "NOT PRESENT"

            else:
                result[disk_id] = status

    except Exception:
        pass

    return result


def read_disk_states(all_disks, disk_paths):
    """
    Devuelve:

    states:
        identidad -> ACTIVE/STBY/ERR/UNKNOWN

    unraid_states:
        diskId de Unraid -> estado Unraid

    No utiliza SMART ni comandos de spin-up/spin-down.
    """

    physical = {}

    for identity, device in disk_paths.items():
        physical[identity] = get_disk_power_state(device)

    unraid = read_unraid_disk_states()

    states = {}

    for identity in all_disks:

        physical_state = physical.get(
            identity,
            "UNKNOWN"
        )

        unraid_state = unraid.get(
            unraid_id_for_identity(identity),
            "UNKNOWN"
        )

        states[identity] = physical_state

        if unraid_state not in ("OK", "UNKNOWN"):
            states[identity] = "ERR"

    return states, unraid


def disk_state(identity, states):
    """
    Estado corto para OLED:
    ACTIVE / STBY / ERR / UNKNOWN
    """

    return states.get(identity, "UNKNOWN")
