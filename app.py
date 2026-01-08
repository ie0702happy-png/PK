import streamlit as st
import yfinance as yf
import pandas as pd

# --- 頁面設定 ---
st.set_page_config(page_title="AVGS vs 美股組合", layout="centered")
st.title("🥊 全球小盤價值股 PK 賽")

# --- 側邊欄設定 (新增比例選擇) ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    
    # 1. 時間範圍
    period = st.selectbox("比較時間範圍", ["YTD", "3mo", "6mo", "1y", "max"], index=3)
    
    # 2. 組合比例選擇 (新增功能)
    st.write("---")
    st.write("🇺🇸 **美股組合配置 (AVUV / AVDV)**")
    combo_type = st.radio(
        "選擇比例:",
        ("50% / 50%", "60% / 40%", "70% / 30%"),
        index=0
    )
    
    # 解析比例
    if "60" in combo_type:
        w_avuv, w_avdv = 0.6, 0.4
    elif "70" in combo_type:
        w_avuv, w_avdv = 0.7, 0.3
    else:
        w_avuv, w_avdv = 0.5, 0.5
        
    st.info(f"當前裁判標準：\n美股 = {int(w_avuv*100)}% AVUV + {int(w_avdv*100)}% AVDV")

st.caption(f"英股 AVGS.L (USD) vs. 美股組合 ({combo_type})")

# --- 核心邏輯 (包含防呆) ---
def load_data(period):
    tickers = {'AVGS': 'AVGS.L', 'AVUV': 'AVUV', 'AVDV': 'AVDV', 'FX': 'USDTWD=X'}
    
    try:
        raw_data = yf.download(list(tickers.values()), period=period, progress=False)
    except Exception as e:
        st.error(f"連線失敗: {e}")
        st.stop()

    if raw_data.empty:
        st.warning("⚠️ 無法取得數據，請稍後重試。")
        st.stop()

    # 彈性讀取欄位
    if 'Adj Close' in raw_data.columns:
        data = raw_data['Adj Close']
    elif 'Close' in raw_data.columns:
        data = raw_data['Close']
    else:
        data = raw_data

    # 處理多層索引
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    rename_map = {v: k for k, v in tickers.items()}
    df.rename(columns=rename_map, inplace=True)
    
    # 從 AVGS 上市日開始切
    if 'AVGS' in df.columns:
        valid_start = df['AVGS'].first_valid_index()
        if valid_start: df = df.loc[valid_start:]
        
    return df

# --- 執行與顯示 ---
try:
    with st.spinner('正在計算不同權重績效...'):
        df = load_data(period).ffill().dropna()
        
        # 檢查數據完整性
        required = ['AVGS', 'AVUV', 'AVDV', 'FX']
        if not all(col in df.columns for col in required):
            st.error("部分數據缺失，請刷新重試。")
            st.stop()

        # 最新數據
        latest_fx = df['FX'].iloc[-1]
        latest_avgs = df['AVGS'].iloc[-1]
        latest_avuv = df['AVUV'].iloc[-1]
        latest_avdv = df['AVDV'].iloc[-1]
        
        # 計算組合價格 (加權平均)
        combo_price = (w_avuv * latest_avuv) + (w_avdv * latest_avdv)
        
        # 歸一化 (起點 100)
        normalized = df / df.iloc[0] * 100
        normalized['Combo'] = (w_avuv * normalized['AVUV']) + (w_avdv * normalized['AVDV'])
        
        # 績效計算
        ret_avgs = normalized['AVGS'].iloc[-1] - 100
        ret_combo = normalized['Combo'].iloc[-1] - 100

        # --- 顯示區 ---
        st.subheader("💰 即時報價 (USD / TWD)")
        col1, col2 = st.columns(2)
        
        # 左邊：AVGS
        col1.metric("🇬🇧 AVGS.L", 
                    f"${latest_avgs:.2f}", 
                    f"NT$ {latest_avgs*latest_fx:.0f}")
        
        # 右邊：美股組合 (動態顯示名稱)
        col2.metric(f"🇺🇸 組合 ({combo_type})", 
                    f"${combo_price:.2f}", 
                    f"NT$ {combo_price*latest_fx:.0f}")
        
        st.caption(f"匯率 1 USD = {latest_fx:.2f} TWD")

        # --- PK 結果 ---
        st.divider()
        diff = ret_avgs - ret_combo
        
        if diff > 0:
            winner = "AVGS.L 勝出!"
            color = "green"
        else:
            winner = f"美股組合 ({combo_type}) 勝出!"
            color = "red"
            
        st.markdown(f"### :{color}[{winner}]")
        st.markdown(f"**差距: {abs(diff):.2f}%** (區間報酬)")
        
        # --- 走勢圖 ---
        chart_data = normalized[['AVGS', 'Combo']]
        chart_data.columns = ['AVGS.L', f'Combo ({combo_type})']
        st.line_chart(chart_data, color=["#FF4B4B", "#1E90FF"])
        
        # --- (加碼) 策略總覽表 ---
        with st.expander("📊 查看所有組合的詳細比較表"):
            # 為了比較，我們一次算出三種組合的報酬率
            res_data = []
            for r_avuv, r_avdv, label in [(0.5, 0.5, "50/50"), (0.6, 0.4, "60/40"), (0.7, 0.3, "70/30")]:
                # 簡單計算該組合的累積報酬
                combo_ret = ((r_avuv * normalized['AVUV'] + r_avdv * normalized['AVDV']).iloc[-1]) - 100
                res_data.append([f"美股 {label}", f"{combo_ret:.2f}%", f"{combo_ret - ret_avgs:.2f}%"])
            
            # 加入 AVGS
            res_data.insert(0, ["🇬🇧 AVGS.L", f"{ret_avgs:.2f}%", "-"])
            
            st.table(pd.DataFrame(res_data, columns=["標的/組合", "區間報酬率", "領先 AVGS"]))


except Exception as e:
    st.error(f"系統忙碌中: {e}")
    if st.button('🔄 重試'): st.rerun()

# 底部刷新
if st.button('🔄 更新報價'):
    st.rerun()
