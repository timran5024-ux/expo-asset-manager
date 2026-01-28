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
# 1. CONFIGURATION
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp {background-color: #f4f6f9;}
    div[data-testid="stForm"] {background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); border-top: 5px solid #cfaa5e;}
    .stButton>button {width: 100%; border-radius: 6px; height: 45px; font-weight: 600;}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# THE MASTER HEADER LIST (Matches your Yellow Picture + System fields)
EXPECTED_HEADERS = [
    "ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", 
    "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"
]

try:
    from pyzbar.pyzbar import decode
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# ==========================================
# 2. CONNECTION
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
# 3. CORE LOGIC (ROBUST DATA LOADER)
# ==========================================
def download_data():
    ws = get_sheet_data("Sheet1")
    # Return empty strict frame if connection fails
    if not ws: return pd.DataFrame(columns=EXPECTED_HEADERS)
    
    try:
        raw = ws.get_all_values()
        if not raw: return pd.DataFrame(columns=EXPECTED_HEADERS)
        
        # 1. Raw Headers
        headers = raw[0]
        rows = raw[1:]
        
        # 2. Create DataFrame
        df = pd.DataFrame(rows, columns=headers)
        
        # 3. Normalize Headers (Upper case + Strip)
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # 4. CRITICAL FIX: Map Old Names to New Names (Prevent KeyError)
        rename_map = {
            "SERIAL NUMBER": "SERIAL",
            "MANUFACTURER": "BRAND",
            "STATUS": "CONDITION",
            "MAC": "MAC ADDRESS",
            "TYPE": "ASSET TYPE",
            "LOC": "LOCATION"
        }
        df.rename(columns=rename_map, inplace=True)
        
        # 5. Ensure all EXPECTED headers exist
        for col in EXPECTED_HEADERS:
            if col not in df.columns:
                df[col] = ""
                
        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame(columns=EXPECTED_HEADERS)

def force_sync():
    st.session_state['inventory_df'] = download_data()

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_all_stores(df):
    valid_stores = set(FIXED_STORES)
    if not df.empty and 'LOCATION' in df.columns:
        for s in df['LOCATION'].unique():
            if str(s).strip() and str(s).upper() not in ["FAULTY", "USED", "NEW", "AVAILABLE", "ISSUED", ""]:
                valid_stores.add(str(s).strip())
    return sorted(list(valid_stores))

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    return output.getvalue()

def get_template():
    t = pd.DataFrame(columns=EXPECTED_HEADERS)
    return to_excel(t)

# ==========================================
# 4. LOGIN
# ==========================================
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

def login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #333;'>Expo Asset Manager</h1>", unsafe_allow_html=True)
        
        client, status = get_client()
        if "Online" in status: st.success("🟢 System Online")
        else: st.error(f"🔴 System Offline: {status}")

        t1, t2 = st.tabs(["Technician", "Admin"])
        with t1:
            users_df = pd.DataFrame(); user_list = []
            try:
                ws = get_sheet_data("Users")
                if ws:
                    users_df = pd.DataFrame(ws.get_all_records())
                    if not users_df.empty: user_list = users_df['Username'].tolist()
            except: pass
            
            with st.form("tech"):
                if user_list:
                    u = st.selectbox("Username", user_list)
                    p = st.text_input("PIN", type="password")
                    if st.form_submit_button("Login"):
                        row = users_df[users_df['Username']==u].iloc[0]
                        if str(row['PIN']) == str(p):
                            st.session_state['logged_in'] = True; st.session_state['role'] = "Technician"; st.session_state['user'] = u
                            st.session_state['can_import'] = (str(row.get('Permissions','')) == "Bulk_Allowed")
                            st.rerun()
                        else: st.error("Wrong PIN")
                else: st.warning("No users found."); st.form_submit_button("Login", disabled=True)

        with t2:
            with st.form("admin"):
                p = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    if p == ADMIN_PASSWORD:
                        st.session_state['logged_in'] = True; st.session_state['role'] = "Admin"; st.session_state['user'] = "Administrator"
                        st.session_state['can_import'] = True
                        st.rerun()
                    else: st.error("Access Denied")

# ==========================================
# 5. APP LOGIC
# ==========================================
if not st.session_state['logged_in']:
    login_screen()
else:
    st.sidebar.markdown(f"### 👤 {st.session_state['user']}")
    st.sidebar.markdown(f"**Role:** {st.session_state['role']}")
    if st.sidebar.button("🔄 Sync"): force_sync(); st.success("Synced!"); time.sleep(0.5); st.rerun()
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"): st.session_state['logged_in'] = False; st.rerun()

    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = download_data()
    df = st.session_state['inventory_df']
    ws_inv = get_sheet_data("Sheet1")

    # Force headers if empty
    if ws_inv and not ws_inv.get_all_values():
        ws_inv.append_row(EXPECTED_HEADERS)
        force_sync()

    # --- TECHNICIAN ---
    if st.session_state['role'] == "Technician":
        st.title("🛠️ Technician Dashboard")
        nav = st.selectbox("Menu", ["🚀 Issue Asset", "📥 Return Asset", "🎒 My Inventory", "➕ Add Asset", "⚡ Bulk Import"])
        st.divider()

        if nav == "🚀 Issue Asset":
            c1, c2 = st.columns([2, 1])
            with c1: search = st.text_input("Enter Serial Number")
            with c2:
                if CAMERA_AVAILABLE:
                    cam = st.camera_input("Scan QR")
                    if cam: 
                        try: search = decode(Image.open(cam))[0].data.decode("utf-8")
                        except: pass
            
            if search:
                # Robust match against 'SERIAL'
                match = df[df['SERIAL'].astype(str).str.strip().str.upper() == search.strip().upper()]
                if not match.empty:
                    item = match.iloc[0]
                    st.info(f"Found: {item['MODEL']} | {item['CONDITION']}")
                    if "Available" in str(item['CONDITION']):
                        with st.form("issue"):
                            tkt = st.text_input("Ticket #")
                            if st.form_submit_button("Confirm Issue"):
                                idx = match.index[0]+2
                                # Mapped to EXPECTED_HEADERS indices:
                                # 0:TYPE, 1:BRAND, 2:MODEL, 3:SERIAL, 4:MAC, 5:COND, 6:LOC, 7:ISSUED, 8:TICKET
                                ws_inv.update_cell(idx, 6, "Issued") # Col F (Condition)
                                ws_inv.update_cell(idx, 8, st.session_state['user']) # Col H (Issued To)
                                ws_inv.update_cell(idx, 9, tkt) # Col I (Ticket)
                                force_sync(); st.success("Issued!"); st.rerun()
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
                    loc = c2.selectbox("Location", get_all_stores(df))
                    if st.form_submit_button("Return"):
                        idx = df[df['SERIAL']==sel].index[0]+2
                        ws_inv.update_cell(idx, 6, stat) # Condition
                        ws_inv.update_cell(idx, 7, loc) # Location
                        ws_inv.update_cell(idx, 8, "") # Issued To (Clear)
                        force_sync(); st.success("Returned!"); st.rerun()

        elif nav == "➕ Add Asset":
            with st.form("add"):
                c1,c2 = st.columns(2)
                typ = c1.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
                man = c1.text_input("Brand"); mod = c2.text_input("Model")
                sn = c2.text_input("Serial"); mac = c1.text_input("MAC")
                loc = c2.selectbox("Location", get_all_stores(df))
                stat = st.selectbox("Condition", ["Available/New", "Available/Used"])
                if st.form_submit_button("Save"):
                    if sn not in df['SERIAL'].astype(str).tolist():
                        # [Type, Brand, Model, Serial, Mac, Cond, Loc, Issued, Ticket, Time, User]
                        ws_inv.append_row([typ, man, mod, sn, mac, stat, loc, "", "", get_timestamp(), st.session_state['user']])
                        force_sync(); st.success("Saved!"); st.rerun()
                    else: st.error("Duplicate Serial")

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
            ws_u = get_sheet_data("Users")
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
                    # Text Input for flexible Asset Type
                    atype = c1.text_input("Asset Type (e.g. Camera, Laptop)")
                    brand = c2.text_input("Brand")
                    model = c3.text_input("Model")
                    
                    c4, c5, c6 = st.columns(3)
                    serial = c4.text_input("Serial")
                    mac = c5.text_input("MAC Address")
                    cond = c6.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    
                    c7, c8 = st.columns(2)
                    loc = c7.selectbox("Location", get_all_stores(df))
                    qty = c8.number_input("Quantity", 1, 100, 1)
                    
                    if st.form_submit_button("Add Asset"):
                        if not atype: st.error("Type Required")
                        elif not serial and qty == 1: st.error("Serial Required")
                        elif serial in df['SERIAL'].astype(str).tolist(): st.error("Duplicate")
                        else:
                            rows = []
                            for i in range(qty):
                                s = serial if qty==1 else f"{serial}-{i+1}"
                                # Order: [Type, Brand, Model, Serial, Mac, Cond, Loc, Issued, Ticket, Time, User]
                                rows.append([atype, brand, model, s, mac, cond, loc, "", "", get_timestamp(), "ADMIN"])
                            ws_inv.append_rows(rows)
                            force_sync(); st.success(f"Added {qty} items"); st.rerun()

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
                                    force_sync(); st.success("Updated"); st.rerun()
                        with c2:
                            if st.button("DELETE PERMANENTLY"):
                                ws_inv.delete_rows(idx); force_sync(); st.success("Deleted"); st.rerun()

        elif nav == "Database":
            st.dataframe(df, use_container_width=True)
            st.download_button("Export", to_excel(df), "data.xlsx")
