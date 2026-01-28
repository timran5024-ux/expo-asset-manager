import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import hashlib
import os

# ==========================================
# 1. THE "ZERO-GAP" PREMIUM CSS
# ==========================================
st.set_page_config(page_title="Expo Asset Manager Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* GLOBAL THEME */
    .stApp { background-color: #FFFFFF !important; }
    header, footer, .stAppDeployButton, #MainMenu { visibility: hidden !important; height: 0 !important; }
    
    /* REMOVE ALL PADDING FROM TOP */
    .main .block-container { 
        padding-top: 0rem !important; 
        max-width: 98% !important; 
        margin-top: -30px !important;
    }

    /* LOGO POSITIONING: ABSOLUTE TOP LEFT */
    .logo-container {
        position: absolute;
        top: 10px;
        left: 0px;
        z-index: 999;
    }

    /* INPUT BOXES: PURE WHITE & LIGHT GREY BORDER */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
        height: 42px !important;
    }

    /* BOLD BLUE REFRESH BUTTON */
    button[key="final_refresh_btn"] {
        background-color: #007BFF !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 6px !important;
    }

    /* BOLD RED LOGOUT BUTTON */
    button[key="final_logout_btn"] {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 6px !important;
    }

    /* DARK GREY FORM SUBMIT BUTTONS */
    button[kind="secondaryFormSubmit"] {
        background-color: #444444 !important;
        color: white !important;
        font-weight: 800 !important;
        width: 100% !important;
        height: 45px !important;
    }

    /* ADMINISTRATOR BADGE */
    .profile-badge {
        padding: 5px 12px;
        background-color: #F8F9FA;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        font-weight: 700;
        color: #2C3E50;
        text-align: center;
    }

    /* DASHBOARD CHART CARDS */
    div[data-testid="column"] {
        background-color: #FFFFFF;
        border: 1px solid #F2F2F2;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_master_v131" 
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
HEADERS = ["ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"]

# ==========================================
# 2. DATA UTILITIES
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

def sync():
    st.session_state['inventory_df'] = load_data()

# ==========================================
# 3. AUTH LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    p = st.query_params
    u, t = p.get("user"), p.get("token")
    if u and t and t == make_token(u):
        st.session_state.update(logged_in=True, user=u, role="Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<br><br><h1 style='text-align: center; color: #2C3E50; font-weight: 800;'>EXPO ASSET MANAGER PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        tabs = st.tabs(["TECHNICIAN PORTAL", "ADMINISTRATOR"])
        with tabs[0]:
            with st.form("t_login"):
                u = st.text_input("Username")
                p = st.text_input("PIN Code", type="password")
                if st.form_submit_button("LOG IN"):
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
                    else: st.error("Incorrect Password")
else:
    if 'inventory_df' not in st.session_state: sync()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    # ==========================================
    # 4. TOP-LEFT LOGO & HEADER MENU
    # ==========================================
    # Logo forced to top-left via container
    if os.path.exists("logo.png"):
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("logo.png", width=170)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="logo-container"><h2 style="color:#CFAA5E; margin:0;">EXPO PRO</h2></div>', unsafe_allow_html=True)

    # Header Spacing for Nav and Profile
    st.markdown("<br><br>", unsafe_allow_html=True)
    h_nav, h_user, h_sync, h_out = st.columns([4, 2, 1, 1])
    
    with h_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET", "MY INVENTORY"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    
    with h_user:
        st.markdown(f'<div class="profile-badge">👤 {st.session_state["user"]}</div>', unsafe_allow_html=True)
    
    with h_sync:
        if st.button("GET DATA", key="final_refresh_btn"):
            sync(); st.rerun()
            
    with h_out:
        if st.button("LOGOUT", key="final_logout_btn"):
            st.session_state.clear(); st.query_params.clear(); st.rerun()

    st.markdown("<hr style='margin: 10px 0; border: 1px solid #F5F5F5;'>", unsafe_allow_html=True)

    # ==========================================
    # 5. INTEGRATED MODEL DASHBOARD
    # ==========================================
    if nav == "DASHBOARD":
        st.markdown("### 📊 Model Performance Analytics")
        
        # Color Map
        clr_map = {"Available/New": "#28A745", "Available/Used": "#218838", "Issued": "#007BFF", "Faulty": "#DC3545"}
        
        if not df.empty:
            models = sorted([m for m in df['MODEL'].unique() if m.strip() != ""])
            
            grid = st.columns(4)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                
                # Model Specific Counts
                tot = len(sub)
                av = len(sub[sub['CONDITION'].str.contains('Available', na=False)])
                iss = len(sub[sub['CONDITION'] == 'Issued'])
                flt = len(sub[sub['CONDITION'] == 'Faulty'])
                
                with grid[i % 4]:
                    # Info Header inside Chart Card
                    st.markdown(f"""
                    <div style='text-align:center;'>
                        <b style='font-size:16px;'>{model}</b><br>
                        <span style='font-size:12px; color:gray;'>Total: {tot}</span><br>
                        <span style='font-size:11px; color:#28A745;'>Avail: {av}</span> | 
                        <span style='font-size:11px; color:#007BFF;'>Issued: {iss}</span> | 
                        <span style='font-size:11px; color:#DC3545;'>Faulty: {flt}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    fig = px.pie(sub, names='CONDITION', hole=0.75, color='CONDITION', color_discrete_map=clr_map)
                    fig.update_layout(showlegend=False, height=160, margin=dict(t=15,b=10,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"mod_pie_{i}")
        else:
            st.info("Database is empty.")

    # ==========================================
    # 6. MANAGEMENT MODULES
    # ==========================================
    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        with st.form("reg_form_master"):
            st.markdown("#### ➕ ADD NEW INVENTORY")
            c1, c2, c3 = st.columns(3)
            at, br, md = c1.text_input("Type"), c2.text_input("Brand"), c3.text_input("Model")
            sn, mc = c1.text_input("Serial"), c2.text_input("MAC")
            lo = c3.selectbox("Store", ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT", "TERRA BASEMENT"])
            if st.form_submit_button("SAVE ASSET"):
                if sn:
                    ws_inv.append_row([at, br, md, sn, mc, "Available/New", lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("DONE")
                    time.sleep(1); sync(); st.rerun()
                else: st.error("Serial Required")

    elif nav == "DATABASE":
        st.markdown("### 📦 FULL INVENTORY")
        q = st.text_input("🔍 Filter records...")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)

    elif nav == "USER MANAGER":
        st.markdown("### 👤 ACCESS CONTROL")
        ws_u = get_ws("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.dataframe(udf, use_container_width=True)
            u1, u2 = st.columns(2)
            with u1:
                with st.form("u_add"):
                    un, up = st.text_input("Name"), st.text_input("PIN")
                    if st.form_submit_button("CREATE USER"):
                        ws_u.append_row([un, up, "Standard"])
                        st.success("DONE"); time.sleep(1); st.rerun()
            with u2:
                target = st.selectbox("Select to Remove", udf['Username'].tolist() if not udf.empty else ["-"])
                if st.button("DELETE PERMANENTLY") and target != "-":
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("DONE"); time.sleep(1); st.rerun()

    elif nav == "ISSUE ASSET":
        with st.form("iss_f_final"):
            st.markdown("### 🚀 AUTHORIZE ISSUE")
            sn, tkt = st.text_input("Serial"), st.text_input("Ticket ID")
            if st.form_submit_button("CONFIRM ISSUANCE"):
                idx = df.index[df['SERIAL'] == sn]
                if not idx.empty:
                    ws_inv.update_cell(int(idx[0])+2, 6, "Issued")
                    ws_inv.update_cell(int(idx[0])+2, 8, st.session_state['user'])
                    ws_inv.update_cell(int(idx[0])+2, 9, tkt)
                    st.success("DONE"); time.sleep(1); sync(); st.rerun()
                else: st.error("Serial not found")

    elif nav == "RETURN ASSET":
        st.markdown("### 📥 PROCESS RETURN")
        my_df = df[df['ISSUED TO'] == st.session_state['user']]
        if not my_df.empty:
            target = st.selectbox("Your Assets", my_df['SERIAL'].tolist())
            with st.form("ret_form_final"):
                cond = st.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                if st.form_submit_button("COMPLETE"):
                    ridx = int(df.index[df['SERIAL'] == target][0]) + 2
                    ws_inv.update_cell(ridx, 6, cond)
                    ws_inv.update_cell(ridx, 8, "")
                    st.success("DONE"); time.sleep(1); sync(); st.rerun()
