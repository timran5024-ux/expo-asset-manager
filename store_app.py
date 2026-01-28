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
from io import BytesIO

# ==========================================
# 1. PERMANENT SIDEBAR & EXECUTIVE UI (V176)
# ==========================================
st.set_page_config(
    page_title="Asset Management Pro", 
    layout="wide", 
    initial_sidebar_state="expanded" # Force it open
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
    /* LOCK SIDEBAR OPEN AND REMOVE HIDE BUTTON */
    [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}

    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(25px);
        border-right: 1px solid rgba(197, 160, 89, 0.3);
        width: 280px !important;
    }}

    .exec-card {{
        background: rgba(255, 255, 255, 0.94) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 16px; padding: 25px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.05); margin-bottom: 25px;
        text-align: center;
    }}

    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-bottom: 10px; }}
    .hw-count {{ font-size: 14px; font-weight: 700; color: #111827; margin: 3px 0; text-align: left; }}
    .metric-value {{ font-size: 38px; font-weight: 900; }}

    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 10px !important; height: 52px !important;
        border: none !important; font-weight: 700 !important;
        width: 100%;
    }}
    div.stButton > button p {{ color: white !important; font-size: 16px; font-weight: 800; }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. DATA UTILITIES
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
            p = st.text_input("Password", type="password")
            if st.form_submit_button("SIGN IN"):
                if mode == "Admin" and p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- LOAD FRESH DATA ---
    ws_inv = get_ws("Sheet1")
    df = pd.DataFrame(ws_inv.get_all_records())

    # --- SIDEBAR (FIXED) ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.markdown(f"### USER: **{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET"]
        nav = st.radio("Navigation", menu, key="nav_radio")
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        if st.button("Logout System"): st.session_state.clear(); st.rerun()

    # --- ROUTING ---
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
                <p class="metric-title">Security Inventory</p>
                <p class="hw-count">📹 Cameras: {c_cam}</p>
                <p class="hw-count">💳 Readers: {c_rdr}</p>
                <p class="hw-count">🖥️ Panels: {c_pnl}</p>
                <p class="hw-count">🧲 Mag Locks: {c_lck}</p>
            </div>""", unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{used}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        clr_map = {"Available/New": "#28A745", "Available/Used": "#FFD700", "Faulty": "#DC3545", "Issued": "#6C757D"}
        fig = px.pie(df, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=clr_map)
        fig.update_layout(showlegend=True, height=450, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.dataframe(udf, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("add_u"):
                st.write("**Register Technician**")
                un, up = st.text_input("Name"), st.text_input("PIN")
                if st.form_submit_button("CREATE"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("User Added"); time.sleep(1); st.rerun()
        with c2:
            if not udf.empty:
                st.write("**Manage Access**")
                target = st.selectbox("Select User", udf['Username'].tolist())
                if st.button("DELETE USER"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("Removed"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        q = st.text_input("🔍 Global Search")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
