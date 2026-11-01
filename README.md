# joana_temp: timer e temperatura do quarto

Um ESP32 com um botão e um ecrã OLED funciona como timer (até 12 horas) e mede a temperatura do quarto a cada 15 minutos. Os dados vão por MQTT (EMQX Serverless) para um backend no Fly.io, que os grava no Supabase e serve um site Flutter.

O site também mostra o ventilador do quarto (desligado, ligado e velocidade) e permite desligá-lo, através de uma tomada Shelly Plug M Gen3. Configuração em [VENTILADOR.md](VENTILADOR.md).

```
ESP32 --MQTT/TLS--> EMQX Serverless <--MQTT/TLS--> Backend Python (Fly.io) --> Supabase
                                                       ^
                                       Site Flutter ---+ (HTTPS /api)
```

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `firmware/` | MicroPython do ESP32 (`main.py`, `ssd1306.py`, `config.example.py`) |
| `backend/` | FastAPI + ponte MQTT -> Supabase; também serve o site |
| `web/` | Site Flutter (gráficos + timer) |
| `supabase/schema.sql` | Tabelas da base de dados |
| `Dockerfile`, `fly.toml` | Deploy no Fly.io |

## Hardware

- ESP32 Dev Module, alimentado por USB
- OLED SSD1306 128x64 I2C
- DHT11
- 3 botões de pressão (2 pinos cada)

```
ESP32          Componente
─────────────────────────────────
3V3      →     OLED VCC, DHT VCC
GND      →     OLED GND, DHT GND, botão (um pino)
GPIO 21  →     OLED SDA
GPIO 22  →     OLED SCL
GPIO 4   →     DHT DATA
GPIO 14  →     botão do timer (outro pino)
GPIO 27  →     botão de override da energia (outro pino)
GPIO 13  →     botão de sono do bebé (outro pino)
```

Os botões usam o pull-up interno do ESP32, não precisam de resistência.

## Funcionamento

- **GPIO 14, clique curto:** mostra o tempo por 3 segundos
- **GPIO 14, segurar 2 segundos:** alterna o timer; mostra `ON`/`OFF` por
  1,5 segundo e `00:01`/`00:00` por mais 1,5 segundo
- **GPIO 27, clique curto:** restaura a energia da tomada se estiver cortada
- **GPIO 13, clique curto:** mostra se o bebé está dormindo ou acordado
- **GPIO 13, segurar 2 segundos:** registra que dormiu/acordou e mostra a
  saudação e o emoji por 2 segundos cada
- Fora dessas mensagens, o OLED fica apagado e os timers continuam contando
- Ao chegar às **12:00** o timer desliga sozinho
- O site pode **ativar ou desativar** o timer à distância
- O site pode **registar que o bebé dormiu ou acordou** à distância
- A temperatura é lida a cada **15 minutos**; sem internet, as leituras e eventos ficam em fila (até 20) e são enviados quando a ligação voltar

Tópicos MQTT (prefixo `joana`):

| Tópico | Quem envia | Conteúdo |
|---|---|---|
| `joana/temp` | ESP32 | `{"t": 22, "h": 55, "ago_s": 0}` |
| `joana/timer/state` | ESP32 (retido) | `{"running": true, "elapsed_s": 0, "event": "start", "reason": "button", "ago_s": 0}` |
| `joana/timer/cmd` | backend | `start` ou `stop` |
| `joana/status` | ESP32 (retido) | `online` / `offline` |
| `joana/sleep/state` | ESP32 (retido) | estado e evento de sono/acordar |
| `joana/sleep/cmd` | backend | `sleep` ou `wake` |
| `joana/plug/override` | ESP32 | pedido para restaurar a energia da tomada |
| `joana/plug/online` | Shelly | `true` / `false` |
| `joana/plug/status/switch:0`, `joana/plug/events/rpc` | Shelly | estado da tomada e potência (`output`, `apower`) |
| `joana/plug/rpc` | backend | pedidos RPC (`Switch.GetStatus`, `Switch.Set`); respostas em `joana-backend/rpc` |

## Passo a passo para pôr a funcionar

### 1. EMQX Serverless (MQTT)

1. Cria conta em [cloud-intl.emqx.com](https://cloud-intl.emqx.com) e um deployment **Serverless** (tem uma quota grátis mensal; define o **Spend Limit** a `0` para nunca pagar)
2. Em **Overview**, copia o **Address** (ex.: `abc123.ala.eu-central-1.emqxsl.com`); a porta MQTT over TLS é `8883`
3. Em **Access Control -> Authentication**, cria dois utilizadores:
   - `esp32` (para o ESP32)
   - `backend` (para o Fly.io)

### 2. Supabase (base de dados)

1. No projeto Supabase, abre **SQL Editor -> New query**, cola o conteúdo de [`supabase/schema.sql`](supabase/schema.sql) e carrega em **Run**
2. Em **Project Settings -> API Keys**, copia a chave **secret** (`sb_secret_...`) ou a antiga **service_role**
3. Em **Project Settings -> Data API**, copia o **Project URL** (`https://xxxx.supabase.co`)

A chave secret dá acesso total à base de dados: só vai para o Fly.io, nunca para o site nem para o ESP32.

### 3. Firmware no ESP32

No Terminal do Mac:

```bash
pip3 install mpremote
ls /dev/cu.*        # descobre a porta do ESP32, ex.: /dev/cu.usbserial-0001
```

Se o ESP32 ainda não tiver MicroPython:

```bash
pip3 install esptool
esptool.py --chip esp32 --port /dev/cu.usbserial-0001 erase_flash
esptool.py --chip esp32 --port /dev/cu.usbserial-0001 write_flash -z 0x1000 ESP32_GENERIC-xxxx.bin
```

(o `.bin` descarrega-se em [micropython.org/download/ESP32_GENERIC](https://micropython.org/download/ESP32_GENERIC/))

Depois:

```bash
cd firmware
cp config.example.py config.py      # preenche WiFi e EMQX (utilizador esp32)
mpremote connect /dev/cu.usbserial-0001 mip install umqtt.simple
mpremote connect /dev/cu.usbserial-0001 cp main.py ssd1306.py config.py :
mpremote connect /dev/cu.usbserial-0001 reset
mpremote connect /dev/cu.usbserial-0001 repl   # ver os logs (sair: Ctrl+])
```

### 4. Fly.io (backend + site)

O `backend/.env` (ver `backend/.env.example`) tem de ter estas variáveis:

| Variável | Valor |
|---|---|
| `SUPABASE_URL` | Project URL do Supabase |
| `SUPABASE_SERVICE_KEY` | chave secret / service_role |
| `MQTT_HOST` | Address do EMQX |
| `MQTT_PORT` | `8883` |
| `MQTT_USER` | `backend` |
| `MQTT_PASS` | senha da credencial `backend` |
Depois, na pasta `joana_temp`:

```bash
brew install flyctl
fly auth login
fly apps create joana-temp-ricardo
grep -v '^SUPABASE_DB_PASSWORD=' backend/.env | fly secrets import --stage
fly deploy --ha=false
fly logs            # deve aparecer "Ligado ao MQTT ..."
```

O site fica em `https://joana-temp-ricardo.fly.dev`. O Fly constrói a imagem nos servidores dele (não precisas de Docker no Mac).

Tem de haver **só 1 máquina** (o backend tem um cliente MQTT com ID fixo; duas máquinas derrubavam-se uma à outra). Por isso o deploy usa `--ha=false`, e o `fly.toml` desliga o adormecimento automático (`auto_stop_machines = "off"`) para a ponte MQTT nunca parar. Para confirmar: `fly status`.

## Desenvolvimento local

Backend (usa o `backend/.env`):

```bash
cd web && flutter build web && cd ..
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
set -a; source .env; set +a
MQTT_CLIENT_ID=joana-backend-local STATIC_DIR=../web/build/web .venv/bin/uvicorn main:app --reload
```

Abre [http://localhost:8000](http://localhost:8000). O `MQTT_CLIENT_ID` diferente evita que o backend local desligue o do Fly.io do EMQX.

## API do backend

O site e a API são públicos: quem tiver o URL vê os dados, pode ligar ou desligar o timer e desligar o ventilador.

| Método | Caminho | Descrição |
|---|---|---|
| `GET` | `/api/dashboard` | leituras dos últimos 7 dias, estado do ESP32, última sessão do timer e estado do ventilador (`fan`) |
| `GET` | `/api/sleep` | períodos e estado atual do sono do bebé |
| `POST` | `/api/sleep` | `{"action": "sleep"}` ou `{"action": "wake"}` |
| `POST` | `/api/timer` | `{"action": "start"}` ou `{"action": "stop"}` |
| `POST` | `/api/fan` | `{"action": "off"}` desliga a tomada; `{"action": "plug_on"}` volta a dar-lhe energia |
| `GET` | `/api/health` | verificação de saúde do Fly.io |
