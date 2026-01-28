import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import hashlib
import os
import base64

# ==========================================
# 1. EXECUTIVE THEME ENGINE (V169)
# ==========================================
st.set_page_config(page_title="Asset Management Pro", layout="wide", initial_sidebar_state="expanded")

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
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}

    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(25px);
        border-right: 1px solid rgba(197, 160, 89, 0.3);
    }}

    .exec-card {{
        background: rgba(255, 255, 255, 0.94) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 16px; padding: 25px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.05); margin-bottom: 25px;
        text-align: center;
    }}

    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-bottom: 10px; }}
    .hw-count {{ font-size: 14px; font-weight: 700; color: #111827; margin: 3px 0; }}
    .metric-value {{ font-size: 38px; font-weight: 900; }}

    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 10px !important; height: 52px !important;
        border: none !important; font-weight: 700 !important;
    }}
    div.stButton > button p {{ color: white !important; font-size: 16px; font-weight: 800; }}
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
    except: return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    if not ws: return pd.DataFrame()
    vals = ws.get_all_values()
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()

# ==========================================
# 3. INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # Standard Sign-in Logic
    st.markdown('<br><br>', unsafe_allow_html=True)
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        mode = st.radio("GATEWAY", ["Technician", "Admin"], horizontal=True)
        with st.form("login_form"):
            u = st.text_input("Username") if mode == "Technician" else "Administrator"
            p = st.text_input("Password", type="password")
            if st.form_submit_button("SIGN IN"):
                if mode == "Admin" and p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
                # Technician logic...
        st.markdown('</div>', unsafe_allow_html=True)
else:
    df = load_data()
    ws_inv = get_ws("Sheet1")
    
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.write(f"USER: **{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET"]
        nav = st.radio("Menu", menu)
        if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

    # --- DASHBOARD ---
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
                <p class="metric-title">Security Inventory Summary</p>
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

    # --- ASSET CONTROL (FULL ADMINISTRATIVE POWER) ---
    elif nav == "ASSET CONTROL":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["➕ Add Asset", "📝 Modify Asset", "❌ Decommission"])
        
        with t1:
            with st.form("manual_add"):
                st.markdown("### Manual Asset Registration")
                c1, c2, c3 = st.columns(3)
                at = c1.selectbox("Asset Type", ["Camera", "Card Reader", "Access Control Panel", "Magnetic Lock", "Other"])
                br = c2.text_input("Brand")
                md = c3.text_input("Model Number")
                sn = c1.text_input("Serial Number (SN)")
                mc = c2.text_input("MAC Address")
                lo = c3.selectbox("Store Location", ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT", "TERRA BASEMENT"])
                stat = st.selectbox("Current Status", ["Available/New", "Available/Used", "Faulty"])
                
                if st.form_submit_button("REGISTER ASSET"):
                    if sn:
                        ws_inv.append_row([at, br, md, sn, mc, stat, lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success(f"Asset {sn} Added!"); time.sleep(1); st.rerun()
                    else: st.error("Serial Number is Required")

        with t2:
            st.markdown("### Search & Modify Existing Asset")
            s_sn = st.text_input("Enter Serial Number to Modify")
            if s_sn:
                match = df[df['SERIAL'].astype(str).str.upper() == s_sn.strip().upper()]
                if not match.empty:
                    item = match.iloc[0]
                    with st.form("mod_form"):
                        c1, c2 = st.columns(2)
                        n_br = c1.text_input("Brand", value=item['BRAND'])
                        n_md = c2.text_input("Model", value=item['MODEL'])
                        n_mc = c1.text_input("MAC Address", value=item['MAC ADDRESS'])
                        n_lo = c2.selectbox("Location", ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT", "TERRA BASEMENT"])
                        n_st = st.selectbox("Status", ["Available/New", "Available/Used", "Issued", "Faulty"])
                        if st.form_submit_button("UPDATE ASSET DATA"):
                            ridx = int(df.index[df['SERIAL'] == s_sn][0]) + 2
                            ws_inv.update_cell(ridx, 2, n_br); ws_inv.update_cell(ridx, 3, n_md)
                            ws_inv.update_cell(ridx, 5, n_mc); ws_inv.update_cell(ridx, 6, n_st); ws_inv.update_cell(ridx, 7, n_lo)
                            st.success("Asset Data Updated Successfully"); time.sleep(1); st.rerun()
                else: st.warning("Asset not found in database.")

        with t3:
            st.markdown("### Decommission Asset")
            d_sn = st.text_input("Enter Serial Number to REMOVE")
            if d_sn:
                match = df[df['SERIAL'].astype(str).str.upper() == d_sn.strip().upper()]
                if not match.empty:
                    st.error(f"WARNING: You are about to delete {match.iloc[0]['MODEL']} (SN: {d_sn})")
                    if st.button("CONFIRM PERMANENT DELETE"):
                        ws_inv.delete_rows(int(df.index[df['SERIAL'] == d_sn][0]) + 2)
                        st.success("Asset Purged from System"); time.sleep(1); st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        q = st.text_input("🔍 Global Security Asset Search")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
