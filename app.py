import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="AVGS vs AVUV+AVDV", layout="centered")
st.title("🥊 全球小盤價值股 PK 賽")
st.caption("英股 AVGS.L (USD) vs. 50% AVUV + 50% AVDV")

with st.sidebar:
    st.header("設定")
    period = st.selectbox("比較時間範圍", ["YTD", "3mo", "6mo", "1y", "max"], index=3)
    st.info("數據來源: Yahoo Finance (英股報價約有15分鐘延遲)")

def load_data(period):
    tickers = {'AVGS': 'AVGS.L', 'AVUV': 'AVUV', 'AVDV': 'AVDV', 'FX': 'USDTWD=X'}
    data = yf.download(list(tickers.values()), period=period, progress=False)['Adj Close']

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]

    rename_map = {v: k for k, v in tickers.items()}
    df = data.rename(columns=rename_map)

    if 'AVGS' in df.columns:
        valid_start = df['AVGS'].first_valid_index()
        if valid_start: df = df.loc[valid_start:]
    return df

try:
    with st.spinner('正在抓取最新報價...'):
        df = load_data(period).ffill().dropna()

        latest_fx = df['FX'].iloc[-1]
        latest_avgs = df['AVGS'].iloc[-1]
        latest_avuv = df['AVUV'].iloc[-1]
        latest_avdv = df['AVDV'].iloc[-1]

        # 歸一化計算績效
        normalized = df / df.iloc[0] * 100
        normalized['Combo'] = 0.5 * normalized['AVUV'] + 0.5 * normalized['AVDV']

        ret_avgs = normalized['AVGS'].iloc[-1] - 100
        ret_combo = normalized['Combo'].iloc[-1] - 100

        st.subheader("💰 即時報價 (USD / TWD)")
        col1, col2 = st.columns(2)
        col1.metric("AVGS.L", f"${latest_avgs:.2f}", f"NT$ {latest_avgs*latest_fx:.0f}")
        col2.metric("50/50 組合", f"${(0.5*latest_avuv + 0.5*latest_avdv):.2f}", f"NT$ {(0.5*latest_avuv + 0.5*latest_avdv)*latest_fx:.0f}")

        st.divider()
        diff = ret_avgs - ret_combo
        winner = "AVGS.L 勝出!" if diff > 0 else "美股組合 勝出!"
        color = "green" if diff > 0 else "red"
        st.markdown(f"### :{color}[{winner}] (差距 {abs(diff):.2f}%)")

        st.line_chart(normalized[['AVGS', 'Combo']], color=["#FF4B4B", "#1E90FF"])

except Exception as e:
    st.error(f"讀取數據時發生錯誤 (可能是剛開盤或連線問題): {e}")
    if st.button('重試'): st.rerun()
