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

# Professional CSS Styling
st.markdown("""
<style>
    /* Main Background */
    .stApp {background-color: #f8f9fa;}
    
    /* Login Box */
    div[data-testid="stForm"] {
        background: #ffffff;
        padding: 30px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border-top: 6px solid #cfaa5e;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        height: 45px;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Status Badges */
    .badge-success {background-color: #d4edda; color: #155724; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold;}
    .badge-warning {background-color: #fff3cd; color: #856404; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold;}
    .badge-danger {background-color: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold;}
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
# 2. CONNECTION HANDLER (The Working Version)
# ==========================================
@st.cache_resource
def get_client():
    try:
        if "gcp_service_account" not in st.secrets:
            return None, "Secrets Missing"

        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Key Fixer
        if "private_key" in creds_dict:
            key = creds_dict["private_key"]
            if "\\n" in key: key = key.replace("\\n", "\n")
            creds_dict["private_key"] = key.strip('"')

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        client.open_by_key(SHEET_ID) # Verification ping
        return client, "Online"
    except Exception as e:
        return None, str(e)

def get_sheet_data(worksheet_name):
    client, status = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        try: return sh.worksheet(worksheet_name)
        except:
            # Auto-Create Sheets if missing
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
        # Unique Headers
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
        st.markdown("<p style='text-align: center; color: #666;'>Professional Asset Tracking System</p>", unsafe_allow_html=True)
        
        client, status = get_client()
        if "Online" in status:
            st.success("🟢 System Online & Connected")
        else:
            st.error(f"🔴 System Offline: {status}")

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
# 5. MAIN APPLICATION LOGIC
# ==========================================
if not st.session_state['logged_in']:
    login_screen()
else:
    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 👤 {st.session_state['user']}")
    st.sidebar.markdown(f"**Role:** {st.session_state['role']}")
    
    if st.sidebar.button("🔄 Refresh Data"):
        with st.spinner("Syncing with Cloud..."):
            force_sync()
        st.success("Synced!")
        time.sleep(0.5)
        st.rerun()
        
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Log Out"):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- LOAD DATA ---
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = download_data()
    df = st.session_state['inventory_df']
    ws_inv = get_sheet_data("Sheet1")

    # ==========================
    # TECHNICIAN DASHBOARD
    # ==========================
    if st.session_state['role'] == "Technician":
        st.title("🛠️ Technician Dashboard")
        nav = st.selectbox("Navigate to:", ["🚀 Issue Asset", "📥 Return Asset", "🎒 My Inventory", "➕ Add New Item", "⚡ Bulk Import"])
        st.divider()

        if nav == "🚀 Issue Asset":
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("Locate Asset")
                search = st.text_input("Scan or Type Serial Number", placeholder="e.g. SN-12345")
            with c2:
                if CAMERA_AVAILABLE:
                    cam = st.camera_input("QR Scanner")
                    if cam: 
                        try: search = decode(Image.open(cam))[0].data.decode("utf-8")
                        except: pass
            
            if search:
                search = search.strip()
                match = df[df['Serial Number'].astype(str).str.strip().str.upper() == search.upper()]
                
                if not match.empty:
                    item = match.iloc[0]
                    status_color = "badge-success" if "Available" in item['Status'] else "badge-danger"
                    
                    st.markdown(f"""
                    <div style="padding: 20px; background: white; border-radius: 10px; border: 1px solid #ddd;">
                        <h3>📦 {item['Model']}</h3>
                        <p><b>Serial:</b> {item['Serial Number']} | <b>Make:</b> {item['Manufacturer']}</p>
                        <span class="{status_color}">{item['Status']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if "Available" in item['Status']:
                        with st.form("issue_form"):
                            st.write("### Assign Asset")
                            tkt = st.text_input("Ticket Number / Reference")
                            if st.form_submit_button("✅ Confirm Issue"):
                                idx = match.index[0] + 2
                                ws_inv.update_cell(idx, 6, "Issued")
                                ws_inv.update_cell(idx, 7, st.session_state['user'])
                                ws_inv.update_cell(idx, 8, tkt)
                                ws_inv.update_cell(idx, 12, st.session_state['user']) # Last User
                                force_sync()
                                st.balloons()
                                st.success(f"Asset {item['Serial Number']} successfully issued to you!")
                    else:
                        st.warning(f"⛔ This item is currently {item['Status']} (Held by: {item.get('Issued To', 'Unknown')})")
                else:
                    st.error("❌ Serial Number not found in the database.")

        elif nav == "📥 Return Asset":
            st.subheader("Process Return")
            my_items = df[(df['Issued To'] == st.session_state['user']) & (df['Status'] == 'Issued')]
            
            if my_items.empty:
                st.info("🎉 You have no pending items to return.")
            else:
                selected_serial = st.selectbox("Select Asset to Return", my_items['Serial Number'] + " - " + my_items['Model'])
                serial_only = selected_serial.split(" - ")[0]
                
                with st.form("return_form"):
                    c1, c2 = st.columns(2)
                    new_status = c1.selectbox("Asset Condition", ["Available/New", "Available/Used", "Faulty"])
                    location = c2.selectbox("Return Location", get_all_stores(df))
                    
                    if st.form_submit_button("✅ Process Return"):
                        idx = df[df['Serial Number'] == serial_only].index[0] + 2
                        ws_inv.update_cell(idx, 6, new_status)
                        ws_inv.update_cell(idx, 7, st.session_state['user'] if new_status == "Faulty" else "")
                        ws_inv.update_cell(idx, 9, location)
                        force_sync()
                        st.success("Asset returned successfully!")
                        time.sleep(1)
                        st.rerun()

        elif nav == "🎒 My Inventory":
            st.subheader("My Active Assets")
            my_items = df[(df['Issued To'] == st.session_state['user']) & (df['Status'] == 'Issued')]
            st.dataframe(my_items[['Asset Type', 'Manufacturer', 'Model', 'Serial Number', 'Ticket_Number', 'Location']], use_container_width=True)

        elif nav == "➕ Add New Item":
            st.subheader("Register New Asset")
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                typ = c1.selectbox("Asset Type", ["Camera", "Reader", "Controller", "Lock", "Switch", "Server", "Accessory"])
                man = c2.text_input("Manufacturer")
                mod = c1.text_input("Model Name")
                sn = c2.text_input("Serial Number")
                mac = c1.text_input("MAC Address (Optional)")
                loc = c2.selectbox("Storage Location", get_all_stores(df))
                stat = st.selectbox("Initial Status", ["Available/New", "Available/Used"])
                
                if st.form_submit_button("💾 Save Asset"):
                    if sn in df['Serial Number'].astype(str).tolist():
                        st.error("❌ Duplicate Error: This Serial Number already exists.")
                    elif not sn or not mod:
                        st.warning("⚠️ Serial Number and Model are required.")
                    else:
                        # Row Structure: [Type, Make, Model, Serial, MAC, Status, IssuedTo, Ticket, Location, Comments, Time, User]
                        row_data = [typ, man, mod, sn, mac, stat, "", "", loc, "", get_timestamp(), st.session_state['user']]
                        ws_inv.append_row(row_data)
                        force_sync()
                        st.success(f"Asset {sn} added successfully!")

        elif nav == "⚡ Bulk Import":
            st.subheader("Bulk Import Assets")
            if st.session_state.get('can_import'):
                st.download_button("📥 Download Template", get_template(), "import_template.xlsx")
                uploaded = st.file_uploader("Upload Excel File", type=['xlsx'])
                
                if uploaded:
                    if st.button("🚀 Run Import"):
                        try:
                            new_data = pd.read_excel(uploaded).fillna("")
                            valid_rows = []
                            duplicates = 0
                            
                            for _, r in new_data.iterrows():
                                if str(r['Serial Number']) not in df['Serial Number'].astype(str).tolist():
                                    valid_rows.append([
                                        r.get('Asset Type', 'Unknown'), r.get('Manufacturer', ''), r.get('Model', ''), 
                                        str(r['Serial Number']), r.get('MAC Address',''), "Available/New", "", "", 
                                        r.get('Location', 'Warehouse'), "", get_timestamp(), "BULK_IMPORT"
                                    ])
                                else:
                                    duplicates += 1
                            
                            if valid_rows:
                                ws_inv.append_rows(valid_rows)
                                force_sync()
                                st.success(f"✅ Imported {len(valid_rows)} items successfully!")
                                if duplicates > 0: st.warning(f"⚠️ Skipped {duplicates} duplicate serial numbers.")
                            else:
                                st.warning("No new unique items found to import.")
                        except Exception as e:
                            st.error(f"Import Failed: {e}")
            else:
                st.error("🚫 Access Denied: You do not have Bulk Import permissions.")

    # ==========================
    # ADMIN DASHBOARD
    # ==========================
    elif st.session_state['role'] == "Admin":
        st.title("📊 Admin Control Panel")
        nav = st.sidebar.radio("Navigation", ["Dashboard Overview", "User Management", "Database Master"])
        
        if nav == "Dashboard Overview":
            if not df.empty:
                # Key Metrics
                total = len(df)
                issued = len(df[df['Status'] == 'Issued'])
                avail = len(df[df['Status'].str.contains('Available', na=False)])
                faulty = len(df[df['Status'] == 'Faulty'])
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Assets", total)
                c2.metric("Available", avail, delta_color="normal")
                c3.metric("Issued", issued, delta_color="inverse")
                c4.metric("Faulty", faulty, delta_color="inverse")
                
                # Charts
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.subheader("Asset Status Distribution")
                    fig1 = px.pie(df, names='Status', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col_chart2:
                    st.subheader("Inventory by Type")
                    fig2 = px.bar(df['Asset Type'].value_counts(), orientation='h', color_discrete_sequence=['#cfaa5e'])
                    st.plotly_chart(fig2, use_container_width=True)
            else:
                st.warning("Database is empty. Please add items.")

        elif nav == "User Management":
            st.subheader("👥 Manage Team")
            ws_u = get_sheet_data("Users")
            if ws_u:
                users_df = pd.DataFrame(ws_u.get_all_records())
                st.dataframe(users_df, use_container_width=True)
                
                with st.expander("➕ Create New User"):
                    with st.form("new_user"):
                        nu = st.text_input("Username")
                        np = st.text_input("PIN Code")
                        nperm = st.selectbox("Permissions", ["Standard", "Bulk_Allowed"])
                        if st.form_submit_button("Create User"):
                            if nu and np:
                                ws_u.append_row([nu, np, nperm])
                                st.success(f"User {nu} created!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Username and PIN are required.")
            else:
                st.error("Could not connect to Users database.")

        elif nav == "Database Master":
            st.subheader("📦 Master Database")
            st.dataframe(df, use_container_width=True, height=600)
            
            c1, c2 = st.columns([1, 4])
            with c1:
                st.download_button("📥 Export to Excel", to_excel(df), f"Inventory_{datetime.now().date()}.xlsx")
