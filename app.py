import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 頁面設定 ---
st.set_page_config(page_title="信用卡帳單管理系統", page_icon="💳", layout="wide")

# --- 資料檔案路徑 ---
CARDS_FILE = "cards.csv"
SPENDING_FILE = "spending.csv"

# --- 初始化與讀取資料 ---
def load_data():
    if not os.path.exists(CARDS_FILE):
        pd.DataFrame(columns=["銀行名稱", "結帳日", "繳款日"]).to_csv(CARDS_FILE, index=False)
    if not os.path.exists(SPENDING_FILE):
        pd.DataFrame(columns=["年份", "月份", "銀行名稱", "消費總額", "已繳款"]).to_csv(SPENDING_FILE, index=False)
    
    cards_df = pd.read_csv(CARDS_FILE)
    spending_df = pd.read_csv(SPENDING_FILE)
    return cards_df, spending_df

def save_data(df, filename):
    df.to_csv(filename, index=False)

cards_df, spending_df = load_data()

# --- 側邊欄導覽 ---
st.sidebar.title("💳 系統選單")
page = st.sidebar.radio("請選擇功能", ["📊 總覽面板與提醒", "📝 登記每月消費", "🏦 管理信用卡"])

# ==========================================
# 頁面 1: 總覽面板與提醒 (Dashboard & Reminders)
# ==========================================
if page == "📊 總覽面板與提醒":
    st.title("📊 信用卡總覽面板")
    
    # --- 繳款提醒區塊 ---
    st.subheader("🔔 繳款提醒")
    if not spending_df.empty:
        # 建立月份字串欄位供後續統計與繪圖使用 (例如: 2024-01)
        spending_df["月份(年-月)"] = spending_df["年份"].astype(str) + "-" + spending_df["月份"].astype(str).str.zfill(2)
        
        # --- 數據統計摘要 ---
        st.subheader("📊 消費數據統計摘要")
        
        # 取得所有可用月份並排序 (最新的在最上面)
        available_months = sorted(spending_df["月份(年-月)"].unique().tolist(), reverse=True)
        
        # 新增下拉選單，讓使用者選擇要看總計還是特定月份
        selected_period = st.selectbox("📅 選擇統計區間", ["歷史所有紀錄"] + available_months)
        
        st.divider()
        
        # 根據選擇的區間過濾資料
        if selected_period == "歷史所有紀錄":
            filtered_df = spending_df
            total_spending = filtered_df["消費總額"].sum()
            
            st.metric(label="💰 歷史所有信用卡總花費", value=f"${total_spending:,} TWD")
            st.markdown("**💳 各信用卡歷史每月平均花費：**")
            
            # 計算平均
            card_stats = filtered_df.groupby("銀行名稱")["消費總額"].mean().round(0).astype(int).reset_index(name="金額")
            suffix = " /月"
        else:
            filtered_df = spending_df[spending_df["月份(年-月)"] == selected_period]
            total_spending = filtered_df["消費總額"].sum()
            
            st.metric(label=f"💰 {selected_period} 信用卡總花費", value=f"${total_spending:,} TWD")
            st.markdown(f"**💳 {selected_period} 各信用卡總花費：**")
            
            # 計算該月總和
            card_stats = filtered_df.groupby("銀行名稱")["消費總額"].sum().round(0).astype(int).reset_index(name="金額")
            suffix = ""
            
        # 優化排版：固定每行最多顯示 4 個數據卡片，避免過擠導致文字被截斷 (...)
        MAX_COLS_PER_ROW = 4
        # 將卡片資料分批，每批 4 個
        for i in range(0, len(card_stats), MAX_COLS_PER_ROW):
            cols = st.columns(MAX_COLS_PER_ROW)
            chunk = card_stats.iloc[i:i+MAX_COLS_PER_ROW]
            for j, (_, row) in enumerate(chunk.iterrows()):
                with cols[j]:
                    st.metric(label=row['銀行名稱'], value=f"${row['金額']:,}{suffix}")
                
        st.divider()

        # --- 花費趨勢圖 (圖表化) ---
        st.subheader("📈 信用卡花費趨勢圖")
        
        # 將資料依據時間排序供圖表使用
        plot_df = spending_df.sort_values("月份(年-月)")

        # 使用 Plotly 繪製互動式折線圖
        fig = px.line(
            plot_df, 
            x="月份(年-月)", 
            y="消費總額", 
            color="銀行名稱",
            markers=True,
            title="各銀行每月消費趨勢",
            labels={"消費總額": "金額 (TWD)", "月份(年-月)": "月份"}
        )
        # 強制設定為白底，並加上淺灰色網格線輔助閱讀
        fig.update_layout(
            plot_bgcolor="white",       
            paper_bgcolor="white",      
            font=dict(color="black"),   
            hovermode="x unified"
        )
        
        # 確保 X 軸為文字類別，不會出現細微的時間刻度
        fig.update_xaxes(type="category", showgrid=True, gridwidth=1, gridcolor="#E5E5E5")
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#E5E5E5")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 顯示原始數據表格
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
                    st.toast(f"已更新 {bank} {year}年{month}月的紀錄！")
                else:
                    new_record = pd.DataFrame([{
                        "年份": year, 
                        "月份": month, 
                        "銀行名稱": bank, 
                        "消費總額": amount, 
                        "已繳款": is_paid
                    }])
                    spending_df = pd.concat([spending_df, new_record], ignore_index=True)
                    st.toast("新增紀錄成功！")
                
                save_data(spending_df, SPENDING_FILE)
                st.rerun()
                
        # 快速切換繳款狀態區塊
        st.divider()
        st.subheader("💡 快速標記繳款狀態")
        spending_df["Ref已繳款"] = spending_df["已繳款"].astype(bool)
        unpaid_list = spending_df[spending_df["Ref已繳款"] == False]
        if not unpaid_list.empty:
            for index, row in unpaid_list.iterrows():
                col_info, col_btn = st.columns([4, 1])
                with col_info:
                    st.write(f"**{row['銀行名稱']}** - {row['年份']}/{row['月份']} (金額: ${row['消費總額']:,})")
                with col_btn:
                    if st.button("標記已繳", key=f"pay_{index}"):
                        spending_df.at[index, "已繳款"] = True
                        if "Ref已繳款" in spending_df.columns:
                            spending_df = spending_df.drop(columns=["Ref已繳款"])
                        save_data(spending_df, SPENDING_FILE)
                        st.rerun()
        else:
            st.write("目前沒有待繳帳單。")

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
                st.toast(f"已更新 {bank_name} 的資訊！")
            else:
                new_card = pd.DataFrame([{"銀行名稱": bank_name, "結帳日": statement_day, "繳款日": due_day}])
                cards_df = pd.concat([cards_df, new_card], ignore_index=True)
                st.toast(f"成功新增 {bank_name}！")
            
            save_data(cards_df, CARDS_FILE)
            st.rerun()

    st.divider()
    st.subheader("目前的信用卡清單")
    if not cards_df.empty:
        st.table(cards_df)
        
        delete_bank = st.selectbox("選擇要移除的信用卡", ["(不進行操作)"] + cards_df["銀行名稱"].tolist())
        if st.button("🗑️ 移除此信用卡") and delete_bank != "(不進行操作)":
            cards_df = cards_df[cards_df["銀行名稱"] != delete_bank]
            save_data(cards_df, CARDS_FILE)
            st.success(f"已移除 {delete_bank}！")
            st.rerun()
    else:
        st.info("目前尚未建立任何信用卡資訊。")