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
# 1. PURE WHITE MASTER DESIGN
# ==========================================
st.set_page_config(page_title="Asset Manager Pro", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* GLOBAL RESET */
    .stApp { background-color: #FFFFFF !important; }
    .main .block-container { padding-top: 1rem !important; max-width: 95% !important; }
    
    /* HIDE EVERYTHING STREAMLIT */
    header, footer, .stAppDeployButton, [data-testid="stDecoration"], [data-testid="stStatusWidget"], #MainMenu {
        display: none !important; visibility: hidden !important; height: 0 !important;
    }

    /* PURE WHITE BOXES WITH GREY BORDER */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input, .stTextArea textarea {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
        color: #2C3E50 !important;
        height: 45px !important;
        box-shadow: none !important;
    }

    /* FORM STYLING */
    div[data-testid="stForm"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F0F0F0 !important;
        border-radius: 15px !important;
        padding: 2.5rem !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.02) !important;
    }

    /* BUTTONS - HIGH END DESIGN */
    .stButton>button {
        background-color: #FFFFFF !important;
        color: #444444 !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 8px !important;
        height: 42px !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        width: 100% !important;
    }
    .stButton>button:hover {
        border-color: #CFAA5E !important;
        color: #CFAA5E !important;
        transform: translateY(-2px);
    }
    
    /* PRIMARY SUBMIT BUTTON */
    button[kind="secondaryFormSubmit"] {
        background-color: #2C3E50 !important;
        color: #FFFFFF !important;
        border: none !important;
    }

    /* METRICS */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF !important;
        border: 1px solid #F5F5F5 !important;
        padding: 1.5rem !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.01) !important;
    }
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_key_2026" 
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
HEADERS = ["ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"]

# ==========================================
# 2. CORE ENGINE
# ==========================================
def make_token(username):
    return hashlib.sha256(f"{username}{SESSION_SECRET}".encode()).hexdigest()

def check_token(username, token):
    return token == make_token(username)

@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def get_ws(name):
    client = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except:
        return client.open_by_key(SHEET_ID).sheet1

def load_all_data():
    ws = get_ws("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    try:
        vals = ws.get_all_values()
        if len(vals) < 2: return pd.DataFrame(columns=HEADERS)
        # Force column names to match HEADERS for consistency
        df = pd.DataFrame(vals[1:], columns=HEADERS[:len(vals[0])])
        return df
    except:
        return pd.DataFrame(columns=HEADERS)

def sync_data():
    st.session_state['inventory_df'] = load_all_data()

# ==========================================
# 3. AUTHENTICATION LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    params = st.query_params
    u, t = params.get("user"), params.get("token")
    if u and t and check_token(u, t):
        st.session_state['logged_in'] = True
        st.session_state['user'] = u
        st.session_state['role'] = "Admin" if u == "Administrator" else "Technician"
    else:
        st.session_state['logged_in'] = False

# ==========================================
# 4. LOGIN SCREEN
# ==========================================
if not st.session_state['logged_in']:
    st.markdown("<br><br><h1 style='text-align: center; color: #2C3E50; letter-spacing: 2px;'>ASSET MANAGER PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        mode = st.tabs(["Technician Access", "System Admin"])
        with mode[0]:
            with st.form("t_log", clear_on_submit=True):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    ws_u = get_ws("Users")
                    if ws_u:
                        users = ws_u.get_all_records()
                        if any(str(r['Username'])==u and str(r['PIN'])==p for r in users):
                            st.session_state['logged_in'] = True
                            st.session_state['user'] = u
                            st.session_state['role'] = "Technician"
                            st.query_params.update(user=u, token=make_token(u))
                            st.rerun()
                        else: st.error("Invalid Login")
        with mode[1]:
            with st.form("a_log"):
                p = st.text_input("Master Password", type="password")
                if st.form_submit_button("ADMIN ACCESS"):
                    if p == ADMIN_PASSWORD:
                        st.session_state['logged_in'] = True
                        st.session_state['user'] = "Administrator"
                        st.session_state['role'] = "Admin"
                        st.query_params.update(user="Administrator", token=make_token("Administrator"))
                        st.rerun()
                    else: st.error("Denied")

# ==========================================
# 5. MAIN APPLICATION
# ==========================================
else:
    if 'inventory_df' not in st.session_state: sync_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    # --- TOP BAR ---
    c_m, c_u, c_b = st.columns([4, 2, 1.2])
    with c_m:
        opts = ["Dashboard", "Asset Control", "Database", "User Manager"] if st.session_state['role'] == "Admin" else ["Issue Asset", "Return Asset", "Register Asset", "My Profile"]
        nav = st.selectbox("NAV", opts, label_visibility="collapsed")
    with c_u:
        st.markdown(f"<div style='text-align:right; padding-top:8px;'><b>{st.session_state['user']}</b></div>", unsafe_allow_html=True)
    with c_b:
        cb1, cb2 = st.columns(2)
        if cb1.button("🔄", key="sync_main"): sync_data(); st.rerun()
        if cb2.button("🚪", key="exit_main"): 
            st.session_state.clear(); st.query_params.clear(); st.rerun()

    st.markdown("---")

    # --- ADMIN: DASHBOARD ---
    if nav == "Dashboard":
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Assets", len(df))
        c2.metric("Available", len(df[df['CONDITION'].str.contains('Available', na=False)]))
        c3.metric("Issued", len(df[df['CONDITION'] == 'Issued']))
        
        st.markdown("<br>", unsafe_allow_html=True)
        if not df.empty and 'MODEL' in df.columns:
            models = sorted(df['MODEL'].unique())
            cols = st.columns(4)
            for i, m in enumerate(models):
                sub = df[df['MODEL'] == m]
                with cols[i % 4]:
                    st.markdown(f"<p style='text-align:center; font-size:12px; margin-bottom:-5px;'><b>{m}</b></p>", unsafe_allow_html=True)
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color_discrete_sequence=["#28A745", "#007BFF", "#DC3545"])
                    fig.update_layout(showlegend=False, height=140, margin=dict(t=10,b=10,l=0,r=0))
                    st.plotly_chart(fig, use_container_width=True, key=f"dash_chart_{i}")

    # --- ADMIN: USER MANAGER ---
    elif nav == "User Manager":
        st.markdown("### 👤 User Accounts")
        ws_u = get_ws("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.dataframe(udf, use_container_width=True)
            
            cx, cy = st.columns(2)
            with cx:
                with st.form("new_u_form"):
                    st.markdown("**Add Technician**")
                    nu = st.text_input("Name")
                    np = st.text_input("PIN")
                    if st.form_submit_button("CREATE"):
                        ws_u.append_row([nu, np, "Standard"])
                        st.success("User Created"); time.sleep(1); st.rerun()
            with cy:
                st.markdown("**Remove Access**")
                target = st.selectbox("Select User", udf['Username'].tolist() if not udf.empty else ["Empty"])
                if st.button("DELETE PERMANENTLY", key="del_u_perm") and target != "Empty":
                    cell = ws_u.find(target)
                    ws_u.delete_rows(cell.row)
                    st.success("User Deleted"); time.sleep(1); st.rerun()

    # --- ADMIN/TECH: ASSET CONTROL ---
    elif nav in ["Asset Control", "Register Asset"]:
        st.markdown("### ➕ Asset Registration")
        with st.form("reg_form"):
            c1, c2, c3 = st.columns(3)
            at = c1.text_input("Asset Type")
            br = c2.text_input("Brand")
            mo = c3.text_input("Model")
            sn = c1.text_input("Serial Number")
            mc = c2.text_input("MAC Address")
            lo = c3.selectbox("Store Location", FIXED_STORES)
            if st.form_submit_button("COMMIT TO DATABASE"):
                if sn:
                    ws_inv.append_row([at, br, mo, sn, mc, "Available/New", lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    sync_data(); st.success("Registered Successfully"); time.sleep(1); st.rerun()
                else: st.error("Serial Required")

    # --- ADMIN: DATABASE ---
    elif nav == "Database":
        st.markdown("### 📦 Master Inventory")
        search = st.text_input("Search anything...", "")
        if search:
            f_df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
            st.dataframe(f_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
        st.download_button("Export to Excel", BytesIO(), "inventory.xlsx", key="dl_btn")

    # --- TECH: ISSUE ---
    elif nav == "Issue Asset":
        st.markdown("### 🚀 Asset Issuance")
        with st.form("iss_f"):
            sn_in = st.text_input("Scan/Enter Serial")
            tkt_in = st.text_input("Ticket Number")
            if st.form_submit_button("AUTHORIZE"):
                idx = df.index[df['SERIAL'] == sn_in]
                if not idx.empty:
                    ws_inv.update_cell(int(idx[0])+2, 6, "Issued")
                    ws_inv.update_cell(int(idx[0])+2, 8, st.session_state['user'])
                    ws_inv.update_cell(int(idx[0])+2, 9, tkt_in)
                    sync_data(); st.success("Issued!"); time.sleep(1); st.rerun()
                else: st.error("Serial not found")

    # --- TECH: RETURN ---
    elif nav == "Return Asset":
        st.markdown("### 📥 Asset Return")
        my_items = df[df['ISSUED TO'] == st.session_state['user']]
        if not my_items.empty:
            target_sn = st.selectbox("Select Item to Return", my_items['SERIAL'].tolist())
            with st.form("ret_f"):
                c_new = st.selectbox("Current Condition", ["Available/New", "Available/Used", "Faulty"])
                l_new = st.selectbox("Store Location", FIXED_STORES)
                if st.form_submit_button("PROCESS RETURN"):
                    row_idx = int(df.index[df['SERIAL'] == target_sn][0]) + 2
                    ws_inv.update_cell(row_idx, 6, c_new)
                    ws_inv.update_cell(row_idx, 7, l_new)
                    ws_inv.update_cell(row_idx, 8, "")
                    sync_data(); st.success("Returned!"); time.sleep(1); st.rerun()
        else: st.info("No items issued to you.")

    # --- TECH: MY PROFILE ---
    elif nav == "My Profile":
        st.markdown(f"### 🎒 Assets held by {st.session_state['user']}")
        my_view = df[df['ISSUED TO'] == st.session_state['user']]
        st.dataframe(my_view, use_container_width=True)
