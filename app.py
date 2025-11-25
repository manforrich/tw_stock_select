import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import feedparser
import datetime
import pandas as pd

# 1. 設定網頁標題
st.set_page_config(page_title="全方位股票分析系統", layout="wide")

# --- 側邊欄：模式選擇 ---
st.sidebar.title("🚀 功能選單")
app_mode = st.sidebar.selectbox("選擇功能", ["📊 單一個股分析", "🔍 策略選股器"])

# ========================================================
#  共用函數區
# ========================================================
def get_stock_data(ticker, mode="預設區間", period="1y", start=None, end=None):
    try:
        if mode == "預設區間":
            hist = yf.download(ticker, period=period, auto_adjust=True, progress=False)
        else:
            hist = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        
        if hist.empty: return None, "無數據"
        if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.droplevel(1)
        return hist, None
    except Exception as e:
        return None, str(e)

def get_google_news(query):
    try:
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
        feed = feedparser.parse(rss_url)
        return feed.entries
    except: return []

# ========================================================
#  模式 A: 單一個股分析 (原本的功能)
# ========================================================
if app_mode == "📊 單一個股分析":
    st.title("📊 單一個股分析儀表板")
    
    # 側邊欄參數
    st.sidebar.header("數據設定")
    input_ticker = st.sidebar.text_input("輸入股票代碼", value="2330.TW")
    
    if input_ticker.isdigit() and len(input_ticker) == 4:
        stock_id = input_ticker + ".TW"
        st.sidebar.caption(f"💡 自動修正為: {stock_id}")
    else:
        stock_id = input_ticker

    time_mode = st.sidebar.radio("時間模式", ["預設區間", "自訂日期"])
    start_date, end_date, selected_period = None, None, None
    
    if time_mode == "預設區間":
        selected_period = st.sidebar.selectbox("範圍", ["3mo", "6mo", "1y", "2y", "5y"], index=2)
    else:
        default_start = datetime.date.today() - datetime.timedelta(days=365)
        start_date = st.sidebar.date_input("開始", default_start)
        end_date = st.sidebar.date_input("結束", datetime.date.today())

    st.sidebar.subheader("圖表指標")
    ma_days = st.sidebar.multiselect("均線 (MA)", [5, 10, 20, 60, 120], default=[5, 20])
    show_bb = st.sidebar.checkbox("布林通道", False)
    show_vp = st.sidebar.checkbox("籌碼密集區", True)
    show_gaps = st.sidebar.checkbox("跳空缺口", True)

    # 主程式邏輯
    if stock_id:
        df, error_msg = get_stock_data(stock_id, time_mode, period=selected_period, start=start_date, end=end_date)
        
        if df is not None and not df.empty:
            # 數據看板
            c1, c2, c3, c4 = st.columns(4)
            close = df['Close'].iloc[-1]
            change = close - df['Close'].iloc[-2]
            pct = (change / df['Close'].iloc[-2]) * 100
            c1.metric("股價", f"{close:.2f}", f"{change:.2f} ({pct:.2f}%)")
            c2.metric("最高", f"{df['High'].max():.2f}")
            c3.metric("最低", f"{df['Low'].min():.2f}")
            c4.metric("成交量", f"{int(df['Volume'].iloc[-1]):,}")

            # 繪圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.03)
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="K線"), row=1, col=1)
            
            colors = ['orange', 'blue', 'purple', 'black']
            for i, d in enumerate(ma_days):
                ma = df['Close'].rolling(d).mean()
                fig.add_trace(go.Scatter(x=df.index, y=ma, mode='lines', name=f"MA{d}", line=dict(width=1.5, color=colors[i%4])), row=1, col=1)

            if show_bb:
                mid = df['Close'].rolling(20).mean()
                std = df['Close'].rolling(20).std()
                fig.add_trace(go.Scatter(x=df.index, y=mid+2*std, line=dict(color='rgba(0,100,255,0.3)'), showlegend=False), row=1, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=mid-2*std, line=dict(color='rgba(0,100,255,0.3)'), fill='tonexty', fillcolor='rgba(0,100,255,0.1)', name='布林'), row=1, col=1)

            if show_vp:
                fig.add_trace(go.Histogram(y=df['Close'], x=df['Volume'], histfunc='sum', orientation='h', nbinsy=50, name="籌碼", xaxis='x3', yaxis='y', marker=dict(color='rgba(31,119,180,0.3)'), hoverinfo='none'))
                fig.update_layout(xaxis3=dict(overlaying='x', side='top', showgrid=False, visible=False, range=[df['Volume'].max()*3, 0]))

            vol_color = ['green' if c >= o else 'red' for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=vol_color, name="量"), row=2, col=1)
            
            fig.update_layout(height=600, xaxis_rangeslider_visible=False, legend=dict(orientation="h", y=1.02))
            fig.update_xaxes(type='date', row=1, col=1)
            fig.update_xaxes(type='date', row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

            # 新聞
            st.divider()
            st.subheader("📰 相關新聞")
            for item in get_google_news(stock_id)[:4]:
                st.markdown(f"- [{item.title}]({item.link}) ({item.published})")

        else:
            st.error(f"無法讀取數據: {error_msg}")

# ========================================================
#  模式 B: 策略選股器 (新增功能)
# ========================================================
elif app_mode == "🔍 策略選股器":
    st.title("🔍 均線策略選股器")
    st.markdown("這個工具會掃描下方的觀察清單，找出符合 **「黃金交叉」** 或 **「強勢多頭」** 的股票。")

    # 1. 設定掃描參數
    col_a, col_b = st.columns(2)
    with col_a:
        short_ma = st.number_input("短期均線 (MA)", value=5)
    with col_b:
        long_ma = st.number_input("長期均線 (MA)", value=20)
    
    # 2. 定義觀察清單 (你可以自己加)
    default_tickers = "2330, 2317, 2454, 2308, 2303, 2603, 2609, 2615, 2881, 2882, 0050, 0056, 00878, 3231, 2382, 6669"
    user_tickers = st.text_area("輸入觀察清單 (用逗號分隔，免加 .TW)", default_tickers)
    
    start_scan = st.button("🚀 開始掃描", type="primary")
    
    if start_scan:
        # 處理代碼清單
        ticker_list = [t.strip() + ".TW" for t in user_tickers.split(",") if t.strip()]
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, ticker in enumerate(ticker_list):
            # 更新進度條
            status_text.text(f"正在掃描: {ticker} ...")
            progress_bar.progress((i + 1) / len(ticker_list))
            
            try:
                # 只抓最近 3 個月的資料就夠了，加快速度
                df = yf.download(ticker, period="3mo", auto_adjust=True, progress=False)
                
                if not df.empty and len(df) > long_ma:
                    # 處理 MultiIndex
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
                    
                    # 計算均線
                    df['MA_Short'] = df['Close'].rolling(window=short_ma).mean()
                    df['MA_Long'] = df['Close'].rolling(window=long_ma).mean()
                    
                    # 取得最近兩天的數據
                    today = df.iloc[-1]
                    yesterday = df.iloc[-2]
                    
                    # --- 策略 1: 黃金交叉 (昨天短<長，今天短>長) ---
                    golden_cross = (yesterday['MA_Short'] < yesterday['MA_Long']) and (today['MA_Short'] > today['MA_Long'])
                    
                    # --- 策略 2: 多頭排列 (股價 > 短 > 長) ---
                    bullish_trend = (today['Close'] > today['MA_Short']) and (today['MA_Short'] > today['MA_Long'])
                    
                    trend_status = "盤整/空頭"
                    if golden_cross: trend_status = "✨ 黃金交叉"
                    elif bullish_trend: trend_status = "🔥 多頭排列"
                    
                    # 只要是多頭或黃金交叉就加入結果
                    if golden_cross or bullish_trend:
                        results.append({
                            "代碼": ticker.replace(".TW", ""),
                            "收盤價": f"{today['Close']:.2f}",
                            "漲跌幅": f"{(today['Close'] - yesterday['Close'])/yesterday['Close']*100:.2f}%",
                            f"MA{short_ma}": f"{today['MA_Short']:.2f}",
                            f"MA{long_ma}": f"{today['MA_Long']:.2f}",
                            "訊號": trend_status
                        })
                        
            except Exception as e:
                continue # 這一檔失敗就跳過
        
        progress_bar.empty()
        status_text.empty()
        
        # 顯示結果
        if results:
            st.success(f"掃描完成！發現 {len(results)} 檔符合條件的股票")
            res_df = pd.DataFrame(results)
            
            # 使用 styling 讓表格更好看
            def highlight_signal(val):
                color = '#d4edda' if '黃金交叉' in val else '#fff3cd' if '多頭' in val else ''
                return f'background-color: {color}'

            st.dataframe(res_df.style.applymap(highlight_signal, subset=['訊號']), use_container_width=True)
        else:
            st.warning("掃描完成，但沒有發現符合策略的股票。")
