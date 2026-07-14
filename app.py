import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import os

# --- 頁面基本設定 ---
st.set_page_config(page_title="信用卡管理儀表板", page_icon="💳", layout="wide")
st.title("💳 信用卡與消費管理儀表板")

# --- 輔助函式：安全地讀取 CSV，若無檔案則建立空 DataFrame ---
def load_data(file_name, default_columns):
    if os.path.exists(file_name):
        try:
            return pd.read_csv(file_name)
        except Exception:
            return pd.DataFrame(columns=default_columns)
    else:
        return pd.DataFrame(columns=default_columns)

# 定義預設的欄位結構 (若沒有 CSV 時的預設樣板)
cards_cols = ['Card_Name', 'Bank', 'Credit_Limit', 'Due_Date']
spending_cols = ['Date', 'Card_Name', 'Category', 'Amount', 'Description']

# 讀取資料
df_cards = load_data('cards.csv', cards_cols)
df_spending = load_data('spending.csv', spending_cols)

# 確保日期欄位格式正確
if not df_cards.empty and 'Due_Date' in df_cards.columns:
    df_cards['Due_Date'] = pd.to_datetime(df_cards['Due_Date'], errors='coerce').dt.date
if not df_spending.empty and 'Date' in df_spending.columns:
    df_spending['Date'] = pd.to_datetime(df_spending['Date'], errors='coerce').dt.date

# ==========================================
# 需求 2：繳費日期快到時特別註記 (置頂提醒)
# ==========================================
st.header("🔔 繳費提醒")
today = datetime.date.today()
reminder_days = 7 # 預設提前 7 天提醒

if not df_cards.empty and 'Due_Date' in df_cards.columns:
    # 篩選出快到期的帳單 (今天 ~ 未來7天內)
    upcoming_bills = df_cards[
        (df_cards['Due_Date'] >= today) & 
        (df_cards['Due_Date'] <= today + datetime.timedelta(days=reminder_days))
    ]
    # 篩選出已逾期的帳單
    overdue_bills = df_cards[df_cards['Due_Date'] < today]

    if not overdue_bills.empty:
        st.error("🚨 **警告：以下信用卡帳單已逾期！請盡速確認繳費！**")
        st.dataframe(overdue_bills, hide_index=True, use_container_width=True)
        
    if not upcoming_bills.empty:
        st.warning(f"⚠️ **提醒：以下信用卡帳單將在 {reminder_days} 天內到期！**")
        st.dataframe(upcoming_bills, hide_index=True, use_container_width=True)
        
    if overdue_bills.empty and upcoming_bills.empty:
        st.success("✅ 目前沒有即將到期或逾期的帳單。")
else:
    st.info("尚無信用卡資料或缺乏 'Due_Date' (繳費日) 欄位。")

st.divider()

# ==========================================
# 資料視覺化 (使用 Plotly)
# ==========================================
st.header("📊 總消費統計")
if not df_spending.empty and 'Amount' in df_spending.columns:
    col1, col2 = st.columns(2)
    with col1:
        if 'Category' in df_spending.columns:
            fig_cat = px.pie(df_spending, values='Amount', names='Category', title='各類別消費佔比')
            st.plotly_chart(fig_cat, use_container_width=True)
    with col2:
        if 'Card_Name' in df_spending.columns:
            card_sum = df_spending.groupby('Card_Name')['Amount'].sum().reset_index()
            fig_card = px.bar(card_sum, x='Card_Name', y='Amount', title='各信用卡消費總額', text_auto=True)
            st.plotly_chart(fig_card, use_container_width=True)
else:
    st.info("尚無消費紀錄可供產生圖表。")

st.divider()

# ==========================================
# 需求 1：可以讓使用者已記錄的資料進行更改
# ==========================================
st.header("📝 資料管理與編輯")
st.markdown("💡 **使用說明**：您可以直接在下方表格中點擊欄位進行修改，或者點擊表格下方的 `+` 新增資料。編輯完成後，請務必點擊**「儲存」**按鈕。")

tab1, tab2 = st.tabs(["💳 信用卡管理 (cards.csv)", "💰 消費紀錄管理 (spending.csv)"])

with tab1:
    st.subheader("編輯信用卡資料")
    # 使用 data_editor 允許動態增刪改
    edited_cards = st.data_editor(df_cards, num_rows="dynamic", use_container_width=True, key="cards_editor")
    
    if st.button("💾 儲存信用卡變更", type="primary"):
        try:
            edited_cards.to_csv('cards.csv', index=False)
            st.success("✅ 信用卡資料已成功更新！(請點擊右上角 Rerun 或重新整理頁面以更新提醒狀態)")
        except Exception as e:
            st.error(f"儲存失敗：{e}")

with tab2:
    st.subheader("編輯消費紀錄")
    # 使用 data_editor 允許動態增刪改
    edited_spending = st.data_editor(df_spending, num_rows="dynamic", use_container_width=True, key="spending_editor")
    
    if st.button("💾 儲存消費變更", type="primary"):
        try:
            edited_spending.to_csv('spending.csv', index=False)
            st.success("✅ 消費紀錄已成功更新！(請點擊右上角 Rerun 或重新整理頁面以更新圖表)")
        except Exception as e:
            st.error(f"儲存失敗：{e}")
