import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from io import BytesIO
import plotly.express as px
from PIL import Image

# ==========================================
# 1. PROFESSIONAL CONFIGURATION
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Professional UI Theme */
    .stApp {background-color: #f4f6f9;}
    
    /* Login & Forms */
    div[data-testid="stForm"] {
        background: #ffffff;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border-top: 5px solid #cfaa5e;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        height: 45px;
        font-weight: 600;
    }
    
    /* Admin Controls */
    .admin-box {
        padding: 15px;
        border: 1px solid #ddd;
        border-radius: 8px;
        background-color: white;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Constants
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    from pyzbar.pyzbar import decode
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ==========================================
# 2. CONNECTION HANDLER
# ==========================================
@st.cache_resource
def get_client():
    try:
        if "gcp_service_account" not in st.secrets: return None, "Secrets Missing"
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in creds_dict:
            key = creds_dict["private_key"]
            if "\\n" in key: key = key.replace("\\n", "\n")
            creds_dict["private_key"] = key.strip('"')
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        client.open_by_key(SHEET_ID)
        return client, "Online"
    except Exception as e: return None, str(e)

def get_sheet_data(worksheet_name):
    client, status = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        try: return sh.worksheet(worksheet_name)
        except:
            if worksheet_name == "Users":
                ws = sh.add_worksheet(title="Users", rows="100", cols="3")
                ws.append_row(["Username", "PIN", "Permissions"])
                return ws
            return sh.sheet1
    except: return None

# ==========================================
# 3. CORE FUNCTIONS
# ==========================================
def download_data():
    ws = get_sheet_data("Sheet1")
    if not ws: return pd.DataFrame()
    try:
        raw = ws.get_all_values()
        if not raw: return pd.DataFrame()
        headers = raw[0]; rows = raw[1:]
        seen = {}; new_headers = []
        for h in headers:
            if h in seen: seen[h]+=1; new_headers.append(f"{h}_{seen[h]}")
            else: seen[h]=0; new_headers.append(h)
        return pd.DataFrame(rows, columns=new_headers)
    except: return pd.DataFrame()

def force_sync():
    st.session_state['inventory_df'] = download_data()

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_all_stores(df):
    valid_stores = set(FIXED_STORES)
    if not df.empty and 'Location' in df.columns:
        for s in df['Location'].unique():
            if str(s).strip() and str(s).upper() not in ["FAULTY", "USED", "NEW", "AVAILABLE", "ISSUED"]:
                valid_stores.add(str(s).strip())
    return sorted(list(valid_stores))

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    return output.getvalue()

def get_template():
    t = pd.DataFrame(columns=["Asset Type", "Manufacturer", "Model", "Serial Number", "MAC Address", "Status", "Location"])
    return to_excel(t)

# ==========================================
# 4. LOGIN SYSTEM
# ==========================================
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

def login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #333;'>Expo Asset Manager</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Professional Asset Tracking</p>", unsafe_allow_html=True)
        
        client, status = get_client()
        if "Online" in status: st.success("🟢 System Online")
        else: st.error(f"🔴 System Offline: {status}")

        t1, t2 = st.tabs(["Technician Login", "Admin Login"])
        with t1:
            users_df = pd.DataFrame(); user_list = []
            try:
                ws = get_sheet_data("Users")
                if ws:
                    users_df = pd.DataFrame(ws.get_all_records())
                    if not users_df.empty: user_list = users_df['Username'].tolist()
            except: pass
            
            with st.form("tech_form"):
                if user_list:
                    u = st.selectbox("Select Profile", user_list)
                    p = st.text_input("Access PIN", type="password")
                    if st.form_submit_button("Access Dashboard"):
                        row = users_df[users_df['Username']==u].iloc[0]
                        if str(row['PIN']) == str(p):
                            st.session_state['logged_in'] = True
                            st.session_state['role'] = "Technician"
                            st.session_state['user'] = u
                            perm = str(row['Permissions']).strip() if 'Permissions' in row else "Standard"
                            st.session_state['can_import'] = (perm == "Bulk_Allowed")
                            st.rerun()
                        else: st.error("Incorrect PIN")
                else:
                    st.info("System initializing... No users found.")
                    st.form_submit_button("Login", disabled=True)

        with t2:
            with st.form("admin_form"):
                p = st.text_input("Administrator Password", type="password")
                if st.form_submit_button("Enter Admin Panel"):
                    if p == ADMIN_PASSWORD:
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "Admin"
                        st.session_state['user'] = "Administrator"
                        st.session_state['can_import'] = True
                        st.rerun()
                    else: st.error("Access Denied")

# ==========================================
# 5. MAIN APPLICATION
# ==========================================
if not st.session_state['logged_in']:
    login_screen()
else:
    # SIDEBAR
    st.sidebar.markdown(f"### 👤 {st.session_state['user']}")
    st.sidebar.markdown(f"**Role:** {st.session_state['role']}")
    if st.sidebar.button("🔄 Refresh Data"):
        with st.spinner("Syncing..."): force_sync()
        st.success("Synced!"); time.sleep(0.5); st.rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Log Out"): st.session_state['logged_in'] = False; st.rerun()

    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = download_data()
    df = st.session_state['inventory_df']
    ws_inv = get_sheet_data("Sheet1")

    # ==========================
    # TECHNICIAN DASHBOARD
    # ==========================
    if st.session_state['role'] == "Technician":
        st.title("🛠️ Technician Dashboard")
        nav = st.selectbox("Navigate:", ["🚀 Issue Asset", "📥 Return Asset", "🎒 My Inventory", "➕ Add New Item", "⚡ Bulk Import"])
        st.divider()

        if nav == "🚀 Issue Asset":
            c1, c2 = st.columns([2, 1])
            with c1: search = st.text_input("Scan/Type Serial Number")
            with c2:
                if CAMERA_AVAILABLE:
                    cam = st.camera_input("Scanner")
                    if cam: 
                        try: search = decode(Image.open(cam))[0].data.decode("utf-8")
                        except: pass
            
            if search:
                match = df[df['Serial Number'].astype(str).str.strip().str.upper() == search.strip().upper()]
                if not match.empty:
                    item = match.iloc[0]
                    st.info(f"**Found:** {item['Model']} | {item['Status']}")
                    if "Available" in item['Status']:
                        with st.form("issue"):
                            tkt = st.text_input("Ticket #")
                            if st.form_submit_button("Confirm Issue"):
                                idx = match.index[0]+2
                                ws_inv.update_cell(idx, 6, "Issued")
                                ws_inv.update_cell(idx, 7, st.session_state['user'])
                                ws_inv.update_cell(idx, 8, tkt)
                                force_sync(); st.success("Issued!"); st.rerun()
                    else: st.warning("Not Available")
                else: st.error("Not Found")

        elif nav == "📥 Return Asset":
            my_items = df[(df['Issued To'] == st.session_state['user']) & (df['Status'] == 'Issued')]
            if my_items.empty: st.info("No items to return.")
            else:
                sel = st.selectbox("Select Asset", my_items['Serial Number'].tolist())
                with st.form("ret"):
                    c1,c2 = st.columns(2)
                    stat = c1.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    loc = c2.selectbox("Location", get_all_stores(df))
                    if st.form_submit_button("Return"):
                        idx = df[df['Serial Number']==sel].index[0]+2
                        ws_inv.update_cell(idx, 6, stat)
                        ws_inv.update_cell(idx, 7, st.session_state['user'] if stat=="Faulty" else "")
                        ws_inv.update_cell(idx, 9, loc)
                        force_sync(); st.success("Returned!"); st.rerun()

        elif nav == "🎒 My Inventory":
            st.dataframe(df[(df['Issued To'] == st.session_state['user']) & (df['Status'] == 'Issued')])

        elif nav == "➕ Add New Item":
            with st.form("add"):
                c1,c2 = st.columns(2)
                typ = c1.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
                man = c1.text_input("Make"); mod = c2.text_input("Model")
                sn = c2.text_input("Serial"); mac = c1.text_input("MAC")
                loc = c2.selectbox("Loc", get_all_stores(df))
                stat = st.selectbox("Stat", ["Available/New", "Available/Used"])
                if st.form_submit_button("Save"):
                    if sn not in df['Serial Number'].astype(str).tolist():
                        ws_inv.append_row([typ, man, mod, sn, mac, stat, "", "", loc, "", get_timestamp(), st.session_state['user']])
                        force_sync(); st.success("Saved!"); st.rerun()
                    else: st.error("Duplicate")

        elif nav == "⚡ Bulk Import":
            if st.session_state.get('can_import'):
                st.download_button("Template", get_template(), "template.xlsx")
                up = st.file_uploader("Upload Excel", type=['xlsx'])
                if up and st.button("Import"):
                    d = pd.read_excel(up).fillna("")
                    rows = []
                    for i,r in d.iterrows():
                        if str(r['Serial Number']) not in df['Serial Number'].astype(str).tolist():
                            rows.append([r.get('Asset Type',''), r.get('Manufacturer',''), r.get('Model',''), str(r['Serial Number']), 
                                         r.get('MAC Address',''), "Available/New", "", "", r.get('Location',''), "", get_timestamp(), "BULK"])
                    if rows: ws_inv.append_rows(rows); force_sync(); st.success(f"Imported {len(rows)}")
            else: st.error("Denied")

    # ==========================
    # ADMIN DASHBOARD (UPDATED)
    # ==========================
    elif st.session_state['role'] == "Admin":
        st.title("📊 Admin Control Panel")
        nav = st.sidebar.radio("Menu", ["Dashboard", "Manage Users", "Master Asset Control", "Database"])
        
        if nav == "Dashboard":
            if not df.empty:
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Total", len(df)); c2.metric("Available", len(df[df['Status'].str.contains('Available',na=False)]))
                c3.metric("Issued", len(df[df['Status']=='Issued'])); c4.metric("Faulty", len(df[df['Status']=='Faulty']))
                st.plotly_chart(px.pie(df, names='Status', title="Status Distribution"), use_container_width=True)

        elif nav == "Manage Users":
            st.subheader("👥 User Management")
            ws_u = get_sheet_data("Users")
            if ws_u:
                users_df = pd.DataFrame(ws_u.get_all_records())
                st.dataframe(users_df, use_container_width=True)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("##### ➕ Create User")
                    with st.form("new_u"):
                        u = st.text_input("Username"); p = st.text_input("PIN"); perm = st.selectbox("Perm", ["Standard", "Bulk_Allowed"])
                        if st.form_submit_button("Add"): ws_u.append_row([u, p, perm]); st.success("Added"); st.rerun()
                
                with c2:
                    st.markdown("##### ❌ Delete / Edit User")
                    target_u = st.selectbox("Select User to Modify", users_df['Username'].tolist() if not users_df.empty else [])
                    if target_u:
                        with st.form("mod_u"):
                            new_p = st.text_input("New PIN (Leave empty to keep)", type="password")
                            if st.form_submit_button("Update PIN"):
                                cell = ws_u.find(target_u)
                                ws_u.update_cell(cell.row, 2, new_p)
                                st.success("PIN Updated"); st.rerun()
                        
                        if st.button("🗑️ Delete Selected User"):
                            cell = ws_u.find(target_u)
                            ws_u.delete_rows(cell.row)
                            st.success("User Deleted"); st.rerun()

        elif nav == "Master Asset Control":
            st.subheader("🛠️ Master Asset Control")
            st.info("Directly modify asset status or delete assets from the database.")
            
            search_q = st.text_input("Search Asset by Serial Number")
            if search_q:
                match = df[df['Serial Number'].astype(str).str.contains(search_q, case=False)]
                if not match.empty:
                    sel_serial = st.selectbox("Select Asset", match['Serial Number'].tolist())
                    item = df[df['Serial Number'] == sel_serial].iloc[0]
                    idx = df[df['Serial Number'] == sel_serial].index[0] + 2
                    
                    st.write(f"**Selected:** {item['Model']} (Current: {item['Status']})")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        with st.form("mod_asset"):
                            n_stat = st.selectbox("Change Status To", ["Available/New", "Available/Used", "Issued", "Faulty", "Hold"])
                            n_loc = st.text_input("Update Location", item['Location'])
                            if st.form_submit_button("Update Asset"):
                                ws_inv.update_cell(idx, 6, n_stat)
                                ws_inv.update_cell(idx, 9, n_loc)
                                force_sync(); st.success("Updated!"); st.rerun()
                    
                    with c2:
                        st.write("### ⚠️ Danger Zone")
                        if st.button("🗑️ DELETE ASSET PERMANENTLY"):
                            ws_inv.delete_rows(idx)
                            force_sync(); st.success("Deleted!"); st.rerun()

        elif nav == "Database":
            st.subheader("📦 Database View")
            st.dataframe(df, use_container_width=True)
            st.download_button("Export Excel", to_excel(df), "inventory.xlsx")
