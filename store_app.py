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
# 1. CLEAN ENTERPRISE INTERFACE (V149)
# ==========================================
st.set_page_config(page_title="Asset Management Pro", layout="wide", initial_sidebar_state="collapsed")

# Simple Background Overlay Logic
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
            background-color: rgba(255, 255, 255, 0.96); z-index: -1;
        }}
        /* Ensure all text is BOLD for visibility */
        * {{ font-weight: 700 !important; }}
        .stButton>button {{ border-radius: 10px !important; height: 50px !important; font-weight: 800 !important; }}
    </style>
    """, unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v149_clean"

# ==========================================
# 2. CORE UTILITIES
# ==========================================
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
# 3. APP LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>ASSET MANAGEMENT LOGIN</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        u = st.text_input("Username")
        p = st.text_input("PIN", type="password")
        if st.button("LOGIN", use_container_width=True):
            ws_u = get_ws("Users")
            if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                st.session_state.update(logged_in=True, user=u)
                st.rerun()
            else: st.error("Invalid Login")
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    
    st.markdown(f"<h1 style='text-align: center;'>Asset Management</h1>", unsafe_allow_html=True)
    
    # Nav Bar
    nav_cols = st.columns([4, 1, 1])
    nav = nav_cols[0].selectbox("", ["DASHBOARD", "ASSET CONTROL", "DATABASE"], label_visibility="collapsed")
    if nav_cols[1].button("SYNC", use_container_width=True):
        st.session_state['inventory_df'] = load_data()
        st.rerun()
    if nav_cols[2].button("LOGOUT", use_container_width=True):
        st.session_state.clear(); st.rerun()

    if nav == "DASHBOARD":
        st.subheader("Inventory Metrics")
        if not df.empty:
            fig = px.pie(df, names='CONDITION', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("No data yet.")

    elif nav == "ASSET CONTROL":
        st.subheader("Register New Asset")
        with st.form("add_form"):
            c1, c2 = st.columns(2)
            at = c1.text_input("Type")
            sn = c2.text_input("Serial")
            if st.form_submit_button("REGISTER"):
                get_ws("Sheet1").append_row([at, "", "", sn, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                st.success("Registered!"); time.sleep(1); st.rerun()

    elif nav == "DATABASE":
        st.subheader("Master Record")
        st.dataframe(df, use_container_width=True)
