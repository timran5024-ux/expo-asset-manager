import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import base64
from PIL import Image
from io import BytesIO
import plotly.express as px

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide")

# ==========================================
# 2. DYNAMIC CSS (ATTRACTIVE UI)
# ==========================================
def inject_custom_css(login_mode=False):
    if login_mode:
        st.markdown("""
        <style>
            /* 1. Background */
            .stApp {
                background-color: #f4f6f8;
            }
            [data-testid="stSidebar"] { display: none; }
            header { visibility: hidden; }

            /* 2. Center Layout */
            .main .block-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 90vh;
                padding: 0 !important;
                max-width: 100%;
            }

            /* 3. The Login Card */
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: white;
                padding: 2rem 2.5rem;
                border-radius: 12px;
                box-shadow: 0 8px 30px rgba(0,0,0,0.08);
                width: 100%;
                max-width: 400px;
                border: 1px solid #eef0f2;
                border-top: 6px solid #cfaa5e; /* Expo Gold Accent */
            }

            /* 4. Tabs Styling (Technician vs Admin) */
            .stTabs [data-baseweb="tab-list"] {
                justify-content: center;
                margin-bottom: 1rem;
                border-bottom: 1px solid #eee;
            }
            .stTabs [data-baseweb="tab"] {
                height: 3rem;
                white-space: pre-wrap;
                background-color: transparent;
                border-radius: 4px;
                color: #6b7280;
                font-weight: 500;
                flex: 1; /* Equal width */
            }
            .stTabs [aria-selected="true"] {
                background-color: #f9fafb;
                color: #cfaa5e; /* Gold Text for Active */
                border-bottom: 2px solid #cfaa5e;
            }

            /* 5. Inputs */
            .stTextInput label, .stSelectbox label {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #374151;
                font-weight: 600;
            }
            .stTextInput input, .stSelectbox div[data-baseweb="select"] {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                min-height: 42px;
            }
            
            /* 6. Buttons */
            .stButton button {
                width: 100%;
                background-color: #111827; /* Dark */
                color: white;
                border-radius: 6px;
                font-weight: 600;
                height: 45px;
                border: none;
                transition: background 0.2s;
            }
            .stButton button:hover {
                background-color: #000;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }

            /* 7. Typography */
            h1, h2, h3 { text-align: center; font-family: 'Inter', sans-serif; }
            .login-header { text-align: center; margin-bottom: 20px; }
            .login-header h3 { font-size: 1.5rem; font-weight: 700; color: #111; margin: 0; }
            .login-header p { font-size: 0.875rem; color: #6b7280; margin-top: 5px; }

            /* 8. Logo */
            div[data-testid="stImage"] {
                display: flex;
                justify-content: center;
                margin-bottom: 1rem;
            }
            
            footer { display: none; }
        </style>
        """, unsafe_allow_html=True)
    else:
        # --- DASHBOARD CSS ---
        st.markdown("""
        <style>
            .stApp { background-color: #f9fafb; }
            section[data-testid="stSidebar"] { background-color: white; border-right: 1px solid #e5e7eb; }
            
            div[data-testid="stMetric"] { 
                background-color: white; padding: 1.5rem; border-radius: 8px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; 
            }
            
            .stButton button { 
                width: 100%; border-radius: 6px; background-color: white; 
                color: #374151; border: 1px solid #d1d5db; font-weight: 500;
            }
            .stButton button:hover { border-color: #cfaa5e; color: #cfaa5e; }
            
            button[kind="primary"] { background-color: #cfaa5e !important; color: white !important; border: none !important; }
        </style>
        """, unsafe_allow_html=True)

# ==========================================
# 3. SETUP & CONSTANTS
# ==========================================
CAMERA_AVAILABLE = False
try:
    from pyzbar.pyzbar import decode
    CAMERA_AVAILABLE = True
except:
    CAMERA_AVAILABLE = False

ADMIN_PASSWORD = "admin123"
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
SHEET_NAME = "Store_Inventory_DB"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 4. CONNECTION
# ==========================================
@st.cache_resource
def get_client():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", SCOPE)
        return gspread.authorize(creds)
    except: st.error("❌ Key Error. Check service_account.json"); st.stop()

def get_inventory_sheet():
    client = get_client()
    try: return client.open(SHEET_NAME).sheet1
    except: st.error(f"❌ Sheet '{SHEET_NAME}' not found."); st.stop()

def get_users_sheet():
    client = get_client()
    sh = client.open(SHEET_NAME)
    try: return sh.worksheet("Users")
    except:
        ws = sh.add_worksheet(title="Users", rows="100", cols="3")
        ws.append_row(["Username", "PIN", "Permissions"]); return ws

# ==========================================
# 5. FAST DATA ENGINE
# ==========================================
@st.cache_data(ttl=600)  
def download_data():
    """Reads data from Google Sheets (Cached for Speed)"""
    sheet = get_inventory_sheet()
    raw_data = sheet.get_all_values()
    if not raw_data: return pd.DataFrame()
    headers = raw_data[0]
    rows = raw_data[1:]
    seen = {}; new_headers = []
    for h in headers:
        if h in seen: seen[h]+=1; new_headers.append(f"{h}_{seen[h]}")
        else: seen[h]=0; new_headers.append(h)
    return pd.DataFrame(rows, columns=new_headers)

def init_data_state():
    if 'inventory_df' not in st.session_state or st.session_state['inventory_df'] is None:
        st.session_state['inventory_df'] = download_data()

def force_sync():
    st.cache_data.clear()
    st.session_state['inventory_df'] = download_data()

# ==========================================
# 6. HELPER FUNCTIONS
# ==========================================
def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def get_date_str(): return datetime.now().strftime("%Y-%m-%d")

def check_serial_exists(df, serial):
    if df.empty: return False
    existing = df['Serial Number'].astype(str).str.strip().str.upper().tolist()
    return str(serial).strip().upper() in existing

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    return output.getvalue()

def get_template_excel():
    df_temp = pd.DataFrame(columns=["Asset Type", "Manufacturer", "Model", "Serial Number", "MAC Address", "Status", "Location"])
    return to_excel(df_temp)

def get_all_stores(df):
    if df.empty: return FIXED_STORES
    valid_stores = set(FIXED_STORES)
    if 'Location' in df.columns:
        db_vals = df['Location'].unique().tolist()
        for s in db_vals:
            if str(s).strip() and str(s).upper() not in ["FAULTY", "USED", "NEW", "AVAILABLE", "ISSUED"]:
                valid_stores.add(str(s).strip())
    return sorted(list(valid_stores))

# ==========================================
# 7. SESSION & LOGIN
# ==========================================
def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['username'] = None
        st.session_state['can_import'] = False
        st.session_state['current_page'] = "Login"

    try: q = st.query_params
    except: q = st.experimental_get_query_params()

    if not st.session_state['logged_in'] and "session_id" in q:
        st.session_state['logged_in'] = True
        st.session_state['username'] = q.get("user", ["Unknown"])[0] if isinstance(q.get("user"), list) else q.get("user")
        st.session_state['user_role'] = q.get("role", ["Technician"])[0] if isinstance(q.get("role"), list) else q.get("role")
        st.session_state['can_import'] = q.get("perm", ["False"])[0] == "True"
        if st.session_state['user_role'] == "Admin": st.session_state['current_page'] = "Overview"
        else: st.session_state['current_page'] = "Collect"

def save_session(user, role, perm=False):
    try:
        st.query_params["session_id"] = "active"
        st.query_params["user"] = user
        st.query_params["role"] = role
        st.query_params["perm"] = str(perm)
    except: pass

def logout(): 
    st.session_state['logged_in']=False
    st.session_state['inventory_df'] = None 
    st.session_state['current_page'] = "Login"
    try: st.query_params.clear()
    except: pass
    st.rerun()

init_session()

def login_screen():
    inject_custom_css(login_mode=True)
    
    with st.container(border=True):
        # 1. LOGO
        try: st.image("logo.png", width=140) 
        except: st.markdown("<h1 style='text-align: center;'>🏢</h1>", unsafe_allow_html=True)
        
        # 2. HEADER
        st.markdown("""
            <div class="login-header">
                <h3>Welcome Back</h3>
                <p>Please enter your details to sign in.</p>
            </div>
        """, unsafe_allow_html=True)

        # 3. TABS (Technician / Admin)
        tab1, tab2 = st.tabs(["Technician", "Administrator"])
        
        # --- TECHNICIAN TAB ---
        with tab1:
            try:
                us = get_users_sheet(); data = us.get_all_records(); df = pd.DataFrame(data)
                users_list = df['Username'].tolist() if not df.empty else []
            except: users_list = []

            with st.form("tech_login"):
                u = st.selectbox("Select User", users_list, placeholder="Choose your name")
                p = st.text_input("Access PIN", type="password", placeholder="••••")
                st.write("") # Spacer
                
                # Custom "Remember Me" text
                st.markdown("<p style='font-size: 11px; color: #888; text-align: right;'>Forgot PIN?</p>", unsafe_allow_html=True)
                
                if st.form_submit_button("Sign In"):
                    if not df.empty:
                        row = df[df['Username']==u].iloc[0]
                        if str(row['PIN']) == str(p):
                            st.session_state['logged_in'] = True; st.session_state['user_role'] = "Technician"
                            st.session_state['username'] = u
                            perm = str(row['Permissions']).strip() if 'Permissions' in row else "Standard"
                            st.session_state['can_import'] = (perm == "Bulk_Allowed")
                            st.session_state['current_page'] = "Collect"
                            save_session(u, "Technician", st.session_state['can_import'])
                            st.rerun()
                        else: st.error("Incorrect PIN")
                    else: st.error("System Error: No users found")

        # --- ADMIN TAB ---
        with tab2:
            with st.form("admin_login"):
                pwd = st.text_input("Password", type="password", placeholder="Admin Password")
                st.write("") # Spacer
                st.markdown("<p style='font-size: 11px; color: #888; text-align: right;'>Contact IT Support</p>", unsafe_allow_html=True)
                
                if st.form_submit_button("Authenticate"):
                    if pwd == ADMIN_PASSWORD:
                        st.session_state['logged_in'] = True; st.session_state['user_role'] = "Admin"
                        st.session_state['username'] = "Administrator"
                        st.session_state['can_import'] = True
                        st.session_state['current_page'] = "Overview"
                        save_session("Administrator", "Admin", True)
                        st.rerun()
                    else: st.error("Access Denied")

        # 4. FOOTER
        st.markdown("<div style='text-align: center; font-size: 10px; color: #ccc; margin-top: 15px;'>© 2026 Expo City Dubai</div>", unsafe_allow_html=True)

# ==========================================
# 8. MAIN APP
# ==========================================
def main():
    if not st.session_state['logged_in']: 
        login_screen()
        return
    
    inject_custom_css(login_mode=False)
    
    # --- BRANDED SIDEBAR ---
    try: st.sidebar.image("logo.png", width=150)
    except: pass

    st.sidebar.markdown(f"**User:** {st.session_state['username']}")
    st.sidebar.caption(f"Role: {st.session_state['user_role']}")
    
    if st.sidebar.button("🔄 Force Refresh"):
        with st.spinner("Syncing..."):
            force_sync()
        st.success("Synced!"); time.sleep(0.5); st.rerun()
    
    st.sidebar.divider()
    init_data_state()
    df = st.session_state['inventory_df']
    sheet = get_inventory_sheet() 

    # --- TECHNICIAN MENU ---
    if st.session_state['user_role'] == "Technician":
        if st.session_state['current_page'] not in ["Collect", "Return", "My Inventory", "Add Item", "Edit Details", "Bulk Import"]:
            st.session_state['current_page'] = "Collect"

        if st.sidebar.button("🚀 Collect"): st.session_state['current_page'] = "Collect"; st.rerun()
        if st.sidebar.button("📥 Return"): st.session_state['current_page'] = "Return"; st.rerun()
        if st.sidebar.button("🎒 My Inventory"): st.session_state['current_page'] = "My Inventory"; st.rerun()
        st.sidebar.divider()
        if st.sidebar.button("➕ Add Item"): st.session_state['current_page'] = "Add Item"; st.rerun()
        if st.sidebar.button("✏️ Edit Details"): st.session_state['current_page'] = "Edit Details"; st.rerun()
        if st.session_state['can_import']:
             if st.sidebar.button("⚡ Bulk Import"): st.session_state['current_page'] = "Bulk Import"; st.rerun()
        st.sidebar.divider()
        if st.sidebar.button("🚪 Logout", type="primary"): logout()

        menu = st.session_state['current_page']

        if menu == "Collect":
            st.title("🚀 Issue Asset")
            with st.container(border=True):
                c1, c2 = st.columns(2)
                scan_val = ""
                with c1: text_scan = st.text_input("🔍 Serial Number", placeholder="Scan or Type...")
                with c2:
                    if CAMERA_AVAILABLE: 
                        cam = st.camera_input("Scanner")
                        if cam: 
                            try: scan_val = decode(Image.open(cam))[0].data.decode("utf-8")
                            except: pass
                if text_scan: scan_val = text_scan.strip()
                if scan_val:
                    match = df[df['Serial Number'].astype(str).str.strip().str.upper() == scan_val.upper()]
                    if not match.empty:
                        item = match.iloc[0]
                        match_idx = match.index[0]
                        st.info(f"**Selected:** {item['Model']} | **Status:** {item['Status']}")
                        if item['Status'].startswith("Available"):
                            ticket = st.text_input("Enter Ticket Number")
                            if st.button("✅ Confirm Issue", type="primary"):
                                idx = match_idx + 2 
                                sheet.update_cell(idx, 6, "Issued")
                                sheet.update_cell(idx, 7, st.session_state['username'])
                                sheet.update_cell(idx, 8, ticket)
                                df.at[match_idx, 'Status'] = "Issued"
                                df.at[match_idx, 'Issued To'] = st.session_state['username']
                                df.at[match_idx, 'Ticket_Number'] = ticket
                                st.session_state['inventory_df'] = df 
                                st.success("Issued!"); time.sleep(0.5); st.rerun()
                        else: st.warning(f"Item is {item['Status']}")
                    else: st.error("Not Found")

        elif menu == "Return":
            st.title("📥 Return Asset")
            my = df[(df['Issued To']==st.session_state['username'])&(df['Status']=='Issued')]
            if my.empty: st.success("No pending items.")
            else:
                with st.container(border=True):
                    sel = st.selectbox("Select Asset", [f"{r['Serial Number']} - {r['Model']}" for i,r in my.iterrows()])
                    if sel:
                        sn = sel.split(" - ")[0]
                        c1, c2 = st.columns(2)
                        cond = c1.selectbox("New Status", ["Available/New", "Available/Used", "Faulty"])
                        loc = c2.selectbox("Return Loc", get_all_stores(df))
                        if st.button("Process Return", type="primary"):
                            match_idx = df[df['Serial Number']==sn].index[0]
                            idx = match_idx + 2
                            sheet.update_cell(idx, 6, cond)
                            sheet.update_cell(idx, 7, st.session_state['username'] if cond=="Faulty" else "")
                            sheet.update_cell(idx, 9, loc)
                            df.at[match_idx, 'Status'] = cond
                            df.at[match_idx, 'Issued To'] = st.session_state['username'] if cond=="Faulty" else ""
                            df.at[match_idx, 'Location'] = loc
                            st.session_state['inventory_df'] = df
                            st.success("Returned!"); time.sleep(0.5); st.rerun()

        elif menu == "My Inventory":
            st.title("🎒 My Items")
            my = df[(df['Issued To']==st.session_state['username'])&(df['Status']=='Issued')]
            st.dataframe(my[['Asset Type', 'Model', 'Serial Number', 'MAC Address', 'Ticket_Number', 'Location']], use_container_width=True)

        elif menu == "Add Item":
            st.title("➕ Register Asset")
            with st.container(border=True):
                with st.form("tech_add"):
                    c1,c2 = st.columns(2)
                    typ = c1.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
                    man = c1.text_input("Make"); mod = c2.text_input("Model")
                    sn = c2.text_input("Serial"); mac = c1.text_input("MAC")
                    loc = c2.selectbox("Location", get_all_stores(df))
                    stat = st.selectbox("Status", ["Available/New", "Available/Used"])
                    if st.form_submit_button("Add", type="primary"):
                        if check_serial_exists(df, sn): st.error("Duplicate Serial")
                        else:
                            row_data = [typ, man, mod, sn, mac, stat, "", "", loc, "", get_timestamp(), f"Add: {st.session_state['username']}"]
                            sheet.append_row(row_data)
                            force_sync(); st.success("Added!"); st.rerun()

        elif menu == "Edit Details":
            st.title("✏️ Edit Asset")
            q = st.text_input("Search Serial")
            if q:
                match = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]
                if not match.empty:
                    with st.container(border=True):
                        sel = st.selectbox("Select", [f"{r['Serial Number']} | {r['Model']}" for i,r in match.iterrows()])
                        sn_sel = sel.split(" | ")[0]
                        match_idx = df[df['Serial Number']==sn_sel].index[0]
                        idx = match_idx+2
                        with st.form("tech_edit"):
                            c1, c2 = st.columns(2)
                            n_mod = c1.text_input("Model", df.iloc[match_idx]['Model'])
                            n_mac = c2.text_input("MAC", df.iloc[match_idx]['MAC Address'])
                            n_loc = st.selectbox("Location", get_all_stores(df))
                            if st.form_submit_button("Save Changes", type="primary"):
                                sheet.update_cell(idx, 3, n_mod)
                                sheet.update_cell(idx, 5, n_mac)
                                sheet.update_cell(idx, 9, n_loc)
                                df.at[match_idx, 'Model'] = n_mod
                                df.at[match_idx, 'MAC Address'] = n_mac
                                df.at[match_idx, 'Location'] = n_loc
                                st.session_state['inventory_df'] = df
                                st.success("Updated!"); time.sleep(0.5); st.rerun()

    # --- ADMIN MENU ---
    elif st.session_state['user_role'] == "Admin":
        if st.session_state['current_page'] not in ["Overview", "Asset Manager", "Team Manager", "Bulk Ops", "Database"]:
            st.session_state['current_page'] = "Overview"

        if st.sidebar.button("📊 Overview"): st.session_state['current_page'] = "Overview"; st.rerun()
        if st.sidebar.button("🛠️ Asset Manager"): st.session_state['current_page'] = "Asset Manager"; st.rerun()
        if st.sidebar.button("👥 Team Manager"): st.session_state['current_page'] = "Team Manager"; st.rerun()
        if st.sidebar.button("⚡ Bulk Ops"): st.session_state['current_page'] = "Bulk Ops"; st.rerun()
        if st.sidebar.button("📦 Database"): st.session_state['current_page'] = "Database"; st.rerun()
        st.sidebar.divider()
        if st.sidebar.button("🚪 Logout", type="primary"): logout()

        menu = st.session_state['current_page']

        if menu == "Overview":
            st.title("📊 System Analytics")
            if not df.empty:
                total = len(df)
                avail = len(df[df['Status'].str.contains("Available", na=False)])
                issued = len(df[df['Status'] == "Issued"])
                faulty = len(df[df['Status'] == "Faulty"])
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", total); c2.metric("Available", avail)
                c3.metric("Issued", issued); c4.metric("Faulty", faulty)
                c1, c2 = st.columns(2)
                with c1:
                    fig = px.pie(df, names='Status', hole=0.4, title="Status Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                with c2:
                    fig2 = px.bar(df['Asset Type'].value_counts(), title="Inventory by Type")
                    st.plotly_chart(fig2, use_container_width=True)

        elif menu == "Asset Manager":
            st.title("🛠️ Asset Control")
            tab1, tab2 = st.tabs(["Add / Edit", "Delete"])
            with tab1:
                c1, c2 = st.columns(2)
                with c1:
                    with st.container(border=True):
                        st.subheader("Add Asset")
                        with st.form("adm_add"):
                            typ = st.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
                            sn = st.text_input("Serial"); mac = st.text_input("MAC")
                            mod = st.text_input("Model"); loc = st.selectbox("Loc", get_all_stores(df))
                            if st.form_submit_button("Create", type="primary"):
                                if not check_serial_exists(df, sn):
                                    sheet.append_row([typ, "", mod, sn, mac, "Available/New", "", "", loc, "", get_timestamp(), "ADMIN"])
                                    force_sync(); st.success("Created!"); st.rerun()
                                else: st.error("Duplicate")
                with c2:
                    with st.container(border=True):
                        st.subheader("Edit Asset")
                        q = st.text_input("Find Asset")
                        if q:
                            match = df[df.astype(str).apply(lambda x: x.str.contains(q, case=False)).any(axis=1)]
                            if not match.empty:
                                item_opt = st.selectbox("Select", [f"{r['Serial Number']}" for i,r in match.iterrows()])
                                match_idx = df[df['Serial Number']==item_opt].index[0]
                                idx = match_idx+2
                                item = df.iloc[match_idx]
                                with st.form("adm_mod"):
                                    n_stat = st.selectbox("Status", ["Available/New", "Issued", "Faulty", "Hold"], index=0)
                                    n_iss = st.text_input("Issued To", item['Issued To'])
                                    n_loc = st.text_input("Location", item['Location'])
                                    if st.form_submit_button("Update", type="primary"):
                                        sheet.update_cell(idx, 6, n_stat); sheet.update_cell(idx, 7, n_iss); sheet.update_cell(idx, 9, n_loc)
                                        df.at[match_idx, 'Status'] = n_stat
                                        df.at[match_idx, 'Issued To'] = n_iss
                                        df.at[match_idx, 'Location'] = n_loc
                                        st.session_state['inventory_df'] = df
                                        st.success("Updated!"); st.rerun()
            with tab2:
                qd = st.text_input("Serial to Delete")
                if qd and st.button("DELETE PERMANENTLY", type="primary"):
                    idx = df[df['Serial Number']==qd].index[0]+2
                    sheet.delete_rows(idx)
                    force_sync(); st.success("Deleted"); st.rerun()

        elif menu == "Team Manager":
            st.title("👥 User Management")
            us_sheet = get_users_sheet()
            u_df = pd.DataFrame(us_sheet.get_all_records())
            c1, c2 = st.columns([2, 1])
            with c1: st.dataframe(u_df, use_container_width=True)
            with c2:
                with st.form("perm"):
                    tu = st.selectbox("User", u_df['Username'].tolist() if not u_df.empty else [])
                    np = st.selectbox("Access", ["Standard", "Bulk_Allowed"])
                    if st.form_submit_button("Update Access"):
                        cell = us_sheet.find(tu)
                        us_sheet.update_cell(cell.row, 3, np)
                        st.success("Updated"); st.rerun()
                with st.expander("Create User"):
                    nu = st.text_input("User"); npin = st.text_input("PIN")
                    if st.button("Add"):
                        us_sheet.append_row([nu, npin, "Standard"])
                        st.success("Added"); st.rerun()

        elif menu == "Bulk Ops":
            st.title("⚡ Bulk Import")
            st.download_button("Template", get_template_excel(), "template.xlsx")
            up = st.file_uploader("Upload", type=['xlsx'])
            if up and st.button("Import"):
                d = pd.read_excel(up).fillna("")
                rows = []
                for i,r in d.iterrows():
                    if not check_serial_exists(df, str(r['Serial Number'])):
                        rows.append([r['Asset Type'], r['Manufacturer'], r['Model'], str(r['Serial Number']), 
                                     r.get('MAC Address',''), r.get('Status','Available/New'), "", "", r['Location'], "", get_timestamp(), "ADMIN BULK"])
                if rows: sheet.append_rows(rows); force_sync(); st.success(f"Imported {len(rows)} items")

        elif menu == "Database":
            st.title("📦 Database")
            st.download_button("Export", to_excel(df), f"Inv_{get_date_str()}.xlsx")
            st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()