import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="Expo Asset Manager", page_icon="🏢")

# Simple CSS to make the login box look nice
st.markdown("""
<style>
    div[data-testid="stForm"] {
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONFIGURATION
# ==========================================
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 3. CONNECTION FUNCTION
# ==========================================
@st.cache_resource
def get_client():
    try:
        # Load secrets
        if "gcp_service_account" not in st.secrets:
            st.error("❌ Secrets not found! Please update Streamlit Secrets.")
            st.stop()
            
        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # KEY REPAIR: Fix newlines if they are broken
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        st.stop()

def get_users_sheet():
    client = get_client()
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet("Users")
    except Exception as e:
        # If the "Users" tab is missing, we catch the error here
        st.error(f"❌ Could not find 'Users' tab in the sheet. Error: {e}")
        return None

# ==========================================
# 4. LOGIN SYSTEM
# ==========================================
def login_screen():
    st.title("Expo Asset Manager")
    
    tab1, tab2 = st.tabs(["Technician Login", "Admin Login"])
    
    # --- TECHNICIAN LOGIN ---
    with tab1:
        st.write("### Technician Access")
        
        # Try to load users
        user_list = []
        users_df = pd.DataFrame()
        
        try:
            ws = get_users_sheet()
            if ws:
                users_df = pd.DataFrame(ws.get_all_records())
                if not users_df.empty and 'Username' in users_df.columns:
                    user_list = users_df['Username'].tolist()
        except Exception as e:
            st.warning(f"Database Warning: {e}")

        if not user_list:
            st.warning("⚠️ No users found. Please login as Admin to create users.")

        with st.form("tech_login"):
            u_sel = st.selectbox("Select Username", user_list if user_list else ["No Users Found"])
            p_in = st.text_input("Enter PIN", type="password")
            
            if st.form_submit_button("Login"):
                if not users_df.empty:
                    user_row = users_df[users_df['Username'] == u_sel]
                    if not user_row.empty:
                        real_pin = str(user_row.iloc[0]['PIN'])
                        if real_pin == str(p_in):
                            st.session_state['logged_in'] = True
                            st.session_state['role'] = "Technician"
                            st.session_state['user'] = u_sel
                            st.rerun()
                        else:
                            st.error("Incorrect PIN")
                    else:
                        st.error("User not found")
                else:
                    st.error("Database connection failed or empty.")

    # --- ADMIN LOGIN ---
    with tab2:
        st.write("### Administrator Access")
        with st.form("admin_login"):
            p_admin = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Login as Admin"):
                if p_admin == ADMIN_PASSWORD:
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = "Admin"
                    st.session_state['user'] = "Administrator"
                    st.rerun()
                else:
                    st.error("Invalid Admin Password")

# ==========================================
# 5. MAIN APP
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_screen()
else:
    # LOGGED IN VIEW
    st.sidebar.success(f"Logged in as {st.session_state['user']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
        
    st.title(f"Welcome, {st.session_state['user']}")
    st.write("✅ System is Online")
    st.info("Select an option from the sidebar (Menu coming soon...)")
