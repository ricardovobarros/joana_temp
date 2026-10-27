# Ventilador com a Shelly Plug M Gen3

O ventilador fica ligado a uma tomada **Shelly Plug M Gen3**. A tomada publica no EMQX se está ligada e quantos watts o ventilador gasta. O backend converte os watts na velocidade e o site mostra o cartão **🌀 Ventilador**.

O que o site mostra:

| Situação | No cartão |
|---|---|
| Tomada sem ligação há mais de 90 s | **Offline** |
| Tomada com energia, ventilador em espera | **Desligado** (Em espera) |
| Watts dentro de uma faixa | **V1**, **V2**, ... (Ligado) |
| Watts fora de todas as faixas | **Ligado** (Velocidade desconhecida) |
| Tomada cortada | **Desligado** (Tomada sem energia), com o botão "Religar tomada" |

O botão **"Desligar ventilador"** corta a energia da tomada. Como o ventilador arranca sempre desligado, ligá-lo outra vez só dá no botão do próprio ventilador.

O código já está pronto. Falta configurar a tomada, medir as potências, preencher as faixas e publicar.

---

## Passo 1: ligar a tomada ao Wi-Fi

1. Liga a Shelly à parede e o ventilador à Shelly.
2. Instala a app **Shelly Smart Control** no telemóvel e adiciona a tomada. Liga-a à rede **FRITZ!Box 7412**, que tem de ser a de 2,4 GHz.
3. Na app, atualiza o firmware da tomada, se houver atualização.
4. Descobre o IP da tomada: na app, em Settings → Device information, ou em [http://fritz.box](http://fritz.box) → Heimnetz → Netzwerk.
5. Abre `http://<IP-da-tomada>` no browser do Mac. É lá que fazes o resto da configuração.

## Passo 2: criar o utilizador da tomada no EMQX

1. Abre a consola do EMQX, no deployment `t0bc1b61`.
2. Vai a **Access Control → Authentication → Users** e adiciona:
   - Username: `shelly`
   - Password: uma senha nova, que guardas para o passo seguinte.

Se um dia criares regras de autorização (ACL) no EMQX, tens de permitir:
- `joana/plug/#` ao utilizador `shelly` e ao `backend`;
- `joana-backend/rpc` ao `shelly`, porque é onde ele envia as respostas.

## Passo 3: configurar o MQTT na tomada

Na página web da tomada, abre **Settings → MQTT**. O nome exato do menu pode variar um pouco com a versão do firmware. Preenche:

| Campo | Valor |
|---|---|
| Enable | ligado |
| Server | `t0bc1b61.ala.eu-central-1.emqxsl.com:8883` |
| Client ID | `joana-plug` |
| Username / Password | `shelly` / a senha do passo 2 |
| MQTT prefix | `joana/plug` |
| Connection type (SSL/TLS) | **Default TLS** (TLS com verificação). Se não ligar, usa **TLS no validation**. |
| RPC over MQTT | ligado |
| RPC status notifications over MQTT | ligado |
| Generic status update over MQTT | ligado |

Guarda. A tomada reinicia. Para confirmar, na consola do EMQX, em **Monitoring → Clients**, tem de aparecer o `joana-plug`.

## Passo 4: Auto ON e arranque ligado

Ainda na página web da tomada, na configuração da saída (Output / Switch):

1. **Auto ON**: ligado, com **5 segundos**. Quando carregas em "Desligar ventilador" no site, a tomada corta a energia e volta a ligá-la 5 segundos depois. O ventilador fica desligado, mas pronto para ser ligado no botão dele.
2. **Power on default / Estado após falha de energia**: **ON**. Depois de uma falha de luz, a tomada volta a dar energia.

## Passo 5: medir a potência de cada velocidade

A página web da tomada mostra a potência em tempo real, em watts.

1. Com o ventilador **desligado** (em espera), anota os watts. Fica tipicamente entre 0 W e 2 W.
2. Liga a **velocidade 1**, espera 30 segundos e anota o valor mais baixo e o mais alto que vires.
3. Repete para cada velocidade.
4. Se o ventilador oscilar, mede também com a oscilação ligada, porque ela pode somar alguns watts.

| Velocidade | Mínimo medido (W) | Máximo medido (W) |
|---|---|---|
| Em espera | | |
| V1 | | |
| V2 | | |
| V3 | | |

## Passo 6: preencher as faixas

Abre **`backend/fan_speeds.py`**. É o único sítio a mudar:

```python
FAN_SPEEDS = [
    # (nome,  mínimo W, máximo W)
    ("V1", 5, 10),
    ("V2", 10, 20),
    ("V3", 20, 35),
]
```

Regras:
- Cada faixa vale de **mínimo (incluído)** até **máximo (excluído)**. Por exemplo, `("V1", 5, 10)` quer dizer maior ou igual a 5 W e menor que 10 W.
- Abaixo do mínimo da **primeira** faixa, o site mostra "Desligado". Esse mínimo tem de ficar acima do consumo em espera.
- Dá uma margem e põe o limite entre duas velocidades a meio caminho entre as medições. Se a V1 mediu 22 W a 24 W e a V2 mediu 30 W a 33 W, usa `("V1", 15, 27)` e `("V2", 27, 38)`.
- As faixas não se devem sobrepor. Se o ventilador tiver mais ou menos velocidades, acrescenta ou apaga linhas.
- O nome é o que aparece no site. Pode ser `"V1"`, `"Baixa"`, `"Turbo"`, etc.

## Passo 7: testar no Mac antes de publicar

```bash
cd ~/Documents/CURSOR/Eletronic-Projects/joana_temp
cd web && flutter build web && cd ..
cd backend
set -a; source .env; set +a
MQTT_CLIENT_ID=joana-backend-local STATIC_DIR=../web/build/web .venv/bin/uvicorn main:app
```

1. Abre [http://localhost:8000](http://localhost:8000).
2. Muda de velocidade no ventilador. Em até 30 segundos o cartão tem de mostrar a velocidade certa e os watts.
3. Testa o botão "Desligar ventilador".

O `MQTT_CLIENT_ID=joana-backend-local` é importante: com o mesmo ID do Fly.io, o EMQX desligava o backend publicado.

Para ver o estado diretamente:

```bash
curl -s http://localhost:8000/api/dashboard | python3 -c "import sys,json; print(json.load(sys.stdin)['fan'])"
```

Para parar o servidor local, carrega em `Ctrl+C`.

## Passo 8: publicar

Na pasta `joana_temp`:

```bash
fly deploy --ha=false --remote-only
fly logs    # deve aparecer "Ligado ao MQTT ..."
```

Abre [https://joana-temp-ricardo.fly.dev](https://joana-temp-ricardo.fly.dev) e confirma o cartão 🌀 Ventilador.

Depois guarda as faixas no git:

```bash
git add backend/fan_speeds.py
git commit -m "Faixas de potência do ventilador"
git push
```

## Problemas comuns

| Sintoma | O que verificar |
|---|---|
| Cartão sempre "Offline" | `joana-plug` aparece nos Clients do EMQX? Prefixo exatamente `joana/plug`? "RPC over MQTT" ligado? |
| A tomada não liga ao EMQX | Usa "TLS no validation"; confirma a porta 8883, o utilizador e a senha |
| Mostra "Ligado" sem velocidade | Os watts caíram num intervalo entre faixas; alarga as faixas no `fan_speeds.py` |
| Mostra "Desligado" com o ventilador a rodar | O mínimo da primeira faixa está alto demais |
| "Desligar ventilador" não faz nada | O botão só fica ativo com o ventilador ligado e a tomada online |
