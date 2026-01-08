import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 頁面設定 ---
st.set_page_config(page_title="AVGS vs 美股組合", layout="centered")
st.title("🥊 全球小盤價值股 PK 賽")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    
    # 1. 自動刷新
    st.write("⏱️ **自動更新**")
    auto_refresh = st.toggle("開啟每 60 秒自動刷新", value=False)
    if auto_refresh:
        st.caption("⚠️ 運行中...請勿頻繁切換參數。")
    
    st.divider()

    # 2. 參數
    period = st.selectbox("比較時間範圍", ["YTD", "3mo", "6mo", "1y", "max"], index=3)
    
    st.write("🇺🇸 **美股資金配置 (本金分配)**")
    combo_type = st.radio("資金分配比例:", ("50% / 50%", "60% / 40%", "70% / 30%"), index=0)
    
    # 解析比例
    if "60" in combo_type:
        w_avuv, w_avdv = 0.6, 0.4
    elif "70" in combo_type:
        w_avuv, w_avdv = 0.7, 0.3
    else:
        w_avuv, w_avdv = 0.5, 0.5

st.caption(f"邏輯：假設投入相同本金，分別買入 AVGS 與 美股組合 ({combo_type})")

# --- 核心邏輯 ---
def load_data(period):
    tickers = {'AVGS': 'AVGS.L', 'AVUV': 'AVUV', 'AVDV': 'AVDV', 'FX': 'USDTWD=X'}
    try:
        raw_data = yf.download(list(tickers.values()), period=period, progress=False)
    except:
        return pd.DataFrame()

    if raw_data.empty: return pd.DataFrame()

    if 'Adj Close' in raw_data.columns: data = raw_data['Adj Close']
    elif 'Close' in raw_data.columns: data = raw_data['Close']
    else: data = raw_data

    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    rename_map = {v: k for k, v in tickers.items()}
    df.rename(columns=rename_map, inplace=True)
    
    # 對齊數據起點
    df = df.ffill().dropna()
    return df

# --- 執行與顯示 ---
try:
    df = load_data(period)
    
    required = ['AVGS', 'AVUV', 'AVDV', 'FX']
    if df.empty or not all(col in df.columns for col in required):
        st.warning("⏳ 讀取數據中... (若卡住請按手動刷新)")
        time.sleep(3)
        st.rerun()
    else:
        # --- 關鍵修正：資金加權邏輯 ---
        # 假設初始本金為 100 (歸一化)
        # 1. 先算出各檔股票的累積報酬倍數 (例如變成 1.1 倍)
        returns_df = df / df.iloc[0]
        
        # 2. 計算組合淨值 (Net Asset Value)
        # 你的邏輯：本金的 50% 買 AVUV，50% 買 AVDV
        # 公式：(0.5 * AVUV倍數) + (0.5 * AVDV倍數)
        combo_nav = (w_avuv * returns_df['AVUV']) + (w_avdv * returns_df['AVDV'])
        
        # 3. AVGS 的淨值
        avgs_nav = returns_df['AVGS']

        # --- 計算最終結果 ---
        latest_fx = df['FX'].iloc[-1]
        
        # 為了更有感，我們假設投入 NT$ 10,000
        initial_investment = 10000 
        
        final_avgs_twd = initial_investment * avgs_nav.iloc[-1]
        final_combo_twd = initial_investment * combo_nav.iloc[-1]
        
        # 報酬率
        ret_avgs_pct = (avgs_nav.iloc[-1] - 1) * 100
        ret_combo_pct = (combo_nav.iloc[-1] - 1) * 100

        # --- 顯示區 ---
        st.subheader(f"💰 戰果結算 (假設初始投入 NT$ {initial_investment:,})")
        col1, col2 = st.columns(2)
        
        # AVGS
        col1.metric(
            "🇬🇧 AVGS.L (單一)", 
            f"${final_avgs_twd:,.0f}", 
            f"{ret_avgs_pct:+.2f}%"
        )
        
        # 組合
        col2.metric(
            f"🇺🇸 美股組合 ({combo_type})", 
            f"${final_combo_twd:,.0f}", 
            f"{ret_combo_pct:+.2f}%"
        )
        
        st.divider()
        
        # 判定勝負
        diff = ret_avgs_pct - ret_combo_pct
        if diff > 0:
            winner = f"AVGS 勝出！ (多賺 ${final_avgs_twd - final_combo_twd:,.0f})"
            color = "green"
        else:
            winner = f"美股組合 勝出！ (多賺 ${final_combo_twd - final_avgs_twd:,.0f})"
            color = "red"
            
        st.markdown(f"### :{color}[{winner}]")
        
        # --- 走勢圖 ---
        # 畫出「本金成長曲線」
        chart_data = pd.DataFrame({
            'AVGS.L': avgs_nav * 100,      # 起點 100
            f'Combo ({combo_type})': combo_nav * 100 # 起點 100
        })
        st.line_chart(chart_data, color=["#FF4B4B", "#1E90FF"])
        
        st.caption(f"匯率換算參考: 1 USD = {latest_fx:.2f} TWD")

except Exception as e:
    st.error(f"系統暫時忙碌: {e}")

# --- 自動刷新 ---
if auto_refresh:
    time.sleep(60)
    st.rerun()
else:
    if st.button('🔄 手動刷新'):
        st.rerun()
