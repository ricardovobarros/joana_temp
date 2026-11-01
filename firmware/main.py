from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import dht
import json
import network
import time

import config

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None
    print("umqtt.simple em falta: corre 'mpremote mip install umqtt.simple'")

# ===== PINOS =====
TIMER_BUTTON_PIN = 14  # Botão do timer entre GPIO 14 e GND
POWER_BUTTON_PIN = 27  # Override da energia da tomada
SLEEP_BUTTON_PIN = 13  # Registo de sono do bebé
DHT_PIN = 4       # DHT11 DATA
OLED_SDA = 21
OLED_SCL = 22

# ===== TEMPOS =====
LONG_PRESS_MS = 2000
DEBOUNCE_MS = 50
TIMER_MAX_S = 12 * 3600
TEMP_INTERVAL_MS = 15 * 60 * 1000
FIRST_TEMP_DELAY_MS = 5000
WIFI_RETRY_MS = 15000
MQTT_RETRY_MS = 10000
MQTT_KEEPALIVE_S = 60
MQTT_PING_MS = 30000
MAX_PENDING = 20

TOPIC_TEMP = config.TOPIC_PREFIX + "/temp"
TOPIC_STATE = config.TOPIC_PREFIX + "/timer/state"
TOPIC_CMD = config.TOPIC_PREFIX + "/timer/cmd"
TOPIC_STATUS = config.TOPIC_PREFIX + "/status"
TOPIC_POWER_OVERRIDE = config.TOPIC_PREFIX + "/plug/override"
TOPIC_SLEEP_STATE = config.TOPIC_PREFIX + "/sleep/state"
TOPIC_SLEEP_CMD = config.TOPIC_PREFIX + "/sleep/cmd"

# ===== HARDWARE =====
i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)
timer_button = Pin(TIMER_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
power_button = Pin(POWER_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
sleep_button = Pin(SLEEP_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
dht_sensor = dht.DHT11(Pin(DHT_PIN, Pin.IN, Pin.PULL_UP))
wlan = network.WLAN(network.STA_IF)

# ===== DISPLAY =====
FONT_8X8 = {
    '0': [0x3E, 0x63, 0x73, 0x7B, 0x6F, 0x67, 0x63, 0x3E],
    '1': [0x18, 0x1C, 0x18, 0x18, 0x18, 0x18, 0x18, 0x7E],
    '2': [0x3E, 0x63, 0x60, 0x38, 0x0E, 0x03, 0x63, 0x7F],
    '3': [0x3E, 0x63, 0x60, 0x3C, 0x60, 0x60, 0x63, 0x3E],
    '4': [0x30, 0x38, 0x3C, 0x36, 0x33, 0x7F, 0x30, 0x30],
    '5': [0x7F, 0x03, 0x03, 0x3F, 0x60, 0x60, 0x63, 0x3E],
    '6': [0x3E, 0x63, 0x03, 0x3F, 0x63, 0x63, 0x63, 0x3E],
    '7': [0x7F, 0x63, 0x60, 0x30, 0x18, 0x0C, 0x0C, 0x0C],
    '8': [0x3E, 0x63, 0x63, 0x3E, 0x63, 0x63, 0x63, 0x3E],
    '9': [0x3E, 0x63, 0x63, 0x63, 0x7E, 0x60, 0x63, 0x3E],
}

# Bit 0 de cada linha da fonte é o pixel mais à esquerda
def draw_large_char(char, x, y, scale=3):
    pattern = FONT_8X8.get(char)
    if pattern is None:
        return
    for row in range(8):
        bits = pattern[row]
        for col in range(8):
            if bits & (1 << col):
                oled.fill_rect(x + col * scale, y + row * scale, scale, scale, 1)


def clear_display():
    oled.fill(0)
    oled.show()


def display_timer(elapsed_s, colon_on):
    hours = elapsed_s // 3600
    minutes = (elapsed_s % 3600) // 60
    text = "{:02d}{:02d}".format(hours, minutes)
    oled.fill(0)
    y = 20
    for char, x in zip(text, (8, 34, 70, 96)):
        draw_large_char(char, x, y)
    if colon_on:
        oled.fill_rect(61, y + 5, 6, 6, 1)
        oled.fill_rect(61, y + 15, 6, 6, 1)
    oled.show()


def display_text(line1, line2=None):
    """Texto centralizado. O driver nativo usa uma fonte legível de 8 px."""
    oled.fill(0)
    y = 22 if line2 is None else 16
    oled.text(line1, max(0, (128 - len(line1) * 8) // 2), y, 1)
    if line2 is not None:
        oled.text(line2, max(0, (128 - len(line2) * 8) // 2), y + 18, 1)
    oled.show()


def display_baby(sleeping):
    """Emoji simples, desenhado no OLED sem depender de caracteres Unicode."""
    oled.fill(0)
    # Cabeça e orelhas. Somente primitivas presentes em versões antigas do
    # framebuf; alguns firmwares MicroPython não oferecem ellipse().
    oled.line(50, 11, 78, 11, 1)
    oled.line(43, 18, 50, 11, 1)
    oled.line(78, 11, 85, 18, 1)
    oled.line(43, 18, 40, 31, 1)
    oled.line(40, 31, 43, 44, 1)
    oled.line(43, 44, 51, 51, 1)
    oled.line(51, 51, 77, 51, 1)
    oled.line(77, 51, 85, 44, 1)
    oled.line(85, 44, 88, 31, 1)
    oled.line(88, 31, 85, 18, 1)
    oled.line(39, 25, 35, 27, 1)
    oled.line(35, 27, 35, 36, 1)
    oled.line(35, 36, 41, 39, 1)
    oled.line(89, 25, 93, 27, 1)
    oled.line(93, 27, 93, 36, 1)
    oled.line(93, 36, 87, 39, 1)
    if sleeping:
        oled.line(51, 29, 55, 31, 1)
        oled.line(55, 31, 59, 29, 1)
        oled.line(69, 29, 73, 31, 1)
        oled.line(73, 31, 77, 29, 1)
        oled.text("zZ", 96, 4, 1)
    else:
        oled.fill_rect(53, 28, 4, 5, 1)
        oled.fill_rect(71, 28, 4, 5, 1)
    # Nariz e boca
    oled.pixel(64, 36, 1)
    oled.line(59, 42, 62, 44, 1)
    oled.line(62, 44, 66, 44, 1)
    oled.line(66, 44, 69, 42, 1)
    oled.show()


# A tela é controlada por etapas não bloqueantes para não interromper MQTT/DHT.
display_steps = []
display_step_started_ms = 0


def _draw_display_step(kind, value=None):
    if kind == "timer":
        display_timer(value, True)
    elif kind == "baby":
        display_baby(value)
    else:
        display_text(value)


def show_sequence(steps):
    global display_steps, display_step_started_ms
    display_steps = list(steps)
    display_step_started_ms = time.ticks_ms()
    kind, value, _duration = display_steps[0]
    _draw_display_step(kind, value)


def poll_display():
    global display_steps, display_step_started_ms
    if not display_steps:
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, display_step_started_ms) < display_steps[0][2]:
        return
    display_steps.pop(0)
    if not display_steps:
        clear_display()
        return
    display_step_started_ms = now
    kind, value, _duration = display_steps[0]
    _draw_display_step(kind, value)


# ===== FILA DE MENSAGENS (para quando não há rede) =====
pending = []


def queue_message(topic, payload, retain=False):
    pending.append((topic, payload, retain, time.ticks_ms()))
    while len(pending) > MAX_PENDING:
        pending.pop(0)


# ===== TIMER =====
timer_running = False
timer_start_ms = 0
last_drawn = None


def timer_elapsed_s():
    if not timer_running:
        return 0
    return time.ticks_diff(time.ticks_ms(), timer_start_ms) // 1000


def publish_state(event, reason, elapsed_s):
    queue_message(TOPIC_STATE, {
        "running": timer_running,
        "elapsed_s": elapsed_s,
        "event": event,
        "reason": reason,
    }, retain=True)


def start_timer(reason):
    global timer_running, timer_start_ms, last_drawn
    if timer_running:
        return
    timer_running = True
    timer_start_ms = time.ticks_ms()
    last_drawn = None
    print("Timer ligado ({})".format(reason))
    publish_state("start", reason, 0)
    show_sequence((("text", "ON", 1500), ("timer", 1, 1500)))


def stop_timer(reason):
    global timer_running, last_drawn
    if not timer_running:
        return
    elapsed = min(timer_elapsed_s(), TIMER_MAX_S)
    timer_running = False
    last_drawn = None
    print("Timer desligado ({}) após {} s".format(reason, elapsed))
    publish_state("stop", reason, elapsed)
    show_sequence((("text", "OFF", 1500), ("timer", 0, 1500)))


def update_timer():
    if not timer_running:
        return
    elapsed = timer_elapsed_s()
    if elapsed >= TIMER_MAX_S:
        stop_timer("auto12h")
        return
    # O timer continua em segundo plano; o OLED só acende sob comando.


# ===== BOTÕES =====
class Button:
    def __init__(self, pin, on_click, on_long=None):
        self.pin = pin
        self.on_click = on_click
        self.on_long = on_long
        self.down = False
        self.down_ms = 0
        self.long_handled = False

    def poll(self):
        pressed = self.pin.value() == 0
        now = time.ticks_ms()
        if pressed and not self.down:
            self.down = True
            self.down_ms = now
            self.long_handled = False
        elif pressed and self.down and self.on_long is not None:
            if (not self.long_handled and
                    time.ticks_diff(now, self.down_ms) >= LONG_PRESS_MS):
                self.long_handled = True
                self.on_long()
        elif not pressed and self.down:
            self.down = False
            held = time.ticks_diff(now, self.down_ms)
            if not self.long_handled and DEBOUNCE_MS <= held < LONG_PRESS_MS:
                self.on_click()


def timer_click():
    show_sequence((("timer", min(timer_elapsed_s(), TIMER_MAX_S), 3000),))


def timer_long_press():
    if timer_running:
        stop_timer("button")
    else:
        start_timer("button")


def power_override_click():
    queue_message(TOPIC_POWER_OVERRIDE, {"event": "ensure_on"})
    show_sequence((("text", "POWER ON", 3000),))


try:
    import esp32
    _sleep_nvs = esp32.NVS("joana")
    try:
        baby_sleeping = bool(_sleep_nvs.get_i32("sleeping"))
    except OSError:
        baby_sleeping = False
except ImportError:
    _sleep_nvs = None
    baby_sleeping = False


def publish_sleep(event, reason="button"):
    queue_message(TOPIC_SLEEP_STATE, {
        "sleeping": baby_sleeping,
        "event": event,
        "reason": reason,
    }, retain=True)


def sleep_click():
    show_sequence((("baby", baby_sleeping, 3000),))


def sleep_long_press():
    set_baby_sleeping(not baby_sleeping, "button")


def set_baby_sleeping(sleeping, reason):
    global baby_sleeping
    if baby_sleeping != sleeping:
        baby_sleeping = sleeping
        if _sleep_nvs is not None:
            _sleep_nvs.set_i32("sleeping", int(baby_sleeping))
            _sleep_nvs.commit()
    # Publica também quando o estado já coincide, para reconciliar o backend.
    publish_sleep("sleep" if baby_sleeping else "wake", reason)
    greeting = "GOOD NIGHT" if baby_sleeping else "GOOD MORNING"
    show_sequence((("text", greeting, 2000), ("baby", baby_sleeping, 2000)))


buttons = (
    Button(timer_button, timer_click, timer_long_press),
    Button(power_button, power_override_click),
    Button(sleep_button, sleep_click, sleep_long_press),
)


def poll_buttons():
    for item in buttons:
        item.poll()


# ===== TEMPERATURA =====
last_temp_ms = time.ticks_add(time.ticks_ms(), FIRST_TEMP_DELAY_MS - TEMP_INTERVAL_MS)


def read_dht():
    for attempt in range(3):
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            hum = dht_sensor.humidity()
            if -40 <= temp <= 80:
                return temp, hum
        except OSError as e:
            print("Erro DHT (tentativa {}/3): {}".format(attempt + 1, e))
        time.sleep_ms(1000)
    return None, None


def poll_temperature():
    global last_temp_ms
    now = time.ticks_ms()
    if time.ticks_diff(now, last_temp_ms) < TEMP_INTERVAL_MS:
        return
    last_temp_ms = now
    temp, hum = read_dht()
    if temp is None:
        return
    print("Temperatura: {} C, humidade: {} %".format(temp, hum))
    queue_message(TOPIC_TEMP, {"t": temp, "h": hum})


# ===== WIFI + MQTT =====
mqtt = None
last_wifi_try = None
last_mqtt_try = None
last_ping_ms = 0


def on_message(topic, msg):
    command = msg.decode().strip().lower()
    print("Comando recebido:", command)
    if topic == TOPIC_CMD.encode():
        if command == "start":
            start_timer("app")
        elif command == "stop":
            stop_timer("app")
    elif topic == TOPIC_SLEEP_CMD.encode():
        if command == "sleep":
            set_baby_sleeping(True, "app")
        elif command == "wake":
            set_baby_sleeping(False, "app")


def make_client():
    kwargs = {
        "user": config.MQTT_USER,
        "password": config.MQTT_PASSWORD,
        "keepalive": MQTT_KEEPALIVE_S,
    }
    try:
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.verify_mode = ssl.CERT_NONE
        client = MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_HOST,
                            port=config.MQTT_PORT, ssl=ctx, **kwargs)
    except (AttributeError, TypeError):
        # Versões antigas do MicroPython / umqtt.simple
        client = MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_HOST,
                            port=config.MQTT_PORT, ssl=True,
                            ssl_params={"server_hostname": config.MQTT_HOST},
                            **kwargs)
    client.set_callback(on_message)
    client.set_last_will(TOPIC_STATUS, b"offline", retain=True)
    return client


def mqtt_disconnected(error):
    global mqtt
    print("MQTT perdido:", error)
    try:
        mqtt.sock.close()
    except Exception:
        pass
    mqtt = None


def ensure_network():
    global last_wifi_try, last_mqtt_try, mqtt, last_ping_ms
    now = time.ticks_ms()

    if not wlan.isconnected():
        mqtt = None
        if wlan.active() and wlan.status() == network.STAT_CONNECTING:
            return
        if last_wifi_try is None or time.ticks_diff(now, last_wifi_try) >= WIFI_RETRY_MS:
            last_wifi_try = now
            print("A ligar ao WiFi", config.WIFI_SSID)
            wlan.active(True)
            try:
                wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            except OSError as e:
                print("Erro WiFi:", e)
        return

    if mqtt is not None or MQTTClient is None:
        return
    if last_mqtt_try is not None and time.ticks_diff(now, last_mqtt_try) < MQTT_RETRY_MS:
        return
    last_mqtt_try = now

    print("A ligar ao MQTT", config.MQTT_HOST)
    try:
        client = make_client()
        client.connect()
        client.subscribe(TOPIC_CMD.encode())
        client.subscribe(TOPIC_SLEEP_CMD.encode())
        client.publish(TOPIC_STATUS.encode(), b"online", retain=True)
        mqtt = client
        last_ping_ms = now
        publish_state("sync", "reconnect", timer_elapsed_s())
        publish_sleep("sync")
        print("MQTT ligado")
    except Exception as e:
        print("Falha MQTT:", e)
        mqtt = None


def poll_mqtt():
    global last_ping_ms
    if mqtt is None:
        return
    try:
        mqtt.check_msg()
        now = time.ticks_ms()
        while pending:
            topic, payload, retain, created = pending[0]
            payload = dict(payload)
            payload["ago_s"] = time.ticks_diff(now, created) // 1000
            mqtt.publish(topic.encode(), json.dumps(payload).encode(), retain=retain)
            pending.pop(0)
        if time.ticks_diff(now, last_ping_ms) >= MQTT_PING_MS:
            mqtt.ping()
            last_ping_ms = now
    except Exception as e:
        mqtt_disconnected(e)


# ===== LOOP PRINCIPAL =====
clear_display()
print("Sistema iniciado")

while True:
    poll_buttons()
    update_timer()
    poll_display()
    poll_temperature()
    ensure_network()
    poll_mqtt()
    time.sleep_ms(20)
