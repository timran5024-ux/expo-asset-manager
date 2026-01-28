import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import hashlib
from PIL import Image

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Asset Management Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================================================
# LOAD LOGO (SAFE)
# ======================================================
LOGO_PATH = "logo.png"
logo = Image.open(LOGO_PATH)

# ======================================================
# UI STYLES
# ======================================================
st.markdown("""
<style>
:root {
    --bg:#F8FAFC;
    --card:#FFFFFF;
    --border:#E5E7EB;
    --dark:#0F172A;
}

.stApp { background: var(--bg); font-family: system-ui; }
header, footer, #MainMenu { visibility: hidden; }

.block-container {
    max-width: 96% !important;
    padding-top: 1.5rem !important;
}

.centered-title {
    text-align: center;
    font-size: 36px;
    font-weight: 900;
    color: var(--dark);
    margin-bottom: 30px;
}

.logo-box {
    display: flex;
    justify-content: center;
    margin-bottom: 10px;
}

div[data-testid="column"] {
    background: var(--card);
    border-radius: 16px;
    border: 1px solid var(--border);
    padding: 18px;
    box-shadow: 0 10px 25px rgba(0,0,0,.05);
}

.stButton button {
    height: 46px;
    border-radius: 12px;
    font-weight: 700;
}

.profile-box {
    background: #111827;
    color: white;
    border-radius: 999px;
    height: 46px;
    display: flex;
    align-items: center;
    justify-content: center;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# CONSTANTS
# ======================================================
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v136_clean"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

HEADERS = [
    "ASSET TYPE","BRAND","MODEL","SERIAL","MAC ADDRESS",
    "CONDITION","LOCATION","ISSUED TO","TICKET","TIMESTAMP","USER"
]

# ======================================================
# UTILITIES
# ======================================================
def make_token(u):
    return hashlib.sha256(f"{u}{SESSION_SECRET}".encode()).hexdigest()

@st.cache_resource
def get_client():
    creds = dict(st.secrets["gcp_service_account"])
    creds["private_key"] = creds["private_key"].replace("\\n", "\n")
    return gspread.authorize(
        ServiceAccountCredentials.from_json_keyfile_dict(creds, SCOPE)
    )

def get_ws(name):
    sh = get_client().open_by_key(SHEET_ID)
    try:
        return sh.worksheet(name)
    except:
        return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    rows = ws.get_all_values()
    return pd.DataFrame(rows[1:], columns=HEADERS) if len(rows) > 1 else pd.DataFrame(columns=HEADERS)

def sync():
    st.session_state["inventory_df"] = load_data()

# ======================================================
# AUTH
# ======================================================
if "logged_in" not in st.session_state:
    p = st.query_params
    if p.get("user") and p.get("token") == make_token(p.get("user")):
        st.session_state.update(
            logged_in=True,
            user=p.get("user"),
            role="Admin" if p.get("user") == "Administrator" else "Technician"
        )
    else:
        st.session_state["logged_in"] = False

# ======================================================
# LOGIN PAGE
# ======================================================
if not st.session_state["logged_in"]:
    st.markdown('<div class="logo-box">', unsafe_allow_html=True)
    st.image(logo, width=120)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div class='centered-title'>ASSET MANAGEMENT PRO</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.4, 1])
    with c2:
        tabs = st.tabs(["TECHNICIAN", "ADMIN"])
        with tabs[0]:
            with st.form("tech_login"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    users = get_ws("Users").get_all_records()
                    if any(x["Username"] == u and str(x["PIN"]) == p for x in users):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.query_params.update(user=u, token=make_token(u))
                        st.rerun()
                    else:
                        st.error("Access Denied")

        with tabs[1]:
            with st.form("admin_login"):
                p = st.text_input("Admin Password", type="password")
                if st.form_submit_button("LOGIN"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.query_params.update(user="Administrator", token=make_token("Administrator"))
                        st.rerun()
                    else:
                        st.error("Invalid Password")

# ======================================================
# MAIN APP
# ======================================================
else:
    if "inventory_df" not in st.session_state:
        sync()

    df = st.session_state["inventory_df"]

    st.markdown('<div class="logo-box">', unsafe_allow_html=True)
    st.image(logo, width=80)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div class='centered-title'>Asset Management</div>", unsafe_allow_html=True)

    # 🔴 FIXED HEADER LINE (NO ERROR)
    h1, h2, h3, h4 = st.columns([4, 2, 1, 1])

    with h1:
        nav = st.selectbox(
            "",
            ["DASHBOARD", "DATABASE"]
            if st.session_state["role"] == "Admin"
            else ["ISSUE ASSET", "RETURN ASSET"],
            label_visibility="collapsed"
        )

    with h2:
        st.markdown(
            f"<div class='profile-box'>👤 {st.session_state['user']}</div>",
            unsafe_allow_html=True
        )

    with h3:
        if st.button("SYNC"):
            sync()
            st.rerun()

    with h4:
        if st.button("LOGOUT"):
            st.session_state.clear()
            st.query_params.clear()
            st.rerun()

    st.divider()

    # ==================================================
    # DATABASE
    # ==================================================
    if nav == "DATABASE":
        st.markdown("## 📦 Inventory Database")
        st.dataframe(df, use_container_width=True, height=520)

    # ==================================================
    # ISSUE ASSET
    # ==================================================
    if nav == "ISSUE ASSET":
        with st.form("issue"):
            sn = st.text_input("Serial Number")
            tk = st.text_input("Ticket ID")
            if st.form_submit_button("ISSUE"):
                idx = df.index[df["SERIAL"] == sn]
                if not idx.empty:
                    ws = get_ws("Sheet1")
                    r = int(idx[0]) + 2
                    ws.update_cell(r, 6, "Issued")
                    ws.update_cell(r, 8, st.session_state["user"])
                    ws.update_cell(r, 9, tk)
                    st.success("Asset Issued Successfully")
                    time.sleep(1)
                    sync()
                    st.rerun()
                else:
                    st.error("Serial Not Found")
