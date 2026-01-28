import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import hashlib

# ==========================================
# 1. PREMIUM CSS: THE WHITE & BOLD SUITE
# ==========================================
st.set_page_config(page_title="Asset Pro", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* Global Background */
    .stApp { background-color: #FFFFFF !important; }
    
    /* Hide Default Headers/Footers */
    header, footer, .stAppDeployButton, #MainMenu { visibility: hidden !important; height: 0 !important; }

    /* Input Box Perfection: Pure White with Light Grey Border */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
        color: #2C3E50 !important;
        height: 45px !important;
        font-weight: 500 !important;
    }

    /* RED LOGOUT BUTTON */
    .btn-logout button {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
        text-transform: uppercase;
    }

    /* BLUE REFRESH BUTTON */
    .btn-refresh button {
        background-color: #007BFF !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
        text-transform: uppercase;
    }

    /* Standard Dark Grey Buttons */
    .stButton>button {
        background-color: #444444 !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 8px !important;
        border: none !important;
    }

    /* Container Styling */
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        border-radius: 15px !important;
        padding: 2rem !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03) !important;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_dashboard_master_2026"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
HEADERS = ["ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"]

# ==========================================
# 2. DATA & SESSION ENGINE
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

def fetch_data():
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
    st.markdown("<br><br><h1 style='text-align: center; color: #444444; font-weight: 800;'>EXPO ASSET MANAGER</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        tabs = st.tabs(["TECHNICIAN", "ADMINISTRATOR"])
        with tabs[0]:
            with st.form("t_login"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOG IN"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.query_params.update(user=u, token=make_token(u))
                        st.rerun()
                    else: st.error("Login Error")
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
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = fetch_data()
    df = st.session_state['inventory_df']
    
    # --- HEADER / MENU ---
    col_nav, col_user, col_refresh, col_logout = st.columns([4, 2, 1, 1])
    
    with col_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET", "MY VIEW"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    
    with col_user:
        st.markdown(f"<p style='text-align:right; margin-top:8px;'><b>{st.session_state['user']}</b></p>", unsafe_allow_html=True)
    
    with col_refresh:
        st.markdown('<div class="btn-refresh">', unsafe_allow_html=True)
        if st.button("GET DATA", key="refresh_top"): 
            st.session_state['inventory_df'] = fetch_data()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_logout:
        st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
        if st.button("LOGOUT", key="logout_top"): 
            st.session_state.clear(); st.query_params.clear(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ==========================================
    # DASHBOARD LOGIC (DEEP ANALYSIS)
    # ==========================================
    if nav == "DASHBOARD":
        st.markdown("### 📊 Enterprise Dashboard")
        
        # High Level Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL STOCK", len(df))
        m2.metric("🟢 AVAILABLE", len(df[df['CONDITION'].str.contains('Available', na=False)]))
        m3.metric("🔵 ISSUED", len(df[df['CONDITION'] == 'Issued']))
        m4.metric("🔴 FAULTY", len(df[df['CONDITION'] == 'Faulty']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not df.empty:
            # PROFESSIONAL COLORS
            color_map = {
                "Available/New": "#28A745", # Emerald
                "Available/Used": "#1E7E34", # Dark Green
                "Issued": "#007BFF",         # Blue
                "Faulty": "#DC3545"          # Red
            }
            
            models = sorted(df['MODEL'].unique())
            rows = [st.columns(4) for _ in range((len(models) + 3) // 4)]
            
            for i, model in enumerate(models):
                sub_df = df[df['MODEL'] == model]
                col = rows[i // 4][i % 4]
                
                with col:
                    st.markdown(f"<p style='text-align:center; margin-bottom:-5px;'><b>{model}</b></p>", unsafe_allow_html=True)
                    fig = px.pie(
                        sub_df, 
                        names='CONDITION', 
                        hole=0.7, 
                        color='CONDITION',
                        color_discrete_map=color_map
                    )
                    fig.update_layout(
                        showlegend=False, 
                        height=160, 
                        margin=dict(t=10,b=10,l=0,r=0),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True, key=f"pchart_{i}")
        else:
            st.info("No data available to display charts.")

    # ==========================================
    # OTHER PAGES (CORE LOGIC ONLY)
    # ==========================================
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
                    st.success("DONE") # Requirement: Done written
                    time.sleep(1); st.session_state['inventory_df'] = fetch_data(); st.rerun()
                else: st.error("Missing Serial")

    elif nav == "DATABASE":
        st.markdown("### 📦 MASTER DATABASE")
        search = st.text_input("Search Assets...", placeholder="Search serial, brand, or status...")
        if search:
            f_df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
            st.dataframe(f_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

    elif nav == "USER MANAGER":
        ws_u = get_ws("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.dataframe(udf, use_container_width=True)
            ux, uy = st.columns(2)
            with ux:
                with st.form("nu"):
                    name, pin = st.text_input("New Name"), st.text_input("New PIN")
                    if st.form_submit_button("CREATE USER"):
                        ws_u.append_row([name, pin, "Standard"])
                        st.success("DONE")
                        time.sleep(1); st.rerun()
            with uy:
                target = st.selectbox("Delete Account", udf['Username'].tolist() if not udf.empty else ["-"])
                if st.button("DELETE PERMANENTLY"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("DONE")
                    time.sleep(1); st.rerun()
