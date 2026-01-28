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
# 1. ENTERPRISE UI ENGINE - SOLID & BOLD
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
            background-color: rgba(255, 255, 255, 0.97); z-index: -1;
        }}
        
        /* SOLID UI CARDS */
        .ui-card {{
            background-color: #FFFFFF !important;
            padding: 30px;
            border-radius: 15px;
            border: 2px solid #000000;
            box-shadow: 10px 10px 0px #000000;
            margin-bottom: 25px;
        }}

        /* FORCED BOLD TEXT */
        * {{ font-weight: 700 !important; color: #000000 !important; }}

        /* INPUT BOXES */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            border: 2px solid #000000 !important;
            border-radius: 8px !important;
            height: 50px !important;
        }}

        /* BUTTON FIX: WHITE TEXT ON BLACK */
        div.stButton > button {{
            background-color: #000000 !important;
            color: #FFFFFF !important;
            border: none !important;
            height: 55px !important;
            width: 100% !important;
        }}
        div.stButton > button p {{ color: white !important; font-weight: 900 !important; font-size: 18px !important; }}

        .header-title {{
            text-align: center; font-size: 40px; font-weight: 900; 
            margin-bottom: 30px; text-transform: uppercase;
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
    st.markdown('<div class="header-title">ASSET MANAGEMENT PRO</div>', unsafe_allow_html=True)
    c1, mid, c3 = st.columns([1, 1.8, 1])
    with mid:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        login_type = st.radio("SELECT PORTAL", ["TECHNICIAN", "ADMINISTRATOR"], horizontal=True)
        with st.form("login_form"):
            if login_type == "TECHNICIAN":
                u = st.text_input("Username")
                p = st.text_input("PIN Code", type="password")
            else:
                p = st.text_input("Master Password", type="password")
            
            if st.form_submit_button("SIGN IN"):
                if login_type == "TECHNICIAN":
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Denied")
                elif p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=150)
        st.title("ASSET PRO")
        st.write(f"USER: **{st.session_state['user']}**")
        st.divider()
        nav = st.radio("MENU", ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role']=="Admin" else ["DASHBOARD", "ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"])
        if st.button("LOGOUT SYSTEM"):
            st.session_state.clear()
            st.rerun()

    # --- MAIN CONTENT ---
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    st.markdown(f'<div class="header-title">{nav}</div>', unsafe_allow_html=True)

    if nav == "DASHBOARD":
        if not df.empty:
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.markdown(f'<div class="ui-card">', unsafe_allow_html=True)
                    st.write(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.6, color_discrete_sequence=px.colors.qualitative.Dark2)
                    fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0))
                    # CRITICAL FIX: Unique key per chart
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{model}_{i}")
                    st.markdown('</div>', unsafe_allow_html=True)
        else: st.info("Database is currently empty.")

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Add Asset", "Modify", "Delete"])
        with t1:
            with st.form("reg_f"):
                at, br, md = st.columns(3)
                at_val = at.text_input("Asset Type")
                br_val = br.text_input("Brand")
                md_val = md.text_input("Model")
                sn_val = st.text_input("Serial Number")
                if st.form_submit_button("REGISTER TO STORE"):
                    if sn_val:
                        ws_inv.append_row([at_val, br_val, md_val, sn_val, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("Asset added to Inventory"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="ui-card">', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
