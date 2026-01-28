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
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        color: #2C3E50 !important;
        height: 42px !important;
        box-shadow: none !important;
    }
    
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"]:focus {
        border-color: #CFAA5E !important;
    }

    /* --- 4. FORM & TABLE CONTAINERS --- */
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02) !important;
    }
    
    /* Style Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #F0F0F0 !important;
        border-radius: 8px !important;
    }

    /* --- 5. MODERN BUTTONS --- */
    .stButton>button {
        background-color: #FFFFFF !important;
        color: #444444 !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        height: 40px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    
    button[kind="secondaryFormSubmit"] {
        background-color: #2C3E50 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    
    .stButton>button:hover {
        border-color: #CFAA5E !important;
        color: #CFAA5E !important;
    }

    /* --- 6. DASHBOARD METRICS --- */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        padding: 1rem !important;
        border-radius: 10px !important;
        text-align: center;
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

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==========================================
# 3. AUTHENTICATION CHECK
# ==========================================
if 'logged_in' not in st.session_state:
    params = st.query_params
    u, t = params.get("user"), params.get("token")
    if u and t and check_token(u, t):
        set_login_session(u, "Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

# ==========================================
# 4. LOGIN INTERFACE
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("<br><br><h2 style='text-align: center; color: #2C3E50; font-weight: 300;'>EXPO ASSET MANAGER</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        t1, t2 = st.tabs(["Technician Portal", "System Administrator"])
        with t1:
            with st.form("t_login"):
                user = st.text_input("Username")
                pin = st.text_input("Access PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    ws_u = get_worksheet("Users")
                    if ws_u and any(str(r['Username'])==user and str(r['PIN'])==pin for r in ws_u.get_all_records()):
                        set_login_session(user, "Technician")
                        st.rerun()
                    else: st.error("Invalid Username or PIN")
        with t2:
            with st.form("a_login"):
                pw = st.text_input("Admin Password", type="password")
                if st.form_submit_button("ADMIN LOGIN"):
                    if pw == ADMIN_PASSWORD:
                        set_login_session("Administrator", "Admin")
                        st.rerun()
                    else: st.error("Access Denied")

# ==========================================
# 5. MAIN APPLICATION
# ==========================================
else:
    # Ensure local data is loaded
    if 'inventory_df' not in st.session_state:
        st.session_state['inventory_df'] = load_data_initial()
    
    df = st.session_state['inventory_df']
    ws_inv = get_worksheet("Sheet1")

    # --- TOP MENU BAR ---
    c_menu, c_info, c_btn = st.columns([4, 2, 1.2])
    with c_menu:
        if st.session_state['role'] == "Admin":
            nav = st.selectbox("", ["📈 Dashboard", "👥 Users Manager", "🛠️ Asset Control", "📦 Database View"], label_visibility="collapsed")
        else:
            nav = st.selectbox("", ["🚀 Issue Asset", "📥 Return Asset", "➕ Add Asset", "🎒 My Inventory"], label_visibility="collapsed")
    
    with c_info:
        st.markdown(f"<p style='text-align:right; margin-top:8px;'><b>{st.session_state['user']}</b> ({st.session_state['role']})</p>", unsafe_allow_html=True)
    
    with c_btn:
        cb1, cb2 = st.columns(2)
        if cb1.button("🔄", help="Sync Data"): 
            st.session_state['inventory_df'] = load_data_initial()
            st.rerun()
        if cb2.button("🚪", help="Logout"): 
            clear_login_session()
            st.rerun()

    st.markdown("---")

    # ==========================================
    # ADMIN PAGES
    # ==========================================
    if nav == "📈 Dashboard":
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Assets", len(df))
        c2.metric("Available", len(df[df['CONDITION'].str.contains('Available', na=False)]))
        c3.metric("Issued", len(df[df['CONDITION']=='Issued']))
        
        models = sorted(df['MODEL'].unique())
        if models:
            cols = st.columns(3)
            for i, m in enumerate(models):
                sub = df[df['MODEL'] == m]
                with cols[i % 3]:
                    st.markdown(f"<p style='text-align:center; margin-bottom:-10px;'><b>{m}</b></p>", unsafe_allow_html=True)
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig.update_layout(showlegend=False, height=160, margin=dict(t=20,b=20,l=0,r=0))
                    st.plotly_chart(fig, use_container_width=True, key=f"ch_{i}")
        else: st.info("No data available for charts.")

    elif nav == "👥 Users Manager":
        st.markdown("### User Management")
        ws_u = get_worksheet("Users")
        if ws_u:
            users_df = pd.DataFrame(ws_u.get_all_records())
            st.dataframe(users_df, use_container_width=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                with st.form("add_user_form"):
                    st.markdown("**Add New Technician**")
                    new_u = st.text_input("Username")
                    new_p = st.text_input("PIN (Numbers only)")
                    new_perm = st.selectbox("Permissions", ["Standard", "Bulk_Allowed"])
                    if st.form_submit_button("CREATE USER"):
                        if new_u and new_p:
                            ws_u.append_row([new_u, new_p, new_perm])
                            st.success(f"User {new_u} added!")
                            time.sleep(1); st.rerun()
            with col_b:
                st.markdown("**Delete User**")
                target = st.selectbox("Select User to Remove", users_df['Username'].tolist() if not users_df.empty else ["None"])
                if st.button("CONFIRM DELETE PERMANENTLY") and target != "None":
                    cell = ws_u.find(target)
                    ws_u.delete_rows(cell.row)
                    st.success("User deleted")
                    time.sleep(1); st.rerun()

    elif nav == "🛠️ Asset Control":
        st.markdown("### Master Asset Control")
        with st.form("admin_add_asset"):
            c1, c2, c3 = st.columns(3)
            atype = c1.text_input("Asset Type")
            brand = c2.text_input("Brand")
            model = c3.text_input("Model Number")
            serial = c1.text_input("Serial Number")
            mac = c2.text_input("MAC Address")
            loc = c3.selectbox("Storage Location", FIXED_STORES)
            if st.form_submit_button("REGISTER ASSET"):
                if serial:
                    row = [atype, brand, model, serial, mac, "Available/New", loc, "", "", get_timestamp(), "ADMIN"]
                    ws_inv.append_row(row)
                    st.success("Asset added to database")
                    st.session_state['inventory_df'] = load_data_initial()
                    time.sleep(1); st.rerun()
                else: st.error("Serial Number is required")

    elif nav == "📦 Database View":
        st.markdown("### Complete Inventory Database")
        st.dataframe(df, use_container_width=True)

    # ==========================================
    # TECHNICIAN PAGES
    # ==========================================
    elif nav == "🚀 Issue Asset":
        st.markdown("### Asset Issuance")
        with st.form("issue_form"):
            sn = st.text_input("Scan/Type Serial Number")
            tkt = st.text_input("Helpdesk Ticket #")
            if st.form_submit_button("VALIDATE & ISSUE"):
                idx = df.index[df['SERIAL'].astype(str).str.upper() == sn.strip().upper()]
                if not idx.empty:
                    row_num = int(idx[0]) + 2
                    if "Available" in df.iloc[int(idx[0])]['CONDITION']:
                        ws_inv.update_cell(row_num, 6, "Issued")
                        ws_inv.update_cell(row_num, 8, st.session_state['user'])
                        ws_inv.update_cell(row_num, 9, tkt)
                        st.success(f"Asset {sn} issued to {st.session_state['user']}")
                        st.session_state['inventory_df'] = load_data_initial()
                        time.sleep(1); st.rerun()
                    else: st.warning("Asset is not available for issuance")
                else: st.error("Serial number not found in database")

    elif nav == "📥 Return Asset":
        st.markdown("### Asset Return")
        my_assets = df[(df['ISSUED TO'] == st.session_state['user']) & (df['CONDITION'] == 'Issued')]
        if not my_assets.empty:
            sel_sn = st.selectbox("Select Asset to Return", my_assets['SERIAL'].tolist())
            with st.form("return_form"):
                new_cond = st.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                new_loc = st.selectbox("Storage Location", FIXED_STORES)
                if st.form_submit_button("PROCESS RETURN"):
                    idx = df.index[df['SERIAL'] == sel_sn]
                    row_num = int(idx[0]) + 2
                    ws_inv.update_cell(row_num, 6, new_cond)
                    ws_inv.update_cell(row_num, 7, new_loc)
                    ws_inv.update_cell(row_num, 8, "")
                    st.success("Return processed")
                    st.session_state['inventory_df'] = load_data_initial()
                    time.sleep(1); st.rerun()
        else: st.info("You have no assets currently issued.")

    elif nav == "➕ Add Asset":
        st.markdown("### Quick Asset Entry")
        with st.form("quick_add"):
            c1, c2 = st.columns(2)
            q_type = c1.selectbox("Type", ["Camera", "Laptop", "Reader"])
            q_brand = c1.text_input("Brand")
            q_model = c2.text_input("Model")
            q_sn = c2.text_input("Serial")
            if st.form_submit_button("ADD TO SYSTEM"):
                row = [q_type, q_brand, q_model, q_sn, "", "Available/New", FIXED_STORES[0], "", "", get_timestamp(), st.session_state['user']]
                ws_inv.append_row(row)
                st.success("Quick Add Complete")
                st.session_state['inventory_df'] = load_data_initial()
                time.sleep(1); st.rerun()

    elif nav == "🎒 My Inventory":
        st.markdown("### My Current Assets")
        st.dataframe(df[df['ISSUED TO'] == st.session_state['user']], use_container_width=True)
