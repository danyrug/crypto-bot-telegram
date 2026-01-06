import requests
import os
import time
import sys
from datetime import datetime

# --- CONFIGURAZIONE SICURA ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ ERRORE: Token o Chat ID mancanti.")
    sys.exit(1)

CRYPTO_IDS = ["bitcoin", "ethereum", "solana", "ripple", "cardano", "polkadot"]
VALUTA = "eur"

# Costanti di analisi
DAYS_HISTORY = 200  # Aumentato a 200 per standard istituzionale
RSI_PERIOD = 14

def requests_retry_session(url, params=None, retries=3, backoff_factor=5):
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 429:
                time.sleep(backoff_factor)
                continue
            response.raise_for_status()
            return response.json()
        except Exception:
            time.sleep(backoff_factor)
    return None

def get_fear_and_greed():
    url = "https://api.alternative.me/fng/"
    data = requests_retry_session(url)
    if data:
        try:
            return int(data['data'][0]['value'])
        except:
            return None
    return None

def generate_sparkline(prices):
    if not prices: return ""
    recent_prices = prices[-7:]
    min_p = min(recent_prices)
    max_p = max(recent_prices)
    if max_p == min_p: return "───────"
    
    bars = u"  ▂▃▄▅▆▇█"
    sparkline = ""
    for p in recent_prices:
        idx = int((p - min_p) / (max_p - min_p) * 8)
        if idx > 8: idx = 8
        sparkline += bars[idx]
    return sparkline

def get_rich_market_data_list():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": VALUTA,
        "ids": ",".join(CRYPTO_IDS),
        "order": "market_cap_desc",
        "sparkline": "false"
    }
    data = requests_retry_session(url, params)
    market_dict = {}
    if data:
        for coin in data:
            market_dict[coin['id']] = coin
    return market_dict

def calculate_rsi_wilder(prices, period=14):
    """
    RSI con Wilder's Smoothing su lungo periodo (200gg).
    Massima precisione.
    """
    if len(prices) < period + 1:
        return None

    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [abs(d) if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100 if avg_gain > 0 else 50

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_historical_analysis(crypto_id):
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
    # Richiediamo 200 giorni (o max disponibili)
    params = {"vs_currency": VALUTA, "days": str(DAYS_HISTORY), "interval": "daily"}
    
    data = requests_retry_session(url, params)
    if not data: return None, None, ""

    try:
        prices = [x[1] for x in data['prices']]
        # Controllo sicurezza: se la moneta è troppo giovane
        if len(prices) < 30: return None, None, ""

        sparkline = generate_sparkline(prices)
        
        # Calcolo SMA Dinamica (usa 200 giorni, o meno se non disponibili)
        # Se abbiamo 200 dati, usiamo gli ultimi 200. Se ne abbiamo 150, usiamo 150.
        window = min(len(prices), DAYS_HISTORY)
        sma = sum(prices[-window:]) / window
        
        rsi = calculate_rsi_wilder(prices, RSI_PERIOD)
        
        return rsi, sma, sparkline
    except Exception as e:
        print(f"Errore calcoli {crypto_id}: {e}")
        return None, None, ""

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Errore Telegram: {e}")

def main():
    print("Inizio analisi 10.0 (Institutional 200gg)...")
    
    rich_data = get_rich_market_data_list()
    fg_value = get_fear_and_greed()
    
    if not rich_data:
        print("Impossibile recuperare i prezzi.")
        return

    now = datetime.now().strftime("%d/%m %H:%M")
    
    message = f"🤖 **Advisor Pro 200** ({now})\n"
    if fg_value:
        if fg_value >= 75: fg_msg = "🤑 Greed"
        elif fg_value >= 55: fg_msg = "😋 Greed"
        elif fg_value <= 25: fg_msg = "😱 Fear"
        elif fg_value <= 45: fg_msg = "😨 Fear"
        else: fg_msg = "😐 Neutral"
        message += f"🧠 Sentiment: *{fg_msg} ({fg_value})*\n"
    
    message += "----------------------------\n"

    for crypto in CRYPTO_IDS:
        if crypto not in rich_data: continue
            
        coin_data = rich_data[crypto]
        price = coin_data['current_price']
        change_24h = coin_data.get('price_change_percentage_24h', 0)
        ath_change = coin_data.get('ath_change_percentage', 0)
        
        print(f"Analizzo {crypto}...") 
        time.sleep(10) 
        
        rsi, sma, sparkline = get_historical_analysis(crypto)

        trend_emoji = "🟢" if change_24h >= 0 else "🔴"
        action_text = "N/D"
        trend_text = "Incerto"
        
        if rsi is not None:
            # TREND: Prezzo vs SMA 200
            if price > sma:
                trend_text = "🐂 Bull (Lungo termine)"
                is_bullish = True
            else:
                trend_text = "🐻 Bear (Lungo termine)"
                is_bullish = False

            # STRATEGIA RSI + TREND 200
            # Regola d'oro: "Buy the dip" solo se siamo in Bull Market (sopra SMA 200)
            if rsi <= 30:
                if is_bullish: action_text = "💎 GOLDEN BUY (Dip in Uptrend)"
                else: action_text = "⚠️ RISCHIO (Accumulo in Downtrend)"
            elif rsi >= 70: action_text = "🔥 VENDI (Ipercomprato)"
            elif rsi >= 60: action_text = "✋ ASPETTA"
            elif rsi <= 40: 
                if is_bullish: action_text = "👀 MONITORARE (Occasione vicina)"
                else: action_text = "👀 MONITORARE"
            else: action_text = "💤 HODL"

        message += f"🔹 *{crypto.capitalize()}*\n"
        message += f"💶 € {price:,.2f} ({trend_emoji} {change_24h:+.2f}%)\n"
        message += f"🏔️ Dal Max: `{ath_change:.2f}%`\n"
        message += f"📉 Grafico 7gg: `{sparkline}`\n" 
        message += f"📊 Trend 200gg: {trend_text}\n" # Aggiornato label
        if rsi is not None:
            message += f"⚙️ RSI: {rsi:.0f}/100\n"
        message += f"💡 **{action_text}**\n\n"
    
    send_telegram_message(message)
    print("Report inviato.")

if __name__ == "__main__":
    main()
