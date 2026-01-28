import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# ==========================================
# 1. SETUP
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢", layout="wide")

# Safe CSS that won't hide errors
st.markdown("""
<style>
    div[data-testid="stForm"] {background: #f9f9f9; padding: 20px; border-radius: 10px; border: 1px solid #ddd;}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. CLOUD CONNECTION HANDLER
# ==========================================
@st.cache_resource
def get_client():
    try:
        # Check if secrets exist
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets are missing! Go to App Settings -> Secrets.")
            st.stop()
            
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # 🔧 CLOUD FIX: Ensure newlines are read correctly
        if "private_key" in creds_dict:
            raw = creds_dict["private_key"]
            # Fix if the key has literal "\n" strings
            if "\\n" in raw:
                creds_dict["private_key"] = raw.replace("\\n", "\n")
            # Fix if the key has extra quotes
            creds_dict["private_key"] = creds_dict["private_key"].strip('"')

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Cloud Connection Failed: {e}")
        st.info("Tip: Delete and re-paste your secrets using the Triple-Quote format.")
        st.stop()

def get_sheet_data(worksheet_name):
    client = get_client()
    try:
        sh = client.open_by_key(SHEET_ID)
        try:
            return sh.worksheet(worksheet_name)
        except:
            # Auto-create if missing
            if worksheet_name == "Users":
                ws = sh.add_worksheet(title="Users", rows="100", cols="3")
                ws.append_row(["Username", "PIN", "Permissions"])
                return ws
            return None
    except Exception as e:
        st.error(f"❌ Error finding Sheet: {e}")
        return None

# ==========================================
# 3. LOGIN SCREEN
# ==========================================
def login_screen():
    st.title("Expo Asset Manager (Cloud Edition)")
    
    t1, t2 = st.tabs(["Technician", "Admin"])
    
    with t1:
        st.write("### Technician Login")
        # Load Users
        users_df = pd.DataFrame()
        user_list = []
        try:
            ws = get_sheet_data("Users")
            if ws:
                users_df = pd.DataFrame(ws.get_all_records())
                if not users_df.empty: user_list = users_df['Username'].tolist()
        except: pass
        
        if not user_list:
            st.warning("No users found. Login as Admin to add users.")
            
        with st.form("tech"):
            u = st.selectbox("Username", user_list if user_list else ["None"])
            p = st.text_input("PIN", type="password")
            if st.form_submit_button("Login"):
                if not users_df.empty and u in user_list:
                    row = users_df[users_df['Username']==u].iloc[0]
                    if str(row['PIN']) == str(p):
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = "Technician"
                        st.session_state['user'] = u
                        st.rerun()
                    else: st.error("Wrong PIN")
                else: st.error("Login Failed")

    with t2:
        st.write("### Admin Login")
        with st.form("admin"):
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if p == ADMIN_PASSWORD:
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = "Admin"
                    st.session_state['user'] = "Administrator"
                    st.rerun()
                else: st.error("Wrong Password")

# ==========================================
# 4. MAIN LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_screen()
else:
    st.sidebar.title(f"👤 {st.session_state['user']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
    
    st.title("✅ Connected Successfully")
    st.info("The connection to Google Sheets is working. You can now build out the rest of the features.")
    
    # Simple Data View to prove it works
    try:
        ws = get_sheet_data("Sheet1")
        if ws:
            df = pd.DataFrame(ws.get_all_records())
            st.dataframe(df)
    except Exception as e:
        st.error(f"Error loading data: {e}")
