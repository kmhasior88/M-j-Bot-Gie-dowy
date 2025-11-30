import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# ---------------------------
# ⚙️ KONFIGURACJA
# ---------------------------
st.set_page_config(page_title="Mój Portfel XTB", page_icon="📈", layout="wide")

# TWOJE RZECZYWISTE SPÓŁKI Z XTB
MY_TICKERS = {
    "GPW.WA": "GPW (Giełda)",
    "PEO.WA": "Bank Pekao",
    "KTY.WA": "Grupa Kęty",
    "KRU.WA": "Kruk SA",
    "EUNL.DE": "iShares MSCI World (ETF)",
    "SXR8.DE": "iShares S&P 500 (ETF)"
}

# ---------------------------
# 🧠 FUNKCJE ANALITYCZNE
# ---------------------------

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_data_for_ai(ticker):
    """Pobiera dane dla AI z naprawioną obsługą dywidend."""
    t = yf.Ticker(ticker)
    
    # Historia cen (6 miesięcy)
    df = t.history(period="6mo")
    if df.empty: return None
    
    current_price = df["Close"].iloc[-1]
    rsi = calculate_rsi(df["Close"]).iloc[-1]
    
    # Średnie do trendu
    ma50 = df["Close"].rolling(50).mean().iloc[-1]
    trend = "Wzrostowy ↗" if current_price > ma50 else "Spadkowy ↘"

    # Dane fundamentalne
    info = t.info
    pe = info.get('trailingPE', 'Brak (ETF?)')
    pb = info.get('priceToBook', '-')
    
    # --- NAPRAWA DYWIDENDY (BUG FIX) ---
    raw_yield = info.get('dividendYield', 0)
    
    # Jeśli Yahoo zwraca None lub bzdury (np. > 0.20 czyli 20%), liczymy sami
    if raw_yield is None or raw_yield > 0.20:
        try:
            # Pobieramy ostatnią wypłaconą kwotę dywidendy
            divs = t.dividends
            if not divs.empty:
                # Bierzemy ostatnią dywidendę
                last_div = float(divs.iloc[-1])
                # Ręczne wyliczenie: (Kwota / Cena) * 100
                calc_yield = (last_div / current_price) * 100
                div_str = f"{round(calc_yield, 2)}% (Szac.)"
            else:
                div_str = "0% (ETF/Brak)"
        except:
            div_str = "-"
    else:
        # Jeśli dane są normalne (np. 0.09), to mnożymy x100
        div_str = f"{round(raw_yield*100, 2)}%"

    return {
        "Cena": round(current_price, 2),
        "Waluta": info.get('currency', '?'),
        "RSI": round(rsi, 1),
        "Trend": trend,
        "P/E": pe,
        "P/B": pb,
        "Dywidenda": div_str,
        "Typ": info.get('quoteType', 'EQUITY') # Czy to ETF czy Akcja?
    }

# ---------------------------
# 🖥️ INTERFEJS APLIKACJI
# ---------------------------

st.title("📈 Twój Portfel XTB + Doradca AI")
st.caption("GPW | Pekao | Kęty | Kruk | S&P500 | MSCI World")

# ZAKŁADKI
tab1, tab2, tab3 = st.tabs(["📊 Stan Portfela", "📰 Wiadomości", "🤖 Zapytaj Gemini (AI)"])

# --- TAB 1: PORTFEL ---
with tab1:
    if st.button('🔄 Odśwież Ceny'):
        st.write("Pobieram najnowsze dane z giełd (Warszawa + Xetra)...")
        
        for ticker, name in MY_TICKERS.items():
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = ((current - prev) / prev) * 100
                
                # Kolor zmiany ceny
                color = "normal"
                if change > 0: color = "off" # Zielony w Streamlit
                else: color = "inverse"      # Czerwony
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.metric(label=name, value=f"{round(current, 2)}", delta=f"{round(change, 2)}%", delta_color=color)
                with col2:
                    st.line_chart(hist['Close'])
            st.markdown("---")

# --- TAB 2: WIADOMOŚCI (NAPRAWIONE) ---
with tab2:
    st.header("Najnowsze komunikaty")
    selected_news = st.selectbox("Wybierz spółkę:", list(MY_TICKERS.keys()))
    
    t = yf.Ticker(selected_news)
    news = t.news
    
    if news:
        for n in news:
            # --- ZABEZPIECZENIE PRZED BRAKIEM DATY (BUG FIX) ---
            try:
                timestamp = n.get('providerPublishTime')
                if timestamp:
                    pub_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                else:
                    pub_date = "Niedawno"
                
                title = n.get('title', 'Bez tytułu')
                link = n.get('link', '#')
                
                st.markdown(f"**{pub_date}** | [{title}]({link})")
            except Exception:
                continue # Pomijamy uszkodzony news
    else:
        st.info("Brak nowych wiadomości w systemie Yahoo Finance.")

# --- TAB 3: GENERATOR PROMPTÓW (AI) ---
with tab3:
    st.header("🧠 Inteligentna Analiza")
    st.write("Wybierz walor, a bot przygotuje zestaw danych, o które zapytasz Gemini.")
    
    target = st.selectbox("Co analizujemy?", list(MY_TICKERS.keys()), format_func=lambda x: MY_TICKERS[x])
    
    if st.button("📝 Przygotuj Raport dla Gemini"):
        with st.spinner("Analizuję wskaźniki..."):
            name = MY_TICKERS[target]
            data = get_data_for_ai(target)
            
            if data:
                # Rozróżnienie zapytania (ETF vs Spółka)
                if "ETF" in data['Typ'] or "ETF" in name:
                    # PROMPT DLA ETF
                    prompt = f"""
                    Jesteś moim doradcą inwestycyjnym. Mam w portfelu ETF: **{name} ({target})**.
                    
                    Twarde dane od mojego bota:
                    - Cena: {data['Cena']} {data['Waluta']}
                    - Trend: {data['Trend']}
                    - RSI: {data['RSI']} (Czy rynek jest przegrzany?)
                    
                    Twoje zadanie (przeszukaj sieć):
                    1. Jakie są **największe spółki** w tym ETF-ie obecnie? Czy zaszły zmiany?
                    2. Jaki jest sentyment dla rynków, które ten ETF pokrywa (np. USA lub Świat)?
                    3. Czy w obecnej sytuacji makroekonomicznej (stopy procentowe, inflacja) warto dokupować ten ETF?
                    4. Wnioski: Kupować, Trzymać czy Czekać na korektę?
                    """
                else:
                    # PROMPT DLA SPÓŁKI (AKCJI)
                    prompt = f"""
                    Jesteś moim doradcą inwestycyjnym. Mam w portfelu spółkę: **{name} ({target})**.
                    
                    Twarde dane techniczne od bota:
                    - Cena: {data['Cena']} {data['Waluta']}
                    - Trend: {data['Trend']}
                    - RSI: {data['RSI']}
                    - P/E (Cena/Zysk): {data['P/E']}
                    - Dywidenda: {data['Dywidenda']}
                    
                    Twoje zadanie (przeszukaj sieć pod kątem najnowszych informacji):
                    1. Znajdź ostatnie **raporty finansowe/kwartalne**. Czy zyski rosną?
                    2. **W co inwestuje firma?** Jakie ma plany rozwoju (np. nowe przejęcia, inwestycje)?
                    3. Kiedy najbliższa **wypłata dywidendy** i czy jest zagrożona?
                    4. Rekomendacje analityków (Kupuj/Sprzedaj) z ostatniego miesiąca.
                    5. Podsumowanie: Czy przy obecnym RSI {data['RSI']} i newsach warto dokupić akcji?
                    """
                
                st.text_area("Skopiuj to i wyślij do Gemini:", value=prompt, height=400)
                st.success("Dane zebrane! Wyślij to do mnie na czacie.")
            else:
                st.error("Błąd pobierania danych.")
