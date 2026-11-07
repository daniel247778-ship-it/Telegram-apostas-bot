import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def telegram_request(method, data=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    response = requests.post(url, json=data or {}, timeout=30)
    return response.json()

def send_message(chat_id, text):
    telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })

def telegram_loop():
    offset = None

    while True:
        try:
            data = {}

            if offset is not None:
                data["offset"] = offset

            result = telegram_request("getUpdates", data)

            if result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1

                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    text = message.get("text", "")

                    if not text:
                        continue

                    chat_id = chat.get("id")

                    if text.startswith("/start"):
                        send_message(
                            chat_id,
                            "🤖 Bot de apostas iniciado!\n\n"
                            "Vou preparar previsões de futebol para o grupo."
                        )

                    elif text.startswith("/teste"):
                        send_message(
                            chat_id,
                            "✅ Teste recebido! O bot está a funcionar."
                        )

        except Exception as e:
            print("Erro:", e)

        time.sleep(2)

@app.route("/")
def home():
    return "Bot de apostas online!"

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    threading.Thread(target=telegram_loop, daemon=True).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
