# Sistema de Monitoramento de Temperatura com Detecção de Movimento

Sistema MicroPython para ESP32 que exibe a temperatura no display OLED quando detecta movimento.

## Componentes

- **ESP32 Dev Module**
- **Sensor PIR** (HC-SR501) - GPIO 27
- **Display OLED I2C** (SSD1306 128x64) - GPIO 21 (SDA), GPIO 22 (SCL)
- **Sensor DHT11/DHT22** - GPIO 4

## Conexões

```
ESP32          Componente
─────────────────────────
3V3      →     OLED VCC, DHT VCC, PIR VCC
GND      →     OLED GND, DHT GND, PIR GND
GPIO 21  →     OLED SDA
GPIO 22  →     OLED SCL
GPIO 4   →     DHT DATA
GPIO 27  →     PIR OUT
```

## Instalação

1. **Instale o MicroPython no ESP32** (se ainda não tiver):
   ```bash
   esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
   esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 esp32-micropython.bin
   ```

2. **Instale as bibliotecas necessárias**:
   - A biblioteca `ssd1306` pode ser instalada via `upip` ou copiada manualmente
   - O driver DHT geralmente já vem incluído no MicroPython

3. **Copie os arquivos para o ESP32**:
   ```bash
   ampy --port /dev/ttyUSB0 put main.py
   ```

## Configuração

Se você estiver usando **DHT22** em vez de DHT11, altere a linha 15 do `main.py`:

```python
dht_sensor = dht.DHT22(Pin(DHT_PIN))  # Troque DHT11 por DHT22
```

## Funcionamento

- O sistema monitora continuamente o sensor PIR
- Quando movimento é detectado, a temperatura é lida e exibida no OLED
- O display permanece ativo por **8 segundos** após a detecção
- Após 8 segundos, o display é limpo automaticamente
- O ciclo se repete quando novo movimento é detectado

## Estrutura do Código

- `main.py`: Código principal do sistema
- `requirements.txt`: Lista de dependências
- `README.md`: Este arquivo

## Notas

- O sensor PIR pode ter um pequeno delay após ser ligado (aquecimento)
- Se o DHT não ler corretamente, verifique as conexões (fios curtos recomendados)
- Todos os componentes devem compartilhar o mesmo GND
