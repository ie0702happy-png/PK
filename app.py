import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 設定頁面 ---
st.set_page_config(page_title="AVGS vs AVUV+AVDV", layout="centered")

# --- 標題與樣式 ---
st.title("🥊 全球小盤價值股 PK 賽")
st.caption("英股 AVGS.L (USD Acc) vs. 50% AVUV + 50% AVDV")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("設定")
    period = st.selectbox("比較時間範圍", ["YTD", "3mo", "6mo", "1y", "max"], index=3)
    st.info("數據來源: Yahoo Finance (英股報價約有15分鐘延遲)")

# --- 核心函數 ---
def load_data(period):
    # 定義代碼
    tickers = {
        'AVGS': 'AVGS.L',    # 英股 USD Accumulating
        'AVUV': 'AVUV',      # 美股 US Small Cap Value
        'AVDV': 'AVDV',      # 美股 Intl Small Cap Value
        'FX': 'USDTWD=X'     # 美元兌台幣
    }
    
    # 下載數據
    data = yf.download(list(tickers.values()), period=period, progress=False)['Adj Close']
    
    # 處理數據 (重命名欄位以便操作)
    # yfinance 下載多個 ticker 時，columns 會是 MultiIndex，需要簡化
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
        
    # 映射回我們好讀的名字
    rename_map = {v: k for k, v in tickers.items()}
    # 針對 yfinance 可能回傳不帶 .L 或帶後綴的情況做模糊匹配處理 (簡化版直接嘗試 rename)
    # 為了保險，我們先用 ticker 對應
    
    df = data.copy()
    # 嘗試重新命名列
    df.rename(columns=rename_map, inplace=True)
    
    # 如果 AVGS 數據太少 (因為它是新出的 ETF)，我們需要從它上市那天開始切
    # 找出 AVGS 第一個有數據的日期
    if 'AVGS' in df.columns:
        valid_start = df['AVGS'].first_valid_index()
        if valid_start:
            df = df.loc[valid_start:]
    
    return df

# --- 執行數據抓取 ---
try:
    with st.spinner('正在從倫敦與紐約抓取最新報價...'):
        df = load_data(period)
        
        # 確保有數據
        if df.empty or 'AVGS' not in df.columns:
            st.error("無法取得 AVGS.L 數據，可能是剛開盤或 Yahoo API 暫時連不上。")
            st.stop()

        # 填補空值 (處理英美休市日不同)
        df = df.ffill().dropna()

        # 取得最新匯率與價格
        latest_fx = df['FX'].iloc[-1]
        latest_avgs = df['AVGS'].iloc[-1]
        latest_avuv = df['AVUV'].iloc[-1]
        latest_avdv = df['AVDV'].iloc[-1]

        # 計算組合價格 (假設初始各投 $50，用漲跌幅回推指數)
        # 方法：將所有資產在第一天歸一化為 100
        normalized = df / df.iloc[0] * 100
        
        # 組合指數 = 50% AVUV指數 + 50% AVDV指數
        normalized['Combo'] = 0.5 * normalized['AVUV'] + 0.5 * normalized['AVDV']
        normalized['AVGS_Index'] = normalized['AVGS']

        # 計算當前績效 (報酬率 %)
        ret_avgs = (normalized['AVGS_Index'].iloc[-1] - 100)
        ret_combo = (normalized['Combo'].iloc[-1] - 100)

        # --- 顯示即時報價區 ---
        st.subheader("💰 即時報價 (USD / TWD)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("AVGS.L (英股)", 
                      f"${latest_avgs:.2f}", 
                      f"約 NT$ {latest_avgs * latest_fx:.0f}")
        
        with col2:
            # 組合價格用加權平均概念展示
            combo_price_usd = 0.5 * latest_avuv + 0.5 * latest_avdv
            st.metric("50/50 組合 (美股)", 
                      f"${combo_price_usd:.2f} (合)", 
                      f"約 NT$ {combo_price_usd * latest_fx:.0f}")

        st.caption(f"目前匯率: 1 USD = {latest_fx:.2f} TWD")

        # --- PK 結果 ---
        st.divider()
        st.subheader("🏆 PK 結果 (區間績效)")
        
        diff = ret_avgs - ret_combo
        if diff > 0:
            winner = "AVGS.L 勝出!"
            color = "green"
            delta_msg = f"領先 {diff:.2f}%"
        else:
            winner = "美股組合 (AVUV+AVDV) 勝出!"
            color = "red"
            delta_msg = f"落後 {abs(diff):.2f}%"

        st.markdown(f"### :{color}[{winner}]")
        st.markdown(f"**差距:** {delta_msg}")

        # 顯示績效表
        perf_data = pd.DataFrame({
            "標的": ["AVGS.L", "50% AVUV + 50% AVDV"],
            "區間報酬": [f"{ret_avgs:.2f}%", f"{ret_combo:.2f}%"]
        })
        st.table(perf_data)

        # --- 走勢圖 ---
        st.subheader("📈 走勢對決 (以 100 為起點)")
        chart_data = normalized[['AVGS_Index', 'Combo']]
        chart_data.columns = ['AVGS.L', 'AVUV+AVDV (50/50)']
        st.line_chart(chart_data, color=["#FF4B4B", "#1E90FF"]) # 紅色 AVGS, 藍色 組合

except Exception as e:
    st.error(f"發生錯誤: {e}")
    st.warning("請稍後重試，或檢查 Yahoo Finance 連線。")

# --- 底部按鈕 ---
if st.button('🔄 刷新報價'):
    st.rerun()
