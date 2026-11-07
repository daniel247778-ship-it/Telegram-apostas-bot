import os
import time
import threading
import requests
from datetime import datetime

from flask import Flask

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_KEY = os.environ.get("API_FOOTBALL_KEY")

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
API_URL = "https://v3.football.api-sports.io"

# Competições
LEAGUES = {
    94: "🇵🇹 Primeira Liga",
    95: "🇵🇹 Liga Portugal 2",
    39: "🏴 Premier League",
    140: "🇪🇸 La Liga",
    135: "🇮🇹 Serie A",
    78: "🇩🇪 Bundesliga",
    61: "🇫🇷 Ligue 1",
    2: "🏆 Champions League"
}

CHAT_ID = None
LAST_UPDATE_ID = 0
SENT_MATCHES = set()


def telegram(method, data=None):
    try:
        r = requests.post(
            f"{TELEGRAM_URL}/{method}",
            json=data or {},
            timeout=20
        )
        return r.json()
    except Exception as e:
        print("Telegram error:", e)
        return {}


def send_message(text):
    global CHAT_ID

    if not CHAT_ID:
        print("CHAT_ID ainda não definido.")
        return

    telegram("sendMessage", {
        "chat_id": CHAT_ID,
        "text": text
    })


def api_get(endpoint, params):
    try:
        r = requests.get(
            f"{API_URL}/{endpoint}",
            headers={"x-apisports-key": API_KEY},
            params=params,
            timeout=20
        )

        data = r.json()

        if data.get("errors"):
            print("API-Football:", data["errors"])
            return None

        return data

    except Exception as e:
        print("API error:", e)
        return None


def obter_jogos():
    """
    Procura os próximos 2 jogos de cada competição.
    """
    jogos = []

    ano = datetime.now().year

    for league_id, league_name in LEAGUES.items():

        data = api_get(
            "fixtures",
            {
                "league": league_id,
                "season": ano,
                "next": 2,
                "timezone": "Europe/Lisbon"
            }
        )

        if not data:
            continue

        for item in data.get("response", []):
            jogos.append({
                "id": item["fixture"]["id"],
                "league_id": league_id,
                "league": league_name,
                "date": item["fixture"]["date"],
                "home": item["teams"]["home"]["name"],
                "away": item["teams"]["away"]["name"]
            })

    return jogos


def obter_previsao(fixture_id):
    """
    Usa o endpoint Predictions da API-Football.
    """
    data = api_get(
        "predictions",
        {
            "fixture": fixture_id
        }
    )

    if not data or not data.get("response"):
        return None

    return data["response"][0]


def criar_previsao(jogo, prediction):
    """
    Converte a resposta da API num texto simples para o Telegram.
    """

    pred = prediction.get("predictions", {})

    vencedor = pred.get("winner") or {}
    advice = pred.get("advice") or "Sem recomendação"

    home_win = pred.get("percent", {}).get("home", "?")
    draw = pred.get("percent", {}).get("draw", "?")
    away_win = pred.get("percent", {}).get("away", "?")

    vencedor_nome = vencedor.get("name")

    hora = jogo["date"]

    try:
        dt = datetime.fromisoformat(
            hora.replace("Z", "+00:00")
        )
        hora = dt.strftime("%d/%m %H:%M")
    except:
        pass

    texto = (
        f"⚽ PREVISÃO\n\n"
        f"{jogo['league']}\n"
        f"📅 {hora}\n\n"
        f"🏠 {jogo['home']}\n"
        f"✈️ {jogo['away']}\n\n"
        f"📊 Probabilidades\n"
        f"🏠 Casa: {home_win}%\n"
        f"🤝 Empate: {draw}%\n"
        f"✈️ Fora: {away_win}%\n\n"
    )

    if vencedor_nome:
        texto += f"🎯 Favorito: {vencedor_nome}\n"

    texto += f"💡 Sugestão da API: {advice}\n\n"
    texto += "⚠️ Análise estatística — não é garantia de aposta."

    return texto


def fazer_scan():
    """
    Faz uma procura de jogos e envia previsões novas.
    """

    global SENT_MATCHES

    print("🔎 A procurar jogos...")

    jogos = obter_jogos()

    print(f"Encontrados {len(jogos)} jogos.")

    enviados = 0

    for jogo in jogos:

        if jogo["id"] in SENT_MATCHES:
            continue

        prediction = obter_previsao(jogo["id"])

        if not prediction:
            continue

        texto = criar_previsao(jogo, prediction)

        send_message(texto)

        SENT_MATCHES.add(jogo["id"])
        enviados += 1

        # Pequena pausa para evitar demasiados pedidos
        time.sleep(1)

    print(f"Previsões enviadas: {enviados}")


def comandos_telegram():
    """
    Recebe comandos enviados no Telegram.
    """

    global LAST_UPDATE_ID
    global CHAT_ID

    while True:

        try:

            data = telegram(
                "getUpdates",
                {
                    "offset": LAST_UPDATE_ID + 1,
                    "timeout": 30
                }
            )

            updates = data.get("result", [])

            for update in updates:

                LAST_UPDATE_ID = update["update_id"]

                message = update.get("message")

                if not message:
                    continue

                chat = message.get("chat", {})
                CHAT_ID = chat.get("id")

                texto = message.get("text", "").strip()

                print(
                    f"Mensagem recebida: {texto} | CHAT_ID: {CHAT_ID}"
                )

                if texto.startswith("/start"):

                    send_message(
                        "🤖 Olá!\n\n"
                        "Sou o robô de previsões de futebol.\n\n"
                        "Comandos:\n"
                        "/teste - testar o bot\n"
                        "/previsoes - procurar previsões agora\n"
                        "/status - verificar estado"
                    )

                elif texto.startswith("/teste"):

                    send_message(
                        "✅ Bot funcionando corretamente!\n"
                        "Telegram ligado ao servidor."
                    )

                elif texto.startswith("/status"):

                    send_message(
                        "🟢 Bot online.\n\n"
                        "📡 API-Football: ligada\n"
                        "📲 Telegram: ligado\n"
                        "⚽ Competições: 8"
                    )

                elif texto.startswith("/previsoes"):

                    send_message(
                        "🔎 Vou procurar os próximos jogos "
                        "e calcular as previsões..."
                    )

                    threading.Thread(
                        target=fazer_scan,
                        daemon=True
                    ).start()

        except Exception as e:

            print("Erro no Telegram:", e)
            time.sleep(5)


def ciclo_automatico():
    """
    Faz uma análise inicial e depois repete aproximadamente
    a cada 6 horas.
    """

    time.sleep(10)

    while True:

        try:
            fazer_scan()
        except Exception as e:
            print("Erro no scan:", e)

        # 6 horas
        time.sleep(21600)


@app.route("/")
def home():
    return "Telegram-apostas-bot is online!"


@app.route("/health")
def health():
    return "OK"


if __name__ == "__main__":

    print("🤖 Telegram-apostas-bot iniciado!")

    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN não configurado!")

    if not API_KEY:
        print("❌ API_FOOTBALL_KEY não configurado!")

    # Receber comandos do Telegram
    threading.Thread(
        target=comandos_telegram,
        daemon=True
    ).start()

    # Análises automáticas
    threading.Thread(
        target=ciclo_automatico,
        daemon=True
    ).start()

    # Servidor Flask para o Render
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
