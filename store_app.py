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
# 1. PARALLEL CONTROL UI ENGINE (V181)
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
    /* EXPO BLACK BUTTONS */
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
</style>
""", unsafe_allow_html=True)
# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
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
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()
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
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
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
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- GUARANTEED SIDEBAR ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=130)
        st.markdown(f"**USER: {st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ASSET CONTROL", "DATABASE"]
        nav = st.radio("Navigation", menu)
        if st.button("Logout"): st.session_state.clear(); st.rerun()
    
    df = load_data()
    ws_inv = get_ws("Sheet1")
   
    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)
    if nav == "DASHBOARD":
        types = df['ASSET TYPE'].str.upper() if not df.empty else pd.Series()
        c_cam = len(df[types.str.contains('CAMERA', na=False)])
        c_rdr = len(df[types.str.contains('READER', na=False)])
        c_pnl = len(df[types.str.contains('PANEL', na=False)])
        c_lck = len(df[types.str.contains('LOCK|MAG', na=False)])
       
        used = len(df[df['CONDITION'] == 'Available/Used'])
        faulty = len(df[df['CONDITION'] == 'Faulty'])
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""<div class="exec-card">
                <p class="metric-title">Security Summary</p>
                <p class="hw-count">📹 Cameras: {c_cam}</p>
                <p class="hw-count">💳 Card Readers: {c_rdr}</p>
                <p class="hw-count">🖥️ Access Panels: {c_pnl}</p>
                <p class="hw-count">🧲 Mag Locks: {c_lck}</p>
            </div>""", unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{used}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Total Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        clr_map = {"Available/New": "#28A745", "Available/Used": "#FFD700", "Faulty": "#DC3545", "Issued": "#6C757D"}
        fig = px.pie(df, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=clr_map)
        fig.update_layout(showlegend=True, height=450, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    # --- ASSET CONTROL (FIXED) ---
    elif nav == "ASSET CONTROL":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        tabs = st.tabs(["➕ Add Asset", "📝 Modify Info", "❌ Delete"])
        with tabs[0]:
            with st.form("add_asset_f"):
                c1, c2, c3 = st.columns(3)
                at = c1.text_input("Asset Type")
                br = c2.text_input("Brand")
                md = c3.text_input("Model")
                sn = c1.text_input("Serial Number (SN)")
                mc = c2.text_input("MAC Address")
                lo = c3.selectbox("Location", ["MOBILITY STORE-10", "BASEMENT", "TERRA"])
                st_v = st.selectbox("Status", ["Available/New", "Available/Used", "Faulty"])
                if st.form_submit_button("REGISTER ASSET"):
                    ws_inv.append_row([at, br, md, sn, mc, st_v, lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Asset Registered!"); time.sleep(1); st.rerun()
        with tabs[1]:
            sn_search = st.text_input("Enter Serial Number to Modify")
            if sn_search:
                cell = ws_inv.find(sn_search)
                if cell:
                    row_num = cell.row
                    data = ws_inv.row_values(row_num)
                    with st.form("modify_asset"):
                        c1, c2, c3 = st.columns(3)
                        at = c1.text_input("Asset Type", value=data[0])
                        br = c2.text_input("Brand", value=data[1])
                        md = c3.text_input("Model", value=data[2])
                        sn = c1.text_input("Serial Number (SN)", value=data[3])
                        mc = c2.text_input("MAC Address", value=data[4])
                        st_v = c3.selectbox("Status", ["Available/New", "Available/Used", "Faulty", "Issued"], index=["Available/New", "Available/Used", "Faulty", "Issued"].index(data[5]) if data[5] in ["Available/New", "Available/Used", "Faulty", "Issued"] else 0)
                        lo = c1.selectbox("Location", ["MOBILITY STORE-10", "BASEMENT", "TERRA"], index=["MOBILITY STORE-10", "BASEMENT", "TERRA"].index(data[6]) if data[6] in ["MOBILITY STORE-10", "BASEMENT", "TERRA"] else 0)
                        issued_to = c2.text_input("Issued To", value=data[7])
                        issued_date = c3.date_input("Issued Date", value=datetime.strptime(data[8], "%Y-%m-%d") if data[8] else datetime.now())
                        if st.form_submit_button("UPDATE ASSET"):
                            ws_inv.update(f'A{row_num}:K{row_num}', [[at, br, md, sn, mc, st_v, lo, issued_to, issued_date.strftime("%Y-%m-%d"), data[9], st.session_state['user']]])
                            st.success("Asset Updated!"); time.sleep(1); st.rerun()
                else:
                    st.error("Serial Number not found.")
        with tabs[2]:
            sn_del = st.text_input("Enter Serial Number to Delete")
            if st.button("DELETE ASSET"):
                cell = ws_inv.find(sn_del)
                if cell:
                    ws_inv.delete_rows(cell.row)
                    st.success("Asset Deleted!"); time.sleep(1); st.rerun()
                else:
                    st.error("Serial Number not found.")
        st.markdown('</div>', unsafe_allow_html=True)
    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    # --- USER MANAGER (PARALLEL BUTTONS) ---
    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.dataframe(udf, use_container_width=True)
       
        c1, c2 = st.columns(2)
        with c1:
            with st.form("new_tech"):
                un, up = st.text_input("Name"), st.text_input("PIN")
                if st.form_submit_button("CREATE ACCOUNT"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("User Created"); st.rerun()
        with c2:
            if not udf.empty:
                target = st.selectbox("Select User", udf['Username'].tolist())
                new_p = st.selectbox("Permission", ["Standard", "Bulk_Allowed"])
               
                # PARALLEL BUTTONS LOGIC
                pb1, pb2 = st.columns(2)
                if pb1.button("UPDATE PERMISSION"):
                    cell = ws_u.find(target)
                    ws_u.update_cell(cell.row, 3, new_p)
                    st.success("Updated")
                if pb2.button("REVOKE ACCESS"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("Removed"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
