import streamlit as st
import yfinance as yf
import pandas as pd

# --- 頁面設定 ---
st.set_page_config(page_title="AVGS vs AVUV+AVDV", layout="centered")
st.title("🥊 全球小盤價值股 PK 賽")
st.caption("英股 AVGS.L (USD) vs. 50% AVUV + 50% AVDV")

# --- 側邊欄 ---
with st.sidebar:
    st.header("設定")
    period = st.selectbox("比較時間範圍", ["YTD", "3mo", "6mo", "1y", "max"], index=3)
    st.info("數據來源: Yahoo Finance")

# --- 核心邏輯 ---
def load_data(period):
    tickers = {'AVGS': 'AVGS.L', 'AVUV': 'AVUV', 'AVDV': 'AVDV', 'FX': 'USDTWD=X'}
    
    # 修正重點 1: 先下載原始數據，不急著指定欄位
    try:
        raw_data = yf.download(list(tickers.values()), period=period, progress=False)
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()

    # 修正重點 2: 檢查是否真的有抓到數據
    if raw_data.empty:
        st.warning("⚠️ 目前無法從 Yahoo 取得數據，請稍後再試 (點擊下方重試按鈕)。")
        st.stop()

    # 修正重點 3: 彈性讀取欄位 (避免 KeyError)
    # Yahoo 有時會回傳 'Adj Close'，有時只有 'Close'
    if 'Adj Close' in raw_data.columns:
        data = raw_data['Adj Close']
    elif 'Close' in raw_data.columns:
        data = raw_data['Close']
    else:
        data = raw_data # 萬一結構不同，直接使用

    # 修正重點 4: 處理欄位名稱，確保能對應到代號
    # 有時候下載多檔股票會有多層索引，需要攤平
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # 嘗試只保留股票代號那層
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    # 重新命名為我們好讀的名字
    rename_map = {v: k for k, v in tickers.items()}
    # 這裡做一個保護，只重新命名那些存在的欄位
    df.rename(columns=rename_map, inplace=True)
    
    # AVGS 上市時間較短，從它有數據那天開始算
    if 'AVGS' in df.columns:
        valid_start = df['AVGS'].first_valid_index()
        if valid_start: df = df.loc[valid_start:]
        
    return df

# --- 執行與顯示 ---
try:
    with st.spinner('正在抓取最新報價...'):
        df = load_data(period).ffill().dropna()
        
        # 檢查是否關鍵數據都在
        required = ['AVGS', 'AVUV', 'AVDV', 'FX']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            st.warning(f"⚠️ 部分數據讀取不全 (可能休市或代號變更): 缺少 {missing}")
            st.stop()

        # 取得最新價格
        latest_fx = df['FX'].iloc[-1]
        latest_avgs = df['AVGS'].iloc[-1]
        latest_avuv = df['AVUV'].iloc[-1]
        latest_avdv = df['AVDV'].iloc[-1]
        
        # 歸一化計算 (起點設為 100)
        normalized = df / df.iloc[0] * 100
        normalized['Combo'] = 0.5 * normalized['AVUV'] + 0.5 * normalized['AVDV']
        
        # 算出漲跌幅 %
        ret_avgs = normalized['AVGS'].iloc[-1] - 100
        ret_combo = normalized['Combo'].iloc[-1] - 100

        # --- 顯示區 ---
        st.subheader("💰 即時報價 (USD / TWD)")
        col1, col2 = st.columns(2)
        col1.metric("AVGS.L (英)", f"${latest_avgs:.2f}", f"NT$ {latest_avgs*latest_fx:.0f}")
        col2.metric("美股組合 (50/50)", f"${(0.5*latest_avuv + 0.5*latest_avdv):.2f}", f"NT$ {(0.5*latest_avuv + 0.5*latest_avdv)*latest_fx:.0f}")
        
        st.divider()
        diff = ret_avgs - ret_combo
        winner = "AVGS.L 勝出!" if diff > 0 else "美股組合 勝出!"
        color = "green" if diff > 0 else "red"
        st.markdown(f"### :{color}[{winner}] (差距 {abs(diff):.2f}%)")
        
        # 畫圖
        st.line_chart(normalized[['AVGS', 'Combo']], color=["#FF4B4B", "#1E90FF"])

except Exception as e:
    st.error(f"發生未預期的錯誤: {e}")
    if st.button('🔄 重試'): st.rerun()

# 底部強制刷新按鈕
if st.button('🔄 更新報價'):
    st.rerun()
