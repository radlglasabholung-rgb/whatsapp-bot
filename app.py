from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mein_geheimer_token")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")


def verbessere_text(text):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Du bist ein Assistent der deutsche Texte verbessert. "
                    "Verbessere den folgenden Text grammatikalisch und stilistisch. "
                    "Behalte den ursprünglichen Sinn bei. "
                    "Gib NUR den verbesserten Text zurück, ohne Erklärungen oder Kommentare."
                )
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=data
    )
    result = response.json()
    return result["choices"][0]["message"]["content"]


def sende_nachricht(telefon_nummer, nachricht):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": telefon_nummer,
        "text": {"body": nachricht}
    }
    requests.post(url, headers=headers, json=data)


@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Fehler", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" in value:
            message = value["messages"][0]
            telefon = message["from"]

            if message["type"] == "text":
                text = message["text"]["body"]

                if text.lower().startswith("!verbessere "):
                    original = text[12:]
                    verbessert = verbessere_text(original)
                    antwort = f"✅ Verbesserter Text:\n\n{verbessert}"
                    sende_nachricht(telefon, antwort)

                elif text.lower() == "!hilfe":
                    hilfe = (
                        "🤖 *WhatsApp Text-Bot*\n\n"
                        "Befehle:\n"
                        "• `!verbessere [dein text]` — Verbessert deinen Text\n\n"
                        "Beispiel:\n"
                        "`!verbessere hey leute könnt ihr morgen kommen`"
                    )
                    sende_nachricht(telefon, hilfe)

    except Exception as e:
        print(f"Fehler: {e}")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
