import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from io import BytesIO
import plotly.express as px

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. CSS & STYLING (Fixed to show Admin Box)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
            #MainMenu, footer, header {visibility: hidden !important;}
            [data-testid="stToolbar"] {visibility: hidden !important;}
            .block-container { padding-top: 1rem !important; }
            
            /* Login Box Styling */
            div[data-testid="stForm"] {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                border: 1px solid #ddd;
                border-top: 5px solid #cfaa5e;
            }
            .stButton>button {
                width: 100%; border-radius: 5px; font-weight: bold;
                background-color: #111; color: white; border: none;
                padding: 10px;
            }
            .stButton>button:hover { background-color: #333; color: white; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. SETUP & CONSTANTS
# ==========================================
try:
    from pyzbar.pyzbar import decode
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

ADMIN_PASSWORD = "admin123"
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]

# ⚠️ SHEET ID
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 4. CONNECTION (WITH KEY SCRUBBER)
# ==========================================
@st.cache_resource
def get_client():
    try:
        # 1. Load the secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 2. KEY SCRUBBER: Force-fix the private key format
        if "private_key" in creds_dict:
            raw_key = creds_dict["private_key"]
            # Replace literal "\n" characters with actual newlines
            fixed_key = raw_key.replace("\\n", "\n")
            creds_dict["private_key"] = fixed_key

        # 3. Connect
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        st.info("Tip: Go to Streamlit Settings -> Secrets and ensure your 'private_key' doesn't have extra spaces.")
        st.stop()

def get_inventory_sheet():
    client = get_client()
    try: return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        st.error(f"❌ Could not open Inventory Sheet: {e}")
        st.stop()

def get_users_sheet():
    client = get_client()
    try: 
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet("Users")
    except:
        # Auto-create Users tab if missing
        try:
            sh = client.open_by_key(SHEET_ID)
            ws = sh.add_worksheet(title="Users", rows="100", cols="3")
            ws.append_row(["Username", "PIN", "Permissions"])
            return ws
        except Exception as e:
            st.error(f"❌ Could not access/create 'Users' tab: {e}")
            st.stop()

# ==========================================
# 5. DATA FUNCTIONS
# ==========================================
@st.cache_data(ttl=600)  
def download_data():
    sheet = get_inventory_sheet()
    raw_data = sheet.get_all_values()
    if not raw_data: return pd.DataFrame()
    headers = raw_data[0]
    rows = raw_data[1:]
    # Fix duplicate headers
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
            s_str = str(s).strip()
            if s_str and s_str.lower() != 'nan' and s_str.upper() not in ["FAULTY", "USED", "NEW", "AVAILABLE", "ISSUED"]:
                valid_stores.add(s_str)
    return sorted(list(valid_stores))

def get_timestamp(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def get_date_str(): return datetime.now().strftime("%Y-%m-%d")

# ==========================================
# 6. AUTHENTICATION & SESSION
# ==========================================
def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
        st.session_state['user_role'] = None
        st.session_state['username'] = None
        st.session_state['can_import'] = False
        st.session_state['current_page'] = "Login"

    # Restore session from URL params if page refreshes
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

# ==========================================
# 7. LOGIN SCREEN (REBUILT)
# ==========================================
def login_screen():
    inject_custom_css()
    
    # Layout Centering
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        try: st.image("logo.png", width=180) 
        except: st.markdown("### Expo Asset Manager")
        
        st.markdown("##### Sign In")
        
        tab_tech, tab_admin = st.tabs(["Technician Login", "Admin Login"])
        
        # --- TECHNICIAN TAB ---
        with tab_tech:
            with st.form("tech_form"):
                try:
                    us = get_users_sheet()
                    data = us.get_all_records()
                    users_df = pd.DataFrame(data)
                    user_list = users_df['Username'].tolist() if not users_df.empty else []
                except:
                    user_list = []
                    st.warning("Could not load user list. Check connection.")

                u_sel = st.selectbox("Select User", user_list)
                p_in = st.text_input("Enter PIN", type="password")
                
                if st.form_submit_button("Login as Technician"):
                    if not users_df.empty:
                        user_row = users_df[users_df['Username'] == u_sel]
                        if not user_row.empty:
                            real_pin = str(user_row.iloc[0]['PIN'])
                            if real_pin == str(p_in):
                                # SUCCESS
                                st.session_state['logged_in'] = True
                                st.session_state['user_role'] = "Technician"
                                st.session_state['username'] = u_sel
                                perm = str(user_row.iloc[0]['Permissions'])
                                st.session_state['can_import'] = (perm == "Bulk_Allowed")
                                st.session_state['current_page'] = "Collect"
                                save_session(u_sel, "Technician", st.session_state['can_import'])
                                st.rerun()
                            else:
                                st.error("Incorrect PIN")
                        else:
                            st.error("User not found")
                    else:
                        st.error("Database is empty")

        # --- ADMIN TAB ---
        with tab_admin:
            with st.form("admin_form"):
                st.info("Enter Administrator Password")
                adm_pass = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login as Admin"):
                    if adm_pass == ADMIN_PASSWORD:
                        st.session_state['logged_in'] = True
                        st.session_state['user_role'] = "Admin"
                        st.session_state['username'] = "Administrator"
                        st.session_state['can_import'] = True
                        st.session_state['current_page'] = "Overview"
                        save_session("Administrator", "Admin", True)
                        st.rerun()
                    else:
                        st.error("Invalid Admin Password")

# ==========================================
# 8. MAIN APP LOGIC
# ==========================================
def main():
    if not st.session_state['logged_in']:
        login_screen()
        return

    inject_custom_css()
    
    # Sidebar
    try: st.sidebar.image("logo.png", width=140)
    except: pass
    st.sidebar.markdown(f"👤 **{st.session_state['username']}**")
    st.sidebar.caption(f"Role: {st.session_state['user_role']}")
    
    if st.sidebar.button("🔄 Sync Data"):
        with st.spinner("Syncing..."):
            force_sync()
        st.success("Synced!"); time.sleep(0.5); st.rerun()
    
    st.sidebar.divider()
    
    # Init Data
    init_data_state()
    df = st.session_state['inventory_df']
    sheet = get_inventory_sheet()

    # --- TECHNICIAN MENU ---
    if st.session_state['user_role'] == "Technician":
        # Navigation
        nav = st.sidebar.radio("Menu", ["Issue Asset", "Return Asset", "My Inventory", "Add Item", "Edit Details", "Bulk Import"])
        
        if st.sidebar.button("Log Out"): logout()

        if nav == "Issue Asset":
            st.title("🚀 Issue Asset")
            with st.container():
                c1, c2 = st.columns(2)
                scan_val = ""
                with c1: text_scan = st.text_input("Enter Serial", placeholder="Type Serial...")
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
                        item = match.iloc[0]
                        match_idx = match.index[0]
                        st.success(f"Found: {item['Model']} ({item['Status']})")
                        
                        if "Available" in item['Status']:
                            ticket = st.text_input("Ticket Number")
                            if st.button("Confirm Issue"):
                                idx = match_idx + 2
                                sheet.update_cell(idx, 6, "Issued")
                                sheet.update_cell(idx, 7, st.session_state['username'])
                                sheet.update_cell(idx, 8, ticket)
                                force_sync()
                                st.balloons()
                                st.success("Asset Issued Successfully!")
                        else:
                            st.warning(f"Cannot issue. Status is {item['Status']}")
                    else:
                        st.error("Serial Number not found.")

        elif nav == "Return Asset":
            st.title("📥 Return Asset")
            my_items = df[(df['Issued To'] == st.session_state['username']) & (df['Status'] == 'Issued')]
            if my_items.empty:
                st.info("You have no items to return.")
            else:
                sel_item = st.selectbox("Select Item", my_items['Serial Number'].tolist())
                if sel_item:
                    c1, c2 = st.columns(2)
                    new_stat = c1.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    new_loc = c2.selectbox("Location", get_all_stores(df))
                    
                    if st.button("Process Return"):
                        match_idx = df[df['Serial Number'] == sel_item].index[0]
                        idx = match_idx + 2
                        sheet.update_cell(idx, 6, new_stat)
                        sheet.update_cell(idx, 7, st.session_state['username'] if new_stat=="Faulty" else "")
                        sheet.update_cell(idx, 9, new_loc)
                        force_sync()
                        st.success("Return Processed!")
                        st.rerun()

        elif nav == "My Inventory":
            st.title("🎒 My Inventory")
            my_items = df[(df['Issued To'] == st.session_state['username']) & (df['Status'] == 'Issued')]
            st.dataframe(my_items)

        elif nav == "Add Item":
            st.title("➕ Add New Item")
            with st.form("add_item_form"):
                c1, c2 = st.columns(2)
                typ = c1.selectbox("Type", ["Camera", "Reader", "Controller", "Lock", "Accessory"])
                man = c2.text_input("Manufacturer")
                mod = c1.text_input("Model")
                sn = c2.text_input("Serial Number")
                mac = c1.text_input("MAC Address")
                loc = c2.selectbox("Location", get_all_stores(df))
                stat = st.selectbox("Status", ["Available/New", "Available/Used"])
                
                if st.form_submit_button("Add Item"):
                    if check_serial_exists(df, sn):
                        st.error("Serial Number already exists!")
                    else:
                        row = [typ, man, mod, sn, mac, stat, "", "", loc, "", get_timestamp(), st.session_state['username']]
                        sheet.append_row(row)
                        force_sync()
                        st.success("Item Added!")

        elif nav == "Edit Details":
            st.title("✏️ Edit Item Details")
            q = st.text_input("Search Serial to Edit")
            if q:
                match = df[df['Serial Number'].astype(str).str.contains(q, case=False)]
                if not match.empty:
                    sel = st.selectbox("Select", match['Serial Number'].tolist())
                    item_idx = df[df['Serial Number'] == sel].index[0]
                    
                    with st.form("edit_form"):
                        n_mod = st.text_input("Model", df.iloc[item_idx]['Model'])
                        n_mac = st.text_input("MAC", df.iloc[item_idx]['MAC Address'])
                        n_loc = st.selectbox("Location", get_all_stores(df), index=0) # simplified logic
                        
                        if st.form_submit_button("Save Changes"):
                            sheet.update_cell(item_idx+2, 3, n_mod)
                            sheet.update_cell(item_idx+2, 5, n_mac)
                            sheet.update_cell(item_idx+2, 9, n_loc)
                            force_sync()
                            st.success("Updated!")

        elif nav == "Bulk Import":
            if st.session_state['can_import']:
                st.title("⚡ Bulk Import")
                st.download_button("Download Template", get_template_excel(), "template.xlsx")
                up = st.file_uploader("Upload Excel", type=['xlsx'])
                if up:
                    if st.button("Run Import"):
                        d = pd.read_excel(up).fillna("")
                        count = 0
                        rows_to_add = []
                        for i, r in d.iterrows():
                            if not check_serial_exists(df, str(r['Serial Number'])):
                                rows_to_add.append([
                                    r['Asset Type'], r['Manufacturer'], r['Model'], str(r['Serial Number']),
                                    r.get('MAC Address',''), r.get('Status','Available/New'), "", "", r['Location'],
                                    "", get_timestamp(), "BULK_IMPORT"
                                ])
                                count += 1
                        if rows_to_add:
                            sheet.append_rows(rows_to_add)
                            force_sync()
                            st.success(f"Successfully imported {count} items!")
                        else:
                            st.warning("No new unique items found.")
            else:
                st.error("Access Denied. You do not have Bulk Import permissions.")

    # --- ADMIN MENU ---
    elif st.session_state['user_role'] == "Admin":
        nav = st.sidebar.radio("Admin Menu", ["Overview", "Manage Assets", "Manage Users", "Database"])
        if st.sidebar.button("Log Out"): logout()

        if nav == "Overview":
            st.title("📊 System Overview")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Assets", len(df))
            c2.metric("Issued", len(df[df['Status']=='Issued']))
            c3.metric("Available", len(df[df['Status'].str.contains('Available')]))
            
            st.subheader("Asset Distribution")
            st.plotly_chart(px.pie(df, names='Status'), use_container_width=True)

        elif nav == "Manage Assets":
            st.title("🛠️ Asset Manager")
            t1, t2 = st.tabs(["Add", "Delete"])
            with t1:
                st.write("Use the 'Add Item' form in Technician view or Bulk Import.")
            with t2:
                d
