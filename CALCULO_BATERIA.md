# Cálculo de Duração das Baterias

## Configuração: 4 Pilhas

### Assumindo Pilhas AA (mais comum)

**Opção 1: 4 Pilhas em Série (6V)**
- Tensão: 4 × 1.5V = **6V**
- Capacidade: **2500 mAh** (capacidade de uma pilha, pois estão em série)
- Total de energia: 6V × 2.5Ah = **15 Wh**

**Opção 2: 4 Pilhas em Paralelo (1.5V)**
- Tensão: **1.5V** (não recomendado para ESP32, precisa de regulador)
- Capacidade: 4 × 2500 mAh = **10000 mAh**
- Total de energia: 1.5V × 10Ah = **15 Wh**

**Assumindo série (mais comum): 6V, 2500 mAh**

---

## Consumo do Sistema

### Estados de Operação:

1. **Modo Inativo (Light Sleep)**
   - Consumo: **~8-12 mA** @ 6V
   - Quando: 95% do tempo (quando não há movimento)

2. **Modo Ativo (Display + DHT)**
   - Consumo: **~80-100 mA** @ 6V
   - Quando: 5% do tempo (8 segundos a cada detecção de movimento)

### Consumo Médio (exemplo):

**Cenário 1: Uso Moderado (1 detecção a cada 5 minutos)**
- Ativo: 8s a cada 5min = 8s / 300s = 2.67% do tempo
- Inativo: 97.33% do tempo
- Consumo médio: (0.0267 × 90mA) + (0.9733 × 10mA) = **12.1 mA**

**Cenário 2: Uso Intenso (1 detecção a cada 1 minuto)**
- Ativo: 8s a cada 60s = 8s / 60s = 13.33% do tempo
- Inativo: 86.67% do tempo
- Consumo médio: (0.1333 × 90mA) + (0.8667 × 10mA) = **20.7 mA**

**Cenário 3: Uso Muito Intenso (1 detecção a cada 30 segundos)**
- Ativo: 8s a cada 30s = 8s / 30s = 26.67% do tempo
- Inativo: 73.33% do tempo
- Consumo médio: (0.2667 × 90mA) + (0.7333 × 10mA) = **31.3 mA**

---

## Duração Estimada

### Com 4 Pilhas AA (2500 mAh @ 6V):

| Cenário | Consumo Médio | Duração Estimada |
|---------|---------------|------------------|
| Uso Moderado (1x/5min) | 12.1 mA | **~206 horas (8.6 dias)** |
| Uso Intenso (1x/1min) | 20.7 mA | **~120 horas (5 dias)** |
| Uso Muito Intenso (1x/30s) | 31.3 mA | **~80 horas (3.3 dias)** |

### Fatores que Afetam a Duração:

✅ **Aumenta duração:**
- Menos detecções de movimento
- Temperatura ambiente mais baixa
- Pilhas de qualidade (Energizer, Duracell)
- Pilhas alcalinas (vs recarregáveis NiMH)

❌ **Diminui duração:**
- Muitas detecções de movimento
- Temperatura muito alta
- Pilhas baratas ou antigas
- Regulador de tensão ineficiente (se usado)

---

## Recomendações para Maximizar Duração:

1. **Ajustar sensibilidade do PIR** para evitar detecções falsas
2. **Usar pilhas alcalinas de qualidade** (Duracell, Energizer)
3. **Verificar regulador de tensão** - se usar 6V, precisa de regulador para 3.3V
4. **Monitorar temperatura** - muito calor reduz eficiência

---

## Nota Importante sobre Tensão:

O ESP32 precisa de **3.3V**. Se você está usando 4 pilhas em série (6V), **PRECISA de um regulador de tensão** (ex: AMS1117-3.3) para reduzir de 6V para 3.3V.

O regulador tem uma eficiência de ~80-85%, então:
- Consumo real = Consumo calculado / 0.82
- Duração real = Duração calculada × 0.82

**Duração real ajustada:**
- Uso Moderado: **~169 horas (7 dias)**
- Uso Intenso: **~98 horas (4 dias)**
- Uso Muito Intenso: **~66 horas (2.7 dias)**

---

## Alternativa: Bateria LiPo

Se quiser mais duração, considere:
- **Bateria LiPo 3.7V 2000 mAh**: ~5-7 dias de uso moderado
- **Bateria LiPo 3.7V 5000 mAh**: ~12-15 dias de uso moderado
- Não precisa de regulador (usa diretamente 3.3V ou com step-down eficiente)



