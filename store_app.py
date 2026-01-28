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
# 1. ELITE GLASS GLOW UI ENGINE
# ==========================================
st.set_page_config(page_title="Asset Management Pro", layout="wide", initial_sidebar_state="collapsed")

def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Background Pattern Logic
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
            background-color: rgba(255, 255, 255, 0.97); 
            backdrop-filter: blur(15px);
            z-index: -1;
        }}
        """
    except: pass

st.markdown(f"""
<style>
    {bg_css}
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; height: 0 !important; }}
    
    /* GLOBAL TEXT OVERRIDE */
    * {{ font-weight: 700 !important; color: #111827 !important; }}

    .main .block-container {{ 
        padding: 2rem !important; 
        max-width: 100% !important; 
    }}

    /* GLASS CARD SYSTEM */
    .glass-card {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid rgba(0, 82, 204, 0.2);
        border-radius: 20px;
        padding: 35px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
        margin-bottom: 25px;
    }}

    /* PROFESSIONAL INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        border: 2px solid #E2E8F0 !important;
        border-radius: 12px !important;
        height: 52px !important;
        background: white !important;
        padding-left: 15px !important;
    }}

    /* FORCED WHITE BUTTON TEXT */
    div.stButton > button {{
        background: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        height: 55px !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    }}
    div.stButton > button p, div.stButton > button span {{
        color: white !important;
        font-weight: 800 !important;
        font-size: 16px !important;
    }}

    .centered-title {{
        text-align: center; font-size: 38px; font-weight: 900 !important; 
        color: #111827; letter-spacing: -1px; margin-bottom: 40px;
    }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v159_elite"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
HEADERS = ["ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"]

# ==========================================
# 2. CORE UTILITIES
# ==========================================
def make_token(u): return hashlib.sha256(f"{u}{SESSION_SECRET}".encode()).hexdigest()

@st.cache_resource
def get_client():
    try:
        creds = dict(st.secrets["gcp_service_account"])
        creds["private_key"] = creds["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds, SCOPE))
    except: return None

def get_ws(name):
    client = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except: return client.open_by_key(SHEET_ID).sheet1

def load_data():
    ws = get_ws("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    vals = ws.get_all_values()
    if len(vals) < 2: return pd.DataFrame(columns=HEADERS)
    return pd.DataFrame(vals[1:], columns=HEADERS)

def sync():
    st.session_state['inventory_df'] = load_data()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    return output.getvalue()

# ==========================================
# 3. AUTHENTICATION (DUAL PORTAL)
# ==========================================
if 'logged_in' not in st.session_state:
    p = st.query_params
    u, t = p.get("user"), p.get("token")
    if u and t and t == make_token(u):
        st.session_state.update(logged_in=True, user=u, role="Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown('<div class="centered-title">ASSET MANAGEMENT PRO</div>', unsafe_allow_html=True)
    c1, mid, c3 = st.columns([1, 1.8, 1])
    with mid:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        tabs = st.tabs(["TECHNICIAN", "ADMINISTRATOR"])
        with tabs[0]:
            with st.form("t_login"):
                u = st.text_input("Username")
                p = st.text_input("PIN Code", type="password")
                if st.form_submit_button("SIGN IN"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.query_params.update(user=u, token=make_token(u))
                        st.rerun()
                    else: st.error("Access Denied")
        with tabs[1]:
            with st.form("a_log"):
                p = st.text_input("Master Password", type="password")
                if st.form_submit_button("ADMIN ACCESS"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.query_params.update(user="Administrator", token=make_token("Administrator"))
                        st.rerun()
                    else: st.error("Invalid")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    if 'inventory_df' not in st.session_state: sync()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    st.markdown('<div class="centered-title">Asset Management</div>', unsafe_allow_html=True)
    
    # NAVIGATION
    h_nav, h_user, h_sync, h_out = st.columns([4, 2, 1, 1])
    with h_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    with h_user: st.markdown(f'<div style="text-align:right; font-weight:bold; padding-top:15px;">👤 {st.session_state["user"]}</div>', unsafe_allow_html=True)
    with h_sync:
        if st.button("SYNC", key="final_refresh_btn"): sync(); st.rerun()
    with h_out:
        if st.button("LOGOUT", key="final_logout_btn"): st.session_state.clear(); st.query_params.clear(); st.rerun()

    st.markdown("---")

    # --- DASHBOARD ---
    if nav == "DASHBOARD":
        if not df.empty:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.write(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.6, color_discrete_sequence=px.colors.qualitative.Prism)
                    fig.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"v159_{model}_{i}")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ASSET CONTROL ---
    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        t_ctrl = st.tabs(["Add Asset", "Modify", "Delete"])
        with t_ctrl[0]:
            with st.form("add_f"):
                c1, c2, c3 = st.columns(3)
                at, br, md = c1.text_input("Type"), c2.text_input("Brand"), c3.text_input("Model")
                sn, mc = c1.text_input("Serial"), c2.text_input("MAC")
                if st.form_submit_button("REGISTER ASSET"):
                    if sn:
                        ws_inv.append_row([at, br, md, sn, mc, "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("Success!"); time.sleep(1); sync(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- DATABASE ---
    elif nav == "DATABASE":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        col_s, col_dl = st.columns([4, 1.5])
        with col_s: q = st.text_input("🔍 Search Database...")
        with col_dl: 
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("📥 DOWNLOAD EXCEL", to_excel(df), "inventory_master.xlsx", use_container_width=True)
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)

    # --- USER MANAGER ---
    elif nav == "USER MANAGER":
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.dataframe(udf, use_container_width=True)
            with st.form("u_add"):
                un, up = st.text_input("Username"), st.text_input("PIN")
                if st.form_submit_button("CREATE USER"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("Done"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
