"""
V3.0 - Controlador de ventiladores.

Extraccion conservadora de la logica termica existente
en rp2040_fan_control.py.

Esta primera version no modifica el daemon principal.
"""

MODE_AUTO = "AUTO"
MODE_SILENT = "SILENT"
MODE_TURBO = "TURBO"


class FanController:

    def __init__(
        self,
        thermal_curve,
        temp_alert,
        hdd_warning_temp,
        silent_max_fan,
        ramp_up,
        ramp_down,
        fan_hysteresis,
    ):
        self.thermal_curve = tuple(thermal_curve)
        self.temp_alert = temp_alert
        self.hdd_warning_temp = hdd_warning_temp
        self.silent_max_fan = silent_max_fan
        self.ramp_up = ramp_up
        self.ramp_down = ramp_down
        self.fan_hysteresis = fan_hysteresis

    def temperature_to_fan(self, temp):
        if temp is None:
            return 100

        if temp >= self.temp_alert:
            return 100

        if temp <= self.thermal_curve[0][0]:
            return self.thermal_curve[0][1]

        if temp >= self.thermal_curve[-1][0]:
            return self.thermal_curve[-1][1]

        for i in range(1, len(self.thermal_curve)):
            t0, f0 = self.thermal_curve[i - 1]
            t1, f1 = self.thermal_curve[i]

            if temp <= t1:
                ratio = (temp - t0) / float(t1 - t0)
                return int(round(
                    f0 + ratio * (f1 - f0)
                ))

        return 100

    def intelligent_target(
        self,
        target,
        temperature,
        previous_temperature,
    ):
        if temperature is None:
            return 100

        if temperature >= self.temp_alert:
            return 100

        if previous_temperature is None:
            return target

        delta = temperature - previous_temperature

        if delta >= 2:
            return min(target + 10, 100)

        if delta >= 1:
            return min(target + 5, 100)

        return target

    def smooth(self, current, target):
        if target > current:
            return min(current + self.ramp_up, target)

        if target < current:
            return max(current - self.ramp_down, target)

        return current

    def control_reason(
        self,
        temperature,
        raw_target,
        intelligent_target_value,
        final_target,
        previous_target,
        previous_temperature,
        current_mode=None,
    ):
        if temperature is None:
            return "NO_TEMP"

        if temperature >= self.temp_alert:
            return "TEMP_ALERT"

        if current_mode == MODE_TURBO:
            return "TURBO"

        if (
            current_mode == MODE_SILENT
            and temperature < self.hdd_warning_temp
        ):
            return "SILENT"

        if (
            intelligent_target_value != raw_target
            and previous_temperature is not None
        ):
            delta = temperature - previous_temperature

            if delta >= 2:
                return "TREND+10"

            if delta >= 1:
                return "TREND+5"

        if (
            previous_target is not None
            and final_target == previous_target
            and abs(intelligent_target_value - previous_target)
            < self.fan_hysteresis
        ):
            return "HYSTERESIS"

        return "CURVE"

    def hysteresis_target(self, previous, target, temperature):
        if temperature is None:
            return 100

        if temperature >= self.temp_alert:
            return 100

        if previous is None:
            return target

        if abs(target - previous) < self.fan_hysteresis:
            return previous

        return target

    def mode_temperature_to_fan(self, temp, current_mode):
        if temp is None:
            return 100

        if temp >= self.temp_alert:
            return 100

        if current_mode == MODE_TURBO:
            return 100

        target = self.temperature_to_fan(temp)

        if current_mode == MODE_SILENT:
            if temp < self.hdd_warning_temp:
                return min(target, self.silent_max_fan)

            return target

        return target
