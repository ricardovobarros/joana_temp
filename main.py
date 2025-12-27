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
# O DHT precisa de pull-up, mas o módulo geralmente já tem
dht_pin = Pin(DHT_PIN, Pin.IN, Pin.PULL_UP)
dht_sensor = dht.DHT11(dht_pin)  # Se for DHT22, troque para dht.DHT22(dht_pin)

# Configuração do sensor PIR
pir = Pin(PIR_PIN, Pin.IN)

# Variáveis de controle
display_time = 0
display_active = False
last_dht_read = 0
DHT_MIN_INTERVAL = 2000  # Mínimo de 2 segundos entre leituras do DHT
dht_initialized = False

# Inicialização do DHT - dá tempo para o sensor estabilizar
print("Inicializando sensor DHT...")
time.sleep(2)  # Dá tempo para o sensor estabilizar (equivalente ao begin() do Arduino)
dht_initialized = True

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
    """Lê a temperatura do sensor DHT com retry e controle de intervalo"""
    global last_dht_read, dht_initialized
    
    if not dht_initialized:
        return None
    
    # Verifica se passou tempo suficiente desde a última leitura
    current_time = time.ticks_ms()
    time_since_last = time.ticks_diff(current_time, last_dht_read)
    
    if time_since_last < DHT_MIN_INTERVAL:
        # Ainda não passou tempo suficiente, retorna None
        return None
    
    # Tenta ler o sensor com retry
    for attempt in range(3):
        try:
            # Delay antes de medir (o DHT precisa de tempo para responder)
            time.sleep_ms(100)
            dht_sensor.measure()
            # Pequeno delay após measure() antes de ler
            time.sleep_ms(50)
            temp = dht_sensor.temperature()
            
            # Verifica se o valor é válido (equivalente ao isnan() do Arduino)
            # DHT11: -40 a 80°C, DHT22: -40 a 125°C
            if temp is not None and -40 <= temp <= 125:
                last_dht_read = current_time
                return temp
            else:
                print(f"Valor inválido lido: {temp}")
        except OSError as e:
            # Timeout ou erro de comunicação
            if attempt < 2:  # Não é a última tentativa
                time.sleep_ms(200)  # Espera mais antes de tentar novamente
            else:
                print(f"Erro ao ler DHT (tentativa {attempt + 1}/3): {e}")
        except Exception as e:
            print(f"Erro inesperado ao ler DHT: {e}")
            break
    
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
                # Se não conseguiu ler, mostra mensagem de aguarde
                # e tenta novamente após esperar o intervalo mínimo
                oled.fill(0)
                oled.text("Aguardando...", 0, 0)
                oled.text("sensor DHT", 0, 20)
                oled.show()
                # Espera o intervalo mínimo antes de tentar novamente
                time.sleep_ms(DHT_MIN_INTERVAL)
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

