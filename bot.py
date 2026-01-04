import requests
import os
import time
from datetime import datetime

# --- CONFIGURAZIONE ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Fallback
if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = "8504447951:AAHkFvYwK_A2k76gendESC41-a2u03pQ7-c"
if not CHAT_ID:
    CHAT_ID = "211228574"

CRYPTO_IDS = ["bitcoin", "ethereum", "solana", "ripple", "cardano", "polkadot"]
VALUTA = "eur"

def get_current_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(CRYPTO_IDS),
        "vs_currencies": VALUTA,
        "include_24hr_change": "true"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Errore prezzi correnti: {e}")
        return None

def get_rsi(crypto_id):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
    params = {
        "vs_currency": VALUTA,
        "days": "14",
        "interval": "daily"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices = [x[1] for x in data['prices']]
        
        if len(prices) < 14:
            return None

        # Calcolo RSI
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]

        if len(losses) == 0: return 100
        if len(gains) == 0: return 0

        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    except Exception as e:
        print(f"Errore RSI per {crypto_id}: {e}")
        return None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Errore Telegram: {e}")

def main():
    print("Inizio analisi di mercato...")
    prices_data = get_current_prices()
    
    if not prices_data:
        return

    now = datetime.now().strftime("%d/%m %H:%M")
    message = f"📊 **Report & Segnali** ({now})\n"
    message += "----------------------------\n"

    for crypto in CRYPTO_IDS:
        if crypto in prices_data:
            price = prices_data[crypto][VALUTA]
            change_24h = prices_data[crypto].get(f"{VALUTA}_24h_change", 0)
            
            # --- MODIFICA QUI ---
            # Pausa aumentata a 15 secondi per evitare il blocco API
            print(f"Calcolo RSI per {crypto}...") 
            time.sleep(15) 
            rsi = get_rsi(crypto)
            # --------------------

            emoji_trend = "🟢" if change_24h >= 0 else "🔴"
            
            rsi_text = ""
            if rsi is not None:
                if rsi <= 30:
                    rsi_text = f"\n💎 **BUY SIGNAL!** RSI {rsi:.0f} (Ipervenduto)"
                elif rsi >= 70:
                    rsi_text = f"\n🔥 **SELL SIGNAL!** RSI {rsi:.0f} (Ipercomprato)"
                else:
                    rsi_text = f" | RSI: {rsi:.0f}"
            
            # Se l'RSI fallisce ancora, metti un avviso
            if rsi is None:
                rsi_text = " | RSI: N/A (Errore API)"

            message += f"🔹 *{crypto.capitalize()}*\n"
            message += f"💶 € {price:,.2f} ({emoji_trend} {change_24h:+.2f}%)"
            message += f"{rsi_text}\n\n"
    
    send_telegram_message(message)
    print("Report inviato.")

if __name__ == "__main__":
    main()
