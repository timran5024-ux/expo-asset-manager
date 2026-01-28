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
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide")

# ==========================================
# 2. CSS (SAFE MODE - NO HIDING)
# ==========================================
def inject_custom_css():
    st.markdown("""
        <style>
            .stApp { background-color: #f8f9fa; }
            div[data-testid="stForm"] {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                border: 1px solid #ddd;
                border-top: 5px solid #cfaa5e;
            }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. CONSTANTS & SETUP
# ==========================================
try:
    from pyzbar.pyzbar import decode
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

ADMIN_PASSWORD = "admin123"
FIXED_STORES = ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT STORE", "TERRA BASEMENT STORE"]
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 4. CONNECTION (SUPER ROBUST)
# ==========================================
@st.cache_resource
def get_client():
    try:
        # 1. Load Secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Critical Error: Secrets not found. Please check Streamlit Settings.")
            st.stop()
            
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 2. FIX PRIVATE KEY (The "Key Scrubber")
        if "private_key" in creds_dict:
            raw_key = creds_dict["private_key"]
            # Remove extra quotes if present
            raw_key = raw_key.strip('"').strip("'")
            # Replace literal \n with actual newlines
            fixed_key = raw_key.replace("\\n", "\n")
            creds_dict["private_key"] = fixed_key

        # 3. Connect
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        st.warning("Your Private Key in secrets is likely broken. The app tried to fix it but failed.")
        st.stop()

def get_inventory_sheet():
    client = get_client()
    try: return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        st.error(f"❌ Connection Failed (Sheet 1): {e}")
        st.stop()

def get_users_sheet():
    client = get_client()
    try: 
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet("Users")
    except:
        try:
            sh = client.open_by_key(SHEET_ID)
            ws = sh.add_worksheet(title="Users", rows="100", cols="3")
            ws.append_row(["Username", "PIN", "Permissions"])
            return ws
        except Exception as e:
            st.error(f"❌ Connection Failed (Users Tab): {e}")
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

# ==========================================
# 6. SESSION & LOGIC
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

# ==========================================
# 7. LOGIN SCREEN (SAFE MODE)
# ==========================================
def login_screen():
    inject_custom_css()
    st.markdown("<h1 style='text-align: center;'>Expo Asset Manager</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Secure Login</p>", unsafe_allow_html=True)
    
    tab_tech, tab_admin = st.tabs(["Technician", "Admin"])

    with tab_tech:
        st.subheader("Technician Access")
        try:
            us = get_users_sheet()
            data = us.get_all_records()
            users_df = pd.DataFrame(data)
            user_list = users_df['Username'].tolist() if not users_df.empty else []
        except Exception as e:
            st.error(f"Database Error: {e}")
            user_list = []

        with st.form("tech_form"):
            u_sel = st.selectbox("Select User", user_list)
            p_in = st.text_input("Enter PIN", type="password")
            if st.form_submit_button("Login"):
                if not users_df.empty and u_sel:
                    user_row = users_df[users_df['Username'] == u_sel]
                    if not user_row.empty:
                        real_pin = str(user_row.iloc[0]['PIN'])
                        if real_pin == str(p_in):
                            st.session_state['logged_in'] = True
                            st.session_state['user_role'] = "Technician"
                            st.session_state['username'] = u_sel
                            perm = str(user_row.iloc[0]['Permissions'])
                            st.session_state['can_import'] = (perm == "Bulk_Allowed")
                            st.session_state['current_page'] = "Collect"
                            save_session(u_sel, "Technician", st.session_state['can_import'])
                            st.rerun()
                        else: st.error("Wrong PIN")
                    else: st.error("User invalid")
                else: st.error("No users found or database error.")

    with tab_admin:
        st.subheader("Administrator Access")
        with st.form("admin_form"):
            adm_pass = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Login as Admin"):
                if adm_pass == ADMIN_PASSWORD:
                    st.session_state['logged_in'] = True
                    st.session_state['user_role'] = "Admin"
                    st.session_state['username'] = "Administrator"
                    st.session_state['can_import'] = True
                    st.session_state['current_page'] = "Overview"
                    save_session("Administrator", "Admin", True)
                    st.rerun()
                else: st.error("Invalid Password")

# ==========================================
# 8. MAIN APP
# ==========================================
def main():
    if not st.session_state['logged_in']:
        login_screen()
        return

    inject_custom_css()
    
    st.sidebar.markdown(f"**User:** {st.session_state['username']}")
    st.sidebar.caption(f"Role: {st.session_state['user_role']}")
    
    if st.sidebar.button("🔄 Sync"): force_sync(); st.success("Synced!"); time.sleep(0.5); st.rerun()
    if st.sidebar.button("Log Out"): logout()
    st.sidebar.divider()
    
    init_data_state()
    df = st.session_state['inventory_df']
    sheet = get_inventory_sheet()

    if st.session_state['user_role'] == "Technician":
        nav = st.sidebar.radio("Menu", ["Issue Asset", "Return Asset", "My Inventory", "Add Item", "Edit Details", "Bulk Import"])
        
        if nav == "Issue Asset":
            st.title("🚀 Issue Asset")
            with st.container():
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
                        st.success(f"Selected: {item['Model']} ({item['Status']})")
                        if "Available" in item['Status']:
                            ticket = st.text_input("Ticket #")
                            if st.button("Confirm Issue"):
                                sheet.update_cell(idx+2, 6, "Issued")
                                sheet.update_cell(idx+2, 7, st.session_state['username'])
                                sheet.update_cell(idx+2, 8, ticket)
                                force_sync(); st.success("Done!"); st.rerun()
                        else: st.warning("Not Available")
                    else: st.error("Not Found")

        elif nav == "Return Asset":
            st.title("📥 Return Asset")
            my = df[(df['Issued To'] == st.session_state['username']) & (df['Status'] == 'Issued')]
            if my.empty: st.info("No items to return.")
            else:
                sel = st.selectbox("Item", my['Serial Number'].tolist())
                c1, c2 = st.columns(2)
                stat = c1.selectbox("Status", ["Available/New", "Available/Used", "Faulty"])
                loc = c2.selectbox("Location", get_all_stores(df))
                if st.button("Return"):
                    idx = df[df['Serial Number']==sel].index[0]+2
                    sheet.update_cell(idx, 6, stat)
                    sheet.update_cell(idx, 7, st.session_state['username'] if stat=="Faulty" else "")
                    sheet.update_cell(idx, 9, loc)
                    force_sync(); st.success("Returned!"); st.rerun()

        elif nav == "My Inventory":
            st.title("🎒 My Items"); st.dataframe(df[(df['Issued To']==st.session_state['username'])&(df['Status']=='Issued')])

        elif nav == "Add Item":
            st.title("➕ Add Item")
            with st.form("add"):
                c1,c2 = st.columns(2)
                typ = c1.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
                man = c1.text_input("Make"); mod = c2.text_input("Model")
                sn = c2.text_input("Serial"); mac = c1.text_input("MAC")
                loc = c2.selectbox("Loc", get_all_stores(df))
                stat = st.selectbox("Status", ["Available/New", "Available/Used"])
                if st.form_submit_button("Add"):
                    if not check_serial_exists(df, sn):
                        sheet.append_row([typ, man, mod, sn, mac, stat, "", "", loc, "", get_timestamp(), st.session_state['username']])
                        force_sync(); st.success("Added!"); st.rerun()
                    else: st.error("Duplicate Serial")

        elif nav == "Edit Details":
            st.title("✏️ Edit")
            q = st.text_input("Search Serial")
            if q:
                match = df[df['Serial Number'].astype(str).str.contains(q, case=False)]
                if not match.empty:
                    sel = st.selectbox("Select", match['Serial Number'].tolist())
                    idx = df[df['Serial Number']==sel].index[0]
                    with st.form("edit"):
                        nm = st.text_input("Model", df.iloc[idx]['Model'])
                        nmac = st.text_input("MAC", df.iloc[idx]['MAC Address'])
                        nl = st.selectbox("Loc", get_all_stores(df))
                        if st.form_submit_button("Save"):
                            sheet.update_cell(idx+2, 3, nm); sheet.update_cell(idx+2, 5, nmac); sheet.update_cell(idx+2, 9, nl)
                            force_sync(); st.success("Saved!"); st.rerun()

        elif nav == "Bulk Import":
            if st.session_state['can_import']:
                st.title("⚡ Bulk Import")
                st.download_button("Template", get_template_excel(), "template.xlsx")
                up = st.file_uploader("Upload .xlsx", type=['xlsx'])
                if up and st.button("Import"):
                    d = pd.read_excel(up).fillna("")
                    rows = []
                    for i,r in d.iterrows():
                        if not check_serial_exists(df, str(r['Serial Number'])):
                            rows.append([r['Asset Type'], r['Manufacturer'], r['Model'], str(r['Serial Number']), 
                                         r.get('MAC Address',''), r.get('Status','Available/New'), "", "", r['Location'], "", get_timestamp(), "BULK"])
                    if rows: sheet.append_rows(rows); force_sync(); st.success(f"Imported {len(rows)}")
            else: st.error("No Permission")

    elif st.session_state['user_role'] == "Admin":
        nav = st.sidebar.radio("Admin", ["Overview", "Manage Assets", "Manage Users", "Database"])
        
        if nav == "Overview":
            st.title("📊 Overview")
            c1,c2,c3 = st.columns(3)
            c1.metric("Total", len(df)); c2.metric("Issued", len(df[df['Status']=='Issued'])); c3.metric("Avail", len(df[df['Status'].str.contains('Available')]))
            st.plotly_chart(px.pie(df, names='Status'), use_container_width=True)

        elif nav == "Manage Assets":
            st.title("🛠️ Assets")
            d_sn = st.text_input("Delete Serial")
            if st.button("Delete"):
                match = df[df['Serial Number']==d_sn]
                if not match.empty: sheet.delete_rows(match.index[0]+2); force_sync(); st.success("Deleted")
                else: st.error("Not Found")

        elif nav == "Manage Users":
            st.title("👥 Users"); us = get_users_sheet(); st.dataframe(pd.DataFrame(us.get_all_records()))
            with st.form("nu"):
                u = st.text_input("User"); p = st.text_input("PIN")
                if st.form_submit_button("Add User"): us.append_row([u, p, "Standard"]); st.success("Created"); st.rerun()

        elif nav == "Database":
            st.title("📦 Database"); st.dataframe(df); st.download_button("Export", to_excel(df), "inv.xlsx")

if __name__ == "__main__":
    main()
