import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from io import BytesIO
import plotly.express as px
from PIL import Image
import hashlib

# ==========================================
# 1. PURE WHITE MINIMALIST UI
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* --- 1. GLOBAL PURE WHITE BACKGROUND --- */
    .stApp {
        background-color: #FFFFFF !important;
    }
    
    .main .block-container {
        padding-top: 1.5rem !important;
        max-width: 95% !important;
    }

    /* --- 2. KILL ALL STREAMLIT BRANDING --- */
    header, footer, .stAppDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"], #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }

    /* --- 3. INPUT BOXES: PURE WHITE & LIGHT GREY BORDER --- */
    /* Targets all inputs, textareas, and dropdown containers */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        color: #2C3E50 !important;
        height: 42px !important;
        box-shadow: none !important;
    }
    
    /* Hover effect for input boxes */
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus {
        border-color: #CFAA5E !important;
    }

    /* --- 4. FORM CONTAINERS --- */
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
    }

    /* --- 5. MODERN BUTTONS --- */
    /* Standard Button Styling */
    .stButton>button {
        background-color: #FFFFFF !important;
        color: #444444 !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        height: 40px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    /* Submit/Primary Button */
    button[kind="secondaryFormSubmit"] {
        background-color: #2C3E50 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    .stButton>button:hover {
        border-color: #CFAA5E !important;
        color: #CFAA5E !important;
        transform: translateY(-1px);
    }

    /* --- 6. DASHBOARD METRICS --- */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        text-align: center;
    }
    
    /* Clean Divider */
    hr {
        margin: 1em 0 !important;
        border: 0;
        border-top: 1px solid #F5F5F5;
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
# 2. SESSION & CONNECTION
# ==========================================
def make_token(username):
    return hashlib.sha256(f"{username}{SESSION_SECRET}".encode()).hexdigest()

def check_token(username, token):
    return token == make_token(username)

def set_login_session(username, role, can_import=False):
    st.session_state['logged_in'] = True
    st.session_state['role'] = role
    st.session_state['user'] = username
    st.session_state['can_import'] = can_import
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
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except: return None

@st.cache_resource
def get_worksheet(name):
    client = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except: return sh.sheet1

def safe_add_rows(ws, rows_list):
    for row in rows_list: ws.append_row(row)

def load_data_initial():
    ws = get_worksheet("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    try:
        raw = ws.get_all_values()
        if not raw: return pd.DataFrame(columns=HEADERS)
        rows = raw[1:]
        clean_rows = [r[:len(HEADERS)] + [""]*(len(HEADERS)-len(r)) for r in rows]
        return pd.DataFrame(clean_rows, columns=HEADERS)
    except: return pd.DataFrame(columns=HEADERS)

def sync_local_state():
    if 'inventory_df' not in st.session_state:
        st.session_state['inventory_df'] = load_data_initial()

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# 3. APP LOGIC
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
                    ws = get_worksheet("Users")
                    if any(str(r['Username'])==user and str(r['PIN'])==pin for r in ws.get_all_records()):
                        set_login_session(user, "Technician")
                        st.rerun()
        with t2:
            with st.form("a_login"):
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("ADMIN LOGIN"):
                    if pw == ADMIN_PASSWORD:
                        set_login_session("Administrator", "Admin")
                        st.rerun()
else:
    sync_local_state()
    df = st.session_state['inventory_df']
    ws_inv = get_worksheet("Sheet1")

    # --- TOP CLEAN MENU ---
    c_menu, c_info, c_btn = st.columns([4, 2, 1])
    with c_menu:
        if st.session_state['role'] == "Admin":
            nav = st.selectbox("", ["📈 Dashboard", "👥 Users", "🛠️ Asset Control", "📦 Database"], label_visibility="collapsed")
        else:
            nav = st.selectbox("", ["🚀 Issue", "📥 Return", "➕ Add", "🎒 My Assets"], label_visibility="collapsed")
    
    with c_info:
        st.markdown(f"<p style='text-align:right; margin-top:8px;'>User: <b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    
    with c_btn:
        cb1, cb2 = st.columns(2)
        if cb1.button("🔄"): 
            st.session_state['inventory_df'] = load_data_initial()
            st.rerun()
        if cb2.button("🚪"): 
            clear_login_session()
            st.rerun()

    st.markdown("---")

    # --- ADMIN DASHBOARD ---
    if nav == "📈 Dashboard":
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Assets", len(df))
        c2.metric("Available", len(df[df['CONDITION'].str.contains('Available', na=False)]))
        c3.metric("Issued", len(df[df['CONDITION']=='Issued']))
        
        models = sorted(df['MODEL'].unique())
        cols = st.columns(3)
        for i, m in enumerate(models):
            sub = df[df['MODEL'] == m]
            with cols[i % 3]:
                st.markdown(f"**{m}**")
                fig = px.pie(sub, names='CONDITION', hole=0.7, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(showlegend=False, height=140, margin=dict(t=0,b=0,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True, key=f"ch_{i}")

    # --- ASSET CONTROL ---
    elif nav == "🛠️ Asset Control":
        st.markdown("#### Master Asset Control")
        with st.form("admin_add"):
            c1, c2, c3 = st.columns(3)
            atype = c1.text_input("Asset Type")
            brand = c2.text_input("Brand")
            model = c3.text_input("Model")
            serial = c1.text_input("Serial")
            mac = c2.text_input("MAC")
            loc = c3.selectbox("Location", FIXED_STORES)
            if st.form_submit_button("ADD TO DATABASE"):
                row = [atype, brand, model, serial, mac, "Available/New", loc, "", "", get_timestamp(), "ADMIN"]
                safe_add_rows(ws_inv, [row])
                st.success("Asset Registered")
                time.sleep(1); st.rerun()

    # --- DATABASE VIEW ---
    elif nav == "📦 Database":
        st.markdown("#### Full Inventory")
        st.dataframe(df, use_container_width=True)

    # --- TECHNICIAN ACTIONS ---
    elif nav == "🚀 Issue":
        with st.form("issue_f"):
            sn = st.text_input("Scan/Type Serial Number")
            tkt = st.text_input("Ticket Number")
            if st.form_submit_button("CONFIRM ISSUE"):
                idx = df.index[df['SERIAL'] == sn]
                if not idx.empty:
                    ws_inv.update_cell(int(idx[0])+2, 6, "Issued")
                    ws_inv.update_cell(int(idx[0])+2, 8, st.session_state['user'])
                    ws_inv.update_cell(int(idx[0])+2, 9, tkt)
                    st.success("Issued Successfully")
                    time.sleep(1); st.rerun()
                else: st.error("Serial not found")
