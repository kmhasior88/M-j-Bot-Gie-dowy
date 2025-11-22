import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------
# 🧠 MÓZG BOTA (Ta sama logika co w PDF)
# ---------------------------

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_advanced_analysis(ticker):
    # Pobieranie danych
    df = yf.download(ticker, period="2y", interval="1d", progress=False)
    
    if df.empty: return None
    
    # Obsługa błędów formatu danych (MultiIndex)
    if isinstance(df.columns, pd.MultiIndex):
        try:
            close = df.xs('Close', level=0, axis=1)[ticker]
        except KeyError:
            close = df['Close']
    else:
        close = df['Close']
    
    close = close.astype(float).squeeze()
    df_clean = pd.DataFrame({"Close": close})

    # Obliczenia wskaźników
    df_clean["MA50"] = df_clean["Close"].rolling(50).mean()
    df_clean["MA200"] = df_clean["Close"].rolling(200).mean()
    df_clean["RSI"] = calculate_rsi(df_clean["Close"])
    
    # Zmienność
    daily_returns = df_clean["Close"].pct_change()
    volatility = daily_returns.std() * (252 ** 0.5) * 100 

    # Fundamenty
    t = yf.Ticker(ticker)
    info = t.info
    
    pe = info.get('trailingPE', None)
    pb = info.get('priceToBook', None)
    reco = info.get("recommendationKey", "brak").upper().replace("_", " ")
    
    return {
        "df": df_clean,
        "current_price": df_clean["Close"].iloc[-1],
        "volatility": volatility,
        "rsi": df_clean["RSI"].iloc[-1],
        "pe": round(pe, 2) if pe else "-",
        "pb": round(pb, 2) if pb else "-",
        "reco": reco
    }

# ---------------------------
# 📱 WYGLĄD APLIKACJI (INTERFEJS)
# ---------------------------

st.set_page_config(page_title="Mój Portfel PRO", page_icon="📈")

st.title("📈 Centrum Dowodzenia")
st.caption("Profesjonalna analiza w czasie rzeczywistym")

# Twoje spółki
TICKERS = {
    "PEO.WA": "Pekao SA",
    "KTY.WA": "Grupa Kęty",
    "SPY": "S&P 500",
    "MSFT": "Microsoft"
}

# Przycisk odświeżania
if st.button('🔄 Analizuj rynki'):
    st.markdown("---")
    
    for ticker, name in TICKERS.items():
        st.subheader(f"{name} ({ticker})")
        
        with st.spinner(f'Przetwarzam dane dla {name}...'):
            data = get_advanced_analysis(ticker)
            
            if data is None:
                st.error("Brak danych")
                continue

            # 1. Główne Liczby (Metrics)
            col1, col2, col3 = st.columns(3)
            
            # Kolorowanie RSI
            rsi_val = data['rsi']
            rsi_delta = "Neutralne"
            if rsi_val > 70: rsi_delta = "⚠️ Wykupienie"
            elif rsi_val < 30: rsi_delta = "✅ Okazja?"

            col1.metric("Cena", f"{round(data['current_price'], 2)}", f"{data['reco']}")
            col2.metric("RSI (14)", f"{round(rsi_val, 1)}", rsi_delta, delta_color="off")
            col3.metric("Zmienność", f"{round(data['volatility'], 1)}%", "Ryzyko roczne", delta_color="inverse")

            # 2. Fundamenty w tabelce
            df_fund = pd.DataFrame({
                "Wskaźnik": ["Cena / Zysk (P/E)", "Cena / WK (P/B)"],
                "Wartość": [data['pe'], data['pb']]
            })
            st.dataframe(df_fund, hide_index=True, use_container_width=True)

            # 3. Wykres Profesjonalny
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(data['df'].index, data['df']['Close'], label='Cena', color='black', linewidth=1)
            ax.plot(data['df'].index, data['df']['MA50'], label='MA50', color='green', linestyle='--', alpha=0.7)
            ax.plot(data['df'].index, data['df']['MA200'], label='MA200', color='red', linestyle='--', alpha=0.7)
            ax.set_title("Analiza Techniczna")
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            st.pyplot(fig)
            
            st.markdown("---")

else:
    st.info("Kliknij przycisk powyżej, aby pobrać najnowsze dane z giełdy.")