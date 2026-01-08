import streamlit as st
import yfinance as yf
import pandas as pd
import time  # 引入時間模組

# --- 頁面設定 ---
st.set_page_config(page_title="AVGS vs 美股組合", layout="centered")
st.title("🥊 全球小盤價值股 PK 賽")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    
    # 1. 自動刷新開關 (新增功能)
    st.write("⏱️ **自動更新**")
    auto_refresh = st.toggle("開啟每 60 秒自動刷新", value=False)
    if auto_refresh:
        st.caption("⚠️ 開啟後上方會顯示 Running，請勿設太快以免被擋。")
    
    st.divider()

    # 2. 時間與組合
    period = st.selectbox("比較時間範圍", ["YTD", "3mo", "6mo", "1y", "max"], index=3)
    
    st.write("🇺🇸 **美股組合配置 (AVUV / AVDV)**")
    combo_type = st.radio("選擇比例:", ("50% / 50%", "60% / 40%", "70% / 30%"), index=0)
    
    # 解析比例
    if "60" in combo_type:
        w_avuv, w_avdv = 0.6, 0.4
    elif "70" in combo_type:
        w_avuv, w_avdv = 0.7, 0.3
    else:
        w_avuv, w_avdv = 0.5, 0.5

st.caption(f"英股 AVGS.L (USD) vs. 美股組合 ({combo_type})")

# --- 核心邏輯 ---
def load_data(period):
    tickers = {'AVGS': 'AVGS.L', 'AVUV': 'AVUV', 'AVDV': 'AVDV', 'FX': 'USDTWD=X'}
    try:
        raw_data = yf.download(list(tickers.values()), period=period, progress=False)
    except:
        return pd.DataFrame() # 失敗回傳空值

    if raw_data.empty: return pd.DataFrame()

    # 欄位處理
    if 'Adj Close' in raw_data.columns: data = raw_data['Adj Close']
    elif 'Close' in raw_data.columns: data = raw_data['Close']
    else: data = raw_data

    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    rename_map = {v: k for k, v in tickers.items()}
    df.rename(columns=rename_map, inplace=True)
    
    if 'AVGS' in df.columns:
        valid_start = df['AVGS'].first_valid_index()
        if valid_start: df = df.loc[valid_start:]
    return df

# --- 執行與顯示 ---
try:
    # 這裡不使用 spinner 以免自動刷新時畫面一直閃爍
    df = load_data(period).ffill().dropna()
    
    # 檢查數據
    required = ['AVGS', 'AVUV', 'AVDV', 'FX']
    if df.empty or not all(col in df.columns for col in required):
        st.warning("⏳ 讀取中或暫無數據...")
        time.sleep(3)
        st.rerun()
    else:
        latest_fx = df['FX'].iloc[-1]
        latest_avgs = df['AVGS'].iloc[-1]
        latest_avuv = df['AVUV'].iloc[-1]
        latest_avdv = df['AVDV'].iloc[-1]
        
        combo_price = (w_avuv * latest_avuv) + (w_avdv * latest_avdv)
        
        normalized = df / df.iloc[0] * 100
        normalized['Combo'] = (w_avuv * normalized['AVUV']) + (w_avdv * normalized['AVDV'])
        
        ret_avgs = normalized['AVGS'].iloc[-1] - 100
        ret_combo = normalized['Combo'].iloc[-1] - 100

        # 顯示區
        st.subheader("💰 即時報價 (USD / TWD)")
        col1, col2 = st.columns(2)
        col1.metric("🇬🇧 AVGS.L", f"${latest_avgs:.2f}", f"NT$ {latest_avgs*latest_fx:.0f}")
        col2.metric(f"🇺🇸 組合 ({combo_type})", f"${combo_price:.2f}", f"NT$ {combo_price*latest_fx:.0f}")
        
        st.divider()
        diff = ret_avgs - ret_combo
        winner = "AVGS.L 勝出!" if diff > 0 else f"美股組合 ({combo_type}) 勝出!"
        color = "green" if diff > 0 else "red"
        st.markdown(f"### :{color}[{winner}] (差距 {abs(diff):.2f}%)")
        
        st.line_chart(normalized[['AVGS', 'Combo']], color=["#FF4B4B", "#1E90FF"])

except Exception as e:
    st.error("連線稍慢，自動重試中...")

# --- 自動刷新邏輯 ---
if auto_refresh:
    time.sleep(60) # 等待 60 秒
    st.rerun()     # 重新執行程式
else:
    if st.button('🔄 手動刷新'):
        st.rerun()
