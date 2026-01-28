import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import hashlib
import os
import base64
from io import BytesIO

# ==========================================
# 1. EXECUTIVE EXPO THEME ENGINE (V163)
# ==========================================
st.set_page_config(page_title="Asset Management Pro", layout="wide", initial_sidebar_state="expanded")

def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

bg_css = ""
if os.path.exists("logo.png"):
    try:
        bin_str = get_base64_bin("logo.png")
        bg_css = f"""
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: 600px; background-repeat: repeat; background-attachment: fixed;
        }}
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(248, 250, 252, 0.96); backdrop-filter: blur(12px); z-index: -1;
        }}
        """
    except: pass

st.markdown(f"""
<style>
    {bg_css}
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}

    /* EXECUTIVE FROSTED SIDEBAR */
    section[data-testid="stSidebar"] {{
        background-color: rgba(255, 255, 255, 0.7) !important;
        backdrop-filter: blur(25px);
        border-right: 1px solid rgba(197, 160, 89, 0.3);
    }}

    /* GLASS CONTENT CARDS */
    .exec-card {{
        background: rgba(255, 255, 255, 0.92) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 16px; padding: 35px;
        box-shadow: 0 12px 45px rgba(0, 0, 0, 0.05); margin-bottom: 25px;
    }}

    /* CORPORATE INPUTS */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
        border: 1.5px solid #E5E7EB !important; border-radius: 10px !important;
        height: 48px !important; background: #FFFFFF !important;
    }}
    .stTextInput input:focus {{ border-color: #C5A059 !important; box-shadow: 0 0 0 4px rgba(197, 160, 89, 0.15) !important; }}

    /* EXPO BLACK BUTTONS */
    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 10px !important; height: 52px !important;
        border: none !important; font-weight: 700 !important;
    }}
    div.stButton > button p {{ color: white !important; font-size: 16px; }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v163_full"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. DATA CORE
# ==========================================
def make_token(u): return hashlib.sha256(f"{u}{SESSION_SECRET}".encode()).hexdigest()

@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
    return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))

def get_ws(name):
    sh = get_client().open_by_key(SHEET_ID)
    try: return sh.worksheet(name)
    except: return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    vals = ws.get_all_values()
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()

# ==========================================
# 3. SYSTEM AUTHENTICATION
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
        st.markdown("### System Authentication")
        portal = st.radio("Node", ["Technician", "Admin"], horizontal=True, label_visibility="collapsed")
        with st.form("auth"):
            if portal == "Technician":
                u = st.text_input("Corporate ID")
                p = st.text_input("Access PIN", type="password")
            else:
                p = st.text_input("Master Key", type="password")
            if st.form_submit_button("AUTHENTICATE"):
                if portal == "Technician":
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                elif p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 4. EXECUTIVE SUITE INTERFACE
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.markdown(f"**{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.radio("System Menu", menu)
        st.markdown('<br>' * 8, unsafe_allow_html=True)
        if st.button("Logout System", use_container_width=True):
            st.session_state.clear(); st.rerun()

    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)

    if nav == "DASHBOARD":
        if not df.empty:
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            # EXPO EXECUTIVE COLOR PALETTE
            clr_map = {"Available/New": "#28A745", "Available/Used": "#007BFF", "Issued": "#6C757D", "Faulty": "#DC3545"}
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.write(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=clr_map)
                    fig.update_layout(showlegend=False, height=200, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"v163_{model}_{i}")
            st.markdown('</div>', unsafe_allow_html=True)

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        t = st.tabs(["➕ Add Asset", "📝 Modify Info", "❌ Decommission"])
        with t[0]:
            with st.form("add"):
                c1, c2, c3 = st.columns(3)
                at, br, md = c1.text_input("Type"), c2.text_input("Brand"), c3.text_input("Model")
                sn = st.text_input("Serial (SN)")
                if st.form_submit_button("REGISTER"):
                    ws_inv.append_row([at, br, md, sn, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Registration Complete"); time.sleep(1); st.rerun()
        with t[1]:
            s_sn = st.text_input("Search SN to Modify")
            if s_sn:
                match = df[df['SERIAL'] == s_sn]
                if not match.empty:
                    with st.form("mod"):
                        n_br = st.text_input("Brand", value=match.iloc[0]['BRAND'])
                        n_md = st.text_input("Model", value=match.iloc[0]['MODEL'])
                        if st.form_submit_button("SAVE UPDATES"):
                            ridx = int(df.index[df['SERIAL'] == s_sn][0]) + 2
                            ws_inv.update_cell(ridx, 2, n_br); ws_inv.update_cell(ridx, 3, n_md)
                            st.success("Updated"); time.sleep(1); st.rerun()
        with t[2]:
            d_sn = st.text_input("SN to Delete")
            if st.button("CONFIRM PERMANENT DELETE"):
                idx = df.index[df['SERIAL'] == d_sn]
                if not idx.empty:
                    ws_inv.delete_rows(int(idx[0]) + 2)
                    st.success("Purged"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        q = st.text_input("🔍 Filter Inventory (Search by SN, Model, or Brand)")
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.dataframe(udf, use_container_width=True)
        u1, u2 = st.columns(2)
        with u1:
            with st.form("u_new"):
                un, up = st.text_input("New Name"), st.text_input("PIN")
                if st.form_submit_button("CREATE ACCOUNT"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("User Created"); st.rerun()
        with u2:
            target = st.selectbox("Select to Remove", udf['Username'].tolist() if not udf.empty else ["-"])
            if st.button("REVOKE ACCESS"):
                ws_u.delete_rows(ws_u.find(target).row)
                st.success("Revoked"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
