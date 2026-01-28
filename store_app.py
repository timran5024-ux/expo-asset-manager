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
# 1. ELITE UI ENGINE - GLASS & CARDS
# ==========================================
st.set_page_config(page_title="Asset Pro", layout="wide", initial_sidebar_state="expanded")

# Background logic
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
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(245, 247, 249, 0.96); z-index: -1;
        }}
        
        /* MODERN CARD WRAPPER */
        .ui-card {{
            background-color: #FFFFFF;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            border: 1px solid #E0E0E0;
            margin-bottom: 20px;
        }}

        /* BOLD INPUTS */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            border: 2px solid #333 !important;
            border-radius: 10px !important;
            height: 48px !important;
            font-weight: 600 !important;
        }}

        /* FORCED WHITE TEXT ON BLACK BUTTONS */
        div.stButton > button {{
            background-color: #000000 !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
            height: 50px !important;
            font-weight: 800 !important;
            border: none !important;
            width: 100% !important;
        }}
        div.stButton > button p {{ color: white !important; font-weight: 800 !important; }}

        .main-header {{
            text-align: center; font-size: 38px; font-weight: 900; 
            color: #111; margin-bottom: 30px; letter-spacing: -1px;
        }}
    </style>
    """, unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"

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
# 3. AUTHENTICATION
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown('<div class="main-header">ASSET MANAGEMENT PRO</div>', unsafe_allow_html=True)
    c1, mid, c3 = st.columns([1, 1.5, 1])
    with mid:
        with st.container():
            st.markdown('<div class="ui-card">', unsafe_allow_html=True)
            mode = st.radio("Access Level", ["Technician", "Administrator"], horizontal=True)
            if mode == "Technician":
                u = st.text_input("Username")
                p = st.text_input("PIN Code", type="password")
                if st.button("SIGN IN AS TECH"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
            else:
                p = st.text_input("Master Password", type="password")
                if st.button("SIGN IN AS ADMIN"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- APP SIDEBAR ---
    with st.sidebar:
        st.image("logo.png") if os.path.exists("logo.png") else st.title("ASSET PRO")
        st.write(f"Welcome, **{st.session_state['user']}**")
        st.divider()
        nav = st.radio("Navigation", ["Dashboard", "Asset Control", "Inventory DB", "User Manager"] if st.session_state['role']=="Admin" else ["Dashboard", "Issue Asset", "Return Asset", "Register Asset"])
        if st.button("Log Out"):
            st.session_state.clear()
            st.rerun()

    # --- MAIN CONTENT ---
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    st.markdown(f'<div class="main-header">{nav.upper()}</div>', unsafe_allow_html=True)

    if nav == "Dashboard":
        if not df.empty:
            st.markdown('<div class="ui-card">', unsafe_allow_html=True)
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.write(f"**{model}** ({len(sub)} units)")
                    fig = px.pie(sub, names='CONDITION', hole=0.6, color_discrete_sequence=px.colors.qualitative.Bold)
                    fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0))
                    st.plotly_chart(fig, use_container_width=True, key=f"ch_{model}_{i}")
            st.markdown('</div>', unsafe_allow_html=True)

    elif nav in ["Asset Control", "Register Asset"]:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Add Asset", "Modify", "Delete"])
        with t1:
            with st.form("add_f"):
                c1, c2 = st.columns(2)
                at = c1.text_input("Type")
                sn = c2.text_input("Serial")
                if st.form_submit_button("REGISTER ASSET"):
                    ws_inv.append_row([at, "", "", sn, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Asset added!"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif "Inventory DB" in nav:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
