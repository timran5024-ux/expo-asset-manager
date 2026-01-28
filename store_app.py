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
# 1. APP CONFIG
# ==========================================
st.set_page_config(
    page_title="Expo Asset Manager",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {background-color: #f4f6f9;}
div[data-testid="stForm"] {
    background: #ffffff;
    padding: 25px;
    border-radius: 12px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    border-top: 5px solid #cfaa5e;
}
.stButton>button {
    width: 100%;
    border-radius: 6px;
    height: 45px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS
# ==========================================
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"

FIXED_STORES = [
    "MOBILITY STORE-10",
    "MOBILITY STORE-8",
    "SUSTAINABILITY BASEMENT STORE",
    "TERRA BASEMENT STORE"
]

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

HEADERS = [
    "ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS",
    "CONDITION", "LOCATION", "ISSUED TO", "TICKET",
    "TIMESTAMP", "USER"
]

# ==========================================
# 3. SAFE GOOGLE SHEETS CONNECTION
# ==========================================
@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        if "\\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        return gspread.authorize(creds)
    except Exception:
        return None

@st.cache_resource
def get_worksheet(name):
    client = get_client()
    if not client:
        return None
    sh = client.open_by_key(SHEET_ID)
    try:
        return sh.worksheet(name)
    except:
        return sh.sheet1

# ==========================================
# 4. SAFE ROW INSERT (NO append_rows)
# ==========================================
def safe_add_data(ws, rows):
    """
    Works on all gspread versions (Streamlit Cloud safe)
    """
    for row in rows:
        ws.append_row(row)

# ==========================================
# 5. DATA ENGINE
# ==========================================
def load_data():
    ws = get_worksheet("Sheet1")
    if not ws:
        return pd.DataFrame(columns=HEADERS)

    raw = ws.get_all_values()
    if len(raw) <= 1:
        return pd.DataFrame(columns=HEADERS)

    rows = raw[1:]
    clean = []
    for r in rows:
        while len(r) < len(HEADERS):
            r.append("")
        clean.append(r[:len(HEADERS)])

    return pd.DataFrame(clean, columns=HEADERS)

def force_reload():
    st.cache_data.clear()
    st.session_state["inventory_df"] = load_data()

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def to_excel(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return bio.getvalue()

# ==========================================
# 6. LOGIN
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login_screen():
    st.title("🏢 Expo Asset Manager")
    tab1, tab2 = st.tabs(["Technician", "Admin"])

    with tab1:
        with st.form("tech"):
            u = st.text_input("Username")
            p = st.text_input("PIN", type="password")
            if st.form_submit_button("Login"):
                ws = get_worksheet("Users")
                users = ws.get_all_records()
                for user in users:
                    if str(user["Username"]) == u and str(user["PIN"]) == p:
                        st.session_state.logged_in = True
                        st.session_state.user = u
                        st.session_state.role = "Technician"
                        st.session_state.can_import = user["Permissions"] == "Bulk_Allowed"
                        st.rerun()
                st.error("Invalid credentials")

    with tab2:
        with st.form("admin"):
            p = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Login"):
                if p == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.user = "Administrator"
                    st.session_state.role = "Admin"
                    st.session_state.can_import = True
                    st.rerun()
                else:
                    st.error("Access denied")

# ==========================================
# 7. MAIN APP
# ==========================================
if not st.session_state.logged_in:
    login_screen()
    st.stop()

if "inventory_df" not in st.session_state:
    st.session_state.inventory_df = load_data()

df = st.session_state.inventory_df
ws_inv = get_worksheet("Sheet1")

st.sidebar.markdown(f"### 👤 {st.session_state.user}")
if st.sidebar.button("🔄 Refresh"):
    force_reload()
    st.rerun()
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

# ==========================================
# 8. TECHNICIAN
# ==========================================
if st.session_state.role == "Technician":
    st.title("🛠 Technician Dashboard")
    nav = st.selectbox("Menu", [
        "🚀 Issue Asset", "📥 Return Asset",
        "➕ Add Asset", "⚡ Bulk Impo
