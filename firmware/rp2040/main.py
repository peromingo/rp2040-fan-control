import machine, time, framebuf, sys, uselect



# ============================================================

# 1. ENCENDIDO SATA - NO CAMBIAR ESTA SECUENCIA

# ============================================================

g14 = machine.Pin(14, machine.Pin.OUT)

g24 = machine.Pin(24, machine.Pin.OUT)



g14.value(0)

g24.value(0)

time.sleep(0.2)



g14.value(1)

time.sleep(0.4)



g24.value(1)



# Estabilización después de arrancar los discos

time.sleep(1.5)



# ============================================================

# 2. RESET OLED

# ============================================================

try:

    oled_rst = machine.Pin(22, machine.Pin.OUT)

    oled_rst.value(0)

    time.sleep(0.1)

    oled_rst.value(1)

    time.sleep(0.1)

except Exception:

    pass



# ============================================================

# 3. VENTILADORES

# ============================================================

fan1 = machine.PWM(machine.Pin(13))

fan2 = machine.PWM(machine.Pin(19))



for f in (fan1, fan2):

    f.freq(25000)

    f.duty_u16(int(65535 * 0.40))



# ============================================================

# 4. BOTON

# ============================================================

btn = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP)



# ============================================================

# 5. OLED

# ============================================================

class OLED_Direct:

    def __init__(self, i2c, addr=0x3c):

        self.i2c = i2c

        self.addr = addr

        self.buffer = bytearray(128 * 4)

        self.init_display()



    def write_cmd(self, cmd):

        try:

            self.i2c.writeto(self.addr, bytes([0x00, cmd]))

        except Exception:

            pass



    def init_display(self):

        init_cmds = [

            0xAE, 0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40,

            0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x02,

            0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF

        ]

        for c in init_cmds:

            self.write_cmd(c)



    def show(self):

        self.write_cmd(0x21)

        self.write_cmd(0)

        self.write_cmd(127)

        self.write_cmd(0x22)

        self.write_cmd(0)

        self.write_cmd(3)



        try:

            self.i2c.writeto_mem(self.addr, 0x40, self.buffer)

        except Exception:

            pass



    def clear(self):

        for i in range(len(self.buffer)):

            self.buffer[i] = 0

        self.show()



# ============================================================

# 6. I2C + OLED

# ============================================================

try:

    i2c = machine.SoftI2C(

        sda=machine.Pin(28),

        scl=machine.Pin(29),

        freq=100000

    )



    time.sleep(0.3)



    oled = OLED_Direct(i2c, 0x3c)

    fb = framebuf.FrameBuffer(

        oled.buffer,

        128,

        32,

        framebuf.MONO_VLSB

    )



    oled.clear()

    time.sleep(0.1)

    oled.clear()



    # ========================================================

    # 7. PAGINAS OLED

    # ========================================================

    page = 0



    pages_data = [

        ["UNRAID SYSTEM", "----------------", "INICIANDO..."],

        ["CPU / RAM", "----------------", "ESPERANDO..."],

        ["HDD 1", "----------------", "ESPERANDO..."],

        ["HDD 2", "----------------", "ESPERANDO..."],

        ["HDD 3", "----------------", "ESPERANDO..."],

        ["HDD 4", "----------------", "ESPERANDO..."],

        ["DOCKER / ARRAY", "----------------", "ESPERANDO..."],

        ["IP / UPTIME", "----------------", "ESPERANDO..."]

    ]



    display_on = True

    last_act_time = time.ticks_ms()



    # ========================================================

    # V2.4.2 - MODOS

    # ========================================================

    MODE_AUTO = "AUTO"

    MODE_SILENT = "SILENT"

    MODE_TURBO = "TURBO"



    current_mode = MODE_AUTO



    # V2.3.2 - ALERTAS TERMICAS

    thermal_alert_active = False

    thermal_alert_until = 0

    thermal_alert_previous_display = True



    # ========================================================

    # AUTO-SCROLL

    # ========================================================

    AUTO_SCROLL = True

    AUTO_SCROLL_SECONDS = 10

    last_scroll_time = time.ticks_ms()



    # ========================================================

    # WATCHDOG REAL DEL RP2040

    # 10 segundos sin paquete FAN valido = 100%

    # ========================================================

    WATCHDOG_STARTUP_GRACE_MS = 15000

    WATCHDOG_TIMEOUT_MS = 10000



    watchdog_start = time.ticks_ms()

    last_valid_packet = watchdog_start



    watchdog_active = False

    watchdog_enabled = False



    def show_thermal_alert(lines):

        global thermal_alert_active

        global thermal_alert_until

        global thermal_alert_previous_display

        global display_on



        thermal_alert_previous_display = display_on

        thermal_alert_active = True

        thermal_alert_until = time.ticks_add(

            time.ticks_ms(),

            6000

        )



        # Una alerta termica fuerza temporalmente el OLED a ON.

        display_on = True



        fb.fill(0)

        fb.text(str(lines[0])[:16], 0, 1, 1)

        fb.text(str(lines[1])[:16], 0, 11, 1)

        fb.text(str(lines[2])[:16], 0, 21, 1)

        oled.show()



    def render_current_page():

        if thermal_alert_active:

            return

        if not display_on:

            oled.clear()

            return



        l1, l2, l3 = pages_data[page]



        pass



        fb.fill(0)

        # Indicador de modo: A=AUTO, S=SILENT, T=TURBO.
        # Se reserva la zona derecha de la primera linea.
        fb.text(str(l1)[:15], 0, 1, 1)
        fb.text(str(l2)[:16], 0, 11, 1)
        fb.text(str(l3)[:16], 0, 21, 1)

        if current_mode == MODE_AUTO:
            mode_letter = "A"
        elif current_mode == MODE_SILENT:
            mode_letter = "S"
        else:
            mode_letter = "T"

        fb.text(mode_letter, 116, 1, 1)

        oled.show()



    def set_fans(p1, p2):

        p1 = max(10, min(100, int(p1)))

        p2 = max(10, min(100, int(p2)))



        fan1.duty_u16(int(65535 * (p1 / 100.0)))

        fan2.duty_u16(int(65535 * (p2 / 100.0)))



    # Mostrar pantalla inicial

    render_current_page()



    # ========================================================

    # 8. USB SERIAL

    # ========================================================

    spoll = uselect.poll()

    spoll.register(sys.stdin.buffer, uselect.POLLIN)



    buf = ""



    # ========================================================

    # 9. BOTON

    # ========================================================

    last_btn_state = 1

    btn_press_start = 0



    # ========================================================

    # GESTION DE CLICK / DOBLE CLICK

    # ========================================================

    DOUBLE_CLICK_MS = 700

    CLICK_PENDING = False

    CLICK_PENDING_TIME = 0



    # ========================================================

    # 10. BUCLE PRINCIPAL

    # ========================================================

    while True:

        now = time.ticks_ms()



        # ----------------------------------------------------

        # BOTON

        # ----------------------------------------------------

        val = btn.value()



        # Pulsacion

        if val == 0 and last_btn_state == 1:

            btn_press_start = now



        # Soltar boton

        elif val == 1 and last_btn_state == 0:

            dur = time.ticks_diff(now, btn_press_start)

            last_act_time = now

            last_scroll_time = now



            # -----------------------------------------------

            # V2.4.2 - PULSACION LARGA -> CAMBIO DE MODO

            # AUTO -> SILENT -> TURBO -> AUTO

            # -----------------------------------------------

            if dur >= 2000:

                CLICK_PENDING = False



                if current_mode == MODE_AUTO:

                    requested_mode = MODE_SILENT



                elif current_mode == MODE_SILENT:

                    requested_mode = MODE_TURBO



                else:

                    requested_mode = MODE_AUTO



                try:

                    sys.stdout.write(

                        "!MODE|%s\n" % requested_mode

                    )

                    pass

                except Exception as e:

                    pass



                # Feedback inmediato.

                #

                # V2.5.0 - MODO PERSISTENTE DURANTE CONFIRMACION

                #

                # No restauramos el titulo anterior. El RP2040 debe

                # mantener visible el modo solicitado hasta recibir

                # la confirmacion del daemon.

                if requested_mode == MODE_TURBO:

                    pages_data[page][0] = "MODE TURBO"

                elif requested_mode == MODE_SILENT:

                    pages_data[page][0] = "MODE SILENT"

                else:

                    pages_data[page][0] = "MODE AUTO"



                render_current_page()



            # -----------------------------------------------

            # PULSACION CORTA

            # -----------------------------------------------

            else:

                if CLICK_PENDING:

                    # ---------------------------------------

                    # DOBLE CLICK -> OLED ON/OFF

                    # ---------------------------------------

                    CLICK_PENDING = False



                    if display_on:

                        display_on = False

                        oled.clear()

                    else:

                        display_on = True

                        last_scroll_time = now

                        render_current_page()



                else:

                    # Guardamos el primer click y esperamos

                    # para saber si llega un segundo click.

                    CLICK_PENDING = True

                    CLICK_PENDING_TIME = now



        # -----------------------------------------------

        # CONFIRMAR CLICK SIMPLE

        # -----------------------------------------------

        if CLICK_PENDING:

            if time.ticks_diff(now, CLICK_PENDING_TIME) >= DOUBLE_CLICK_MS:

                CLICK_PENDING = False



                if display_on:

                    page = (page + 1) % 8

                    last_scroll_time = now

                    render_current_page()



        # ----------------------------------------------------

        # V2.3.2 - TIMEOUT ALERTA TERMICA

        # ----------------------------------------------------

        if thermal_alert_active:

            if time.ticks_diff(now, thermal_alert_until) >= 0:

                thermal_alert_active = False

                display_on = thermal_alert_previous_display



                if display_on:

                    last_scroll_time = now

                    render_current_page()

                else:

                    oled.clear()



        # ----------------------------------------------------

        # AUTO-SCROLL

        # ----------------------------------------------------

        if AUTO_SCROLL and display_on and not thermal_alert_active:

            if time.ticks_diff(now, last_scroll_time) >= (AUTO_SCROLL_SECONDS * 1000):

                page = (page + 1) % 8

                last_scroll_time = now

                render_current_page()



        last_btn_state = val



        # ----------------------------------------------------

        # SERIAL

        # V2.4.2

        #

        # Protocolo:

        #

        # pagina0#pagina1#...#pagina7

        # !ALERT|titulo|linea2|linea3       (opcional)

        # !MODE|AUTO/SILENT/TURBO           (opcional)

        # @fan1,fan2

        #

        # Todo el paquete se procesa al recibir @ + FAN.

        # ----------------------------------------------------

        if spoll.poll(0):

            ch = sys.stdin.buffer.read(1).decode()



            if ch in ("\n", "\r"):

                cmd = buf.strip()

                buf = ""



                # ------------------------------------------------

                # Solo procesar una trama que tenga el bloque FAN.

                # Esto mantiene el protocolo principal intacto.

                # ------------------------------------------------

                if "@" in cmd:

                    parts = cmd.split("@", 1)



                    trama = parts[0]

                    fan_str = parts[1]



                    # ====================================================

                    # V2.4.2 - RECEPCION DE MODO

                    # ====================================================

                    mode_received = None



                    if "!MODE|" in trama:

                        mode_part = trama.split("!MODE|", 1)[1]



                        # El modo termina al siguiente separador de

                        # protocolo, si existe.

                        mode_received = mode_part.split("|", 1)[0].strip()

                        trama = trama.split("!MODE|", 1)[0]



                        if mode_received not in (

                            MODE_AUTO,

                            MODE_SILENT,

                            MODE_TURBO

                        ):

                            mode_received = None

                        else:

                            current_mode = mode_received



                            pass



                    # ====================================================

                    # V2.3.2 - RECEPCION DE ALERTA TERMICA

                    # ====================================================

                    alert_lines = None



                    if "!ALERT|" in trama:

                        alert_part = trama.split("!ALERT|", 1)[1]

                        trama = trama.split("!ALERT|", 1)[0]



                        try:

                            alert_parts = alert_part.split("|")



                            if len(alert_parts) >= 3:

                                alert_lines = [

                                    alert_parts[0],

                                    alert_parts[1],

                                    alert_parts[2]

                                ]



                        except Exception:

                            alert_lines = None



                    # ====================================================

                    # FAN

                    # ====================================================

                    valid_fan_packet = False



                    try:

                        fan_parts = fan_str.split(",")



                        if len(fan_parts) == 2:

                            p1 = int(fan_parts[0])

                            p2 = int(fan_parts[1])



                            if 0 <= p1 <= 100 and 0 <= p2 <= 100:

                                valid_fan_packet = True

                                set_fans(p1, p2)



                    except Exception:

                        valid_fan_packet = False



                    # ====================================================

                    # WATCHDOG - COMUNICACION VALIDA

                    # ====================================================

                    if valid_fan_packet:

                        last_valid_packet = now



                        if watchdog_active:

                            watchdog_active = False

                            pass



                    # ====================================================

                    # PAGINAS OLED

                    # ====================================================

                    pass

                    if "#" in trama and "|" in trama:

                        p_parts = trama.split("#")



                        for idx, p_str in enumerate(p_parts[:8]):

                            lines = p_str.split("|")



                            if len(lines) >= 3:

                                pages_data[idx] = lines[:3]

                                pass



                    # ====================================================

                    # ALERTA

                    # ====================================================

                    if alert_lines is not None:

                        show_thermal_alert(alert_lines)



                    # ====================================================

                    # MODO

                    # ====================================================

                    elif mode_received is not None:



                        if mode_received in (MODE_TURBO, MODE_SILENT):

                            # El modo ya queda reflejado por A/S/T
                            # en render_current_page(). No repintar
                            # MODE SILENT/TURBO en cada paquete.

                            if display_on:
                                render_current_page()



                        else:

                            last_act_time = now

                            render_current_page()



                    # ====================================================

                    # NORMAL

                    # ====================================================

                    else:

                        last_act_time = now

                        render_current_page()



            else:

                buf += ch



        # ----------------------------------------------------

        # WATCHDOG

        # 10 segundos sin paquete FAN valido:

        # FAN1 y FAN2 al 100%.

        # ----------------------------------------------------

        # Activar watchdog después de la gracia inicial.

        if not watchdog_enabled:

            if time.ticks_diff(now, watchdog_start) >= WATCHDOG_STARTUP_GRACE_MS:

                watchdog_enabled = True

                last_valid_packet = now

                pass



        # Una vez activo, exigir comunicación cada 10 segundos.

        if watchdog_enabled:

            if time.ticks_diff(now, last_valid_packet) >= WATCHDOG_TIMEOUT_MS:



                if not watchdog_active:

                    watchdog_active = True



                    fan1.duty_u16(65535)

                    fan2.duty_u16(65535)



                    pass



                else:

                    fan1.duty_u16(65535)

                    fan2.duty_u16(65535)



        time.sleep(0.01)



except Exception as e:

    pass

