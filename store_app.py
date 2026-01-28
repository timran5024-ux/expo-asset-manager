import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import os
import base64
from io import BytesIO
# ==========================================
# 1. PROFESSIONAL ASSET MANAGEMENT SYSTEM (V2.0)
# ==========================================
st.set_page_config(
    page_title="Asset Management Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)
def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()
bg_css = ""
if os.path.exists("logo.png"):
    try:
        bin_str = get_base64_bin("logo.png")
        bg_css = f"""
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: 600px; background-repeat: repeat; background-attachment: fixed;
        }}
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(255, 255, 255, 0.96); backdrop-filter: blur(12px); z-index: -1;
        }}
        """
    except: pass
st.markdown(f"""
<style>
    {bg_css}
    footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}
    /* PROFESSIONAL STYLING */
    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 10px !important; height: 50px !important;
        border: none !important; font-weight: 700 !important; width: 100%;
    }}
    div.stButton > button p {{ color: white !important; font-size: 15px !important; font-weight: 800 !important; }}
    .exec-card {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 12px; padding: 20px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.05); margin-bottom: 20px;
        text-align: center;
    }}
    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-bottom: 10px; }}
    .hw-count {{ font-size: 15px; font-weight: 700; color: #111827; margin: 4px 0; text-align: left; }}
    .metric-value {{ font-size: 38px; font-weight: 900; }}
    .stDataFrame {{ border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)
# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
LOGO_URL = "https://gcdn.net/wp-content/uploads/2024/11/EXPO_CITY_DUBAI_LOGO_DUAL_HORIZONTAL_YELLOW-1024x576.png"
# ==========================================
# 2. CORE UTILITIES
# ==========================================
@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
    return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
def get_ws(name):
    sh = get_client().open_by_key(SHEET_ID)
    try: return sh.worksheet(name)
    except:
        if name == "Users":
            ws = sh.add_worksheet(title="Users", rows="100", cols="5")
            ws.append_row(["Username", "PIN", "Permission"])
            return ws
        return sh.sheet1
def load_data():
    ws = get_ws("Sheet1")
    vals = ws.get_all_values()
    if len(vals) > 1:
        df = pd.DataFrame(vals[1:], columns=vals[0])
        return df
    else:
        return pd.DataFrame(columns=["ASSET TYPE", "Brand", "Model", "Serial Number", "MAC Address", "CONDITION", "Location", "Issued To", "Issued Date", "Registered Date", "Registered By"])
# ==========================================
# 3. INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.image(LOGO_URL, width=150)
        mode = st.radio("GATEWAY", ["Technician", "Admin"], horizontal=True)
        with st.form("login"):
            u = st.text_input("Username") if mode == "Technician" else "Administrator"
            p = st.text_input("PIN / Password", type="password")
            if st.form_submit_button("SIGN IN"):
                if mode == "Admin" and p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
                elif mode == "Technician":
                    ws_u = get_ws("Users")
                    recs = ws_u.get_all_records()
                    if any(str(r['Username']).strip()==u.strip() and str(r['PIN']).strip()==p.strip() for r in recs):
                        st.session_state.update(logged_in=True, user=u, role="Technician", permission=next(r['Permission'] for r in recs if r['Username']==u))
                        st.rerun()
                    else: st.error("Access Refused: Invalid Technician Credentials")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- GUARANTEED SIDEBAR ---
    with st.sidebar:
        st.markdown(f'<div style="display: flex; justify-content: center;"><img src="{LOGO_URL}" width="200"></div>', unsafe_allow_html=True)
        st.markdown(f"**USER: {st.session_state['user']}**")
        st.divider()
        if st.session_state['role'] == "Admin":
            menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"]
        else:
            menu = ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET", "DATABASE"]
        nav = st.radio("Navigation", menu)
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        if st.button("Logout"): st.session_state.clear(); st.rerun()
    
    df = load_data()
    ws_inv = get_ws("Sheet1")
   
    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)
    if nav == "DASHBOARD":
        if df.empty:
            st.info("No assets registered yet.")
        else:
            types = df['ASSET TYPE'].str.upper()
            c_cam = len(df[types.str.contains('CAMERA', na=False)])
            c_rdr = len(df[types.str.contains('READER', na=False)])
            c_pnl = len(df[types.str.contains('PANEL', na=False)])
            c_lck = len(df[types.str.contains('LOCK|MAG', na=False)])
            total_assets = len(df)
            new = len(df[df['CONDITION'] == 'Available/New'])
            used = len(df[df['CONDITION'] == 'Available/Used'])
            faulty = len(df[df['CONDITION'] == 'Faulty'])
            issued = len(df[df['CONDITION'] == 'Issued'])
           
            m1, m2, m3, m4, m5 = st.columns(5)
            with m1: st.markdown(f'<div class="exec-card"><p class="metric-title">Total Assets</p><p class="metric-value" style="color:#1F2937;">{total_assets}</p></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Available New</p><p class="metric-value" style="color:#28A745;">{new}</p></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{used}</p></div>', unsafe_allow_html=True)
            with m4: st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)
            with m5: st.markdown(f'<div class="exec-card"><p class="metric-title">Issued</p><p class="metric-value" style="color:#6C757D;">{issued}</p></div>', unsafe_allow_html=True)
           
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                st.markdown(f"""<p class="metric-title">Hardware Breakdown</p>
                    <p class="hw-count">📹 Cameras: {c_cam}</p>
                    <p class="hw-count">💳 Card Readers: {c_rdr}</p>
                    <p class="hw-count">🖥️ Access Panels: {c_pnl}</p>
                    <p class="hw-count">🧲 Mag Locks: {c_lck}</p>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                clr_map = {"Available/New": "#28A745", "Available/Used": "#FFD700", "Faulty": "#DC3545", "Issued": "#6C757D"}
                fig_pie = px.pie(df, names='CONDITION', hole=0.4, color='CONDITION', color_discrete_map=clr_map)
                fig_pie.update_layout(title="Asset Status Distribution", showlegend=True, height=400, margin=dict(t=40,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
           
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            fig_bar = px.bar(df.groupby('ASSET TYPE').size().reset_index(name='Count'), x='ASSET TYPE', y='Count', title="Assets by Type")
            fig_bar.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
           
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            st.subheader("Recently Issued Assets")
            recent_issued = df[df['CONDITION'] == 'Issued'].sort_values('Issued Date', ascending=False).head(10)
            st.dataframe(recent_issued[['ASSET TYPE', 'Serial Number', 'Issued To', 'Issued Date']], use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        if st.session_state['role'] != "Admin" and nav == "ASSET CONTROL": st.error("Access Denied"); st.stop()
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if st.session_state['role'] == "Admin":
            tabs = st.tabs(["➕ Add Asset", "📝 Modify Asset", "🚀 Issue Asset", "↩️ Return Asset", "❌ Delete Asset"])
        else:
            tabs = st.tabs(["➕ Register Asset"])
        if st.session_state['role'] == "Admin" or nav == "REGISTER ASSET":
            with tabs[0]:
                with st.form("add_asset_f"):
                    c1, c2, c3 = st.columns(3)
                    at = c1.text_input("Asset Type")
                    br = c2.text_input("Brand")
                    md = c3.text_input("Model")
                    sn = c1.text_input("Serial Number (SN)")
                    mc = c2.text_input("MAC Address")
                    lo = c3.selectbox("Location", ["MOBILITY STORE-10", "BASEMENT", "TERRA"])
                    st_v = st.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    if st.form_submit_button("REGISTER ASSET"):
                        ws_inv.append_row([at, br, md, sn, mc, st_v, lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("Asset Registered!"); time.sleep(1); st.rerun()
        if st.session_state['role'] == "Admin":
            with tabs[1]:
                sn_search = st.text_input("Enter Serial Number to Modify")
                if sn_search:
                    matching_rows = df[df['Serial Number'].str.contains(sn_search, case=False, na=False)]
                    if not matching_rows.empty:
                        row_idx = matching_rows.index[0]
                        data = df.iloc[row_idx]
                        with st.form("modify_asset"):
                            c1, c2, c3 = st.columns(3)
                            at = c1.text_input("Asset Type", value=data['ASSET TYPE'])
                            br = c2.text_input("Brand", value=data['Brand'])
                            md = c3.text_input("Model", value=data['Model'])
                            sn = c1.text_input("Serial Number (SN)", value=data['Serial Number'])
                            mc = c2.text_input("MAC Address", value=data['MAC Address'])
                            st_v = c3.selectbox("Condition", ["Available/New", "Available/Used", "Faulty", "Issued"], index=["Available/New", "Available/Used", "Faulty", "Issued"].index(data['CONDITION']) if data['CONDITION'] in ["Available/New", "Available/Used", "Faulty", "Issued"] else 0)
                            lo = c1.selectbox("Location", ["MOBILITY STORE-10", "BASEMENT", "TERRA"], index=["MOBILITY STORE-10", "BASEMENT", "TERRA"].index(data['Location']) if data['Location'] in ["MOBILITY STORE-10", "BASEMENT", "TERRA"] else 0)
                            issued_to = c2.text_input("Issued To", value=data['Issued To'])
                            issued_date = c3.date_input("Issued Date", value=datetime.strptime(data['Issued Date'], "%Y-%m-%d") if data['Issued Date'] else datetime.now())
                            if st.form_submit_button("UPDATE ASSET"):
                                row_num = row_idx + 2  # +1 for header, +1 for 1-based
                                ws_inv.update(f'A{row_num}:K{row_num}', [[at, br, md, sn, mc, st_v, lo, issued_to, issued_date.strftime("%Y-%m-%d"), data['Registered Date'], st.session_state['user']]])
                                st.success("Asset Updated!"); time.sleep(1); st.rerun()
                    else:
                        st.error("Serial Number not found.")
            with tabs[2]:
                sn_issue = st.text_input("Enter Serial Number to Issue")
                issued_to = st.text_input("Issued To")
                if st.button("ISSUE ASSET"):
                    matching_rows = df[(df['Serial Number'] == sn_issue) & (df['CONDITION'].isin(['Available/New', 'Available/Used']))]
                    if not matching_rows.empty:
                        row_idx = matching_rows.index[0]
                        row_num = row_idx + 2
                        ws_inv.update(f'F{row_num}:I{row_num}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                        st.success("Asset Issued!"); time.sleep(1); st.rerun()
                    else:
                        st.error("Asset not found or not available.")
            with tabs[3]:
                sn_return = st.text_input("Enter Serial Number to Return")
                return_status = st.selectbox("Return Condition", ["Available/Used", "Faulty"])
                if st.button("RETURN ASSET"):
                    matching_rows = df[(df['Serial Number'] == sn_return) & (df['CONDITION'] == 'Issued')]
                    if not matching_rows.empty:
                        row_idx = matching_rows.index[0]
                        row_num = row_idx + 2
                        ws_inv.update(f'F{row_num}:I{row_num}', [[return_status, "", "", ""]])
                        st.success("Asset Returned!"); time.sleep(1); st.rerun()
                    else:
                        st.error("Asset not found or not issued.")
            with tabs[4]:
                sn_del = st.text_input("Enter Serial Number to Delete")
                if st.button("DELETE ASSET"):
                    matching_rows = df[df['Serial Number'] == sn_del]
                    if not matching_rows.empty:
                        row_idx = matching_rows.index[0]
                        ws_inv.delete_rows(row_idx + 2)
                        st.success("Asset Deleted!"); time.sleep(1); st.rerun()
                    else:
                        st.error("Serial Number not found.")
        st.markdown('</div>', unsafe_allow_html=True)
    elif nav == "ISSUE ASSET":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        sn_issue = st.text_input("Enter Serial Number to Issue")
        issued_to = st.text_input("Issued To")
        if st.button("ISSUE ASSET"):
            matching_rows = df[(df['Serial Number'] == sn_issue) & (df['CONDITION'].isin(['Available/New', 'Available/Used']))]
            if not matching_rows.empty:
                row_idx = matching_rows.index[0]
                row_num = row_idx + 2
                ws_inv.update(f'F{row_num}:I{row_num}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                st.success("Asset Issued!"); time.sleep(1); st.rerun()
            else:
                st.error("Asset not found or not available.")
        st.markdown('</div>', unsafe_allow_html=True)
    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        search_term = st.text_input("Search Database (by Serial Number, Asset Type, etc.)")
        if search_term:
            filtered_df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)]
        else:
            filtered_df = df
        st.dataframe(filtered_df, use_container_width=True)
       
        # Excel Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='Assets')
        output.seek(0)
        st.download_button(
            label="Download Excel",
            data=output,
            file_name="assets.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.subheader("Personnel Directory")
        st.dataframe(udf, use_container_width=True)
       
        c1, c2 = st.columns(2)
        with c1:
            with st.form("new_tech"):
                un = st.text_input("Username")
                up = st.text_input("PIN")
                perm = st.selectbox("Permission", ["Standard", "Bulk_Allowed"])
                if st.form_submit_button("CREATE ACCOUNT"):
                    ws_u.append_row([un, up, perm])
                    st.success("User Created"); time.sleep(1); st.rerun()
        with c2:
            if not udf.empty:
                target = st.selectbox("Select User", udf['Username'].tolist())
                new_p = st.selectbox("Update Permission", ["Standard", "Bulk_Allowed"])
               
                pb1, pb2 = st.columns(2)
                if pb1.button("UPDATE PERMISSION"):
                    cell = ws_u.find(target)
                    ws_u.update_cell(cell.row, 3, new_p)
                    st.success("Updated"); time.sleep(1); st.rerun()
                if pb2.button("REVOKE ACCESS"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("Removed"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
