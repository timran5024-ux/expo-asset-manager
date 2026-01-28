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
# 1. VISION PRO GLASS ENGINE (V160)
# ==========================================
st.set_page_config(
    page_title="Asset Management Pro", 
    layout="wide", 
    initial_sidebar_state="expanded" # SIDEBAR NOW SHOWS BY DEFAULT
)

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
            background: rgba(248, 250, 252, 0.95); 
            backdrop-filter: blur(12px);
            z-index: -1;
        }}
        """
    except: pass

st.markdown(f"""
<style>
    {bg_css}
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}

    /* MODERN FROSTED SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.8) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(0, 82, 204, 0.1);
    }}
    
    section[data-testid="stSidebar"] * {{
        color: #111827 !important;
        font-weight: 700 !important;
    }}

    /* ELITE GLASS CARD SYSTEM */
    .glass-card {{
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0;
        border-radius: 24px;
        padding: 40px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05);
        margin-bottom: 30px;
    }}

    /* INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        border: 2.5px solid #E2E8F0 !important;
        border-radius: 12px !important;
        height: 52px !important;
        font-weight: 700 !important;
        color: #000000 !important;
    }}

    /* GLOWING BLACK BUTTONS */
    div.stButton > button {{
        background: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 14px !important;
        height: 56px !important;
        border: none !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2) !important;
        width: 100% !important;
    }}
    
    /* FORCED WHITE TEXT ON BUTTONS */
    div.stButton > button p, div.stButton > button span, div.stButton > button div {{
        color: #FFFFFF !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        text-transform: uppercase;
    }}

    .main-header {{
        font-size: 42px; font-weight: 900; color: #111827;
        margin-bottom: 10px; letter-spacing: -1px; text-align: center;
    }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v160_high_end"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. CORE UTILITIES
# ==========================================
def make_token(u): return hashlib.sha256(f"{u}{SESSION_SECRET}".encode()).hexdigest()

@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
    except: return None

def get_ws(name):
    sh = get_client().open_by_key(SHEET_ID)
    try: return sh.worksheet(name)
    except: return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    vals = ws.get_all_values()
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()

# ==========================================
# 3. AUTHENTICATION PORTAL
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown('<br><br>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">ASSET MANAGEMENT PRO</div>', unsafe_allow_html=True)
    c1, mid, c3 = st.columns([1, 1.8, 1])
    with mid:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        mode = st.radio("GATEWAY", ["TECHNICIAN", "ADMINISTRATOR"], horizontal=True)
        with st.form("gate_form"):
            if mode == "TECHNICIAN":
                u = st.text_input("Username")
                p = st.text_input("PIN Code", type="password")
                if st.form_submit_button("LOGIN SYSTEM"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Denied")
            else:
                p = st.text_input("Master Password", type="password")
                if st.form_submit_button("ADMIN ACCESS"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.rerun()
                    else: st.error("Invalid")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']

    # SIDEBAR NAVIGATION
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png")
        st.title("ASSET PRO")
        st.write(f"USER: **{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.radio("NAVIGATION", menu)
        st.markdown('<br>' * 8, unsafe_allow_html=True)
        if st.button("LOGOUT", use_container_width=True):
            st.session_state.clear(); st.rerun()

    # CONTENT
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
                    fig = px.pie(sub, names='CONDITION', hole=0.6, color_discrete_sequence=px.colors.qualitative.Bold)
                    fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"v160_{model}_{i}")
            st.markdown('</div>', unsafe_allow_html=True)

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Add Asset", "Modify", "Delete"])
        with t1:
            with st.form("add_f"):
                at, br, md = st.columns(3)
                at_v = at.text_input("Type")
                br_v = br.text_input("Brand")
                md_v = md.text_input("Model")
                sn_v = st.text_input("Serial Number")
                if st.form_submit_button("REGISTER TO STORE"):
                    get_ws("Sheet1").append_row([at_v, br_v, md_v, sn_v, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Successfully Registered!"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
