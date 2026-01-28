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
# 1. PRECISION UI ENGINE (CSS)
# ==========================================
st.set_page_config(page_title="Expo Asset Manager Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* GLOBAL THEME */
    .stApp { background-color: #FFFFFF !important; }
    header, footer, .stAppDeployButton, #MainMenu { visibility: hidden !important; height: 0 !important; }
    
    /* REMOVE ALL MARGINS FOR CORNER LOGO */
    .main .block-container { 
        padding-top: 0rem !important; 
        max-width: 98% !important; 
        margin-top: -45px !important;
    }

    /* ABSOLUTE CORNER LOGO POSITIONING */
    .fixed-logo {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 999999;
    }

    /* INPUT BOXES: PURE WHITE & LIGHT GREY BORDER */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        height: 42px !important;
    }

    /* BLUE REFRESH BUTTON - BOLD WHITE TEXT */
    button[key="final_refresh_btn"] {
        background-color: #007BFF !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 6px !important;
        text-transform: uppercase;
        border: none !important;
    }

    /* RED LOGOUT BUTTON - BOLD WHITE TEXT */
    button[key="final_logout_btn"] {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 6px !important;
        text-transform: uppercase;
        border: none !important;
    }

    /* DARK GREY FORM SUBMIT BUTTONS */
    button[kind="secondaryFormSubmit"] {
        background-color: #444444 !important;
        color: white !important;
        font-weight: 800 !important;
        width: 100% !important;
        height: 45px !important;
        text-transform: uppercase;
        border: none !important;
    }

    /* ADMINISTRATOR PROFILE BOX */
    .profile-box {
        padding: 5px 15px;
        background-color: #F8F9FA;
        border: 1px solid #EAEAEA;
        border-radius: 8px;
        font-weight: 700;
        color: #333;
        text-align: center;
        margin-top: 5px;
    }

    /* CHART CARD DESIGN */
    div[data-testid="column"] {
        background-color: #FFFFFF;
        border: 1px solid #F0F0F0;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_master_v132" 
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

# ==========================================
# 3. AUTH & LOGOUT
# ==========================================
if 'logged_in' not in st.session_state:
    p = st.query_params
    u, t = p.get("user"), p.get("token")
    if u and t and t == make_token(u):
        st.session_state.update(logged_in=True, user=u, role="Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<br><br><h1 style='text-align: center; color: #333; font-weight: 800;'>EXPO ASSET MANAGER PRO</h1>", unsafe_allow_html=True)
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
                    else: st.error("Access Denied")
        with tabs[1]:
            with st.form("a_log"):
                p = st.text_input("Password", type="password")
                if st.form_submit_button("ADMIN ACCESS"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.query_params.update(user="Administrator", token=make_token("Administrator"))
                        st.rerun()
                    else: st.error("Denied")
else:
    if 'inventory_df' not in st.session_state: sync()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    # ==========================================
    # 4. THE PRECISION HEADER (LOGO TOP LEFT)
    # ==========================================
    if os.path.exists("logo.png"):
        st.markdown(f'<div class="fixed-logo"><img src="data:image/png;base64,{st.secrets.get("logo_base64","")}" width="160"></div>', unsafe_allow_html=True)
        # Note: If local loading fails, use standard st.image inside the container
        st.markdown('<div class="fixed-logo">', unsafe_allow_html=True)
        st.image("logo.png", width=170)
        st.markdown('</div>', unsafe_allow_html=True)

    # Header Spacing & Navigation
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    h_nav, h_user, h_sync, h_out = st.columns([4, 2, 1, 1])
    
    with h_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET", "MY VIEW"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    
    with h_user:
        st.markdown(f'<div class="profile-box">👤 {st.session_state["user"]}</div>', unsafe_allow_html=True)
    
    with h_sync:
        if st.button("GET DATA", key="final_refresh_btn"):
            sync(); st.rerun()
            
    with h_out:
        if st.button("LOGOUT", key="final_logout_btn"):
            st.session_state.clear(); st.query_params.clear(); st.rerun()

    st.markdown("<hr style='margin: 15px 0; border: 1px solid #F8F8F8;'>", unsafe_allow_html=True)

    # ==========================================
    # 5. INTEGRATED DASHBOARD WITH IN-CHART INFO
    # ==========================================
    if nav == "DASHBOARD":
        st.markdown("### 📊 Enterprise Model Analytics")
        
        # Dashboard Color Standard
        clr_map = {"Available/New": "#28A745", "Available/Used": "#218838", "Issued": "#007BFF", "Faulty": "#DC3545"}
        
        if not df.empty:
            models = sorted([m for m in df['MODEL'].unique() if m.strip() != ""])
            
            grid = st.columns(3) # Larger charts (3 per row)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                
                # Internal Metrics Calculation
                t = len(sub)
                a = len(sub[sub['CONDITION'].str.contains('Available', na=False)])
                s = len(sub[sub['CONDITION'] == 'Issued'])
                f = len(sub[sub['CONDITION'] == 'Faulty'])
                
                with grid[i % 3]:
                    st.markdown(f"""
                    <div style='text-align:center;'>
                        <b style='font-size:18px;'>{model}</b><br>
                        <span style='font-size:13px; color:#555;'>Total Units: {t}</span><br>
                        <div style='margin-top:5px; font-size:12px;'>
                            <span style='color:#28A745; font-weight:bold;'>Available: {a}</span> | 
                            <span style='color:#007BFF; font-weight:bold;'>Issued: {s}</span> | 
                            <span style='color:#DC3545; font-weight:bold;'>Faulty: {f}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    fig = px.pie(sub, names='CONDITION', hole=0.72, color='CONDITION', color_discrete_map=clr_map)
                    fig.update_layout(showlegend=False, height=200, margin=dict(t=20,b=10,l=10,r=10), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"v132_pie_{i}")
        else:
            st.info("System Ready. Please populate data to view analytics.")

    # ==========================================
    # 6. MANAGEMENT SYSTEMS (DONE Logic)
    # ==========================================
    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        with st.form("final_reg_form"):
            st.markdown("#### ➕ ADD NEW ASSET")
            c1, c2, c3 = st.columns(3)
            atype, brand, model = c1.text_input("Type"), c2.text_input("Brand"), c3.text_input("Model")
            serial, mac = c1.text_input("Serial"), c2.text_input("MAC")
            loc = c3.selectbox("Storage", ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT", "TERRA BASEMENT"])
            if st.form_submit_button("SAVE TO SYSTEM"):
                if serial:
                    ws_inv.append_row([atype, brand, model, serial, mac, "Available/New", loc, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("DONE")
                    time.sleep(1); sync(); st.rerun()
                else: st.error("Serial Required")

    elif nav == "DATABASE":
        st.markdown("### 📦 SYSTEM MASTER RECORD")
        q = st.text_input("🔍 Global Search...")
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
                    if st.form_submit_button("CREATE TECHNICIAN"):
                        ws_u.append_row([un, up, "Standard"])
                        st.success("DONE"); time.sleep(1); st.rerun()
            with u2:
                target = st.selectbox("Remove Access", udf['Username'].tolist() if not udf.empty else ["-"])
                if st.button("DELETE ACCESS") and target != "-":
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("DONE"); time.sleep(1); st.rerun()

    elif nav == "ISSUE ASSET":
        with st.form("iss_form_v132"):
            st.markdown("### 🚀 ASSET ISSUANCE")
            sn, tkt = st.text_input("Serial"), st.text_input("Ticket #")
            if st.form_submit_button("AUTHORIZE"):
                idx = df.index[df['SERIAL'] == sn]
                if not idx.empty:
                    ws_inv.update_cell(int(idx[0])+2, 6, "Issued")
                    ws_inv.update_cell(int(idx[0])+2, 8, st.session_state['user'])
                    ws_inv.update_cell(int(idx[0])+2, 9, tkt)
                    st.success("DONE"); time.sleep(1); sync(); st.rerun()
                else: st.error("Serial not found")
