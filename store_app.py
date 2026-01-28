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
# 1. VISION PRO GLASS ENGINE
# ==========================================
st.set_page_config(page_title="Asset Pro", layout="wide", initial_sidebar_state="expanded")

def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Background logic using your logo
bg_css = ""
if os.path.exists("logo.png"):
    try:
        bin_str = get_base64_bin("logo.png")
        bg_css = f"""
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-attachment: fixed;
        }}
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(248, 250, 252, 0.94); 
            backdrop-filter: blur(10px);
            z-index: -1;
        }}
        """
    except: pass

st.markdown(f"""
<style>
    {bg_css}
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}

    /* MODERN SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.8) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(0, 82, 204, 0.1);
    }}

    /* GLASS CARD SYSTEM */
    .glass-card {{
        background: #FFFFFF !important;
        border: 1px solid rgba(0, 82, 204, 0.2);
        border-radius: 20px;
        padding: 35px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        margin-bottom: 25px;
    }}

    /* INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 12px !important;
        height: 50px !important;
        font-weight: 600 !important;
        transition: 0.3s;
    }}
    .stTextInput input:focus {{
        border-color: #0052cc !important;
        box-shadow: 0 0 0 4px rgba(0, 82, 204, 0.1) !important;
    }}

    /* GLOWING BUTTONS */
    div.stButton > button {{
        background: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        height: 52px !important;
        font-weight: 800 !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        transition: 0.3s ease;
    }}
    div.stButton > button:hover {{
        background: #1e1e1e !important;
        box-shadow: 0 8px 20px rgba(0, 82, 204, 0.3) !important;
        transform: translateY(-1px);
    }}
    div.stButton > button p {{ color: white !important; font-size: 16px; }}

    .main-header {{
        font-size: 38px; font-weight: 800; color: #111827;
        margin-bottom: 10px; letter-spacing: -1px;
    }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"

# ==========================================
# 2. CORE UTILITIES
# ==========================================
@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
    return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]))

def get_ws(name):
    sh = get_client().open_by_key(SHEET_ID)
    try: return sh.worksheet(name)
    except: return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    vals = ws.get_all_values()
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()

# ==========================================
# 3. AUTHENTICATION (GLASS PORTAL)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.8, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h1 style="text-align:center; margin-bottom:30px;">System Access</h1>', unsafe_allow_html=True)
        
        mode = st.radio("Select Portal", ["Technician", "Administrator"], horizontal=True)
        with st.form("auth_form"):
            if mode == "Technician":
                u = st.text_input("Username")
                p = st.text_input("PIN Code", type="password")
            else:
                p = st.text_input("Master Password", type="password")
            
            if st.form_submit_button("AUTHORIZE SYSTEM"):
                if mode == "Technician":
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Denied")
                elif p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. MAIN APPLICATION
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    # SIDEBAR NAVIGATION
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png")
        st.markdown(f"### Welcome, **{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.radio("System Menu", menu)
        st.markdown('<br>' * 5, unsafe_allow_html=True)
        if st.button("LOGOUT", use_container_width=True):
            st.session_state.clear(); st.rerun()

    # MAIN CONTENT
    st.markdown(f'<div class="main-header">{nav}</div>', unsafe_allow_html=True)
    
    if nav == "DASHBOARD":
        if not df.empty:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.write(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.6, color_discrete_sequence=px.colors.qualitative.G10)
                    fig.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"dash_{model}_{i}")
            st.markdown('</div>', unsafe_allow_html=True)

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        tabs = st.tabs(["Add Asset", "Modify", "Delete"])
        with tabs[0]:
            with st.form("add_asset_form"):
                at, br, md = st.columns(3)
                at_v = at.text_input("Type")
                br_v = br.text_input("Brand")
                md_v = md.text_input("Model")
                sn_v = st.text_input("Serial Number")
                if st.form_submit_button("REGISTER TO STORE"):
                    if sn_v:
                        ws_inv.append_row([at_v, br_v, md_v, sn_v, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("Asset added!"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
