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
# 1. PREMIUM UI ENGINE (CSS)
# ==========================================
st.set_page_config(page_title="Asset Manager Pro", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* GLOBAL THEME */
    .stApp { background-color: #FFFFFF !important; }
    .main .block-container { padding-top: 1rem !important; max-width: 95% !important; }
    
    /* HIDE STREAMLIT BRANDING */
    header, footer, .stAppDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"], #MainMenu {
        display: none !important; visibility: hidden !important; height: 0 !important;
    }

    /* INPUT BOXES: WHITE WITH LIGHT GREY BORDER */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        color: #2C3E50 !important;
        height: 45px !important;
        font-weight: 500 !important;
    }

    /* FORM STYLING */
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        border-radius: 15px !important;
        padding: 2rem !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.02) !important;
    }

    /* DARK GREY ACTION BUTTONS */
    .stButton>button {
        background-color: #444444 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        height: 45px !important;
        font-weight: 800 !important; /* Bold White Text */
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #222222 !important;
        transform: translateY(-2px);
    }
    
    /* RED LOGOUT BUTTON */
    button[key="exit_btn"] {
        background-color: #FF4B4B !important;
        color: white !important;
        border: none !important;
        font-weight: 800 !important;
    }

    /* FORM SUBMIT BUTTONS (DARK GREY) */
    button[kind="secondaryFormSubmit"] {
        background-color: #444444 !important;
        color: white !important;
        font-weight: 800 !important;
        width: 100% !important;
    }

    /* METRICS */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F5F5F5 !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.01) !important;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v126" 
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

# ==========================================
# 3. AUTHENTICATION
# ==========================================
if 'logged_in' not in st.session_state:
    p = st.query_params
    u, t = p.get("user"), p.get("token")
    if u and t and t == make_token(u):
        st.session_state.update(logged_in=True, user=u, role="Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<br><br><h1 style='text-align: center; color: #444444; font-weight: 800;'>ASSET MANAGER PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        tabs = st.tabs(["TECHNICIAN ACCESS", "ADMINISTRATOR"])
        with tabs[0]:
            with st.form("t_log"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.query_params.update(user=u, token=make_token(u))
                        st.rerun()
                    else: st.error("Invalid Login")
        with tabs[1]:
            with st.form("a_log"):
                p = st.text_input("Master Password", type="password")
                if st.form_submit_button("ADMIN ACCESS"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.query_params.update(user="Administrator", token=make_token("Administrator"))
                        st.rerun()
                    else: st.error("Denied")
else:
    # DATA HANDLING
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    # --- TOP MENU BAR ---
    m1, m2, m3 = st.columns([4, 2, 1.2])
    with m1:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET", "MY VIEW"]
        nav = st.selectbox("NAV", opts, label_visibility="collapsed")
    with m2:
        st.markdown(f"<div style='text-align:right; padding-top:10px;'><b>{st.session_state['user']}</b></div>", unsafe_allow_html=True)
    with m3:
        ca1, ca2 = st.columns(2)
        if ca1.button("🔄"): 
            st.session_state['inventory_df'] = load_data()
            st.rerun()
        if ca2.button("🚪", key="exit_btn"): 
            st.session_state.clear(); st.query_params.clear(); st.rerun()

    st.divider()

    # --- PAGE LOGIC ---
    if nav == "DASHBOARD":
        c1, c2, c3 = st.columns(3)
        c1.metric("TOTAL ASSETS", len(df))
        c2.metric("🟢 AVAILABLE", len(df[df['CONDITION'].str.contains('Available', na=False)]))
        c3.metric("🔵 ISSUED", len(df[df['CONDITION'] == 'Issued']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        models = sorted(df['MODEL'].unique()) if not df.empty else []
        grid = st.columns(4)
        for i, m in enumerate(models):
            sub = df[df['MODEL'] == m]
            with grid[i % 4]:
                st.markdown(f"<p style='text-align:center; font-size:13px;'><b>{m}</b></p>", unsafe_allow_html=True)
                fig = px.pie(sub, names='CONDITION', hole=0.75, color_discrete_sequence=["#28A745", "#007BFF", "#DC3545"])
                fig.update_layout(showlegend=False, height=130, margin=dict(t=0,b=0,l=0,r=0))
                st.plotly_chart(fig, use_container_width=True, key=f"pie_{i}")

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        with st.form("reg_asset"):
            st.markdown("### ➕ REGISTER ASSET")
            col1, col2, col3 = st.columns(3)
            atype = col1.text_input("Asset Type")
            brand = col2.text_input("Brand")
            model = col3.text_input("Model")
            sn = col1.text_input("Serial Number")
            mac = col2.text_input("MAC Address")
            loc = col3.selectbox("Store Location", FIXED_STORES)
            if st.form_submit_button("SAVE TO SYSTEM"):
                if sn:
                    ws_inv.append_row([atype, brand, model, sn, mac, "Available/New", loc, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("DONE") # User Requirement: Done written
                    time.sleep(1); st.session_state['inventory_df'] = load_data(); st.rerun()
                else: st.error("Serial Required")

    elif nav == "DATABASE":
        st.markdown("### 📦 MASTER INVENTORY")
        find = st.text_input("Quick Search...", "")
        view_df = df[df.apply(lambda r: r.astype(str).str.contains(find, case=False).any(), axis=1)] if find else df
        st.dataframe(view_df, use_container_width=True)

    elif nav == "USER MANAGER":
        st.markdown("### 👤 USER ACCOUNTS")
        ws_u = get_ws("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.dataframe(udf, use_container_width=True)
            colx, coly = st.columns(2)
            with colx:
                with st.form("add_u"):
                    st.markdown("**New Access**")
                    nu, np = st.text_input("Name"), st.text_input("PIN")
                    if st.form_submit_button("CREATE"):
                        ws_u.append_row([nu, np, "Standard"])
                        st.success("DONE")
                        time.sleep(1); st.rerun()
            with coly:
                st.markdown("**Remove Access**")
                target = st.selectbox("Select User", udf['Username'].tolist() if not udf.empty else ["-"])
                if st.button("DELETE PERMANENTLY") and target != "-":
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("DONE")
                    time.sleep(1); st.rerun()

    elif nav == "ISSUE ASSET":
        with st.form("iss"):
            st.markdown("### 🚀 AUTHORIZE ISSUANCE")
            sn_in = st.text_input("Serial Number")
            tkt_in = st.text_input("Ticket ID")
            if st.form_submit_button("CONFIRM ISSUE"):
                idx = df.index[df['SERIAL'] == sn_in]
                if not idx.empty:
                    ws_inv.update_cell(int(idx[0])+2, 6, "Issued")
                    ws_inv.update_cell(int(idx[0])+2, 8, st.session_state['user'])
                    ws_inv.update_cell(int(idx[0])+2, 9, tkt_in)
                    st.success("DONE")
                    time.sleep(1); st.session_state['inventory_df'] = load_data(); st.rerun()
                else: st.error("Serial not found")

    elif nav == "RETURN ASSET":
        st.markdown("### 📥 PROCESS RETURN")
        my_items = df[df['ISSUED TO'] == st.session_state['user']]
        if not my_items.empty:
            target = st.selectbox("Your Assets", my_items['SERIAL'].tolist())
            with st.form("ret"):
                cond = st.selectbox("Status", ["Available/Used", "Faulty"])
                loc = st.selectbox("Location", FIXED_STORES)
                if st.form_submit_button("COMPLETE RETURN"):
                    ridx = int(df.index[df['SERIAL'] == target][0]) + 2
                    ws_inv.update_cell(ridx, 6, cond)
                    ws_inv.update_cell(ridx, 7, loc)
                    ws_inv.update_cell(ridx, 8, "")
                    st.success("DONE")
                    time.sleep(1); st.session_state['inventory_df'] = load_data(); st.rerun()
        else: st.info("No items in your custody.")
