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
# 1. HIGH-CONTRAST BOLD & VISIBLE CSS
# ==========================================
st.set_page_config(
    page_title="Asset Management Pro", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Background Pattern Logic
bg_css = ""
if os.path.exists("logo.png"):
    try:
        bin_str = get_base64_bin("logo.png")
        bg_css = f"""
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
            background-size: cover; 
        }}
        .stApp::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(255, 255, 255, 0.95); 
            z-index: -1;
        }}
        """
    except: pass

st.markdown(f"""
<style>
    {bg_css}
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; height: 0 !important; }}
    
    /* GLOBAL BOLD RESET */
    * {{
        font-weight: 800 !important;
        color: #000000 !important;
    }}

    .main .block-container {{ 
        padding: 1.5rem !important; 
        max-width: 100% !important; 
        margin-top: -20px !important;
    }}

    .centered-title {{
        text-align: center;
        color: #000000 !important;
        font-size: clamp(28px, 6vw, 42px);
        font-weight: 900 !important;
        letter-spacing: 2px;
        margin-bottom: 45px;
        text-transform: uppercase;
        padding-top: 15px;
    }}

    /* INPUTS - HIGH VISIBILITY */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {{
        background-color: #FFFFFF !important;
        border: 2.5px solid #000000 !important;
        border-radius: 12px !important;
        height: 55px !important;
        color: #000000 !important;
        font-size: 18px !important;
    }}

    /* --- BUTTON COLOR & VISIBILITY FIXES --- */
    
    /* BLUE BUTTON (Refresh) */
    button[key="final_refresh_btn"] {{ 
        background-color: #007BFF !important; 
        color: #FFFFFF !important; 
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }}

    /* RED BUTTON (Logout) */
    button[key="final_logout_btn"] {{ 
        background-color: #FF4B4B !important; 
        color: #FFFFFF !important; 
        border: none !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }}

    /* BLACK/DARK BUTTONS (Submit) - FORCING WHITE TEXT VISIBILITY */
    button[kind="secondaryFormSubmit"], .stButton>button {{
        background-color: #111111 !important;
        color: #FFFFFF !important; /* FIXED: Text now visible on black */
        height: 55px !important;
        border: none !important;
        font-size: 16px !important;
        border-radius: 12px !important;
    }}
    
    /* Hover effect for buttons */
    button:hover {{
        opacity: 0.9 !important;
        transform: scale(1.02) !important;
        transition: 0.2s !important;
    }}

    /* PROFILE & CONTAINERS */
    .profile-box {{
        background-color: #FFFFFF;
        border: 2.5px solid #000000;
        border-radius: 12px;
        text-align: center;
        padding: 10px;
        font-size: 16px;
    }}

    /* DATA CONTAINERS (Glass Effect for visibility over pattern) */
    div[data-testid="column"] > div {{
        background-color: rgba(255, 255, 255, 1.0) !important;
        border: 2.5px solid #000000 !important;
        border-radius: 18px !important;
        padding: 25px !important;
        box-shadow: 0 8px 30px rgba(0,0,0,0.05) !important;
    }}
    
    /* Metric label visibility */
    [data-testid="stMetricLabel"] p {{
        font-size: 1.2rem !important;
        color: #333333 !important;
    }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SESSION_SECRET = "expo_final_v141_visible"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
HEADERS = ["ASSET TYPE", "BRAND", "MODEL", "SERIAL", "MAC ADDRESS", "CONDITION", "LOCATION", "ISSUED TO", "TICKET", "TIMESTAMP", "USER"]

# ==========================================
# 2. CORE UTILITIES
# ==========================================
def make_token(u): return hashlib.sha256(f"{u}{SESSION_SECRET}".encode()).hexdigest()

@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
    except: return None

def get_ws(name):
    client = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except: return client.open_by_key(SHEET_ID).sheet1

def load_data():
    ws = get_ws("Sheet1")
    if not ws: return pd.DataFrame(columns=HEADERS)
    vals = ws.get_all_values()
    if len(vals) < 2: return pd.DataFrame(columns=HEADERS)
    return pd.DataFrame(vals[1:], columns=HEADERS)

def sync():
    st.session_state['inventory_df'] = load_data()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    return output.getvalue()

# ==========================================
# 3. AUTHENTICATION
# ==========================================
if 'logged_in' not in st.session_state:
    p = st.query_params
    u, t = p.get("user"), p.get("token")
    if u and t and t == make_token(u):
        st.session_state.update(logged_in=True, user=u, role="Admin" if u=="Administrator" else "Technician")
    else: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<br><br><h1 style='text-align: center; color: #000000; font-weight: 900;'>ASSET MANAGEMENT PRO</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.6, 1])
    with c2:
        tabs = st.tabs(["TECHNICIAN", "ADMINISTRATOR"])
        with tabs[0]:
            with st.form("t_login"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("LOGIN"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.query_params.update(user=u, token=make_token(u))
                        st.rerun()
                    else: st.error("Access Denied")
        with tabs[1]:
            with st.form("a_log"):
                p = st.text_input("Master Password", type="password")
                if st.form_submit_button("ADMIN ACCESS"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.query_params.update(user="Administrator", token=make_token("Administrator"))
                        st.rerun()
                    else: st.error("Invalid")
else:
    if 'inventory_df' not in st.session_state: sync()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    # HEADER
    st.markdown('<div class="centered-title">Asset Management</div>', unsafe_allow_html=True)
    
    h_nav, h_user, h_sync, h_out = st.columns([4, 2, 1, 1])
    with h_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET", "MY VIEW"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    with h_user: st.markdown(f'<div class="profile-box">👤 {st.session_state["user"]}</div>', unsafe_allow_html=True)
    with h_sync:
        if st.button("GET DATA", key="final_refresh_btn", use_container_width=True): sync(); st.rerun()
    with h_out:
        if st.button("LOGOUT", key="final_logout_btn", use_container_width=True): st.session_state.clear(); st.query_params.clear(); st.rerun()
    st.markdown("<hr style='margin: 15px 0; border: 2.5px solid #000000;'>", unsafe_allow_html=True)

    # PAGE ROUTING
    if nav == "DASHBOARD":
        st.markdown("### 📊 Analytics Stock Overview")
        clr_map = {"Available/New": "#1E7E34", "Available/Used": "#2E8B57", "Issued": "#0056b3", "Faulty": "#bd2130"}
        if not df.empty:
            models = sorted([m for m in df['MODEL'].unique() if m.strip() != ""])
            grid = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                t, a, s, f = len(sub), len(sub[sub['CONDITION'].str.contains('Available', na=False)]), len(sub[sub['CONDITION'] == 'Issued']), len(sub[sub['CONDITION'] == 'Faulty'])
                with grid[i % 3]:
                    st.markdown(f"<div style='text-align:center;'><b style='font-size:1.5rem;'>{model}</b><br><span>Total Units: {t}</span><br><div style='margin-top:10px;'><span style='color:#1E7E34;'>Avail: {a}</span> | <span style='color:#0056b3;'>Issued: {s}</span> | <span style='color:#bd2130;'>Faulty: {f}</span></div></div>", unsafe_allow_html=True)
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color='CONDITION', color_discrete_map=clr_map)
                    fig.update_layout(showlegend=False, height=240, margin=dict(t=10,b=10,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"v141_pie_{i}")

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown("### 🛠️ Inventory Management")
        t1, t2, t3 = st.tabs(["➕ Add Asset", "📝 Modify Asset", "❌ Remove Asset"])
        with t1:
            with st.form("f_add"):
                c1, c2, c3 = st.columns(3)
                at, br, md = c1.text_input("Asset Type"), c2.text_input("Brand"), c3.text_input("Model")
                sn, mc = c1.text_input("Serial Number"), c2.text_input("MAC Address")
                lo = c3.selectbox("Location", ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT", "TERRA BASEMENT"], key="st_add")
                if st.form_submit_button("SAVE TO DATABASE"):
                    if sn:
                        ws_inv.append_row([at, br, md, sn, mc, "Available/New", lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("DONE"); time.sleep(1); sync(); st.rerun()
                    else: st.error("Serial Required")
        with t2:
            s_sn = st.text_input("Enter Serial to Edit")
            if s_sn:
                match = df[df['SERIAL'].astype(str).str.upper() == s_sn.strip().upper()]
                if not match.empty:
                    item = match.iloc[0]
                    with st.form("f_mod"):
                        n_br, n_md = st.text_input("Brand", value=item['BRAND']), st.text_input("Model", value=item['MODEL'])
                        n_mc = st.text_input("MAC", value=item['MAC ADDRESS'])
                        n_lo = st.selectbox("Location", ["MOBILITY STORE-10", "MOBILITY STORE-8", "SUSTAINABILITY BASEMENT", "TERRA BASEMENT"], key="st_mod")
                        if st.form_submit_button("UPDATE ASSET"):
                            ridx = int(df.index[df['SERIAL'] == s_sn][0]) + 2
                            ws_inv.update(f"B{ridx}:C{ridx}", [[n_br, n_md]])
                            ws_inv.update_cell(ridx, 5, n_mc); ws_inv.update_cell(ridx, 7, n_lo)
                            st.success("DONE"); time.sleep(1); sync(); st.rerun()
        with t3:
            r_sn = st.text_input("Enter Serial to Delete")
            if r_sn:
                match = df[df['SERIAL'].astype(str).str.upper() == r_sn.strip().upper()]
                if not match.empty:
                    st.error(f"Deleting {match.iloc[0]['MODEL']} (SN: {r_sn})")
                    if st.button("CONFIRM DELETE", use_container_width=True):
                        ws_inv.delete_rows(int(df.index[df['SERIAL'] == r_sn][0]) + 2)
                        st.success("DONE"); time.sleep(1); sync(); st.rerun()

    elif nav == "DATABASE":
        st.markdown("### 📦 Inventory Records")
        col_s, col_dl = st.columns([4, 1.5])
        with col_s: q = st.text_input("🔍 Search Database...", placeholder="Type serial, model or brand...")
        with col_dl: 
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button("📥 DOWNLOAD EXCEL", to_excel(df), "inventory_master.xlsx", use_container_width=True)
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)

    elif nav == "USER MANAGER":
        st.markdown("### 👤 Admin User Tools")
        ws_u = get_ws("Users")
        if ws_u:
            udf = pd.DataFrame(ws_u.get_all_records())
            st.dataframe(udf, use_container_width=True)
            u_t1, u_t2 = st.tabs(["Manage Users", "Permissions"])
            with u_t1:
                with st.form("u_add"):
                    un, up = st.text_input("Username"), st.text_input("PIN Code")
                    if st.form_submit_button("CREATE USER"):
                        ws_u.append_row([un, up, "Standard"])
                        st.success("DONE"); time.sleep(1); st.rerun()
                target = st.selectbox("Select User to Remove", udf['Username'].tolist() if not udf.empty else ["-"])
                if st.button("DELETE USER ACCESS", use_container_width=True) and target != "-":
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("DONE"); time.sleep(1); st.rerun()
            with u_t2:
                if not udf.empty:
                    target_p = st.selectbox("Update Level for", udf['Username'].tolist())
                    new_perm = st.selectbox("New Permission Level", ["Standard", "Bulk_Allowed"])
                    if st.button("SAVE PERMISSION CHANGE", use_container_width=True):
                        cell = ws_u.find(target_p)
                        ws_u.update_cell(cell.row, 3, new_perm)
                        st.success("DONE"); time.sleep(1); st.rerun()

    elif nav == "ISSUE ASSET":
        with st.form("iss_f"):
            st.markdown("### 🚀 Asset Issuance")
            sn, tkt = st.text_input("Serial Number"), st.text_input("Ticket ID")
            if st.form_submit_button("AUTHORIZE"):
                idx = df.index[df['SERIAL'] == sn]
                if not idx.empty:
                    ws_inv.update_cell(int(idx[0])+2, 6, "Issued")
                    ws_inv.update_cell(int(idx[0])+2, 8, st.session_state['user'])
                    ws_inv.update_cell(int(idx[0])+2, 9, tkt)
                    st.success("DONE"); time.sleep(1); sync(); st.rerun()
                else: st.error("Serial not found")

    elif nav == "RETURN ASSET":
        st.markdown("### 📥 Return to Store")
        my_df = df[df['ISSUED TO'] == st.session_state['user']]
        if not my_df.empty:
            target = st.selectbox("Asset for Return", my_df['SERIAL'].tolist())
            with st.form("ret_form"):
                cond = st.selectbox("Current Condition", ["Available/New", "Available/Used", "Faulty"])
                if st.form_submit_button("COMPLETE RETURN"):
                    ridx = int(df.index[df['SERIAL'] == target][0]) + 2
                    ws_inv.update_cell(ridx, 6, cond); ws_inv.update_cell(ridx, 8, "")
                    st.success("DONE"); time.sleep(1); sync(); st.rerun()
        else: st.info("No assets currently issued.")
