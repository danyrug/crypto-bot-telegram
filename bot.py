import requests
import os
from datetime import datetime

# --- CONFIGURAZIONE ---
# Leggiamo i dati dalle "variabili segrete" di GitHub per sicurezza
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Se non trova le variabili (es. test locale), usa quelli che mi hai dato
if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = "8504447951:AAHkFvYwK_A2k76gendESC41-a2u03pQ7-c"
if not CHAT_ID:
    CHAT_ID = "211228574"

CRYPTO_IDS = ["bitcoin", "ethereum", "solana", "ripple", "cardano", "polkadot"]
VALUTA = "eur"

def get_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(CRYPTO_IDS),
        "vs_currencies": VALUTA
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Errore API: {e}")
        return None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def main():
    data = get_prices()
    if data:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        message = f"📊 **Report Orario** ({now})\n\n"
        for crypto in CRYPTO_IDS:
            if crypto in data:
                price = data[crypto][VALUTA]
                message += f"🔹 *{crypto.capitalize()}:* € {price:,.2f}\n"
        
        send_telegram_message(message)
        print("Messaggio inviato, chiusura script.")

if __name__ == "__main__":
    main()
