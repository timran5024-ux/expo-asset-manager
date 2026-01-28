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
# 1. EXECUTIVE SECURITY THEME (V167)
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

    /* EXECUTIVE FROSTED SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(25px);
        border-right: 1px solid rgba(197, 160, 89, 0.3);
    }}

    /* GLASS CONTENT CARDS */
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

    /* BLACK BUTTONS */
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
SESSION_SECRET = "expo_final_v167_hardware"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. CORE ENGINE
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
    vals = ws.get_all_values()
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()

# ==========================================
# 3. INTERFACE & NAVIGATION
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # Standard Login logic...
    st.rerun()
else:
    df = load_data()
    
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.markdown(f"**{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET"]
        nav = st.radio("Menu", menu)
        if st.button("Logout System", use_container_width=True): st.session_state.clear(); st.rerun()

    if nav == "DASHBOARD":
        # HARDWARE COUNT LOGIC
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
                <p class="metric-title">Security Hardware Summary</p>
                <p class="hw-count">📹 Cameras: {c_cam}</p>
                <p class="hw-count">💳 Card Readers: {c_rdr}</p>
                <p class="hw-count">🖥️ Access Panels: {c_pnl}</p>
                <p class="hw-count">🧲 Mag Locks: {c_lck}</p>
            </div>""", unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{used}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Total Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)

        # PIE CHART WITH EXACT COLOR MAPPING
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.markdown("### Global Condition Breakdown")
        clr_map = {{
            "Available/New": "#28A745", # Green
            "Available/Used": "#FFD700", # Yellow
            "Faulty": "#DC3545", # Red
            "Issued": "#6C757D" # Grey
        }}
        fig = px.pie(df, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=clr_map)
        fig.update_layout(showlegend=True, height=450, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True, key="v167_security_pie")
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.dataframe(udf, use_container_width=True)
        u1, u2 = st.columns(2)
        with u1:
            with st.form("u_new"):
                un, up = st.text_input("New Technician"), st.text_input("PIN")
                if st.form_submit_button("CREATE ACCOUNT"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("Account Created"); st.rerun()
        with u2:
            target = st.selectbox("Update Access", udf['Username'].tolist() if not udf.empty else ["-"])
            new_perm = st.selectbox("Permission Level", ["Standard", "Bulk_Allowed"])
            if st.button("SAVE PERMISSION"):
                cell = ws_u.find(target)
                ws_u.update_cell(cell.row, 3, new_perm)
                st.success("Updated")
        st.markdown('</div>', unsafe_allow_html=True)
