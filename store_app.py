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
# 1. CONFIGURATION & PROFESSIONAL WHITE THEME
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    /* --- 1. CLEAN WHITE BACKGROUND --- */
    .stApp {
        background-color: #ffffff !important;
    }
    
    /* Remove top whitespace */
    .block-container {
        padding-top: 2rem !important;
        max-width: 95% !important;
    }

    /* --- 2. HIDE STREAMLIT BRANDING (AGGRESSIVE) --- */
    header {visibility: hidden !important;}
    footer {display: none !important;}
    .stAppDeployButton {display: none !important; height: 0px !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    
    /* --- 3. UNIFORM INPUT BOX STYLING --- */
    /* This targets Text Inputs, Select Boxes, and Number Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #f8f9fa !important; /* Very light grey for contrast against white */
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        color: #333333 !important;
        height: 45px !important; /* Uniform height */
    }
    
    /* Fix Selectbox internal text alignment */
    .stSelectbox div[data-baseweb="select"] > div {
        align-items: center !important;
    }

    /* --- 4. CARD & FORM STYLING --- */
    /* The white containers for forms */
    div[data-testid="stForm"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 12px !important;
        padding: 30px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.03) !important; /* Soft shadow */
    }
    
    /* Top Menu Styling */
    div[data-testid="stSelectbox"] {
        margin-top: 0px !important;
    }

    /* --- 5. BUTTON STYLING --- */
    .stButton>button {
        width: 100%;
        height: 45px;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        box-shadow: none;
        transition: 0.2s;
    }
    
    /* Primary Action Button (Blue/Black) */
    button[kind="secondaryFormSubmit"] {
        background-color: #2c3e50 !important;
        color: white !important;
    }
    button[kind="secondaryFormSubmit"]:hover {
        background-color: #34495e !important;
    }

    /* Standard Button */
    .stButton>button {
        background-color: #f1f3f5;
        color: #333;
    }
    .stButton>button:hover {
        background-color: #e9ecef;
        border: 1px solid #cfaa5e;
    }

    /* --- 6. METRIC CARDS --- */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #eee;
        padding: 20px;
        border-radius: 10px;
        border-left: 4px solid #cfaa5e; /* Gold Accent */
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
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

try:
    from pyzbar.pyzbar import decode
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ==========================================
# 2. SESSION SECURITY
# ==========================================
def make_token(username):
    raw = f"{username}{SESSION_SECRET}"
    return hashlib.sha256(raw.encode()).hexdigest()

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

# ==========================================
# 3. CONNECTION & DATA
# ==========================================
@st.cache_resource
def get_client():
    try:
        if "gcp_service_account" not in st.secrets: return None
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            key = creds_dict["private_key"]
            if "\\n" in key: key = key.replace("\\n", "\n")
            creds_dict["private_key"] = key.strip('"')
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        return client
    except: return None

@st.cache_resource
def get_worksheet(name):
    client = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        try: return sh.worksheet(name)
        except: return sh.sheet1
    except: return None

def safe_add_rows(ws, rows_list):
    for row in rows_list:
        ws.append_row(row)

def load_data_initial():
    ws = get_worksheet("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    try:
        raw = ws.get_all_values()
        if not raw:
            ws.append_row(HEADERS)
            return pd.DataFrame(columns=HEADERS)
        
        rows = raw[1:]
        clean_rows = []
        for r in rows:
            while len(r) < len(HEADERS): r.append("")
            clean_rows.append(r[:len(HEADERS)])
        return pd.DataFrame(clean_rows, columns=HEADERS)
    except: return pd.DataFrame(columns=HEADERS)

def sync_local_state():
    if 'inventory_df' not in st.session_state or st.session_state['inventory_df'] is None:
        with st.spinner("Syncing..."):
            st.session_state['inventory_df'] = load_data_initial()

def force_reload():
    st.cache_data.clear()
    st.session_state['inventory_df'] = load_data_initial()

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    return output.getvalue()

# ==========================================
# 4. AUTO-LOGIN CHECK
# ==========================================
if 'logged_in' not in st.session_state:
    params = st.query_params
    url_user = params.get("user")
    url_token = params.get("token")
    
    if url_user and url_token and check_token(url_user, url_token):
        if url_user == "Administrator":
             set_login_session("Administrator", "Admin", True)
        else:
             ws_u = get_worksheet("Users")
             can_bulk = False
             if ws_u:
                 records = ws_u.get_all_records()
                 for r in records:
                     if str(r.get('Username')) == url_user:
                         can_bulk = (str(r.get('Permissions')) == "Bulk_Allowed")
                         break
             set_login_session(url_user, "Technician", can_bulk)
    else:
        st.session_state['logged_in'] = False

# ==========================================
# 5. LOGIN SCREEN
# ==========================================
def login_screen():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #2c3e50; font-weight: 300;'>EXPO ASSET MANAGER</h1>", unsafe_allow_html=True)
        st.markdown("<hr style='border:1px solid #cfaa5e'>", unsafe_allow_html=True)
        
        t1, t2 = st.tabs(["Technician", "Administrator"])
        
        with t1:
            with st.form("tech"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    ws_u = get_worksheet("Users")
                    if ws_u:
                        users = ws_u.get_all_records()
                        valid = False
                        for user in users:
                            if str(user.get('Username')) == u and str(user.get('PIN')) == p:
                                perm = (str(user.get('Permissions')) == "Bulk_Allowed")
                                set_login_session(u, "Technician", perm)
                                valid = True
                                st.rerun()
                        if not valid: st.error("Invalid Credentials")
                    else: st.error("System Offline")

        with t2:
            with st.form("admin"):
                p = st.text_input("Password", type="password")
                if st.form_submit_button("LOGIN"):
                    if p == ADMIN_PASSWORD:
                        set_login_session("Administrator", "Admin", True)
                        st.rerun()
                    else: st.error("Access Denied")

# ==========================================
# 6. MAIN APP
# ==========================================
if not st.session_state['logged_in']:
    login_screen()
else:
    sync_local_state()
    df = st.session_state['inventory_df']
    ws_inv = get_worksheet("Sheet1")

    # --- TOP NAVIGATION BAR ---
    # Styled like a professional header
    c_nav, c_user, c_act = st.columns([4, 2, 1])
    
    with c_nav:
        # Determine Menu Options
        if st.session_state['role'] == "Technician":
            options = ["🚀 Issue Asset", "📥 Return Asset", "🎒 My Inventory", "➕ Add Asset", "⚡ Bulk Import"]
        else:
            options = ["📊 Dashboard", "👥 User Manager", "🛠️ Asset Control", "📦 Database View"]
            
        nav = st.selectbox("Menu Navigation", options, label_visibility="collapsed")

    with c_user:
        st.markdown(f"<div style='text-align:right; padding-top:10px; color:#555;'>User: <b>{st.session_state['user']}</b></div>", unsafe_allow_html=True)

    with c_act:
        c_r, c_l = st.columns(2)
        if c_r.button("🔄"): force_reload(); st.rerun()
        if c_l.button("🚪"): clear_login_session(); st.rerun()

    st.divider()

    # --- TECHNICIAN LOGIC ---
    if st.session_state['role'] == "Technician":
        
        if nav == "🚀 Issue Asset":
            st.markdown("#### 🚀 Issue Asset")
            c1, c2 = st.columns([3, 1])
            with c1: search = st.text_input("Enter Asset Serial Number", placeholder="Scan or Type...")
            with c2:
                if CAMERA_AVAILABLE:
                    cam = st.camera_input("Scan QR")
                    if cam: 
                        try: search = decode(Image.open(cam))[0].data.decode("utf-8")
                        except: pass
            
            if search:
                match = df[df['SERIAL'].astype(str).str.strip().str.upper() == search.strip().upper()]
                if not match.empty:
                    item = match.iloc[0]
                    idx = int(match.index[0])
                    st.success(f"Verified: {item['MODEL']} ({item['ASSET TYPE']})")
                    
                    if "Available" in str(item['CONDITION']):
                        with st.form("issue"):
                            tkt = st.text_input("Helpdesk Ticket Number")
                            if st.form_submit_button("CONFIRM ISSUANCE"):
                                sheet_row = idx + 2
                                ws_inv.update_cell(sheet_row, 6, "Issued")
                                ws_inv.update_cell(sheet_row, 8, st.session_state['user'])
                                ws_inv.update_cell(sheet_row, 9, tkt)
                                force_reload(); st.success("Asset Issued Successfully"); st.rerun()
                    else: st.warning(f"Status: {item['CONDITION']} - Cannot Issue")
                else: st.error("Serial Number Not Found")

        elif nav == "📥 Return Asset":
            st.markdown("#### 📥 Return Asset")
            my = df[(df['ISSUED TO'] == st.session_state['user']) & (df['CONDITION'] == 'Issued')]
            if my.empty: st.info("No assets currently issued to you.")
            else:
                sel = st.selectbox("Select Asset to Return", my['SERIAL'].tolist())
                with st.form("ret"):
                    c1,c2 = st.columns(2)
                    stat = c1.selectbox("Condition Upon Return", ["Available/New", "Available/Used", "Faulty"])
                    stores = sorted(list(set(FIXED_STORES) | set(df['LOCATION'].unique())))
                    loc = c2.selectbox("Return Location", stores)
                    if st.form_submit_button("CONFIRM RETURN"):
                        idx = int(df[df['SERIAL']==sel].index[0])
                        sheet_row = idx + 2
                        ws_inv.update_cell(sheet_row, 6, stat)
                        ws_inv.update_cell(sheet_row, 7, loc)
                        ws_inv.update_cell(sheet_row, 8, "")
                        force_reload(); st.success("Asset Returned Successfully"); st.rerun()

        elif nav == "➕ Add Asset":
            st.markdown("#### ➕ Register New Asset")
            with st.form("add"):
                c1,c2 = st.columns(2)
                typ = c1.selectbox("Asset Category", ["Camera", "Reader", "Controller", "Lock", "Laptop", "Switch", "Server"])
                man = c1.text_input("Brand / Manufacturer")
                mod = c2.text_input("Model Number")
                sn = c2.text_input("Serial Number")
                mac = c1.text_input("MAC Address (Optional)")
                stores = sorted(list(set(FIXED_STORES) | set(df['LOCATION'].unique())))
                loc = c2.selectbox("Storage Location", stores)
                stat = st.selectbox("Initial Condition", ["Available/New", "Available/Used"])
                if st.form_submit_button("SAVE TO DATABASE"):
                    if sn not in df['SERIAL'].astype(str).tolist():
                        row = [typ, man, mod, sn, mac, stat, loc, "", "", get_timestamp(), st.session_state['user']]
                        safe_add_rows(ws_inv, [row])
                        force_reload(); st.success("Asset Registered"); st.rerun()
                    else: st.error("Error: Duplicate Serial Number")

        elif nav == "⚡ Bulk Import":
            st.markdown("#### ⚡ Bulk Data Import")
            if st.session_state.get('can_import'):
                st.download_button("Download Excel Template", to_excel(pd.DataFrame(columns=HEADERS)), "template.xlsx")
                up = st.file_uploader("Upload Completed Excel", type=['xlsx'])
                if up and st.button("PROCESS IMPORT"):
                    d = pd.read_excel(up).fillna("")
                    d.columns = [str(c).strip().upper() for c in d.columns]
                    rows = []
                    for i,r in d.iterrows():
                        s = str(r.get('SERIAL', r.get('SERIAL NUMBER', '')))
                        if s and s not in df['SERIAL'].astype(str).tolist():
                            rows.append([r.get('ASSET TYPE', ''), r.get('BRAND', ''), r.get('MODEL', ''), s, r.get('MAC ADDRESS', ''), "Available/New", r.get('LOCATION', ''), "", "", get_timestamp(), "BULK"])
                    if rows: 
                        safe_add_rows(ws_inv, rows)
                        force_reload(); st.success(f"Successfully Imported {len(rows)} Assets"); st.rerun()
            else: st.error("Access Denied: You do not have bulk import permissions.")

        elif nav == "🎒 My Inventory":
            st.markdown("#### 🎒 Currently Held Assets")
            st.dataframe(df[(df['ISSUED TO'] == st.session_state['user']) & (df['CONDITION'] == 'Issued')], use_container_width=True)

    # --- ADMIN ---
    elif st.session_state['role'] == "Admin":
        
        if nav == "📊 Dashboard":
            st.markdown("#### 📊 System Overview")
            if not df.empty:
                # METRICS
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Assets", len(df))
                c2.metric("Available", len(df[df['CONDITION'].str.contains('Available', na=False)]))
                c3.metric("Issued", len(df[df['CONDITION']=='Issued']))
                c4.metric("Faulty", len(df[df['CONDITION']=='Faulty']))
                
                st.markdown("<br>", unsafe_allow_html=True)

                # PIE CHARTS GRID
                color_map = {"Available/New": "#28a745", "Available/Used": "#218838", "Issued": "#007bff", "Faulty": "#dc3545"}
                valid_models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
                
                cols_per_row = 3
                rows_needed = (len(valid_models) + cols_per_row - 1) // cols_per_row
                
                for row_idx in range(rows_needed):
                    cols = st.columns(cols_per_row)
                    for col_idx in range(cols_per_row):
                        idx = row_idx * cols_per_row + col_idx
                        if idx < len(valid_models):
                            m_name = valid_models[idx]
                            sub = df[df['MODEL'] == m_name]
                            atype = sub['ASSET TYPE'].iloc[0] if not sub.empty else ""
                            with cols[col_idx]:
                                # Clean Card for Chart
                                with st.container():
                                    st.caption(f"{atype}")
                                    st.markdown(f"**{m_name}**")
                                    fig = px.pie(sub, names='CONDITION', color='CONDITION', color_discrete_map=color_map, hole=0.6)
                                    fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150)
                                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Database is empty.")

        elif nav == "👥 User Manager":
            st.markdown("#### 👥 User Management")
            ws_u = get_worksheet("Users")
            if ws_u:
                udf = pd.DataFrame(ws_u.get_all_records())
                st.dataframe(udf, use_container_width=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    with st.form("add_u"):
                        st.markdown("**Add New User**")
                        u = st.text_input("Username")
                        p = st.text_input("PIN Code")
                        perm = st.selectbox("Permission Level", ["Standard", "Bulk_Allowed"])
                        if st.form_submit_button("Create User"): 
                            ws_u.append_row([u, p, perm])
                            st.success("User Added")
                            time.sleep(1); st.rerun()
                with c2:
                    st.markdown("**Delete User**")
                    target = st.selectbox("Select User to Delete", udf['Username'].tolist() if not udf.empty else [])
                    if st.button("DELETE USER PERMANENTLY"):
                        cell = ws_u.find(target)
                        ws_u.delete_rows(cell.row)
                        st.success("User Deleted")
                        time.sleep(1); st.rerun()

        elif nav == "🛠️ Asset Control":
            st.markdown("#### 🛠️ Master Asset Control")
            tab1, tab2 = st.tabs(["Add Assets", "Edit/Delete Assets"])
            
            with tab1:
                with st.form("adm_add"):
                    c1, c2, c3 = st.columns(3)
                    atype = c1.text_input("Asset Type (e.g. Laptop)")
                    brand = c2.text_input("Brand")
                    model = c3.text_input("Model")
                    c4, c5, c6 = st.columns(3)
                    serial = c4.text_input("Serial Number (Start)")
                    mac = c5.text_input("MAC Address")
                    cond = c6.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    c7, c8 = st.columns(2)
                    stores = sorted(list(set(FIXED_STORES) | set(df['LOCATION'].unique())))
                    loc = c7.selectbox("Location", stores)
                    qty = c8.number_input("Quantity", 1, 100, 1)
                    if st.form_submit_button("ADD ASSETS"):
                        if not atype: st.error("Asset Type Required")
                        elif not serial and qty == 1: st.error("Serial Required")
                        elif serial in df['SERIAL'].astype(str).tolist(): st.error("Duplicate Serial")
                        else:
                            rows = []
                            for i in range(qty):
                                s = serial if qty==1 else f"{serial}-{i+1}"
                                rows.append([atype, brand, model, s, mac, cond, loc, "", "", get_timestamp(), "ADMIN"])
                            safe_add_rows(ws_inv, rows)
                            force_reload(); st.success(f"Added {qty} items"); st.rerun()

            with tab2:
                q = st.text_input("Search Asset by Serial Number")
                if q:
                    match = df[df['SERIAL'].astype(str).str.contains(q, case=False)]
                    if not match.empty:
                        sel = st.selectbox("Select Asset", match['SERIAL'].tolist())
                        idx = int(df[df['SERIAL']==sel].index[0])
                        sheet_row = idx + 2
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            with st.form("upd"):
                                st.markdown("**Update Status**")
                                n_stat = st.selectbox("New Status", ["Available/New", "Issued", "Faulty"])
                                n_loc = st.text_input("New Location", df[df['SERIAL']==sel].iloc[0]['LOCATION'])
                                if st.form_submit_button("UPDATE ASSET"):
                                    ws_inv.update_cell(sheet_row, 6, n_stat)
                                    ws_inv.update_cell(sheet_row, 7, n_loc)
                                    force_reload(); st.success("Updated"); st.rerun()
                        with c2:
                            st.markdown("**Danger Zone**")
                            if st.button("DELETE ASSET PERMANENTLY"):
                                ws_inv.delete_rows(sheet_row)
                                force_reload(); st.success("Deleted"); st.rerun()

        elif nav == "📦 Database View":
            st.markdown("#### 📦 Full Database")
            c1, c2 = st.columns([6, 1])
            c2.download_button("📥 Export to Excel", to_excel(df), "inventory_data.xlsx")
            st.dataframe(df, use_container_width=True)
