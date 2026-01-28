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
# 1. PAGE CONFIG & CSS
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide")

st.markdown("""
<style>
    /* Make the login box look clean */
    div[data-testid="stForm"] {background: #ffffff; padding: 25px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-top: 5px solid #cfaa5e;}
    .stButton>button {width: 100%; border-radius: 5px; font-weight: 600;}
    /* Status indicators */
    .success-box {padding: 10px; border-radius: 5px; background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb;}
    .error-box {padding: 10px; border-radius: 5px; background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS
# ==========================================
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
# 3. CONNECTION (SUPER KEY CLEANER)
# ==========================================
@st.cache_resource
def get_client():
    try:
        # 1. Load Secrets
        if "gcp_service_account" not in st.secrets:
            return None, "Secrets Missing"

        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 2. AGGRESSIVE KEY FIXING (The Fixer)
        if "private_key" in creds_dict:
            key = creds_dict["private_key"]
            # Remove external quotes if user accidentally pasted them
            key = key.strip('"').strip("'")
            # Convert literal "\n" to real newlines
            key = key.replace("\\n", "\n")
            # Ensure it has the correct headers
            if "-----BEGIN PRIVATE KEY-----" not in key:
                key = "-----BEGIN PRIVATE KEY-----\n" + key
            if "-----END PRIVATE KEY-----" not in key:
                key = key + "\n-----END PRIVATE KEY-----"
            creds_dict["private_key"] = key

        # 3. Connect
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        return client, "Success"
    except Exception as e:
        return None, str(e)

def get_sheet_data(worksheet_name):
    client, status = get_client()
    if not client:
        return None  # Fail silently to avoid crashing the app
    try:
        sh = client.open_by_key(SHEET_ID)
        try:
            return sh.worksheet(worksheet_name)
        except:
            # Auto-create Users tab if missing
            if worksheet_name == "Users":
                ws = sh.add_worksheet(title="Users", rows="100", cols="3")
                ws.append_row(["Username", "PIN", "Permissions"])
                return ws
            return sh.sheet1
    except:
        return None

# ==========================================
# 4. DATA FUNCTIONS
# ==========================================
@st.cache_data(ttl=600)
def download_data():
    ws = get_sheet_data("Sheet1")
    if not ws: return pd.DataFrame() # Return empty if connection fails
    try:
        raw_data = ws.get_all_values()
        if not raw_data: return pd.DataFrame()
        headers = raw_data[0]
        rows = raw_data[1:]
        seen = {}; new_headers = []
        for h in headers:
            if h in seen: seen[h]+=1; new_headers.append(f"{h}_{seen[h]}")
            else: seen[h]=0; new_headers.append(h)
        return pd.DataFrame(rows, columns=new_headers)
    except:
        return pd.DataFrame()

def force_sync():
    st.cache_data.clear()
    st.session_state['inventory_df'] = download_data()

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    return output.getvalue()

def get_all_stores(df):
    if df.empty: return FIXED_STORES
    valid_stores = set(FIXED_STORES)
    if 'Location' in df.columns:
        db_vals = df['Location'].unique().tolist()
        for s in db_vals:
            s_str = str(s).strip()
            if s_str and s_str.lower() != 'nan' and s_str.upper() not in ["FAULTY", "USED", "NEW", "AVAILABLE", "ISSUED"]:
                valid_stores.add(s_str)
    return sorted(list(valid_stores))

# ==========================================
# 5. LOGIN LOGIC (NON-BLOCKING)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login_screen():
    st.markdown("<h1 style='text-align: center;'>Expo Asset Manager</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Cloud Edition ☁️</p>", unsafe_allow_html=True)
    
    # Check Connection Status quietly
    client, status = get_client()
    if "Success" not in status:
        st.markdown(f"<div class='error-box'>⚠️ Cloud Connection Issue: {status} <br> (You can still login as Admin to check settings)</div>", unsafe_allow_html=True)

    t1, t2 = st.tabs(["Technician", "Admin"])
    
    # --- TECHNICIAN TAB ---
    with t1:
        st.write("### Technician Access")
        users_df = pd.DataFrame()
        user_list = []
        
        # Try to load users, but DO NOT CRASH if it fails
        try:
            ws = get_sheet_data("Users")
            if ws:
                users_df = pd.DataFrame(ws.get_all_records())
                if not users_df.empty: user_list = users_df['Username'].tolist()
        except: pass
        
        with st.form("tech_login"):
            if user_list:
                u = st.selectbox("Username", user_list)
                p = st.text_input("PIN Code", type="password")
                if st.form_submit_button("Sign In"):
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
                st.warning("Cannot load users. System Offline or Empty.")
                st.form_submit_button("Sign In", disabled=True)

    # --- ADMIN TAB ---
    with t2:
        st.write("### Admin Access")
        with st.form("admin_login"):
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Authenticate"):
                if p == ADMIN_PASSWORD:
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = "Admin"
                    st.session_state['user'] = "Administrator"
                    st.session_state['can_import'] = True
                    st.rerun()
                else: st.error("Invalid Password")

# ==========================================
# 6. MAIN APP
# ==========================================
if not st.session_state['logged_in']:
    login_screen()
else:
    # --- SIDEBAR ---
    st.sidebar.markdown(f"👤 **{st.session_state['user']}**")
    st.sidebar.caption(f"Role: {st.session_state['role']}")
    
    # Test Connection Indicator
    client, status = get_client()
    if "Success" in status:
        st.sidebar.success("🟢 Online")
    else:
        st.sidebar.error("🔴 Offline")
        
    if st.sidebar.button("🔄 Sync"): force_sync(); st.rerun()
    if st.sidebar.button("Log Out"): st.session_state['logged_in'] = False; st.rerun()
    st.sidebar.divider()

    # --- LOAD DATA ---
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = download_data()
    df = st.session_state['inventory_df']
    
    # Try to get sheet writer
    ws_inv = get_sheet_data("Sheet1")

    # --- TECHNICIAN VIEW ---
    if st.session_state['role'] == "Technician":
        nav = st.sidebar.radio("Menu", ["Issue Asset", "Return Asset", "My Inventory", "Add Item", "Bulk Import"])
        
        if nav == "Issue Asset":
            st.title("🚀 Issue Asset")
            if df.empty: st.error("Database unavailable.")
            else:
                c1, c2 = st.columns(2)
                scan_val = ""
                with c1: text_scan = st.text_input("Search Serial")
                with c2:
                    if CAMERA_AVAILABLE:
                        cam = st.camera_input("Scan QR")
                        if cam:
                            try: scan_val = decode(Image.open(cam))[0].data.decode("utf-8")
                            except: pass
                if text_scan: scan_val = text_scan.strip()
                
                if scan_val:
                    match = df[df['Serial Number'].astype(str).str.strip().str.upper() == scan_val.upper()]
                    if not match.empty:
                        item = match.iloc[0]; idx = match.index[0]
                        st.info(f"**Found:** {item['Model']} | **Status:** {item['Status']}")
                        if "Available" in item['Status']:
                            tkt = st.text_input("Ticket Number")
                            if st.button("Confirm Issue"):
                                if ws_inv:
                                    ws_inv.update_cell(idx+2, 6, "Issued")
                                    ws_inv.update_cell(idx+2, 7, st.session_state['user'])
                                    ws_inv.update_cell(idx+2, 8, tkt)
                                    force_sync(); st.success("Issued!"); st.rerun()
                                else: st.error("Cannot write to sheet.")
                        else: st.warning("Not available.")
                    else: st.error("Not found.")

        elif nav == "Return Asset":
            st.title("📥 Return Asset")
            if df.empty: st.error("Database unavailable.")
            else:
                my = df[(df['Issued To'] == st.session_state['user']) & (df['Status'] == 'Issued')]
                if my.empty: st.info("No pending returns.")
                else:
                    sel = st.selectbox("Select", my['Serial Number'].tolist())
                    c1, c2 = st.columns(2)
                    stat = c1.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    loc = c2.selectbox("Location", get_all_stores(df))
                    if st.button("Return"):
                        idx = df[df['Serial Number']==sel].index[0]
                        if ws_inv:
                            ws_inv.update_cell(idx+2, 6, stat)
                            ws_inv.update_cell(idx+2, 7, st.session_state['user'] if stat=="Faulty" else "")
                            ws_inv.update_cell(idx+2, 9, loc)
                            force_sync(); st.success("Returned!"); st.rerun()

        elif nav == "My Inventory":
            st.title("🎒 My Items")
            if not df.empty: st.dataframe(df[(df['Issued To'] == st.session_state['user']) & (df['Status'] == 'Issued')])

        elif nav == "Add Item":
            st.title("➕ Add Asset")
            with st.form("add"):
                c1,c2 = st.columns(2)
                typ = c1.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
                man = c1.text_input("Make"); mod = c2.text_input("Model")
                sn = c2.text_input("Serial"); mac = c1.text_input("MAC")
                loc = c2.selectbox("Location", get_all_stores(df))
                stat = st.selectbox("Status", ["Available/New", "Available/Used"])
                if st.form_submit_button("Add"):
                    if ws_inv:
                        if sn not in df['Serial Number'].astype(str).tolist():
                            ws_inv.append_row([typ, man, mod, sn, mac, stat, "", "", loc, "", get_timestamp(), st.session_state['user']])
                            force_sync(); st.success("Added!"); st.rerun()
                        else: st.error("Duplicate!")
                    else: st.error("Connection Offline")

        elif nav == "Bulk Import":
            st.title("⚡ Bulk Import")
            if st.session_state.get('can_import'):
                up = st.file_uploader("Upload .xlsx", type=['xlsx'])
                if up and st.button("Import"):
                    if ws_inv:
                        d = pd.read_excel(up).fillna("")
                        rows = []
                        for i,r in d.iterrows():
                             if str(r['Serial Number']) not in df['Serial Number'].astype(str).tolist():
                                 rows.append([r['Asset Type'], r['Manufacturer'], r['Model'], str(r['Serial Number']), 
                                              r.get('MAC Address',''), "Available/New", "", "", r['Location'], "", get_timestamp(), "BULK"])
                        if rows: ws_inv.append_rows(rows); force_sync(); st.success(f"Imported {len(rows)}")
                    else: st.error("Offline")
            else: st.error("Permission Denied")

    # --- ADMIN VIEW ---
    elif st.session_state['role'] == "Admin":
        nav = st.sidebar.radio("Admin", ["Overview", "Manage Users", "Database"])
        
        if nav == "Overview":
            st.title("📊 System Overview")
            if not df.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Total", len(df))
                c2.metric("Issued", len(df[df['Status']=='Issued']))
                c3.metric("Available", len(df[df['Status'].str.contains('Available', na=False)]))
                st.plotly_chart(px.pie(df, names='Status'), use_container_width=True)
            else: st.warning("No Data Available")

        elif nav == "Manage Users":
            st.title("👥 Users")
            ws_u = get_sheet_data("Users")
            if ws_u:
                st.dataframe(pd.DataFrame(ws_u.get_all_records()), use_container_width=True)
                with st.expander("Add User"):
                    u = st.text_input("User"); p = st.text_input("PIN"); perm = st.selectbox("Perm", ["Standard", "Bulk_Allowed"])
                    if st.button("Create"): ws_u.append_row([u, p, perm]); st.success("Created"); st.rerun()
            else: st.error("Users Sheet Unavailable")

        elif nav == "Database":
            st.title("📦 Database")
            st.dataframe(df, use_container_width=True)
            st.download_button("Export", to_excel(df), "inv.xlsx")
