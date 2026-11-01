# Ventilador com a Shelly Plug M Gen3

O ventilador fica ligado a uma tomada **Shelly Plug M Gen3**. A tomada publica no EMQX se está ligada e quantos watts o ventilador gasta. O backend converte os watts na velocidade e o site mostra o cartão **🌀 Ventilador**.

O que o site mostra:

| Situação | No cartão |
|---|---|
| Tomada sem ligação há mais de 90 s | **Offline** |
| Tomada com energia, ventilador em espera | **Desligado** (Em espera) |
| Watts dentro de uma faixa | **V1**, **V2**, ... (Ligado) |
| Watts fora de todas as faixas | **Ligado** (Velocidade desconhecida) |
| Tomada cortada | **Desligado** (Sem energia até às 8:00). O botão diz "Ligar energia" |
| Tomada com energia e ventilador parado | **Desligado**. O botão diz "Ligar energia"; "Cortar energia" tira a corrente |

O botão **"Desligar ventilador"** corta a energia e deixa a tomada desligada. A energia volta às **8:00** (hora da Alemanha) ou nesse mesmo botão, que passa a **Ligar energia**. O ventilador em si continua a ligar-se só no botão dele.

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

## Passo 4: energia só às 8:00 ou pelo botão

Na saída da tomada (Output / Switch):

1. **Auto ON**: desligado. A tomada não volta a dar energia sozinha depois de desligar.
2. **Estado após falha de energia**: **OFF**. Uma falha de luz não liga o relé outra vez.
3. Um agendamento diário às **8:00**, fuso **Europe/Berlin**, executa `Switch.Set` com `on: true`.

O botão do site também liga a energia na hora, sem esperar pelas 8:00.

## Passo 5: medir a potência de cada velocidade

A página web da tomada mostra a potência em tempo real, em watts.

1. Com o ventilador **desligado** (em espera), anota os watts. Fica tipicamente entre 0 W e 2 W.
2. Liga a **velocidade 1**, espera 30 segundos e anota o valor mais baixo e o mais alto que vires.
3. Repete para cada velocidade.
4. Se o ventilador oscilar, mede também com a oscilação ligada, porque ela pode somar alguns watts.

| Velocidade | Mínimo medido (W) | Máximo medido (W) |
|---|---|---|
| Em espera | | |
| V1 | 3.3 | 3.3 |
| V2 | 6.8 | 6.8 |
| V3 | 8.2 | 8.2 |
| V4 | 9.3 | 9.3 |
| V5 | 11.3 | 11.3 |
| V6 | 13.8 | 13.8 |
| V7 | 15.4 | 15.4 |
| V8 | acima de 16.2 | |

## Passo 6: preencher as faixas

Abre **`backend/fan_speeds.py`**. É o único sítio a mudar:

```python
FAN_SPEEDS = [
    # (nome,  mínimo W, máximo W)  medições: 3.3, 6.8, 8.2, 9.3, 11.3, 13.8, 15.4
    ("V1", 1.7, 5.1),
    ("V2", 5.1, 7.5),
    ("V3", 7.5, 8.8),
    ("V4", 8.8, 10.3),
    ("V5", 10.3, 12.6),
    ("V6", 12.6, 14.6),
    ("V7", 14.6, 16.2),
    ("V8", 16.2, float("inf")),
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
