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
# 1. EXECUTIVE GLASS UI ENGINE (V162)
# ==========================================
st.set_page_config(page_title="Asset Pro | Executive Edition", layout="wide", initial_sidebar_state="expanded")

def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Background logic using logo pattern
bg_css = ""
if os.path.exists("logo.png"):
    try:
        bin_str = get_base64_bin("logo.png")
        bg_css = f"""
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: 650px;
            background-repeat: repeat;
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

    /* FROSTED NAVIGATION PANE */
    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(197, 160, 89, 0.2);
    }}

    /* EXECUTIVE GLASS CARDS */
    .exec-card {{
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(197, 160, 89, 0.3);
        border-radius: 16px;
        padding: 35px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.04);
        margin-bottom: 25px;
    }}

    /* CORPORATE TYPOGRAPHY */
    * {{ font-family: 'Inter', 'Segoe UI', sans-serif !important; }}
    h1, h2, h3 {{ font-weight: 800 !important; color: #111827 !important; letter-spacing: -1px; }}

    /* EXPO-STYLE INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        border: 1.5px solid #E5E7EB !important;
        border-radius: 10px !important;
        height: 50px !important;
        background: #FFFFFF !important;
        transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .stTextInput input:focus {{
        border-color: #C5A059 !important;
        box-shadow: 0 0 0 4px rgba(197, 160, 89, 0.15) !important;
    }}

    /* BLACK EXECUTIVE BUTTONS */
    div.stButton > button {{
        background: #1A1A1A !important;
        color: #FFFFFF !important;
        border-radius: 10px !important;
        height: 54px !important;
        border: none !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }}
    div.stButton > button:hover {{
        background: #333333 !important;
        transform: translateY(-1px);
        box-shadow: 0 8px 20px rgba(197, 160, 89, 0.2) !important;
    }}
    div.stButton > button p {{ color: white !important; font-size: 16px; }}

    /* TABLE STYLING */
    [data-testid="stDataFrame"] {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #F0F0F0;
    }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v162_executive"

# ==========================================
# 2. DATA UTILITIES
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
# 3. EXECUTIVE PORTAL
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if os.path.exists("logo.png"): st.image("logo.png", width=110)
        st.markdown("### System Authentication")
        
        mode = st.radio("Access Node", ["Technician", "Admin"], horizontal=True, label_visibility="collapsed")
        with st.form("auth_gate"):
            if mode == "Technician":
                u = st.text_input("Corporate ID")
                p = st.text_input("Access PIN", type="password")
            else:
                p = st.text_input("Master Node Key", type="password")
            
            if st.form_submit_button("AUTHENTICATE"):
                if mode == "Technician":
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Refused")
                elif p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. MAIN EXECUTIVE DASHBOARD
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=130)
        st.markdown(f"**{st.session_state['user']}**")
        st.markdown("<small>Executive Portal Access</small>", unsafe_allow_html=True)
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.radio("Control Panel", menu)
        st.markdown('<br>' * 8, unsafe_allow_html=True)
        if st.button("Logout System", use_container_width=True):
            st.session_state.clear(); st.rerun()

    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)
    
    if nav == "DASHBOARD":
        if not df.empty:
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.write(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color_discrete_sequence=["#1A1A1A", "#C5A059", "#E5E7EB"])
                    fig.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"v162_{model}_{i}")
            st.markdown('</div>', unsafe_allow_html=True)

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        tabs = st.tabs(["Add Asset", "Modify Inventory", "Decommission"])
        with tabs[0]:
            with st.form("reg_new"):
                c1, c2, c3 = st.columns(3)
                at_v = c1.text_input("Asset Type")
                br_v = c2.text_input("Brand")
                md_v = c3.text_input("Model")
                sn_v = st.text_input("Serial Identification (SN)")
                if st.form_submit_button("COMMIT TO INVENTORY"):
                    if sn_v:
                        ws_inv.append_row([at_v, br_v, md_v, sn_v, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("Authorized Registration Complete"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
