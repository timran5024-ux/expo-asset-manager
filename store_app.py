import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from io import BytesIO
import plotly.express as px
import hashlib

# ==========================================
# 1. PURE WHITE PROFESSIONAL UI
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #FFFFFF !important; }
    .main .block-container { padding-top: 1.5rem !important; max-width: 95% !important; }
    header, footer, .stAppDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"], #MainMenu {
        display: none !important; visibility: hidden !important;
    }
    /* INPUT BOXES: PURE WHITE & LIGHT GREY BORDER */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        color: #2C3E50 !important;
        height: 42px !important;
    }
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
    }
    .stButton>button {
        background-color: #FFFFFF !important;
        color: #444444 !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        height: 40px !important;
        font-weight: 500 !important;
        width: 100% !important;
    }
    button[kind="secondaryFormSubmit"] {
        background-color: #2C3E50 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        padding: 1rem !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_secure_salt_2026" 
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
HEADERS = ["ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"]

# ==========================================
# 2. CORE UTILITIES
# ==========================================
def make_token(username):
    return hashlib.sha256(f"{username}{SESSION_SECRET}".encode()).hexdigest()

def check_token(username, token):
    return token == make_token(username)

def set_login_session(username, role):
    st.session_state['logged_in'] = True
    st.session_state['role'] = role
    st.session_state['user'] = username
    st.query_params["user"] = username
    st.query_params["token"] = make_token(username)

def clear_login_session():
    st.session_state['logged_in'] = False
    st.session_state.clear()
    st.query_params.clear()

@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
    except: return None

def get_worksheet(name):
    client = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except: return None

def load_data_raw():
    """Reads everything from the sheet without strict filtering to prevent 'Empty' error."""
    ws = get_worksheet("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    try:
        data = ws.get_all_records()
        if not data:
            # Fallback if records fails
            vals = ws.get_all_values()
            if len(vals) > 1:
                return pd.DataFrame(vals[1:], columns=vals[0])
            return pd.DataFrame(columns=HEADERS)
        return pd.DataFrame(data)
    except: return pd.DataFrame(columns=HEADERS)

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# 3. AUTHENTICATION
# ==========================================
if 'logged_in' not in st.session_state:
    params = st.query_params
    u, t = params.get("user"), params.get("token")
    if u and t and check_token(u, t):
        set_login_session(u, "Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<br><br><h2 style='text-align: center; color: #2C3E50;'>EXPO ASSET MANAGER</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        t1, t2 = st.tabs(["Technician", "Administrator"])
        with t1:
            with st.form("t_login"):
                user = st.text_input("Username")
                pin = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    ws_u = get_worksheet("Users")
                    if ws_u and any(str(r['Username'])==user and str(r['PIN'])==pin for r in ws_u.get_all_records()):
                        set_login_session(user, "Technician"); st.rerun()
                    else: st.error("Invalid Credentials")
        with t2:
            with st.form("a_login"):
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("ADMIN LOGIN"):
                    if pw == ADMIN_PASSWORD:
                        set_login_session("Administrator", "Admin"); st.rerun()
                    else: st.error("Access Denied")
else:
    # --- DATA SYNC ---
    if 'inventory_df' not in st.session_state:
        st.session_state['inventory_df'] = load_data_raw()
    
    df = st.session_state['inventory_df']
    ws_inv = get_worksheet("Sheet1")

    # --- TOP MENU ---
    c_menu, c_info, c_btn = st.columns([4, 2, 1.2])
    with c_menu:
        if st.session_state['role'] == "Admin":
            nav = st.selectbox("", ["📈 Dashboard", "👥 Users", "🛠️ Asset Control", "📦 Database View"], label_visibility="collapsed")
        else:
            nav = st.selectbox("", ["🚀 Issue", "📥 Return", "➕ Add", "🎒 My Assets"], label_visibility="collapsed")
    with c_info: st.markdown(f"<p style='text-align:right; margin-top:8px;'><b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    with c_btn:
        cb1, cb2 = st.columns(2)
        if cb1.button("🔄"): st.session_state['inventory_df'] = load_data_raw(); st.rerun()
        if cb2.button("🚪"): clear_login_session(); st.rerun()

    st.markdown("---")

    # ==========================================
    # PAGE LOGIC
    # ==========================================
    if nav == "📈 Dashboard":
        st.markdown("### Executive Dashboard")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Items", len(df))
            try:
                avail = len(df[df['CONDITION'].str.contains('Available', case=False, na=False)])
                issued = len(df[df['CONDITION'].str.contains('Issued', case=False, na=False)])
                c2.metric("Available", avail)
                c3.metric("Issued", issued)
            except: st.info("Check Condition column name in Google Sheet")
            
            if 'MODEL' in df.columns:
                models = sorted(df['MODEL'].unique())
                cols = st.columns(3)
                for i, m in enumerate(models):
                    sub = df[df['MODEL'] == m]
                    with cols[i % 3]:
                        st.markdown(f"**{m}**")
                        fig = px.pie(sub, names='CONDITION', hole=0.7)
                        fig.update_layout(showlegend=False, height=150, margin=dict(t=0,b=0,l=0,r=0))
                        st.plotly_chart(fig, use_container_width=True, key=f"d_{i}")
        else: st.warning("Database is empty or headers do not match.")

    elif nav == "👥 Users":
        st.markdown("### User Management")
        ws_u = get_worksheet("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.table(udf)
            with st.form("add_u"):
                u_new = st.text_input("New Username")
                p_new = st.text_input("New PIN")
                if st.form_submit_button("ADD USER"):
                    ws_u.append_row([u_new, p_new, "Standard"])
                    st.success("User Added"); time.sleep(1); st.rerun()

    elif nav == "🛠️ Asset Control":
        st.markdown("### Add New Asset")
        with st.form("ctrl_add"):
            c1, c2, c3 = st.columns(3)
            at = c1.text_input("Asset Type")
            br = c2.text_input("Brand")
            md = c3.text_input("Model")
            sn = c1.text_input("Serial Number")
            lc = c2.selectbox("Location", FIXED_STORES)
            if st.form_submit_button("SAVE ASSET"):
                ws_inv.append_row([at, br, md, sn, "", "Available/New", lc, "", "", get_timestamp(), "ADMIN"])
                st.success("Saved"); time.sleep(1); st.rerun()

    elif nav == "📦 Database View":
        st.markdown("### Full Inventory Record")
        search = st.text_input("🔍 Search Database (Serial, Model, Brand...)", "")
        if search:
            filtered_df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
