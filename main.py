from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import dht
import time

# Configuração dos pinos
PIR_PIN = 27      # Sensor de movimento PIR
DHT_PIN = 4       # Sensor de temperatura DHT11/DHT22
OLED_SDA = 21     # OLED SDA
OLED_SCL = 22     # OLED SCL

# Configuração do display OLED
i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=400000)
oled = SSD1306_I2C(128, 64, i2c)

# Configuração do sensor DHT
dht_sensor = dht.DHT11(Pin(DHT_PIN))  # Se for DHT22, troque para dht.DHT22(Pin(DHT_PIN))

# Configuração do sensor PIR
pir = Pin(PIR_PIN, Pin.IN)

# Variáveis de controle
display_time = 0
display_active = False

def clear_display():
    """Limpa o display OLED"""
    oled.fill(0)
    oled.show()

def display_temperature(temp):
    """Mostra a temperatura no display OLED"""
    oled.fill(0)
    oled.text("Temperatura:", 0, 0)
    oled.text(f"{temp} C", 0, 20)
    oled.show()

def read_temperature():
    """Lê a temperatura do sensor DHT"""
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        return temp
    except Exception as e:
        print(f"Erro ao ler DHT: {e}")
        return None

# Limpa o display inicialmente
clear_display()

print("Sistema iniciado. Aguardando detecção de movimento...")

# Loop principal
while True:
    # Verifica se há movimento detectado
    if pir.value() == 1:
        if not display_active:
            # Movimento detectado - ativa o display
            display_active = True
            display_time = time.ticks_ms()
            print("Movimento detectado!")
            
            # Lê e mostra a temperatura
            temp = read_temperature()
            if temp is not None:
                display_temperature(temp)
            else:
                oled.fill(0)
                oled.text("Erro ao ler", 0, 0)
                oled.text("temperatura", 0, 20)
                oled.show()
    
    # Verifica se passaram 8 segundos desde a ativação
    if display_active:
        elapsed = time.ticks_diff(time.ticks_ms(), display_time)
        if elapsed >= 8000:  # 8 segundos = 8000 ms
            clear_display()
            display_active = False
            print("Display desativado após 8 segundos")
    
    # Pequeno delay para não sobrecarregar o processador
    time.sleep_ms(100)

