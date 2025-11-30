import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# ---------------------------
# ⚙️ KONFIGURACJA STRONY
# ---------------------------
st.set_page_config(page_title="Mój Portfel XTB Pro", page_icon="💰", layout="wide")

# ---------------------------
# 💼 TWÓJ PORTFEL (TUTAJ WPISZ SWOJE ILOŚCI!)
# ---------------------------
# "qty": wpisz tutaj, ile masz sztuk akcji w XTB
MY_PORTFOLIO = [
    {"ticker": "GPW.WA",  "name": "GPW",           "qty": 14.4158},  # Np. masz 55 akcji GPW
    {"ticker": "PEO.WA",  "name": "Bank Pekao",    "qty": 4.7125},  # Np. masz 10 akcji Pekao
    {"ticker": "KTY.WA",  "name": "Grupa Kęty",    "qty": 1.0158},
    {"ticker": "KRU.WA",  "name": "Kruk SA",       "qty": 1.9493},
    {"ticker": "EUNL.DE", "name": "iShares World", "qty": 2.936},  # ETF w Euro
    {"ticker": "SXR8.DE", "name": "iShares S&P500","qty": 0.5437}   # ETF w Euro
]

# ---------------------------
# 🧠 FUNKCJE ANALITYCZNE
# ---------------------------

def get_currency_rate():
    """Pobiera kurs EUR/PLN, żeby przeliczyć ETFy."""
    try:
        eur = yf.Ticker("EURPLN=X").history(period="1d")['Close'].iloc[-1]
        return eur
    except:
        return 4.30 # Domyślny kurs w razie błędu

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_position_data(item, eur_rate):
    """Analizuje pojedynczą pozycję i wylicza jej wartość w PLN."""
    ticker = item['ticker']
    qty = item['qty']
    name = item['name']
    
    t = yf.Ticker(ticker)
    
    # Cena i Historia
    hist = t.history(period="6mo")
    if hist.empty: return None
    
    current_price = hist["Close"].iloc[-1]
    prev_price = hist["Close"].iloc[-2]
    change_pct = ((current_price - prev_price) / prev_price) * 100
    
    # RSI
    rsi = calculate_rsi(hist["Close"]).iloc[-1]
    
    # Waluta i Przeliczanie
    info = t.info
    currency = info.get('currency', 'PLN')
    
    val_native = current_price * qty
    
    if currency == 'EUR':
        val_pln = val_native * eur_rate
        price_display = f"€{round(current_price, 2)}"
    elif currency == 'USD':
        # Uproszczenie: zakładamy że USDPLN jest zbliżony do EURPLN dla logiki, 
        # ale w XTB masz EUNL/SXR8 w EUR, więc to wystarczy.
        val_pln = val_native * 4.0 
        price_display = f"${round(current_price, 2)}"
    else:
        val_pln = val_native
        price_display = f"{round(current_price, 2)} zł"

    # Szacowanie dywidendy (Pasywny Przychód)
    div_yield = info.get('dividendYield', 0)
    
    # Fix na dziwne dane Yahoo (>20%)
    if div_yield and div_yield > 0.20: 
        div_yield = 0.05 # Zakładamy bezpieczne 5% jeśli dane są błędne
    if div_yield is None: 
        div_yield = 0

    est_income = val_pln * div_yield

    return {
        "name": name,
        "ticker": ticker,
        "price_str": price_display,
        "change_pct": change_pct,
        "rsi": rsi,
        "value_pln": val_pln,
        "est_income": est_income,
        "qty": qty,
        "trend_chart": hist['Close']
    }

# ---------------------------
# 🖥️ INTERFEJS
# ---------------------------

st.title("💰 Twój Osobisty Księgowy")

# Pobieramy kurs Euro raz
eur_rate = get_currency_rate()
st.caption(f"Kurs EUR/PLN przyjęty do wyceny: {round(eur_rate, 2)} zł")

# ZAKŁADKI
tab1, tab2, tab3 = st.tabs(["💎 Wycena Portfela", "🤖 Doradca AI", "📰 Newsy"])

# --- TAB 1: PORTFEL I WARTOŚĆ ---
with tab1:
    if st.button('🔄 Przelicz Portfel'):
        total_value = 0
        total_income = 0
        
        st.write("---")
        
        for item in MY_PORTFOLIO:
            data = get_position_data(item, eur_rate)
            
            if data:
                total_value += data['value_pln']
                total_income += data['est_income']
                
                # Wyświetlanie kafelka
                c1, c2, c3 = st.columns([2, 2, 2])
                
                with c1:
                    st.subheader(f"{data['name']}")
                    st.caption(f"Ilość: {data['qty']} szt. | Cena: {data['price_str']}")
                
                with c2:
                    # Kolor zmiany
                    color = "normal"
                    if data['change_pct'] > 0: color = "off"
                    else: color = "inverse"
                    st.metric("Wartość pozycji", f"{round(data['value_pln'], 2)} zł", f"{round(data['change_pct'], 2)}%", delta_color=color)
                
                with c3:
                    rsi_color = "red" if data['rsi'] > 70 else ("green" if data['rsi'] < 30 else "grey")
                    st.markdown(f"RSI: **:{rsi_color}[{round(data['rsi'], 1)}]**")
                    if data['est_income'] > 0:
                        st.caption(f"Szac. dywidenda rocznie: +{round(data['est_income'], 2)} zł")
                
                st.markdown("---")

        # PODSUMOWANIE NA GÓRZE (Licznik Bogactwa)
        st.markdown("### 🏆 Podsumowanie Majątku")
        k1, k2 = st.columns(2)
        k1.metric("Łączna Wartość Aktywów", f"{round(total_value, 2)} PLN")
        k2.metric("Pasywny Przychód (Szacowany)", f"{round(total_income, 2)} PLN / rok", "Dywidendy")

# --- TAB 2: DORADCA AI (BEZ ZMIAN) ---
with tab2:
    st.header("🧠 Inteligentna Analiza")
    target_ticker = st.selectbox("Wybierz walor:", [i['ticker'] for i in MY_PORTFOLIO])
    # Znajdź nazwę dla tickera
    target_name = next(item['name'] for item in MY_PORTFOLIO if item['ticker'] == target_ticker)
    
    if st.button("📝 Generuj Prompt"):
        # Uproszczona logika dla promptu
        st.text_area("Wyślij to do Gemini:", 
                     f"Przeanalizuj spółkę {target_name} ({target_ticker}). Mam jej w portfelu sporo. RSI, P/E i raporty - co robić?")

# --- TAB 3: NEWSY (BEZ ZMIAN) ---
with tab3:
    st.header("Newsy")
    news_ticker = st.selectbox("Wybierz:", [i['ticker'] for i in MY_PORTFOLIO])
    t = yf.Ticker(news_ticker)
    for n in t.news[:3]:
        st.write(f"- [{n.get('title')}]({n.get('link')})")
