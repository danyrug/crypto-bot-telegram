import requests
import os
from datetime import datetime

# --- CONFIGURAZIONE ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Fallback per test locale (i tuoi dati)
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
        "vs_currencies": VALUTA,
        "include_24hr_change": "true" # ABBIAMO AGGIUNTO QUESTO
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
    # Usiamo la versione con print per debug, utile se ci sono problemi
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram status: {response.status_code}")
    except Exception as e:
        print(f"Errore invio Telegram: {e}")

def main():
    data = get_prices()
    
    if data:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        message = f"📊 **Report Mercato** ({now})\n\n"
        
        for crypto in CRYPTO_IDS:
            if crypto in data:
                price = data[crypto][VALUTA]
                change_24h = data[crypto].get(f"{VALUTA}_24h_change", 0)
                
                # Scegliamo l'emoji in base al segno
                if change_24h >= 0:
                    emoji = "🟢"
                else:
                    emoji = "🔴"
                
                # Formattiamo: Nome: Prezzo (Emoji Percentuale%)
                # :+.2f significa "metti sempre il segno + o - e usa 2 decimali"
                message += f"🔹 *{crypto.capitalize()}:* € {price:,.2f} ({emoji} {change_24h:+.2f}%)\n"
        
        send_telegram_message(message)

if __name__ == "__main__":
    main()
