"""
Example per-installation disk mapping.
Copy to site_config_local.py and replace all example values before starting the daemon.
Never publish site_config.py: it contains hardware-specific serial numbers.
"""

# Format: (model reported by Unraid, disk serial number)
# These placeholders deliberately do not match real disks.
FAN1_DISKS = {
    ("REPLACE_WITH_MODEL_FOR_FAN1_DISK_1", "REPLACE_WITH_SERIAL_FOR_FAN1_DISK_1"),
    ("REPLACE_WITH_MODEL_FOR_FAN1_DISK_2", "REPLACE_WITH_SERIAL_FOR_FAN1_DISK_2"),
}

FAN2_DISKS = {
    ("REPLACE_WITH_MODEL_FOR_FAN2_DISK_1", "REPLACE_WITH_SERIAL_FOR_FAN2_DISK_1"),
    ("REPLACE_WITH_MODEL_FOR_FAN2_DISK_2", "REPLACE_WITH_SERIAL_FOR_FAN2_DISK_2"),
}

def validate_disk_config():
    all_disks = FAN1_DISKS | FAN2_DISKS
    if not all_disks or any("REPLACE_WITH_" in value for item in all_disks for value in item):
        raise RuntimeError(
            "Disk mapping is still using example placeholders. "
            "Copy site_config.example.py to site_config_local.py and configure actual disks."
        )
    if FAN1_DISKS & FAN2_DISKS:
        raise RuntimeError("A disk cannot be assigned to both fan groups.")
    return True
