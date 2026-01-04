import requests
import os
import time
from datetime import datetime

# --- CONFIGURAZIONE ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TELEGRAM_TOKEN:
    TELEGRAM_TOKEN = "8504447951:AAHkFvYwK_A2k76gendESC41-a2u03pQ7-c"
if not CHAT_ID:
    CHAT_ID = "211228574"

CRYPTO_IDS = ["bitcoin", "ethereum", "solana", "ripple", "cardano", "polkadot"]
VALUTA = "eur"

def get_fear_and_greed():
    """Scarica l'indice di Paura e Avidità"""
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url)
        data = response.json()
        value = int(data['data'][0]['value'])
        return value
    except Exception as e:
        print(f"Errore Fear&Greed: {e}")
        return None

def generate_sparkline(prices):
    """Crea un grafico testuale 7 giorni su riga dedicata"""
    if not prices: return ""
    recent_prices = prices[-7:]
    min_p = min(recent_prices)
    max_p = max(recent_prices)
    if max_p == min_p: return "───────"
    
    # Set di caratteri per il grafico (stile barre verticali)
    bars = u"  ▂▃▄▅▆▇█"
    sparkline = ""
    for p in recent_prices:
        idx = int((p - min_p) / (max_p - min_p) * 8)
        if idx > 8: idx = 8
        sparkline += bars[idx]
    return sparkline

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
        
        if len(prices) < 60: return None, None, ""

        sparkline = generate_sparkline(prices)
        sma = sum(prices[-60:]) / 60
        
        prices_14 = prices[-15:] 
        deltas = [prices_14[i+1] - prices_14[i] for i in range(len(prices_14)-1)]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]

        if len(losses) == 0: rsi = 100
        elif len(gains) == 0: rsi = 0
        else:
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        return rsi, sma, sparkline

    except Exception as e:
        print(f"Errore Dati per {crypto_id}: {e}")
        return None, None, ""

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
    print("Inizio analisi 6.1 (Clean)...")
    prices_data = get_current_prices()
    fg_value = get_fear_and_greed()
    
    if not prices_data: return

    now = datetime.now().strftime("%d/%m %H:%M")
    
    # Intestazione
    message = f"🤖 **Advisor Crypto** ({now})\n"
    if fg_value:
        # Definiamo l'emoji del sentiment generale
        if fg_value >= 75: fg_msg = "🤑 Extreme Greed"
        elif fg_value >= 55: fg_msg = "😋 Greed"
        elif fg_value <= 25: fg_msg = "😱 Extreme Fear"
        elif fg_value <= 45: fg_msg = "😨 Fear"
        else: fg_msg = "😐 Neutral"
        message += f"🧠 Sentiment Mercato: *{fg_msg} ({fg_value})*\n"
    
    message += "----------------------------\n"

    for crypto in CRYPTO_IDS:
        if crypto in prices_data:
            price = prices_data[crypto][VALUTA]
            change_24h = prices_data[crypto].get(f"{VALUTA}_24h_change", 0)
            
            print(f"Analizzo {crypto}...") 
            time.sleep(15) 
            
            rsi, sma, sparkline = get_market_data(crypto)

            trend_emoji = "🟢" if change_24h >= 0 else "🔴"
            action_text = "N/D"
            trend_text = "Incerto"
            
            if rsi is not None:
                # Logica Trend SMA
                if price > sma:
                    trend_text = "🐂 Bull (Sale)"
                    is_bullish = True
                else:
                    trend_text = "🐻 Bear (Scende)"
                    is_bullish = False

                # Logica Consigli Advisor
                if rsi <= 30:
                    if is_bullish: action_text = "💎 COMPRA ORA (Strong Buy)"
                    else: action_text = "⚠️ ACCUMULA (Buy the Dip)"
                elif rsi >= 70: action_text = "🔥 VENDI / PRENDI PROFITTO"
                elif rsi >= 60: action_text = "✋ ASPETTA (Prezzo Altino)"
                elif rsi <= 40: action_text = "👀 MONITORARE (Quasi Buy)"
                else: action_text = "💤 HODL / Tieni (Neutro)"

            # --- FORMATTAZIONE PULITA (Stile V5 + Grafico sotto) ---
            message += f"🔹 *{crypto.capitalize()}*\n"
            message += f"💶 € {price:,.2f} ({trend_emoji} {change_24h:+.2f}%)\n"
            message += f"📉 Grafico 7gg: `{sparkline}`\n" # Grafico qui, separato
            message += f"📊 Trend 60gg: {trend_text}\n"
            message += f"⚙️ RSI: {rsi:.0f}/100\n"
            message += f"💡 **{action_text}**\n\n"
    
    send_telegram_message(message)
    print("Report inviato.")

if __name__ == "__main__":
    main()
