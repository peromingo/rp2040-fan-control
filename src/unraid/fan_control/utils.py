import os
import subprocess


def run_cmd(cmd, timeout=5):
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout
        )
        return p.stdout
    except Exception:
        return ""


def cpu_temperature():
    """
    Lee directamente el sensor x86_pkg_temp.
    Devuelve grados Celsius o None.
    """

    try:
        base = "/sys/class/thermal"

        for name in os.listdir(base):
            if not name.startswith("thermal_zone"):
                continue

            zone = os.path.join(base, name)

            try:
                with open(os.path.join(zone, "type"), "r") as f:
                    zone_type = f.read().strip()

                if zone_type != "x86_pkg_temp":
                    continue

                with open(os.path.join(zone, "temp"), "r") as f:
                    raw = int(f.read().strip())

                temp = raw / 1000.0

                if -20 <= temp <= 120:
                    return int(round(temp))

            except Exception:
                continue

    except Exception:
        pass

    return None


def cpu_load():
    try:
        return os.getloadavg()[0]
    except Exception:
        return None


def system_info():
    load = cpu_load()

    if load is None:
        return "LOAD --"

    return "LOAD %.1f" % load


def ram_info():
    """
    Lee /proc/meminfo directamente.
    Devuelve used_mb, total_mb, percent.
    """

    try:
        values = {}

        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()

                if len(parts) >= 2:
                    key = parts[0].rstrip(":")
                    values[key] = int(parts[1])

        total = values.get("MemTotal")
        available = values.get("MemAvailable")

        if total is None or available is None:
            return None

        used = total - available

        percent = int(round(
            used * 100.0 / total
        ))

        return (
            used // 1024,
            total // 1024,
            percent
        )

    except Exception:
        return None


def primary_ip():
    """
    Obtiene la IP de la interfaz br0.
    """

    try:
        out = run_cmd([
            "ip",
            "-4",
            "addr",
            "show",
            "dev",
            "br0"
        ])

        for line in out.splitlines():
            line = line.strip()

            if line.startswith("inet "):
                ip = line.split()[1].split("/")[0]

                if ip:
                    return ip

    except Exception:
        pass

    return "--"


def uptime_text():
    """
    Uptime desde /proc/uptime.
    """

    try:
        with open("/proc/uptime", "r") as f:
            seconds = int(float(f.read().split()[0]))

        days = seconds // 86400
        seconds %= 86400

        hours = seconds // 3600
        seconds %= 3600

        minutes = seconds // 60

        if days > 0:
            return "UP %dd %02dh" % (
                days,
                hours
            )

        return "UP %02dh %02dm" % (
            hours,
            minutes
        )

    except Exception:
        return "UP --"


def docker_counts():
    running_out = run_cmd([
        "docker",
        "ps",
        "-q"
    ])

    total_out = run_cmd([
        "docker",
        "ps",
        "-a",
        "-q"
    ])

    running = len([
        x for x in running_out.splitlines()
        if x.strip()
    ])

    total = len([
        x for x in total_out.splitlines()
        if x.strip()
    ])

    return running, total


def docker_info():
    running, total = docker_counts()

    return "DOCKER %d/%d" % (
        running,
        total
    )


def unraid_array_info():
    out = run_cmd([
        "mdcmd",
        "status"
    ])

    if not out:
        return "ARRAY --"

    state = "--"
    ok = 0
    configured = 0
    disabled = 0

    for line in out.splitlines():

        if line.startswith("mdState="):
            state = line.split("=", 1)[1].strip()

        elif line.startswith("diskId."):

            disk_id = line.split("=", 1)[1].strip()

            if disk_id:
                configured += 1

        elif line.startswith("rdevStatus."):

            status = line.split("=", 1)[1].strip()

            if status == "DISK_OK":
                ok += 1

            elif status == "DISK_NP_DSBL":
                disabled += 1

    if state == "STARTED":

        if configured > 0:
            if ok == configured:
                return "ARRAY %d OK" % configured

            return "ARRAY %d/%d OK" % (
                ok,
                configured
            )

        return "ARRAY STARTED"

    return "ARRAY " + state[:9]
