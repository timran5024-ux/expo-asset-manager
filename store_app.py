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
# 1. FIXED SIDEBAR & ELITE THEME (V175)
# ==========================================
st.set_page_config(
    page_title="Asset Management Pro", 
    layout="wide", 
    initial_sidebar_state="expanded" # Force open on startup
)

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
    /* PERMANENTLY LOCK SIDEBAR - REMOVE TOGGLE BUTTON */
    button[kind="headerNoPadding"], [data-testid="collapsedControl"] {{
        display: none !important;
    }}
    
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}

    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(25px);
        border-right: 1px solid rgba(197, 160, 89, 0.3);
        min-width: 250px !important;
        width: 250px !important;
    }}

    .exec-card {{
        background: rgba(255, 255, 255, 0.94) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 16px; padding: 25px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.05); margin-bottom: 25px;
        text-align: center;
    }}

    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-bottom: 10px; }}
    .hw-count {{ font-size: 14px; font-weight: 700; color: #111827; margin: 3px 0; text-align: left; }}
    .metric-value {{ font-size: 38px; font-weight: 900; }}

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
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. CORE UTILITIES
# ==========================================
@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
    return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))

def get_ws(name):
    sh = get_client().open_by_key(SHEET_ID)
    try:
        return sh.worksheet(name)
    except:
        if name == "Users":
            new_ws = sh.add_worksheet(title="Users", rows="100", cols="5")
            new_ws.append_row(["Username", "PIN", "Permission"])
            return new_ws
        return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    vals = ws.get_all_values()
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory_Master')
    return output.getvalue()

# ==========================================
# 3. INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        mode = st.radio("LOGIN", ["Technician", "Admin"], horizontal=True)
        with st.form("login_form"):
            u = st.text_input("User ID") if mode == "Technician" else "Administrator"
            p = st.text_input("PIN / Password", type="password")
            if st.form_submit_button("SIGN IN"):
                if mode == "Admin" and p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
                elif mode == "Technician":
                    ws_u = get_ws("Users")
                    recs = ws_u.get_all_records()
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in recs):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Refused")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    df = load_data()
    
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.write(f"USER: **{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET"]
        nav = st.radio("System Menu", menu)
        st.markdown("<br>" * 8, unsafe_allow_html=True)
        if st.button("Logout System", use_container_width=True): st.session_state.clear(); st.rerun()

    # --- DASHBOARD ---
    if nav == "DASHBOARD":
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
                <p class="metric-title">Security Summary</p>
                <p class="hw-count">📹 Cameras: {c_cam}</p>
                <p class="hw-count">💳 Readers: {c_rdr}</p>
                <p class="hw-count">🖥️ Panels: {c_pnl}</p>
                <p class="hw-count">🧲 Mag Locks: {c_lck}</p>
            </div>""", unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{used}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Total Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)

        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        clr_map = {"Available/New": "#28A745", "Available/Used": "#FFD700", "Faulty": "#DC3545", "Issued": "#6C757D"}
        fig = px.pie(df, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=clr_map)
        fig.update_layout(showlegend=True, height=450, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ASSET CONTROL ---
    elif nav == "ASSET CONTROL":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Add Asset", "Modify", "Delete"])
        with t1:
            with st.form("manual_add"):
                c1, c2, c3 = st.columns(3)
                at = c1.text_input("Asset Type (Manual)")
                br = c2.text_input("Brand")
                md = c3.text_input("Model")
                sn = c1.text_input("Serial (SN)")
                mc = c2.text_input("MAC Address")
                lo = c3.selectbox("Store", ["MOBILITY STORE-10", "MOBILITY STORE-8", "BASEMENT"])
                st_val = st.selectbox("Status", ["Available/New", "Available/Used", "Faulty"])
                if st.form_submit_button("REGISTER ASSET"):
                    get_ws("Sheet1").append_row([at, br, md, sn, mc, st_val, lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Registered!"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- DATABASE ---
    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        q = st.text_input("🔍 Global Search")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- USER MANAGER (FORCE RENDER) ---
    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        user_records = ws_u.get_all_records()
        udf = pd.DataFrame(user_records) if user_records else pd.DataFrame(columns=["Username", "PIN", "Permission"])
        
        st.markdown("### Personnel Directory")
        st.dataframe(udf, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("u_new"):
                st.write("**New Technician Account**")
                un, up = st.text_input("Username"), st.text_input("PIN")
                if st.form_submit_button("CREATE"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("User Created!"); time.sleep(1); st.rerun()
        with c2:
            if not udf.empty:
                st.write("**Access Controls**")
                target = st.selectbox("Select User", udf['Username'].tolist())
                if st.button("DELETE USER"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("Deleted!"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
