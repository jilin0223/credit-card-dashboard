import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials

# --- 頁面設定 ---
st.set_page_config(page_title="信用卡帳單管理系統", page_icon="💳", layout="wide")

# ==========================================
# 🌟 雲端資料庫初始化 (Google Sheets 連線)
# ==========================================
@st.cache_resource
def init_gsheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # 讀取 Streamlit Secrets 中的憑證
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], 
        scopes=scopes
    )
    client = gspread.authorize(creds)
    # 讀取目標試算表網址
    sheet = client.open_by_url(st.secrets["sheet_url"]["url"])
    return sheet

def load_data():
    sheet = init_gsheets()
    
    # 讀取 Cards 工作表
    try:
        ws_cards = sheet.worksheet("cards")
        cards_records = ws_cards.get_all_records()
        if not cards_records:
            cards_df = pd.DataFrame(columns=["銀行名稱", "結帳日", "繳款日"])
        else:
            cards_df = pd.DataFrame(cards_records)
    except gspread.exceptions.WorksheetNotFound:
        ws_cards = sheet.add_worksheet(title="cards", rows=100, cols=5)
        cards_df = pd.DataFrame(columns=["銀行名稱", "結帳日", "繳款日"])
        set_with_dataframe(ws_cards, cards_df)
        
    # 讀取 Spending 工作表
    try:
        ws_spending = sheet.worksheet("spending")
        spending_records = ws_spending.get_all_records()
        if not spending_records:
            spending_df = pd.DataFrame(columns=["年份", "月份", "銀行名稱", "消費總額", "已繳款"])
        else:
            spending_df = pd.DataFrame(spending_records)
            # 確保已繳款欄位型態正確
            if "已繳款" in spending_df.columns:
                # 處理從 Sheet 讀取回來可能是字串 "TRUE"/"FALSE" 或整數的問題
                spending_df["已繳款"] = spending_df["已繳款"].apply(lambda x: True if str(x).upper() == 'TRUE' else False)
    except gspread.exceptions.WorksheetNotFound:
        ws_spending = sheet.add_worksheet(title="spending", rows=1000, cols=10)
        spending_df = pd.DataFrame(columns=["年份", "月份", "銀行名稱", "消費總額", "已繳款"])
        set_with_dataframe(ws_spending, spending_df)
        
    return cards_df, spending_df

def save_data(df, tab_name):
    sheet = init_gsheets()
    ws = sheet.worksheet(tab_name)
    ws.clear()  # 清空舊資料
    set_with_dataframe(ws, df) # 寫入最新 DataFrame

cards_df, spending_df = load_data()

# --- 側邊欄導覽 ---
st.sidebar.title("💳 系統選單")
page = st.sidebar.radio("請選擇功能", ["📊 總覽面板與提醒", "📝 登記每月消費", "🏦 管理信用卡"])

# ==========================================
# 🌟 核心修復：跨頁面全域提示訊息攔截器
# ==========================================
if "success_msg" in st.session_state:
    st.success(st.session_state["success_msg"])
    del st.session_state["success_msg"] 

# ==========================================
# 頁面 1: 總覽面板與提醒 (Dashboard & Reminders)
# ==========================================
if page == "📊 總覽面板與提醒":
    st.title("📊 信用卡總覽面板")
    
    st.subheader("🔔 繳款提醒")
    if not spending_df.empty:
        spending_df["月份(年-月)"] = spending_df["年份"].astype(str) + "-" + spending_df["月份"].astype(str).str.zfill(2)
        st.subheader("📊 消費數據統計摘要")
        
        available_months = sorted(spending_df["月份(年-月)"].unique().tolist(), reverse=True)
        selected_period = st.selectbox("📅 選擇統計區間", ["歷史所有紀錄"] + available_months)
        
        st.divider()
        
        if selected_period == "歷史所有紀錄":
            filtered_df = spending_df
            total_spending = filtered_df["消費總額"].sum()
            
            st.metric(label="💰 歷史所有信用卡總花費", value=f"${total_spending:,} TWD")
            st.markdown("**💳 各信用卡歷史每月平均花費：**")
            
            card_stats = filtered_df.groupby("銀行名稱")["消費總額"].mean().round(0).astype(int).reset_index(name="金額")
            suffix = " /月"
        else:
            filtered_df = spending_df[spending_df["月份(年-月)"] == selected_period]
            total_spending = filtered_df["消費總額"].sum()
            
            st.metric(label=f"💰 {selected_period} 信用卡總花費", value=f"${total_spending:,} TWD")
            st.markdown(f"**💳 {selected_period} 各信用卡總花費：**")
            
            card_stats = filtered_df.groupby("銀行名稱")["消費總額"].sum().round(0).astype(int).reset_index(name="金額")
            suffix = ""
            
        MAX_COLS_PER_ROW = 4
        for i in range(0, len(card_stats), MAX_COLS_PER_ROW):
            cols = st.columns(MAX_COLS_PER_ROW)
            chunk = card_stats.iloc[i:i+MAX_COLS_PER_ROW]
            for j, (_, row) in enumerate(chunk.iterrows()):
                with cols[j]:
                    st.metric(label=row['銀行名稱'], value=f"${row['金額']:,}{suffix}")
                
        st.divider()
        st.subheader("📈 信用卡花費趨勢圖")
        
        plot_df = spending_df.sort_values("月份(年-月)")

        fig = px.line(
            plot_df, 
            x="月份(年-月)", 
            y="消費總額", 
            color="銀行名稱",
            markers=True,
            title="各銀行每月消費趨勢",
            labels={"消費總額": "金額 (TWD)", "月份(年-月)": "月份"}
        )
        fig.update_layout(
            plot_bgcolor="white",       
            paper_bgcolor="white",      
            font=dict(color="black"),   
            hovermode="x unified"
        )
        fig.update_xaxes(type="category", showgrid=True, gridwidth=1, gridcolor="#E5E5E5")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#E5E5E5")
        
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("查看完整消費統計資料表"):
            st.dataframe(spending_df.drop(columns=["月份(年-月)"]).sort_values(by=["年份", "月份"], ascending=[False, False]), use_container_width=True)
    else:
        st.subheader("📈 信用卡花費趨勢圖")
        st.write("請先至「登記每月消費」新增資料，以產生趨勢與統計數據。")

# ==========================================
# 頁面 2: 登記每月消費 (Record Spending)
# ==========================================
elif page == "📝 登記每月消費":
    st.title("📝 登記每月消費")
    
    if cards_df.empty:
        st.error("請先至「管理信用卡」新增發卡銀行，才能登記消費！")
    else:
        with st.form("add_spending_form"):
            col1, col2 = st.columns(2)
            with col1:
                year = st.number_input("年份", min_value=2000, max_value=2100, value=datetime.now().year)
                bank = st.selectbox("選擇信用卡 (發卡銀行)", cards_df["銀行名稱"].tolist())
            with col2:
                month = st.number_input("月份", min_value=1, max_value=12, value=datetime.now().month)
                amount = st.number_input("本月消費總額", min_value=0, value=0, step=100)
            
            is_paid = st.checkbox("✅ 此帳單已繳款")
            submitted = st.form_submit_button("儲存紀錄")

            if submitted:
                mask = (spending_df["年份"] == year) & (spending_df["月份"] == month) & (spending_df["銀行名稱"] == bank)
                if mask.any():
                    spending_df.loc[mask, "消費總額"] = amount
                    spending_df.loc[mask, "已繳款"] = is_paid
                    st.session_state["success_msg"] = f"✅ 已更新：{bank} {year}年{month}月的消費紀錄！"
                else:
                    new_record = pd.DataFrame([{
                        "年份": year, 
                        "月份": month, 
                        "銀行名稱": bank, 
                        "消費總額": amount, 
                        "已繳款": is_paid
                    }])
                    spending_df = pd.concat([spending_df, new_record], ignore_index=True)
                    st.session_state["success_msg"] = f"✅ 新增成功：{bank} {year}年{month}月的消費紀錄！"
                
                # 存入名稱為 "spending" 的工作表
                save_data(spending_df, "spending")
                st.rerun() 
                
        st.divider()
        st.subheader("💡 快速標記繳款狀態與到期提醒")
        
        spending_df["Ref已繳款"] = spending_df["已繳款"].astype(bool)
        unpaid_list = spending_df[spending_df["Ref已繳款"] == False]
        
        if not unpaid_list.empty:
            import calendar
            today = datetime.now()
            
            for index, row in unpaid_list.iterrows():
                bank = row['銀行名稱']
                card_info = cards_df[cards_df["銀行名稱"] == bank]
                closing_day = card_info["結帳日"].values[0] if not card_info.empty else 1
                due_day = card_info["繳款日"].values[0] if not card_info.empty else 15
                
                bill_year = row['年份']
                bill_month = row['月份']
                
                if due_day > closing_day:
                    due_year = bill_year
                    due_month = bill_month
                else:
                    if bill_month == 12:
                        due_year = bill_year + 1
                        due_month = 1
                    else:
                        due_year = bill_year
                        due_month = bill_month + 1
                    
                try:
                    max_day_of_month = calendar.monthrange(due_year, due_month)[1]
                    actual_due_day = min(due_day, max_day_of_month)
                    due_date = datetime(due_year, due_month, actual_due_day)
                    days_left = (due_date - today).days
                    
                    if days_left < 0:
                        status_emoji = "🚨"
                        status_text = f"【已逾期 {abs(days_left)} 天】"
                        text_color = "#FF4B4B"
                    elif 0 <= days_left <= 7:
                        status_emoji = "⚠️"
                        status_text = f"【即將到期：剩 {days_left} 天】"
                        text_color = "#FFA500"
                    else:
                        status_emoji = "✅"
                        status_text = f" (距離繳款還有 {days_left} 天)"
                        text_color = "#00CC66"
                except Exception:
                    status_emoji = "📅"
                    status_text = f" (建議繳款日: {due_day}日)"
                    text_color = "gray"

                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    display_html = f"""
                    <div style="padding-top: 5px; font-size: 16px;">
                        {status_emoji} <b>{bank}</b> - {row['年份']} / {row['月份']} (金額: <b>${row['消費總額']:,}</b>) 
                        <span style="color: {text_color}; font-weight: bold;">{status_text}</span>
                    </div>
                    """
                    st.markdown(display_html, unsafe_allow_html=True)
                with col_btn:
                    if st.button("標記已繳", key=f"pay_{index}"):
                        spending_df.at[index, "已繳款"] = True
                        if "Ref已繳款" in spending_df.columns:
                            spending_df = spending_df.drop(columns=["Ref已繳款"])
                        save_data(spending_df, "spending")
                        st.session_state["success_msg"] = f"✅ 已成功將 {bank} ({row['年份']}年{row['月份']}月) 標記為已繳款！"
                        st.rerun()
        else:
            st.success("目前沒有待繳帳單，太棒了！🎉")
            
        st.divider()
        st.subheader("🗑️ 管理與刪除消費紀錄")
        if not spending_df.empty:
            delete_options = ["(不進行操作)"]
            delete_mapping = {}
            
            sorted_spending = spending_df.sort_values(by=["年份", "月份"], ascending=[False, False])
            
            for idx, row in sorted_spending.iterrows():
                label = f"{row['年份']}年{row['月份']:02d}月 - {row['銀行名稱']} (消費額: ${row['消費總額']:,})"
                delete_options.append(label)
                delete_mapping[label] = idx
            
            selected_delete = st.selectbox("請選擇您要刪除的歷史消費紀錄：", delete_options)
            
            if st.button("🗑️ 確認刪除此紀錄") and selected_delete != "(不進行操作)":
                idx_to_drop = delete_mapping[selected_delete]
                spending_df = spending_df.drop(idx_to_drop)
                
                core_columns = ["年份", "月份", "銀行名稱", "消費總額", "已繳款"]
                save_df = spending_df[core_columns]
                
                save_data(save_df, "spending")
                st.session_state["success_msg"] = f"🗑️ 刪除成功：您已移除 {selected_delete} 的紀錄。"
                st.rerun()
        else:
            st.info("目前沒有任何消費紀錄可供刪除。")

# ==========================================
# 頁面 3: 管理信用卡 (Manage Cards)
# ==========================================
elif page == "🏦 管理信用卡":
    st.title("🏦 管理信用卡與結帳日")
    
    with st.form("add_card_form"):
        st.write("新增或修改信用卡資訊")
        col1, col2, col3 = st.columns(3)
        with col1:
            bank_name = st.text_input("發卡銀行名稱 (例如: 台新, 中信)")
        with col2:
            statement_day = st.number_input("結帳日 (每月幾號)", min_value=1, max_value=31, value=1)
        with col3:
            due_day = st.number_input("繳款日 (每月幾號)", min_value=1, max_value=31, value=15)
            
        submitted = st.form_submit_button("新增 / 更新信用卡")
        
        if submitted and bank_name:
            if bank_name in cards_df["銀行名稱"].values:
                cards_df.loc[cards_df["銀行名稱"] == bank_name, ["結帳日", "繳款日"]] = [statement_day, due_day]
                st.session_state["success_msg"] = f"✅ 已更新：{bank_name} 的結帳與繳款日資訊！"
            else:
                new_card = pd.DataFrame([{"銀行名稱": bank_name, "結帳日": statement_day, "繳款日": due_day}])
                cards_df = pd.concat([cards_df, new_card], ignore_index=True)
                st.session_state["success_msg"] = f"✅ 新增成功：已將 {bank_name} 加入信用卡清單！"
            
            # 存入名稱為 "cards" 的工作表
            save_data(cards_df, "cards")
            st.rerun()

    st.divider()
    st.subheader("目前的信用卡清單")
    if not cards_df.empty:
        st.table(cards_df)
        
        delete_bank = st.selectbox("選擇要移除的信用卡", ["(不進行操作)"] + cards_df["銀行名稱"].tolist())
        if st.button("🗑️ 移除此信用卡") and delete_bank != "(不進行操作)":
            cards_df = cards_df[cards_df["銀行名稱"] != delete_bank]
            save_data(cards_df, "cards")
            st.session_state["success_msg"] = f"🗑️ 移除成功：已將 {delete_bank} 從清單中刪除。"
            st.rerun()
    else:
        st.info("目前尚未建立任何信用卡資訊。")
