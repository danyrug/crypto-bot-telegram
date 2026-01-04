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

def get_market_data(crypto_id):
    """Scarica 60 giorni di dati per calcolare RSI e SMA"""
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
    params = {
        "vs_currency": VALUTA,
        "days": "60", # --- CAMBIATO A 60 GIORNI ---
        "interval": "daily"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices = [x[1] for x in data['prices']]
        
        # Ci servono almeno 60 giorni per la SMA
        if len(prices) < 60:
            return None, None

        # 1. Calcolo SMA (Media Mobile Semplice a 60 giorni)
        # Prende gli ultimi 60 prezzi e fa la media
        sma = sum(prices[-60:]) / 60
        
        # 2. Calcolo RSI (Standard a 14 periodi)
        # Usiamo solo gli ultimi 15 giorni dei 60 scaricati per l'RSI corrente
        prices_14 = prices[-15:] 
        deltas = [prices_14[i+1] - prices_14[i] for i in range(len(prices_14)-1)]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]

        if len(losses) == 0: 
            rsi = 100
        elif len(gains) == 0: 
            rsi = 0
        else:
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        return rsi, sma

    except Exception as e:
        print(f"Errore Dati per {crypto_id}: {e}")
        return None, None

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
    print("Inizio analisi 60gg...")
    prices_data = get_current_prices()
    
    if not prices_data:
        return

    now = datetime.now().strftime("%d/%m %H:%M")
    message = f"📊 **Analisi Medio Termine (60gg)**\n📅 {now}\n"
    message += "----------------------------\n"

    for crypto in CRYPTO_IDS:
        if crypto in prices_data:
            price = prices_data[crypto][VALUTA]
            change_24h = prices_data[crypto].get(f"{VALUTA}_24h_change", 0)
            
            # Pausa Anti-Blocco (15 sec)
            print(f"Analizzo {crypto}...") 
            time.sleep(15) 
            
            rsi, sma = get_market_data(crypto)

            trend_emoji = "🟢" if change_24h >= 0 else "🔴"
            
            signal_text = ""
            trend_icon = "➖" # Icona neutra di default
            
            if rsi is not None and sma is not None:
                # Determina il Trend di fondo (Prezzo vs Media 60gg)
                if price > sma:
                    trend_msg = "Bullish (Rialzista)"
                    trend_icon = "🐂"
                else:
                    trend_msg = "Bearish (Ribassista)"
                    trend_icon = "🐻"

                # Genera Segnali Combinati
                # Logica: Comprare quando l'RSI è basso MA il trend a 60gg è ancora rialzista
                if rsi <= 30 and price > sma:
                    signal_text = f"\n💎 **GOLDEN OPPORTUNITY**\n(Prezzo in salita sul lungo, ma in sconto oggi)"
                elif rsi <= 30 and price < sma:
                    signal_text = f"\n⚠️ **Attenzione**\n(Prezzo basso, ma trend negativo)"
                elif rsi >= 70:
                    signal_text = f"\n🔥 **Prezzo Alto**\n(Probabile discesa a breve)"
                else:
                    signal_text = f"\n⚙️ RSI: {rsi:.0f} | Trend: {trend_icon}"

            message += f"🔹 *{crypto.capitalize()}*\n"
            message += f"💶 € {price:,.2f} ({trend_emoji} {change_24h:+.2f}%)\n"
            message += f"📊 Media 60gg: € {sma:,.2f}"
            message += f"{signal_text}\n\n"
    
    send_telegram_message(message)
    print("Report inviato.")

if __name__ == "__main__":
    main()
