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
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# 2. DYNAMIC CSS (CLEAN - NO ICONS)
# ==========================================
def inject_custom_css(login_mode=False):
    # CSS TO HIDE MENUS & ICONS
    hide_menus = """
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            [data-testid="stToolbar"] {visibility: hidden !important; display: none !important;}
            [data-testid="stDecoration"] {visibility: hidden !important; display: none !important;}
            .block-container { padding-top: 1rem !important; }
        </style>
    """
    st.markdown(hide_menus, unsafe_allow_html=True)

    if login_mode:
        st.markdown("""
        <style>
            .stApp { background-color: #f4f6f9; }
            .main .block-container {
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                height: 95vh; padding: 0 !important; max-width: 100%;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: white; padding: 40px; border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08); width: 100%; max-width: 400px; 
                border: 1px solid #e1e4e8; border-top: 5px solid #cfaa5e;
            }
            div[data-testid="stImage"] { display: flex; justify-content: center; margin-bottom: 20px; }
            .stButton>button {
                width: 100%; border-radius: 5px; height: 45px; font-weight: 600;
                background-color: #111; color: white; border: none; transition: 0.3s;
            }
            .stButton>button:hover { background-color: #333; }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            .stApp { background-color: #f8f9fa; }
            section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #eee; }
            div[data-testid="stMetric"] { 
                background-color: #ffffff; padding: 20px; border-radius: 8px; 
                box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #eee; 
            }
            .stButton>button { 
                border-radius: 5px; font-weight: 500; width: 100%; 
                border: 1px solid #eee; background-color: white; color: #333; 
            }
            .stButton>button:hover { border-color: #cfaa5e; color: #cfaa5e; background-color: #fff; }
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

# ⚠️ YOUR GOOGLE SHEET ID IS HERE NOW:
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 4. CONNECTION (USING ID INSTEAD OF NAME)
# ==========================================
@st.cache_resource
def get_client():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        st.stop()

def get_inventory_sheet():
    client = get_client()
    try: 
        # OPEN BY KEY (ID) - IGNORES FILENAME
        return client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        st.error(f"❌ Connection Failed. The app cannot open Sheet ID: {SHEET_ID}")
        st.info("Solution: Copy 'store-admin@securityapp-485516.iam.gserviceaccount.com' and share the sheet with it as Editor.")
        st.stop()

def get_users_sheet():
    client = get_client()
    try: 
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet("Users")
    except:
        # Create Users sheet if it doesn't exist
        try:
            sh = client.open_by_key(SHEET_ID)
            ws = sh.add_worksheet(title="Users", rows="100", cols="3")
            ws.append_row(["Username", "PIN", "Permissions"])
            return ws
        except:
            st.error("❌ Error accessing 'Users' tab.")
            st.stop()

# ==========================================
# 5. FAST DATA ENGINE
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
            s_str = str(s).strip()
            if s_str and s_str.lower() != 'nan' and s_str.upper() not in ["FAULTY", "USED", "NEW", "AVAILABLE", "ISSUED"]:
                valid_stores.add(s_str)
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
        try: st.image("logo.png", width=160) 
        except: st.markdown("<h1 style='text-align: center;'>🏢</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Welcome Back</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Sign in to continue</p>", unsafe_allow_html=True)
        
        role_tab1, role_tab2 = st.tabs(["Technician", "Admin"])
        with role_tab1:
            try:
                us = get_users_sheet(); data = us.get_all_records(); df = pd.DataFrame(data)
                users_list = df['Username'].tolist() if not df.empty else []
            except: users_list = []
            with st.form("tech_login"):
                u = st.selectbox("Username", users_list, placeholder="Select User")
                p = st.text_input("PIN Code", type="password", placeholder="Enter PIN")
                st.write("")
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
                    else: st.error("Database error")
        with role_tab2:
            with st.form("admin_login"):
                pwd = st.text_input("Password", type="password", placeholder="Admin Password")
                st.write("")
                if st.form_submit_button("Authenticate"):
                    if pwd == ADMIN_PASSWORD:
                        st.session_state['logged_in'] = True; st.session_state['user_role'] = "Admin"
                        st.session_state['username'] = "Administrator"
                        st.session_state['can_import'] = True
                        st.session_state['current_page'] = "Overview"
                        save_session("Administrator", "Admin", True)
                        st.rerun()
                    else: st.error("Access Denied")
        st.markdown("<div style='text-align: center; font-size: 10px; color: #ccc; margin-top: 15px;'>© 2026 Expo City Dubai</div>", unsafe_allow_html=True)

# ==========================================
# 8. MAIN APP
# ==========================================
def main():
    if not st.session_state['logged_in']: 
        login_screen()
        return
    
    inject_custom_css(login_mode=False)
    
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

    if st.session_state['user_role'] == "Technician":
        if st.session_state['current_page'] not in ["Collect", "Return", "My Inventory", "Add Item", "Edit Details", "Bulk Import"]:
            st.session_state['current_page'] = "Collect"
        if st.sidebar.button("🚀 Issue Asset"): st.session_state['current_page'] = "Collect"; st.rerun()
        if st.sidebar.button("📥 Return Asset"): st.session_state['current_page'] = "Return"; st.rerun()
        if st.sidebar.button("🎒 My Inventory"): st.session_state['current_page'] = "My Inventory"; st.rerun()
        st.sidebar.divider()
        if st.sidebar.
