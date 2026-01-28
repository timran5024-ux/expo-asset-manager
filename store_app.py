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
# 1. EXECUTIVE EXPO THEME ENGINE (V164)
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
            background: rgba(248, 250, 252, 0.96); backdrop-filter: blur(12px); z-index: -1;
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
        background: rgba(255, 255, 255, 0.92) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 16px; padding: 25px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.05); margin-bottom: 25px;
        text-align: center;
    }}

    /* METRIC COLORS */
    .metric-title {{ font-size: 14px; font-weight: 700; color: #6B7280; text-transform: uppercase; }}
    .metric-value {{ font-size: 32px; font-weight: 900; }}

    /* CORPORATE INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        border: 1.5px solid #E5E7EB !important; border-radius: 10px !important;
        height: 48px !important; background: #FFFFFF !important;
    }}

    /* EXPO BLACK BUTTONS */
    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 10px !important; height: 52px !important;
        border: none !important; font-weight: 700 !important;
    }}
    div.stButton > button p {{ color: white !important; font-size: 16px; }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v164_full"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. DATA CORE
# ==========================================
def make_token(u): return hashlib.sha256(f"{u}{SESSION_SECRET}".encode()).hexdigest()

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
# 3. LOGIN & INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        st.markdown("### System Authentication")
        portal = st.radio("Node", ["Technician", "Admin"], horizontal=True, label_visibility="collapsed")
        with st.form("auth"):
            p = st.text_input("Access PIN" if portal == "Technician" else "Master Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                if portal == "Admin" and p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
                # Technician login logic here...
        st.markdown('</div>', unsafe_allow_html=True)
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.markdown(f"**{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET"]
        nav = st.radio("Menu", menu)
        if st.button("Logout", use_container_width=True):
            st.session_state.clear(); st.rerun()

    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)

    if nav == "DASHBOARD":
        # EXECUTIVE ANALYTICS SUMMARY
        m1, m2, m3 = st.columns(3)
        total_count = len(df)
        used_count = len(df[df['CONDITION'].str.contains('Used|Issued', na=False, case=False)])
        faulty_count = len(df[df['CONDITION'].str.contains('Faulty', na=False, case=False)])

        with m1: st.markdown(f'<div class="exec-card"><p class="metric-title">Total Inventory</p><p class="metric-value" style="color:#111827;">{total_count}</p></div>', unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Used Assets</p><p class="metric-value" style="color:#007BFF;">{used_count}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{faulty_count}</p></div>', unsafe_allow_html=True)

        if not df.empty:
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            clr_map = {"Available/New": "#28A745", "Available/Used": "#007BFF", "Issued": "#6C757D", "Faulty": "#DC3545"}
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.write(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=clr_map)
                    fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"v164_{model}_{i}")
            st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        q = st.text_input("🔍 Filter Inventory (Serial, MAC, Model, Brand)")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Rest of the functions (Asset Control, User Manager) follow the same V163 logic...
