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
        "days": "60", 
        "interval": "daily"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices = [x[1] for x in data['prices']]
        
        if len(prices) < 60:
            return None, None

        sma = sum(prices[-60:]) / 60
        
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
    print("Inizio analisi Advisor...")
    prices_data = get_current_prices()
    
    if not prices_data:
        return

    now = datetime.now().strftime("%d/%m %H:%M")
    message = f"🤖 **Advisor Crypto** ({now})\n"
    message += "----------------------------\n"

    for crypto in CRYPTO_IDS:
        if crypto in prices_data:
            price = prices_data[crypto][VALUTA]
            change_24h = prices_data[crypto].get(f"{VALUTA}_24h_change", 0)
            
            print(f"Analizzo {crypto}...") 
            time.sleep(15) 
            
            rsi, sma = get_market_data(crypto)

            trend_emoji = "🟢" if change_24h >= 0 else "🔴"
            
            action_text = "N/D"
            trend_icon = "➖"
            
            if rsi is not None and sma is not None:
                # 1. Definisci il Trend
                if price > sma:
                    trend_icon = "🐂 Bull (Sale)"
                    is_bullish = True
                else:
                    trend_icon = "🐻 Bear (Scende)"
                    is_bullish = False

                # 2. Definisci l'Azione (Consiglio)
                if rsi <= 30:
                    if is_bullish:
                        action_text = "💎 COMPRA ORA (Strong Buy)"
                    else:
                        action_text = "⚠️ ACCUMULA (Buy the Dip)"
                elif rsi >= 70:
                    action_text = "🔥 VENDI / PRENDI PROFITTO"
                elif rsi >= 60:
                     action_text = "✋ ASPETTA (Prezzo Altino)"
                elif rsi <= 40:
                     action_text = "👀 MONITORARE (Quasi Buy)"
                else:
                    action_text = "💤 HODL / Tieni (Neutro)"

            message += f"🔹 *{crypto.capitalize()}*\n"
            message += f"💶 € {price:,.2f} ({trend_emoji} {change_24h:+.2f}%)\n"
            message += f"📊 Trend: {trend_icon}\n"
            message += f"⚙️ RSI: {rsi:.0f}/100\n"
            message += f"💡 **{action_text}**\n\n"
    
    send_telegram_message(message)
    print("Report inviato.")

if __name__ == "__main__":
    main()
