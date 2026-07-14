import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# ==========================================
# 0. 頁面基本設定
# ==========================================
st.set_page_config(page_title="信用卡儀表板", page_icon="💳", layout="wide")
st.title("💳 信用卡消費與繳費儀表板")

# ==========================================
# 1. 資料讀取功能
# ==========================================
# 定義預設欄位 (若無檔案時的防呆機制)
CARDS_FILE = 'cards.csv'
SPENDING_FILE = 'spending.csv'

def load_data(file_name, default_cols):
    if os.path.exists(file_name):
        try:
            return pd.read_csv(file_name)
        except Exception:
            return pd.DataFrame(columns=default_cols)
    else:
        return pd.DataFrame(columns=default_cols)

# 讀取信用卡與消費資料
df_cards = load_data(CARDS_FILE, ['Card_Name', 'Bank', 'Credit_Limit', 'Due_Date'])
df_spending = load_data(SPENDING_FILE, ['Date', 'Card_Name', 'Category', 'Amount', 'Description'])

# 確保日期欄位為標準 datetime 格式
if not df_cards.empty and 'Due_Date' in df_cards.columns:
    df_cards['Due_Date'] = pd.to_datetime(df_cards['Due_Date'], errors='coerce').dt.date
if not df_spending.empty and 'Date' in df_spending.columns:
    df_spending['Date'] = pd.to_datetime(df_spending['Date'], errors='coerce').dt.date


# ==========================================
# 2. 新增功能：繳費日期快到特別註記
# ==========================================
st.header("🔔 繳費提醒")
today = datetime.date.today()
reminder_days = 7 # 提前 7 天提醒

if not df_cards.empty and 'Due_Date' in df_cards.columns:
    # 篩選出快到期的帳單 (今天 ~ 7天內)
    upcoming_bills = df_cards[
        (df_cards['Due_Date'] >= today) & 
        (df_cards['Due_Date'] <= today + datetime.timedelta(days=reminder_days))
    ]
    
    # 篩選出逾期帳單
    overdue_bills = df_cards[df_cards['Due_Date'] < today]

    if not overdue_bills.empty:
        st.error("🚨 **警告：以下信用卡已逾期！請盡速確認繳費！**")
        st.dataframe(overdue_bills, hide_index=True, use_container_width=True)
        
    if not upcoming_bills.empty:
        st.warning(f"⚠️ **提醒：以下信用卡將在 {reminder_days} 天內到期！**")
        st.dataframe(upcoming_bills, hide_index=True, use_container_width=True)
        
    if overdue_bills.empty and upcoming_bills.empty:
        st.success("✅ 目前沒有即將到期或逾期的帳單。")
else:
    st.info("尚無信用卡繳費日資料。")

st.divider()

# ==========================================
# 3. 保留原功能：圖表與視覺化分析 (Plotly)
# ==========================================
st.header("📊 消費數據分析")
if not df_spending.empty and 'Amount' in df_spending.columns:
    col1, col2 = st.columns(2)
    
    with col1:
        # 各類別消費圓餅圖
        if 'Category' in df_spending.columns:
            cat_sum = df_spending.groupby('Category')['Amount'].sum().reset_index()
            fig_pie = px.pie(cat_sum, values='Amount', names='Category', title='各類別消費佔比')
            st.plotly_chart(fig_pie, use_container_width=True)
            
    with col2:
        # 各信用卡消費長條圖
        if 'Card_Name' in df_spending.columns:
            card_sum = df_spending.groupby('Card_Name')['Amount'].sum().reset_index()
            fig_bar = px.bar(card_sum, x='Card_Name', y='Amount', title='各信用卡消費總額', text_auto=True)
            st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("尚無消費紀錄可供產生圖表。")

st.divider()

# ==========================================
# 4. 新增功能：讓使用者可以更改已記錄的資料
# ==========================================
st.header("📝 資料編輯區")
st.markdown("💡 **提示：您可以直接在下方表格內點擊並修改信用卡金額或消費紀錄。修改完成後請務必按下「儲存按鈕」。**")

tab1, tab2 = st.tabs(["💳 修改信用卡資料 (額度/繳費日)", "💰 修改消費紀錄 (金額/日期)"])

# --- 信用卡資料編輯區 ---
with tab1:
    st.subheader("編輯信用卡資料 (cards.csv)")
    # num_rows="dynamic" 允許使用者直接在畫面上新增或刪除資料列
    edited_cards = st.data_editor(df_cards, num_rows="dynamic", use_container_width=True, key="cards_editor")
    
    if st.button("💾 儲存信用卡變更", type="primary"):
        try:
            # 將修改後的資料存回 CSV
            edited_cards.to_csv(CARDS_FILE, index=False)
            st.success("✅ 信用卡資料已成功更新！")
            st.rerun() # 自動重新整理頁面以更新最上方的繳費提醒
        except Exception as e:
            st.error(f"儲存失敗：{e}")

# --- 消費紀錄編輯區 ---
with tab2:
    st.subheader("編輯消費紀錄 (spending.csv)")
    edited_spending = st.data_editor(df_spending, num_rows="dynamic", use_container_width=True, key="spending_editor")
    
    if st.button("💾 儲存消費變更", type="primary"):
        try:
            # 將修改後的資料存回 CSV
            edited_spending.to_csv(SPENDING_FILE, index=False)
            st.success("✅ 消費紀錄已成功更新！")
            st.rerun() # 自動重新整理頁面以更新圖表
        except Exception as e:
            st.error(f"儲存失敗：{e}")
