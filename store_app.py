import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
from io import BytesIO
import plotly.express as px
from PIL import Image

# =====================================================
# 🔒 CRITICAL PATCH — PREVENT append_rows CRASH
# =====================================================
from gspread.models import Worksheet

if not hasattr(Worksheet, "append_rows"):
    def append_rows(self, rows, **kwargs):
        for row in rows:
            self.append_row(row)
    Worksheet.append_rows = append_rows

# =====================================================
# APP CONFIG
# =====================================================
st.set_page_config(
    page_title="Expo Asset Manager",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CONSTANTS
# =====================================================
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

# =====================================================
# GOOGLE SHEETS CONNECTION
# =====================================================
@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    return gspread.authorize(creds)

@st.cache_resource
def get_worksheet(name):
    client = get_client()
    sh = client.open_by_key(SHEET_ID)
    try:
        return sh.worksheet(name)
    except:
        return sh.sheet1

# =====================================================
# HELPERS
# =====================================================
def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_data():
    ws = get_worksheet("Sheet1")
    raw = ws.get_all_values()
    if len(raw) <= 1:
        return pd.DataFrame(columns=HEADERS)

    rows = raw[1:]
    while any(len(r) < len(HEADERS) for r in rows):
        for r in rows:
            r += [""] * (len(HEADERS) - len(r))

    return pd.DataFrame(rows, columns=HEADERS)

def force_reload():
    st.cache_data.clear()
    st.session_state["inventory_df"] = load_data()

def to_excel(df):
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return bio.getvalue()

# =====================================================
# LOGIN
# =====================================================
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
                for user in ws.get_all_records():
                    if str(user["Username"]) == u and str(user["PIN"]) == p:
                        st.session_state.logged_in = True
                        st.session_state.role = "Technician"
                        st.session_state.user = u
                        st.session_state.can_import = user["Permissions"] == "Bulk_Allowed"
                        st.rerun()
                st.error("Invalid credentials")

    with tab2:
        with st.form("admin"):
            p = st.text_input("Admin Password", type="password")
            if st.form_submit_button("Login"):
                if p == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.session_state.user = "Administrator"
                    st.session_state.can_import = True
                    st.rerun()
                else:
                    st.error("Access denied")

# =====================================================
# MAIN APP
# =====================================================
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

# =====================================================
# TECHNICIAN
# =====================================================
if st.session_state.role == "Technician":
    st.title("🛠 Technician Dashboard")
    nav = st.selectbox("Menu", ["➕ Add Asset", "⚡ Bulk Import", "🎒 My Inventory"])

    if nav == "➕ Add Asset":
        with st.form("add"):
            at = st.selectbox("Type", ["Camera", "Reader", "Controller", "Lock"])
            brand = st.text_input("Brand")
            model = st.text_input("Model")
            serial = st.text_input("Serial")
            mac = st.text_input("MAC")
            loc = st.selectbox("Location", FIXED_STORES)
            cond = st.selectbox("Condition", ["Available/New", "Available/Used"])

            if st.form_submit_button("Save"):
                ws_inv.append_rows([[
                    at, brand, model, serial, mac,
                    cond, loc, "", "", timestamp(), st.session_state.user
                ]])
                force_reload()
                st.success("Asset Added")
                st.rerun()

    if nav == "⚡ Bulk Import" and st.session_state.can_import:
        st.download_button("📄 Template", to_excel(pd.DataFrame(columns=HEADERS)), "template.xlsx")
        up = st.file_uploader("Upload Excel", type=["xlsx"])
        if up and st.button("Import"):
            d = pd.read_excel(up).fillna("")
            rows = []
            for _, r in d.iterrows():
                rows.append([
                    r.get("ASSET TYPE", ""), r.get("BRAND", ""), r.get("MODEL", ""),
                    r.get("SERIAL", ""), r.get("MAC ADDRESS", ""),
                    "Available/New", r.get("LOCATION", ""),
                    "", "", timestamp(), "BULK"
                ])
            ws_inv.append_rows(rows)
            force_reload()
            st.success(f"Imported {len(rows)} assets")

# =====================================================
# ADMIN DASHBOARD
# =====================================================
if st.session_state.role == "Admin":
    st.title("📊 Admin Dashboard")
    st.metric("Total Assets", len(df))
    st.plotly_chart(px.pie(df, names="CONDITION"), use_container_width=True)
    st.download_button("📥 Export", to_excel(df), "assets.xlsx")
