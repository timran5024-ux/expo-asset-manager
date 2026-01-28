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
# 1. ELITE GLASSMORPISM & GLOW CSS
# ==========================================
st.set_page_config(page_title="Asset Pro Elite", layout="wide", initial_sidebar_state="collapsed")

# Background logic using your logo
if os.path.exists("logo.png"):
    with open("logo.png", "rb") as f:
        bin_str = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-attachment: fixed;
        }}
        
        /* 1. THE GLASS LAYER - Frosted & Opaque */
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(255, 255, 255, 0.85); /* Heavy frosting */
            backdrop-filter: blur(15px);
            z-index: -1;
        }}

        /* 2. THE GLOWING CARDS */
        [data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {{
            background: rgba(255, 255, 255, 0.9) !important;
            border-radius: 24px !important;
            border: 1px solid rgba(0, 82, 204, 0.3) !important;
            box-shadow: 0 8px 32px 0 rgba(0, 82, 204, 0.15), inset 0 0 20px rgba(255,255,255,0.5) !important;
            padding: 40px !important;
        }}

        /* 3. INPUTS - BOLD & GLOWING */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            background: white !important;
            border: 2px solid #e1e5eb !important;
            border-radius: 12px !important;
            height: 52px !important;
            font-weight: 700 !important;
            color: #111827 !important;
        }}
        .stTextInput input:focus {{
            border: 2px solid #0052cc !important;
            box-shadow: 0 0 12px rgba(0, 82, 204, 0.3) !important;
        }}

        /* 4. THE POWER BUTTON - GLOWING BLUE */
        div.stButton > button {{
            background: linear-gradient(135deg, #0052cc 0%, #003d99 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 14px !important;
            height: 58px !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            box-shadow: 0 10px 20px rgba(0, 82, 204, 0.2) !important;
            transition: 0.3s !important;
        }}
        div.stButton > button:hover {{
            box-shadow: 0 0 30px rgba(0, 82, 204, 0.5) !important;
            transform: translateY(-2px);
        }}
        div.stButton > button p {{ color: white !important; }}

        .main-title {{
            text-align: center; font-size: 42px; font-weight: 900; 
            color: #111827; letter-spacing: -1px; margin-bottom: 40px;
        }}
    </style>
    """, unsafe_allow_html=True)

# CONSTANTS & AUTH
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v156_glass"

def make_token(u): return hashlib.sha256(f"{u}{SESSION_SECRET}".encode()).hexdigest()

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
# 2. DUAL PORTAL LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown('<div class="main-title">ASSET MANAGEMENT PRO</div>', unsafe_allow_html=True)
    c1, mid, c3 = st.columns([1, 1.6, 1])
    with mid:
        portal = st.tabs(["TECHNICIAN PORTAL", "ADMINISTRATOR PORTAL"])
        with portal[0]:
            with st.form("t_login"):
                u = st.text_input("Username")
                p = st.text_input("PIN Code", type="password")
                if st.form_submit_button("AUTHORIZE ACCESS"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Denied")
        with portal[1]:
            with st.form("a_login"):
                p = st.text_input("System Master Password", type="password")
                if st.form_submit_button("ADMIN LOGIN"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.rerun()
                    else: st.error("Incorrect Password")

# ==========================================
# 3. MAIN DASHBOARD
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    st.markdown('<div class="main-title">Asset Control Dashboard</div>', unsafe_allow_html=True)
    
    # NAVIGATION
    h_nav, h_user, h_sync, h_out = st.columns([4, 2, 1, 1])
    with h_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    with h_user: st.markdown(f'<div style="text-align:right; font-weight:800; padding-top:15px;">USER: {st.session_state["user"]}</div>', unsafe_allow_html=True)
    with h_sync:
        if st.button("SYNC", key="btn_sync"):
            st.session_state['inventory_df'] = load_data()
            st.rerun()
    with h_out:
        if st.button("LOGOUT", key="btn_out"):
            st.session_state.clear(); st.rerun()

    st.markdown("---")

    if nav == "DASHBOARD":
        if not df.empty:
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.markdown(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.6, color_discrete_sequence=px.colors.qualitative.G10)
                    fig.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"pie_{model}_{i}")
