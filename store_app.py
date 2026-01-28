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
# 1. EXECUTIVE UI ARCHITECTURE (V165)
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

    /* FROSTED SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(25px);
        border-right: 1px solid rgba(197, 160, 89, 0.3);
    }}

    /* GLASS CARDS */
    .exec-card {{
        background: rgba(255, 255, 255, 0.94) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 16px; padding: 25px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.05); margin-bottom: 25px;
        text-align: center;
    }}

    .metric-title {{ font-size: 14px; font-weight: 700; color: #6B7280; text-transform: uppercase; }}
    .metric-value {{ font-size: 36px; font-weight: 900; }}

    /* BUTTONS */
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
SESSION_SECRET = "expo_final_v165_full"

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
# 3. AUTHENTICATION & NAV
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        st.markdown("### Executive Sign-In")
        portal = st.radio("Access Node", ["Technician", "Admin"], horizontal=True, label_visibility="collapsed")
        with st.form("auth"):
            u = st.text_input("Username") if portal == "Technician" else "Administrator"
            p = st.text_input("Access PIN" if portal == "Technician" else "Master Password", type="password")
            if st.form_submit_button("Sign In"):
                if portal == "Admin" and p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
                elif portal == "Technician":
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    df = load_data()
    ws_inv = get_ws("Sheet1")

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.markdown(f"**{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET"]
        nav = st.radio("Menu", menu)
        if st.button("Logout System", use_container_width=True):
            st.session_state.clear(); st.rerun()

    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)

    # --- DASHBOARD ---
    if nav == "DASHBOARD":
        total = len(df)
        new = len(df[df['CONDITION'] == 'Available/New'])
        used = len(df[df['CONDITION'].str.contains('Used|Issued', na=False)])
        faulty = len(df[df['CONDITION'] == 'Faulty'])

        # Executive Metrics
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f'<div class="exec-card"><p class="metric-title">Inventory Total</p><p class="metric-value">{total}</p></div>', unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Used/Issued</p><p class="metric-value" style="color:#007BFF;">{used}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)

        # Global Condition Pie
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.markdown("### Global Condition Breakdown")
        fig_main = px.pie(df, names='CONDITION', hole=0.7, color_discrete_sequence=["#28A745", "#007BFF", "#6C757D", "#DC3545"])
        fig_main.update_layout(showlegend=True, height=350, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_main, use_container_width=True, key="main_pie")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- DATABASE ---
    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        q = st.text_input("🔍 Global Search (Serial, MAC, Model, Brand)")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- USER MANAGER ---
    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.dataframe(udf, use_container_width=True)
        
        u_t1, u_t2 = st.tabs(["Manage Accounts", "Set Permissions"])
        with u_t1:
            with st.form("u_new"):
                un, up = st.text_input("New Technician Name"), st.text_input("PIN Code")
                if st.form_submit_button("CREATE ACCOUNT"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("Account Created"); st.rerun()
        with u_t2:
            target = st.selectbox("Select User", udf['Username'].tolist() if not udf.empty else ["-"])
            new_perm = st.selectbox("New Level", ["Standard", "Bulk_Allowed"])
            if st.button("UPDATE PERMISSION"):
                cell = ws_u.find(target)
                ws_u.update_cell(cell.row, 3, new_perm)
                st.success("Permission Updated")
        st.markdown('</div>', unsafe_allow_html=True)
