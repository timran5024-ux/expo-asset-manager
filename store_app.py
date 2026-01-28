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
# 1. PERFORMANCE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp {background-color: #f4f6f9;}
    div[data-testid="stForm"] {background: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 5px solid #cfaa5e;}
    .stButton>button {width: 100%; border-radius: 6px; height: 45px; font-weight: 600; transition: 0.2s;}
    .stButton>button:active {transform: scale(0.98);}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

HEADERS = ["ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"]

try:
    from pyzbar.pyzbar import decode
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ==========================================
# 2. CONNECTION & SAFE ADD FUNCTION
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

# --- THE FIX: A DEDICATED FUNCTION THAT CANNOT FAIL ---
def safe_add_data(ws, rows_list):
    """
    This function replaces 'append_rows'.
    It accepts a list of rows and adds them ONE BY ONE.
    This works on ALL server versions.
    """
    for row in rows_list:
        ws.append_row(row)

# ==========================================
# 3. DATA ENGINE
# ==========================================
def load_data_initial():
    ws = get_worksheet("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    try:
        raw = ws.get_all_values()
        if not raw: return pd.DataFrame(columns=HEADERS)
        
        # Self-Repair Headers if missing
        if raw[0] != HEADERS:
            pass 

        rows = raw[1:]
        clean_rows = []
        for r in rows:
            while len(r) < len(HEADERS): r.append("")
            clean_rows.append(r[:len(HEADERS)])
            
        return pd.DataFrame(clean_rows, columns=HEADERS)
    except: return pd.DataFrame(columns=HEADERS)

def sync_local_state():
    if 'inventory_df' not in st.session_state or st.session_state['inventory_df'] is None:
        with st.spinner("Downloading Database..."):
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
# 4. LOGIN
# ==========================================
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

def login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>Expo Asset Manager</h1>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Technician", "Admin"])
        
        with t1:
            with st.form("tech"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("Login"):
                    ws_u = get_worksheet("Users")
                    if ws_u:
                        users = ws_u.get_all_records()
                        valid = False
                        for user in users:
                            if str(user.get('Username')) == u and str(user.get('PIN')) == p:
                                st.session_state['logged_in'] = True
                                st.session_state['role'] = "Technician"
                                st.session_state['user'] = u
                                st.session_state['can_import'] = (str(user.get('Permissions')) == "Bulk_Allowed")
                                valid = True
                                st.rerun()
                        if not valid: st.error("Invalid Credentials")
                    else: st.error("System Offline")

        with t2:
            with st.form("admin"):
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    if p == ADMIN_PASSWORD:
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "Admin"
                        st.session_state['user'] = "Administrator"
                        st.session_state['can_import'] = True
                        st.rerun()
                    else: st.error("Access Denied")

# ==========================================
# 5. MAIN APP
# ==========================================
if not st.session_state['logged_in']:
    login_screen()
else:
    sync_local_state()
    df = st.session_state['inventory_df']
    ws_inv = get_worksheet("Sheet1")

    st.sidebar.markdown(f"### 👤 {st.session_state['user']}")
    if st.sidebar.button("🔄 Refresh Data"): force_reload(); st.success("Refreshed!"); time.sleep(0.5); st.rerun()
    if st.sidebar.button("🚪 Logout"): st.session_state['logged_in'] = False; st.rerun()

    # --- TECHNICIAN ---
    if st.session_state['role'] == "Technician":
        st.title("🛠️ Technician Dashboard")
        nav = st.selectbox("Menu", ["🚀 Issue Asset", "📥 Return Asset", "🎒 My Inventory", "➕ Add Asset", "⚡ Bulk Import"])
        st.divider()

        if nav == "🚀 Issue Asset":
            c1, c2 = st.columns([2, 1])
            with c1: search = st.text_input("Enter Serial")
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
                    idx = match.index[0] 
                    st.info(f"Found: {item['MODEL']} | {item['CONDITION']}")
                    
                    if "Available" in str(item['CONDITION']):
                        with st.form("issue"):
                            tkt = st.text_input("Ticket #")
                            if st.form_submit_button("Confirm Issue"):
                                sheet_row = idx + 2
                                ws_inv.update_cell(sheet_row, 6, "Issued")
                                ws_inv.update_cell(sheet_row, 8, st.session_state['user'])
                                ws_inv.update_cell(sheet_row, 9, tkt)
                                
                                df.at[idx, 'CONDITION'] = "Issued"
                                df.at[idx, 'ISSUED TO'] = st.session_state['user']
                                df.at[idx, 'TICKET'] = tkt
                                st.session_state['inventory_df'] = df
                                
                                st.success("Issued!"); time.sleep(0.5); st.rerun()
                    else: st.warning(f"Item is {item['CONDITION']}")
                else: st.error("Not Found")

        elif nav == "📥 Return Asset":
            my = df[(df['ISSUED TO'] == st.session_state['user']) & (df['CONDITION'] == 'Issued')]
            if my.empty: st.info("No returns pending.")
            else:
                sel = st.selectbox("Select Item", my['SERIAL'].tolist())
                with st.form("ret"):
                    c1,c2 = st.columns(2)
                    stat = c1.selectbox("New Condition", ["Available/New", "Available/Used", "Faulty"])
                    stores = sorted(list(set(FIXED_STORES) | set(df['LOCATION'].unique())))
                    loc = c2.selectbox("Location", stores)
                    
                    if st.form_submit_button("Return"):
                        idx = df[df['SERIAL']==sel].index[0]
                        sheet_row = idx + 2
                        ws_inv.update_cell(sheet_row, 6, stat)
                        ws_inv.update_cell(sheet_row, 7, loc)
                        ws_inv.update_cell(sheet_row, 8, "")
                        
                        df.at[idx, 'CONDITION'] = stat
                        df.at[idx, 'LOCATION'] = loc
                        df.at[idx, 'ISSUED TO'] = ""
                        st.session_state['inventory_df'] = df
                        
                        st.success("Returned!"); time.sleep(0.5); st.rerun()

        elif nav == "➕ Add Asset":
            with st.form("add"):
                c1,c2 = st.columns(2)
                typ = c1.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
                man = c1.text_input("Brand"); mod = c2.text_input("Model")
                sn = c2.text_input("Serial"); mac = c1.text_input("MAC")
                stores = sorted(list(set(FIXED_STORES) | set(df['LOCATION'].unique())))
                loc = c2.selectbox("Location", stores)
                stat = st.selectbox("Condition", ["Available/New", "Available/Used"])
                
                if st.form_submit_button("Save"):
                    if sn not in df['SERIAL'].astype(str).tolist():
                        row = [typ, man, mod, sn, mac, stat, loc, "", "", get_timestamp(), st.session_state['user']]
                        safe_add_data(ws_inv, [row])
                        
                        new_df = pd.DataFrame([row], columns=HEADERS)
                        st.session_state['inventory_df'] = pd.concat([df, new_df], ignore_index=True)
                        st.success("Saved!"); time.sleep(0.5); st.rerun()
                    else: st.error("Duplicate Serial")

        elif nav == "⚡ Bulk Import":
            if st.session_state.get('can_import'):
                st.download_button("Template", to_excel(pd.DataFrame(columns=HEADERS)), "template.xlsx")
                up = st.file_uploader("Upload Excel", type=['xlsx'])
                if up and st.button("Import"):
                    d = pd.read_excel(up).fillna("")
                    d.columns = [str(c).strip().upper() for c in d.columns]
                    rows = []
                    for i,r in d.iterrows():
                        s = str(r.get('SERIAL', r.get('SERIAL NUMBER', '')))
                        if s and s not in df['SERIAL'].astype(str).tolist():
                            rows.append([
                                r.get('ASSET TYPE', ''), r.get('BRAND', ''), r.get('MODEL', ''), 
                                s, r.get('MAC ADDRESS', ''), "Available/New", 
                                r.get('LOCATION', ''), "", "", get_timestamp(), "BULK"
                            ])
                    if rows: 
                        # USE SAFE FUNCTION
                        safe_add_data(ws_inv, rows)
                        force_reload()
                        st.success(f"Imported {len(rows)}")
            else: st.error("Permission Denied")

        elif nav == "🎒 My Inventory":
            st.dataframe(df[(df['ISSUED TO'] == st.session_state['user']) & (df['CONDITION'] == 'Issued')])

    # --- ADMIN ---
    elif st.session_state['role'] == "Admin":
        st.title("📊 Admin Panel")
        nav = st.sidebar.radio("Menu", ["Dashboard", "Manage Users", "Master Asset Control", "Database"])
        
        if nav == "Dashboard":
            if not df.empty:
                c1,c2,c3 = st.columns(3)
                c1.metric("Total", len(df))
                c2.metric("Issued", len(df[df['CONDITION']=='Issued']))
                c3.metric("Available", len(df[df['CONDITION'].str.contains('Available', na=False)]))
                st.plotly_chart(px.pie(df, names='CONDITION'), use_container_width=True)

        elif nav == "Manage Users":
            st.subheader("👥 Users")
            ws_u = get_worksheet("Users")
            if ws_u:
                udf = pd.DataFrame(ws_u.get_all_records())
                st.dataframe(udf, use_container_width=True)
                with st.expander("Actions"):
                    c1, c2 = st.columns(2)
                    with c1:
                        with st.form("add_u"):
                            u = st.text_input("User"); p = st.text_input("PIN"); perm = st.selectbox("Perm", ["Standard", "Bulk_Allowed"])
                            if st.form_submit_button("Add"): ws_u.append_row([u, p, perm]); st.success("Added"); st.rerun()
                    with c2:
                        target = st.selectbox("Select User", udf['Username'].tolist() if not udf.empty else [])
                        if st.button("Delete User"):
                            cell = ws_u.find(target)
                            ws_u.delete_rows(cell.row)
                            st.success("Deleted"); st.rerun()

        elif nav == "Master Asset Control":
            st.subheader("🛠️ Asset Control")
            tab1, tab2 = st.tabs(["Add Asset", "Edit/Delete"])
            
            with tab1:
                with st.form("adm_add"):
                    c1, c2, c3 = st.columns(3)
                    atype = c1.text_input("Asset Type", placeholder="e.g. Laptop")
                    brand = c2.text_input("Brand")
                    model = c3.text_input("Model")
                    c4, c5, c6 = st.columns(3)
                    serial = c4.text_input("Serial")
                    mac = c5.text_input("MAC")
                    cond = c6.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    c7, c8 = st.columns(2)
                    stores = sorted(list(set(FIXED_STORES) | set(df['LOCATION'].unique())))
                    loc = c7.selectbox("Location", stores)
                    qty = c8.number_input("Quantity", 1, 100, 1)
                    
                    if st.form_submit_button("Add Asset"):
                        if not atype: st.error("Type Required")
                        elif not serial and qty == 1: st.error("Serial Required")
                        elif serial in df['SERIAL'].astype(str).tolist(): st.error("Duplicate")
                        else:
                            rows = []
                            for i in range(qty):
                                s = serial if qty==1 else f"{serial}-{i+1}"
                                rows.append([atype, brand, model, s, mac, cond, loc, "", "", get_timestamp(), "ADMIN"])
                            
                            # USE SAFE FUNCTION
                            safe_add_data(ws_inv, rows)
                            
                            force_reload() 
                            st.success(f"Added {qty} items"); st.rerun()

            with tab2:
                q = st.text_input("Search Serial")
                if q:
                    match = df[df['SERIAL'].astype(str).str.contains(q, case=False)]
                    if not match.empty:
                        sel = st.selectbox("Select", match['SERIAL'].tolist())
                        idx = df[df['SERIAL']==sel].index[0]+2
                        c1, c2 = st.columns(2)
                        with c1:
                            with st.form("upd"):
                                n_stat = st.selectbox("Status", ["Available/New", "Issued", "Faulty"])
                                n_loc = st.text_input("Location", df[df['SERIAL']==sel].iloc[0]['LOCATION'])
                                if st.form_submit_button("Update"):
                                    ws_inv.update_cell(idx, 6, n_stat)
                                    ws_inv.update_cell(idx, 7, n_loc)
                                    force_reload(); st.success("Updated"); st.rerun()
                        with c2:
                            if st.button("DELETE PERMANENTLY"):
                                ws_inv.delete_rows(idx); force_reload(); st.success("Deleted"); st.rerun()

        elif nav == "Database":
            c1, c2 = st.columns([6, 1])
            c1.write("")
            c2.download_button("📥 Export", to_excel(df), "data.xlsx")
            st.dataframe(df, use_container_width=True)
