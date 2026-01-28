import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import hashlib

# ==========================================
# 1. PREMIUM CSS: CORPORATE DESIGN
# ==========================================
st.set_page_config(page_title="Asset Manager Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Global White Theme */
    .stApp { background-color: #FFFFFF !important; }
    header, footer, .stAppDeployButton, #MainMenu { visibility: hidden !important; height: 0 !important; }

    /* Remove top gap completely */
    .main .block-container { padding-top: 0.5rem !important; }

    /* --- INPUT BOXES: PURE WHITE & GREY BORDER --- */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        color: #2C3E50 !important;
        height: 42px !important;
    }

    /* --- RED LOGOUT BUTTON --- */
    div.stButton > button:first-child[key*="logout"] {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 6px !important;
    }

    /* --- BLUE REFRESH BUTTON --- */
    div.stButton > button:first-child[key*="refresh"] {
        background-color: #007BFF !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 6px !important;
    }

    /* --- DARK GREY ACTION BUTTONS --- */
    .stButton>button {
        background-color: #444444 !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 6px !important;
    }

    /* User Profile Badge at Top Right */
    .user-badge {
        background-color: #f8f9fa;
        padding: 5px 15px;
        border-radius: 20px;
        border: 1px solid #E0E0E0;
        color: #444;
        font-weight: 600;
        font-size: 14px;
        text-align: center;
        margin-top: 5px;
    }

    /* Dashboard Grid Styling */
    div[data-testid="column"] {
        background-color: #FFFFFF;
        border: 1px solid #F0F0F0;
        padding: 10px;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v128" 
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
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
    sh = client.open_by_key(SHEET_ID)
    try: return sh.worksheet(name)
    except: return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    vals = ws.get_all_values()
    if len(vals) < 2: return pd.DataFrame(columns=HEADERS)
    return pd.DataFrame(vals[1:], columns=HEADERS)

# ==========================================
# 3. AUTH LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    p = st.query_params
    u, t = p.get("user"), p.get("token")
    if u and t and t == make_token(u):
        st.session_state.update(logged_in=True, user=u, role="Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

# ==========================================
# 4. LOGIN INTERFACE
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("<br><br><h1 style='text-align: center; color: #444444; font-weight: 800;'>ASSET MANAGER PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        tabs = st.tabs(["TECHNICIAN", "ADMINISTRATOR"])
        with tabs[0]:
            with st.form("t_login"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.query_params.update(user=u, token=make_token(u))
                        st.rerun()
                    else: st.error("Login Error")
        with tabs[1]:
            with st.form("a_log"):
                p = st.text_input("Master Password", type="password")
                if st.form_submit_button("ADMIN LOGIN"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.query_params.update(user="Administrator", token=make_token("Administrator"))
                        st.rerun()
                    else: st.error("Denied")

# ==========================================
# 5. MASTER APP UI
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    
    # --- PROFESSIONAL HEADER ---
    col_logo, col_nav, col_user, col_refresh, col_logout = st.columns([1.5, 3.5, 2, 1, 1])
    
    with col_logo:
        # Placeholder for Company Logo
        st.markdown("<h3 style='margin-top:0; color:#CFAA5E;'>🏢 EXPO PRO</h3>", unsafe_allow_html=True)

    with col_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET", "MY VIEW"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    
    with col_user:
        # MOVED ADMINISTRATOR NAME TO A BADGE
        st.markdown(f'<div class="user-badge">👤 {st.session_state["user"]}</div>', unsafe_allow_html=True)
    
    with col_refresh:
        if st.button("GET DATA", key="refresh_btn"): 
            st.session_state['inventory_df'] = load_data()
            st.rerun()
        
    with col_logout:
        if st.button("LOGOUT", key="logout_btn"): 
            st.session_state.clear(); st.query_params.clear(); st.rerun()

    st.markdown("<hr style='margin-top:0; border:1px solid #f0f0f0;'>", unsafe_allow_html=True)

    # --- DASHBOARD ANALYSIS ---
    if nav == "DASHBOARD":
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL ITEMS", len(df))
        m2.metric("🟢 AVAILABLE", len(df[df['CONDITION'].str.contains('Available', na=False)]))
        m3.metric("🔵 ISSUED", len(df[df['CONDITION'] == 'Issued']))
        m4.metric("🔴 FAULTY", len(df[df['CONDITION'] == 'Faulty']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Professional Color Logic
        cmap = {"Available/New": "#28A745", "Available/Used": "#218838", "Issued": "#007BFF", "Faulty": "#DC3545"}
        
        if not df.empty:
            models = sorted(df['MODEL'].unique())
            grid = st.columns(4)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with grid[i % 4]:
                    st.markdown(f"<p style='text-align:center; margin-bottom:-5px; font-size:14px;'><b>{model}</b></p>", unsafe_allow_html=True)
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=cmap)
                    fig.update_layout(showlegend=False, height=150, margin=dict(t=10,b=10,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"donut_{i}")
        else:
            st.info("No data found.")

    # --- OTHER SECTIONS ---
    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        ws_inv = get_ws("Sheet1")
        with st.form("asset_f"):
            st.markdown("#### ➕ REGISTER NEW ASSET")
            c1, c2, c3 = st.columns(3)
            at = c1.text_input("Asset Type")
            br = c2.text_input("Brand")
            md = c3.text_input("Model Number")
            sn = c1.text_input("Serial Number")
            lo = c2.selectbox("Location", FIXED_STORES)
            if st.form_submit_button("SAVE ASSET"):
                if sn:
                    ws_inv.append_row([at, br, md, sn, "", "Available/New", lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("DONE") # User feedback requirement
                    time.sleep(1); st.session_state['inventory_df'] = load_data(); st.rerun()
                else: st.error("Serial Required")

    elif nav == "DATABASE":
        st.markdown("### 📦 MASTER DATABASE")
        search = st.text_input("Quick Find...")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)] if search else df
        st.dataframe(f_df, use_container_width=True)

    elif nav == "USER MANAGER":
        ws_u = get_ws("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.table(udf)
            ux, uy = st.columns(2)
            with ux:
                with st.form("nu"):
                    un, up = st.text_input("New Name"), st.text_input("PIN")
                    if st.form_submit_button("CREATE USER"):
                        ws_u.append_row([un, up, "Standard"])
                        st.success("DONE")
                        time.sleep(1); st.rerun()
