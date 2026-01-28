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
# LOAD LOGO
# ======================================================
LOGO_PATH = "logo.png"
logo = Image.open(LOGO_PATH)

# ======================================================
# MODERN UI / UX CSS
# ======================================================
st.markdown("""
<style>
:root {
    --primary:#2563EB;
    --dark:#0F172A;
    --muted:#64748B;
    --bg:#F8FAFC;
    --card:#FFFFFF;
    --border:#E5E7EB;
    --success:#16A34A;
    --danger:#DC2626;
}

.stApp {
    background: var(--bg);
    font-family: 'Inter', system-ui, sans-serif;
}

header, footer, #MainMenu { visibility: hidden; }

.block-container {
    padding-top: 1.5rem !important;
    max-width: 96% !important;
}

.centered-title {
    text-align: center;
    font-size: 36px;
    font-weight: 900;
    color: var(--dark);
    margin-bottom: 30px;
    letter-spacing: 1px;
}

.logo-box {
    display: flex;
    justify-content: center;
    margin-bottom: 15px;
}

div[data-testid="column"] {
    background: var(--card);
    border-radius: 18px;
    border: 1px solid var(--border);
    padding: 22px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.05);
    transition: all .3s ease;
}

div[data-testid="column"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 40px rgba(0,0,0,0.08);
}

.stTextInput input,
.stSelectbox div[data-baseweb="select"] {
    border-radius: 14px !important;
    height: 46px !important;
    border: 1px solid var(--border) !important;
}

.stButton button {
    border-radius: 14px;
    height: 46px;
    font-weight: 800;
}

button[key="final_refresh_btn"] {
    background: linear-gradient(135deg,#2563EB,#1D4ED8);
    color: white;
}

button[key="final_logout_btn"] {
    background: linear-gradient(135deg,#DC2626,#B91C1C);
    color: white;
}

.profile-box {
    background: linear-gradient(135deg,#0F172A,#1E293B);
    color: white;
    border-radius: 999px;
    height: 46px;
    font-weight: 700;
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
    creds["private_key"] = creds["private_key"].replace("\\n","\n")
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
            role="Admin" if p.get("user")=="Administrator" else "Technician"
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

    c1,c2,c3 = st.columns([1,1.4,1])
    with c2:
        tabs = st.tabs(["TECHNICIAN","ADMIN"])
        with tabs[0]:
            with st.form("tlogin"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    users = get_ws("Users").get_all_records()
                    if any(x["Username"]==u and str(x["PIN"])==p for x in users):
                        st.session_state.update(logged_in=True,user=u,role="Technician")
                        st.query_params.update(user=u,token=make_token(u))
                        st.rerun()
                    else:
                        st.error("Access Denied")

        with tabs[1]:
            with st.form("alogin"):
                p = st.text_input("Admin Password", type="password")
                if st.form_submit_button("LOGIN"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True,user="Administrator",role="Admin")
                        st.query_params.update(user="Administrator",token=make_token("Administrator"))
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
    ws_inv = get_ws("Sheet1")

    st.markdown('<div class="logo-box">', unsafe_allow_html=True)
    st.image(logo, width=80)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div class='centered-title'>Asset Management</div>", unsafe_allow_html=True)

    h1,h2,h3,h4
