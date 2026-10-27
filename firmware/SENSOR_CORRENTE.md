# Sensor de corrente SCT-013 sem ADS1115

Sem o ADS1115, o sensor liga direto ao ADC do ESP32. Só se acrescentam o sensor e 4 componentes ao que já existe.

## Ligação completa do sistema

| Componente | Pino do componente | ESP32 |
|---|---|---|
| OLED | VCC / GND | 3,3 V / GND |
| OLED | SDA / SCL | GPIO21 / GPIO22 |
| DHT11 | VCC / GND | 3,3 V / GND |
| DHT11 | DATA | GPIO4 |
| Botão | perna 1 / perna 2 (diagonais) | GPIO14 / GND |
| **Sensor SCT-013** | fio 1 | ponto de 1,65 V do divisor |
| **Sensor SCT-013** | fio 2 | **GPIO34** |

## Circuito do sensor

```
3,3V ──[10k]──┬──[10k]── GND
              │
              ├──[10µF]── GND
              │
              └──── fio 1 do sensor ──┐
                                      [100Ω]
GPIO34 ───────────── fio 2 do sensor ─┘
```

### Componentes

| Componente | Quantidade | Para quê |
|---|---|---|
| Resistência 100 Ω | 1 | Converte a corrente do sensor em tensão (resistência de carga) |
| Resistência 10 kΩ | 2 | Divisor que cria os 1,65 V de polarização |
| Condensador 10 µF | 1 | Estabiliza a polarização |

O GPIO34 fica parado em cerca de 1,65 V (cerca de 2048 na leitura do ADC). Quando o aparelho liga, o valor passa a oscilar à volta desse ponto. O código mede essa oscilação, ou seja, o máximo menos o mínimo, e decide se o aparelho está ligado ou desligado.

## Código (MicroPython)

```python
from machine import ADC, Pin

ct = ADC(Pin(34))
ct.atten(ADC.ATTN_11DB)

def equipamento_ligado(limite=150):
    lo, hi = 4095, 0
    for _ in range(400):  # ~40 ms, cobre 2 ciclos de 50 Hz
        v = ct.read()
        lo = min(lo, v)
        hi = max(hi, v)
    return (hi - lo) > limite
```

O valor de `limite` acerta-se a testar: vê a diferença com o aparelho desligado (só ruído) e com ele ligado, e escolhe um valor no meio.

## Atenções

- Usa o GPIO34, ou outro do ADC1 (GPIO32 a 39). Os pinos ADC2 não funcionam com o Wi-Fi ligado.
- A pinça envolve só um fio, a fase, e não o cabo inteiro.
- Para aparelhos abaixo de cerca de 50 W o sinal fica fraco. Nesse caso usa uma resistência de carga maior (330 Ω a 1 kΩ) ou dá 2 a 3 voltas com o fio dentro da pinça.

## Comparação com o ADS1115

| | Direto no ESP32 | Com ADS1115 |
|---|---|---|
| Componentes extra | 3 resistências e 1 condensador | os mesmos, mais a placa |
| Resolução | 12 bits, com algum ruído | 16 bits, mais limpo |
| Aparelhos pequenos (abaixo de 50 W) | difícil | melhor |
| Para saber se está ligado ou desligado | suficiente | mais do que o necessário |

Se o aparelho gastar mais de uns 100 W, a ligação direta ao ESP32 chega.

## Alternativa sem ESP32 nem ADS1115

Uma tomada inteligente com MQTT, a Shelly Plug S (cerca de 20 €), liga-se direto ao EMQX e publica se o aparelho está ligado e quantos watts gasta. Não precisa de fios nem de alterar o ESP32.
