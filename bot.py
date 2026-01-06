import requests
import os
import time
import sys
from datetime import datetime

# --- CONFIGURAZIONE SICURA ---
# Legge SOLO dai Secrets di GitHub.
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# Se non trova i secrets, si ferma (Sicurezza)
if not TELEGRAM_TOKEN or not CHAT_ID:
    print("❌ ERRORE: Token o Chat ID mancanti.")
    print("Imposta i 'Repository Secrets' su GitHub.")
    sys.exit(1)

CRYPTO_IDS = ["bitcoin", "ethereum", "solana", "ripple", "cardano", "polkadot"]
VALUTA = "eur"

def requests_retry_session(url, params=None, retries=3, backoff_factor=5):
    """
    Funzione intelligente che riprova se l'API fallisce.
    Utile per evitare buchi nel report quando CoinGecko è sovraccarico.
    """
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 429: # Troppe richieste
                print(f"⚠️ Rate Limit (429). Attendo {backoff_factor}s...")
                time.sleep(backoff_factor)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Tentativo {i+1}/{retries} fallito: {e}")
            time.sleep(backoff_factor)
    
    print(f"❌ Errore definitivo per {url}")
    return None

def get_fear_and_greed():
    """Scarica l'indice di Paura e Avidità"""
    url = "https://api.alternative.me/fng/"
    data = requests_retry_session(url)
    if data:
        try:
            value = int(data['data'][0]['value'])
            return value
        except:
            return None
    return None

def generate_sparkline(prices):
    """Crea un grafico testuale 7 giorni"""
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
    """
    Nuova funzione: Scarica dati ricchi (Prezzo, cambio, ATH) per TUTTE le crypto insieme.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": VALUTA,
        "ids": ",".join(CRYPTO_IDS),
        "order": "market_cap_desc",
        "sparkline": "false"
    }
    data = requests_retry_session(url, params)
    
    # Trasformiamo la lista in un dizionario per trovarli facilmente dopo
    market_dict = {}
    if data:
        for coin in data:
            market_dict[coin['id']] = coin
    return market_dict

def get_historical_analysis(crypto_id):
    """Scarica 60 giorni per analisi Trend e RSI"""
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
    params = {
        "vs_currency": VALUTA,
        "days": "60", 
        "interval": "daily"
    }
    
    data = requests_retry_session(url, params)
    if not data: return None, None, ""

    try:
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
        print(f"Errore calcolo indicatori {crypto_id}: {e}")
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
    print("Inizio analisi 9.0 (Bulletproof)...")
    
    # 1. Scarichiamo i dati "ricchi" (Prezzi + ATH)
    rich_data = get_rich_market_data_list()
    fg_value = get_fear_and_greed()
    
    if not rich_data:
        print("Impossibile recuperare i prezzi base.")
        return

    now = datetime.now().strftime("%d/%m %H:%M")
    
    # Intestazione
    message = f"🤖 **Advisor Pro** ({now})\n"
    if fg_value:
        if fg_value >= 75: fg_msg = "🤑 Greed"
        elif fg_value >= 55: fg_msg = "😋 Greed"
        elif fg_value <= 25: fg_msg = "😱 Fear"
        elif fg_value <= 45: fg_msg = "😨 Fear"
        else: fg_msg = "😐 Neutral"
        message += f"🧠 Sentiment: *{fg_msg} ({fg_value})*\n"
    
    message += "----------------------------\n"

    for crypto in CRYPTO_IDS:
        # Se la moneta non è nei dati scaricati, la saltiamo
        if crypto not in rich_data:
            continue
            
        coin_data = rich_data[crypto]
        price = coin_data['current_price']
        change_24h = coin_data.get('price_change_percentage_24h', 0)
        ath_change = coin_data.get('ath_change_percentage', 0) # Distanza dal record storico
        
        print(f"Analizzo {crypto}...") 
        # Pausa intelligente: abbiamo già i prezzi, ma per RSI/SMA serve lo storico
        # CoinGecko è severo, manteniamo la pausa
        time.sleep(15) 
        
        rsi, sma, sparkline = get_historical_analysis(crypto)

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
                if is_bullish: action_text = "💎 COMPRA (Strong)"
                else: action_text = "⚠️ ACCUMULA (Dip)"
            elif rsi >= 70: action_text = "🔥 VENDI (High)"
            elif rsi >= 60: action_text = "✋ ASPETTA"
            elif rsi <= 40: action_text = "👀 MONITORARE"
            else: action_text = "💤 HODL"

        # --- FORMATTAZIONE AVANZATA ---
        message += f"🔹 *{crypto.capitalize()}*\n"
        message += f"💶 € {price:,.2f} ({trend_emoji} {change_24h:+.2f}%)\n"
        
        # NUOVA RIGA: Distanza dal massimo storico
        # Se ath_change è -15%, significa che siamo sotto del 15% dal record
        message += f"🏔️ Dal Max: `{ath_change:.2f}%`\n"
        
        message += f"📉 Grafico 7gg: `{sparkline}`\n" 
        message += f"📊 Trend 60gg: {trend_text}\n"
        message += f"⚙️ RSI: {rsi:.0f}/100\n"
        message += f"💡 **{action_text}**\n\n"
    
    send_telegram_message(message)
    print("Report inviato.")

if __name__ == "__main__":
    main()
