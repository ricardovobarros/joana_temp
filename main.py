from machine import Pin, I2C, freq, lightsleep
from ssd1306 import SSD1306_I2C
import dht
import time

# ===== ECONOMIA DE ENERGIA =====
# Desabilita WiFi e Bluetooth para economizar bateria
try:
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    wlan = network.WLAN(network.AP_IF)
    wlan.active(False)
except:
    pass

try:
    import bluetooth
    bluetooth.disable()
except:
    pass

# Reduz frequência da CPU para economizar energia (80 MHz é suficiente)
# Padrão é 240 MHz, reduzindo para 80 MHz economiza bastante
freq(80000000)  # 80 MHz

print("Modo economia de energia ativado")

# Configuração dos pinos
PIR_PIN = 27      # Sensor de movimento PIR
DHT_PIN = 4       # Sensor de temperatura DHT11/DHT22
OLED_SDA = 21     # OLED SDA
OLED_SCL = 22     # OLED SCL

# Configuração do display OLED (frequência reduzida quando não em uso)
i2c = I2C(0, scl=Pin(OLED_SCL), sda=Pin(OLED_SDA), freq=100000)  # 100kHz é suficiente
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

def reverse_bits(byte):
    """Inverte os bits de um byte (LSB <-> MSB)"""
    result = 0
    for i in range(8):
        if byte & (1 << i):
            result |= (1 << (7 - i))
    return result

def draw_large_char(char, x, y, scale=3):
    """Desenha um caractere grande (escala 3x)"""
    # Fonte 8x8 padrão, desenhada em escala maior
    font_8x8 = {
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
        '-': [0x00, 0x00, 0x00, 0x7F, 0x7F, 0x00, 0x00, 0x00],
        '.': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C],
    }
    
    if char not in font_8x8:
        return
    
    pattern = font_8x8[char]
    for row in range(8):
        # Inverte os bits de cada linha para corrigir espelhamento horizontal
        reversed_row = reverse_bits(pattern[row])
        for col in range(8):
            if reversed_row & (1 << (7 - col)):
                oled.fill_rect(x + col * scale, y + row * scale, scale, scale, 1)

def display_temperature(temp):
    """Mostra a temperatura grande e centralizada no display OLED"""
    oled.fill(0)
    
    # Formata a temperatura com 1 casa decimal (ex: "23.5")
    temp_str = f"{temp:.1f}"
    parts = temp_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""
    
    # Escalas diferentes: números grandes e decimal menor
    scale_large = 3  # Escala 3x para números principais
    scale_small = 1  # Escala 1x (metade visual) para decimal
    
    # Calcula larguras
    char_width_large = 8 * scale_large
    char_width_small = 8 * scale_small
    char_spacing = 3
    
    # Calcula largura total
    total_width = (len(integer_part) * char_width_large + 
                   (len(integer_part) - 1) * char_spacing +
                   char_width_small +  # ponto decimal
                   char_spacing +
                   char_width_small)  # dígito decimal
    
    # Centraliza horizontalmente (tela tem 128 pixels)
    start_x = (128 - total_width) // 2
    
    # Centraliza verticalmente (tela tem 64 pixels, altura do caractere grande é 8*scale = 24)
    start_y = (64 - 8 * scale_large) // 2
    
    # Desenha parte inteira (números grandes)
    x_offset = 0
    for char in integer_part:
        draw_large_char(char, start_x + x_offset, start_y, scale_large)
        x_offset += char_width_large + char_spacing
    
    # Desenha ponto decimal (pequeno, alinhado na base)
    decimal_y = start_y + 8 * scale_large - 8 * scale_small
    draw_large_char('.', start_x + x_offset, decimal_y, scale_small)
    x_offset += char_width_small + char_spacing
    
    # Desenha dígito decimal (pequeno, alinhado na base)
    if decimal_part:
        draw_large_char(decimal_part[0], start_x + x_offset, decimal_y, scale_small)
        x_offset += char_width_small
    
    # Adiciona o símbolo "C" pequeno ao lado
    oled.text("C", start_x + x_offset + 5, start_y + 8 * scale_large - 8)
    
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

# Loop principal com economia de energia
print("Sistema iniciado. Aguardando detecção de movimento...")

while True:
    # IMPORTANTE: Só verifica o PIR quando a tela NÃO está ativa
    # Isso evita que o brilho da tela OLED ative o sensor PIR causando loop
    if not display_active:
        # Verifica se há movimento detectado apenas quando tela está desligada
        if pir.value() == 1:
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
            # Pequeno delay após desligar para garantir que PIR estabilize
            time.sleep_ms(500)
    
    # ECONOMIA DE ENERGIA: Light sleep quando não há movimento
    # O ESP32 entra em modo de baixo consumo mas mantém a RAM
    # Acorda automaticamente quando há interrupção (movimento do PIR)
    if not display_active:
        # Light sleep por 100ms - economiza bastante energia
        # O PIR pode acordar o ESP32 via interrupção se configurado
        lightsleep(100)  # Sleep por 100ms quando não há atividade
    else:
        # Quando display está ativo, apenas um pequeno delay
        time.sleep_ms(50)

