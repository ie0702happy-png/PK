import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 頁面設定 ---
st.set_page_config(page_title="全球 SCV 終極對決", layout="centered")
st.title("🥊 全球小盤價值 (SCV) 終極對決")
st.caption("🇹🇼 100 萬本金實戰模擬 | 含 30% 股息稅與匯率影響")

# --- 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    
    # 1. 自動刷新
    auto_refresh = st.toggle("⏱️ 每 60 秒自動刷新", value=False)
    
    st.divider()

    # 2. 時間與本金
    period = st.selectbox("比較時間範圍", ["YTD", "6mo", "1y", "2y", "max"], index=3)
    principal = st.number_input("初始本金 (TWD)", value=1000000, step=100000)
    
    st.divider()
    
    # 3. 組合比例
    st.write("🇺🇸 **美股組合比例 (AVUV / AVDV)**")
    combo_ratio = st.radio("資金分配:", ("50% / 50%", "60% / 40%", "70% / 30%"), index=1)
    
    if "50" in combo_ratio: w_avuv, w_avdv = 0.5, 0.5
    elif "60" in combo_ratio: w_avuv, w_avdv = 0.6, 0.4
    else: w_avuv, w_avdv = 0.7, 0.3

    st.divider()
    
    # 4. 稅務開關
    apply_tax = st.toggle("扣除美股 30% 股息稅", value=True)
    if apply_tax:
        st.info("ℹ️ 已開啟 Tax Drag：\nAVUV (美) 與 AVDV (非美) 因配息較高，每日將扣除估算稅損。AVGS (英) 不扣稅。")

# --- 稅務損耗參數 (年化殖利率估算) ---
# Value 股票配息通常較高，稅的影響更明顯
TAX_PARAMS = {
    "AVUV": 0.018 * 0.30,  # 估算 Yield 1.8% -> 稅損 0.54%
    "AVDV": 0.032 * 0.30,  # 估算 Yield 3.2% -> 稅損 0.96% (痛!)
    "AVGS.L": 0.0          # 愛爾蘭註冊 -> 0%
}

# --- 核心邏輯 ---
def load_and_process_data(period):
    tickers = ["AVGS.L", "AVUV", "AVDV", "USDTWD=X"]
    try:
        raw = yf.download(tickers, period=period, progress=False)
        if raw.empty: return pd.DataFrame()
        
        # 抓取 Adj Close
        if 'Adj Close' in raw.columns: df = raw['Adj Close']
        elif 'Close' in raw.columns: df = raw['Close']
        else: df = raw
        
        # 欄位清理
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            
        df = df.ffill().dropna()
        return df

    except:
        return pd.DataFrame()

# --- 主程式 ---
try:
    df = load_and_process_data(period)
    
    required = ["AVGS.L", "AVUV", "AVDV", "USDTWD=X"]
    if df.empty or not all(col in df.columns for col in required):
        st.warning("⏳ 讀取數據中... (請稍候)")
        time.sleep(3)
        st.rerun()
    else:
        # --- 1. 計算稅後淨值曲線 (Tax Adjusted NAV) ---
        adjusted_nav = pd.DataFrame(index=df.index)
        
        for ticker in ["AVGS.L", "AVUV", "AVDV"]:
            # 每日報酬率
            daily_ret = df[ticker].pct_change().fillna(0)
            
            # 扣稅邏輯
            if apply_tax and ticker in TAX_PARAMS:
                daily_drag = TAX_PARAMS[ticker] / 252
                daily_ret = daily_ret - daily_drag
            
            # 重建成淨值 (起點為 1)
            adjusted_nav[ticker] = (1 + daily_ret).cumprod()

        # --- 2. 資金模擬實戰 ---
        fx = df["USDTWD=X"]
        start_fx = fx.iloc[0]
        
        # 步驟 A: 將 100 萬台幣在 Day 1 換成美金
        initial_usd = principal / start_fx
        
        # 選手 1: AVGS (全押)
        # 每日價值(USD) = 初始美金 * AVGS淨值增長
        avgs_val_usd = initial_usd * adjusted_nav["AVGS.L"]
        
        # 選手 2: 美股組合 (拆分資金)
        # 資金分配
        usd_part_avuv = initial_usd * w_avuv
        usd_part_avdv = initial_usd * w_avdv
        
        # 兩筆資金分別成長，最後加總
        combo_val_usd = (usd_part_avuv * adjusted_nav["AVUV"]) + \
                        (usd_part_avdv * adjusted_nav["AVDV"])

        # 步驟 B: 每日換回台幣 (Mark to Market)
        # 這裡我們要看「假如今天賣掉換回台幣是多少」
        avgs_val_twd = avgs_val_usd * fx
        combo_val_twd = combo_val_usd * fx
        
        # --- 3. 結算數據 ---
        final_avgs = avgs_val_twd.iloc[-1]
        final_combo = combo_val_twd.iloc[-1]
        
        avgs_ret = (final_avgs - principal) / principal * 100
        combo_ret = (final_combo - principal) / principal * 100
        
        diff_val = final_avgs - final_combo
        diff_pct = avgs_ret - combo_ret

        # --- 顯示介面 ---
        st.subheader(f"💰 戰果結算 (初始投入: NT$ {principal:,.0f})")
        
        col1, col2 = st.columns(2)
        
        # AVGS 卡片
        col1.metric(
            label="🇬🇧 AVGS (全球SCV)",
            value=f"${final_avgs:,.0f}",
            delta=f"{avgs_ret:+.2f}%"
        )
        
        # 美股組合 卡片
        col2.metric(
            label=f"🇺🇸 美股組合 ({int(w_avuv*100)}/{int(w_avdv*100)})",
            value=f"${final_combo:,.0f}",
            delta=f"{combo_ret:+.2f}%"
        )
        
        st.divider()

        # 勝負判定
        if diff_val > 0:
            winner = "AVGS (英股) 勝出！"
            color = "green"
            comment = "稅務優勢顯現：雖然 AVUV 很強，但 AVDV 的高股息稅拖累了美股組合。"
        else:
            winner = "美股組合 (AVUV+AVDV) 勝出！"
            color = "red"
            comment = "因子強度獲勝：儘管有稅務損耗，美股組合的漲幅仍足以抵銷成本。"
            
        st.markdown(f"## :{color}[{winner}]")
        st.markdown(f"#### 差距金額: NT$ {abs(diff_val):,.0f} (差距 {abs(diff_pct):.2f}%)")
        st.caption(comment)

        # --- 圖表 ---
        st.subheader("📈 資產走勢對比 (TWD)")
        chart_data = pd.DataFrame({
            "AVGS (英股)": avgs_val_twd,
            "Combo (美股)": combo_val_twd
        })
        st.line_chart(chart_data, color=["#00CC96", "#EF553B"])
        
        # --- 詳細數據表 ---
        with st.expander("📊 查看詳細收益與稅務參數"):
            st.write(f"**目前匯率**: 1 USD = {fx.iloc[-1]:.2f} TWD")
            st.write("**稅務損耗 (Tax Drag) 設定**:")
            st.code(f"""
            AVUV (美股): 每年扣除約 {(TAX_PARAMS['AVUV']/0.3)*100:.1f}% Yield x 30% 稅 = {TAX_PARAMS['AVUV']*100:.2f}%
            AVDV (非美): 每年扣除約 {(TAX_PARAMS['AVDV']/0.3)*100:.1f}% Yield x 30% 稅 = {TAX_PARAMS['AVDV']*100:.2f}%
            AVGS (英股): 0% (已內含於股價，無額外預扣稅)
            """)

except Exception as e:
    st.error(f"發生錯誤: {e}")

# --- 自動刷新 ---
if auto_refresh:
    time.sleep(60)
    st.rerun()
elif st.button("🔄 手動刷新"):
    st.rerun()
