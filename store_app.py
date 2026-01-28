import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import time
import plotly.express as px
import os
import base64
from io import BytesIO

# ==========================================
# 1. CORE CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="Asset Pro | Expo City", layout="wide", initial_sidebar_state="expanded")

LOGO_URL = "https://gcdn.net/wp-content/uploads/2024/11/EXPO_CITY_DUBAI_LOGO_DUAL_HORIZONTAL_YELLOW-1024x576.png"

st.markdown(f"""
<style>
    footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}
    div.stButton > button {{ background: #1A1A1A !important; color: #FFFFFF !important; border-radius: 8px !important; height: 48px !important; font-weight: 700 !important; width: 100%; }}
    .exec-card {{ background: rgba(255, 255, 255, 0.98) !important; border: 1px solid rgba(197, 160, 89, 0.4); border-radius: 12px; padding: 20px; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.05); margin-bottom: 20px; }}
    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-bottom: 10px; }}
    .metric-value {{ font-size: 32px; font-weight: 900; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA UTILITIES (FIXES DUPLICATE COLUMNS)
# ==========================================
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
    except Exception as e:
        st.error(f"Auth Error: {e}")
        return None

def get_ws(name):
    client = get_client()
    if not client: return None
    sh = client.open_by_key(SHEET_ID)
    try: return sh.worksheet(name)
    except:
        if name == "Users":
            ws = sh.add_worksheet(title="Users", rows="100", cols="5")
            ws.append_row(["Username", "PIN", "Permission"])
            return ws
        return sh.sheet1

@st.cache_data(ttl=10)
def load_data():
    ws = get_ws("Sheet1")
    vals = ws.get_all_values()
    if len(vals) < 2: return pd.DataFrame()
    
    # RENAME DUPLICATE HEADERS TO PREVENT VALUEERROR
    raw_headers = vals[0]
    clean_headers = []
    counts = {}
    for h in raw_headers:
        name = h if h.strip() != "" else "Unnamed"
        if name in counts:
            counts[name] += 1
            clean_headers.append(f"{name}.{counts[name]}")
        else:
            counts[name] = 0
            clean_headers.append(name)
            
    return pd.DataFrame(vals[1:], columns=clean_headers)

# ==========================================
# 3. INTERFACE LOGIC
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br><div class="exec-card">', unsafe_allow_html=True)
        st.image(LOGO_URL, width=150)
        mode = st.radio("GATEWAY", ["Technician", "Admin"], horizontal=True)
        with st.form("login"):
            u = st.text_input("Username") if mode == "Technician" else "Administrator"
            p = st.text_input("Password", type="password")
            if st.form_submit_button("SIGN IN"):
                if mode == "Admin" and p == "admin123":
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
                elif mode == "Technician":
                    recs = get_ws("Users").get_all_records()
                    if any(str(r.get('Username'))==u and str(r.get('PIN'))==p for r in recs):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    df = load_data()
    ws_inv = get_ws("Sheet1")

    with st.sidebar:
        st.image(LOGO_URL, width=180)
        st.markdown(f"**USER: {st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "DATABASE"]
        nav = st.radio("Navigation", menu)
        if st.button("Logout"): st.session_state.clear(); st.rerun()

    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)

    if nav == "DASHBOARD":
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f'<div class="exec-card"><p class="metric-title">Inventory Total</p><p class="metric-value">{len(df)}</p></div>', unsafe_allow_html=True)
        with m2: 
            used = len(df[df['CONDITION'].str.contains('Used', na=False)]) if not df.empty else 0
            st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{used}</p></div>', unsafe_allow_html=True)
        with m3:
            faulty = len(df[df['CONDITION'].str.contains('Faulty', na=False)]) if not df.empty else 0
            st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)

    elif nav == "ASSET CONTROL":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        t1, t2 = st.tabs(["➕ Single Asset", "📊 Bulk Upload"])
        with t1:
            with st.form("add_f"):
                c1, c2, c3 = st.columns(3)
                at, br, md = c1.text_input("Asset Type"), c2.text_input("Brand"), c3.text_input("Model")
                sn, mc, lo = c1.text_input("Serial (SN)"), c2.text_input("MAC Address"), c3.selectbox("Location", ["STORE-10", "BASEMENT"])
                if st.form_submit_button("REGISTER"):
                    ws_inv.append_row([at, br, md, sn, mc, "Available/New", lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Asset Added"); time.sleep(1); st.rerun()
        with t2:
            # Template Downloader
            template = pd.DataFrame(columns=["Asset Type", "Brand", "Model", "Serial", "MAC", "Location"])
            tmp_io = BytesIO()
            with pd.ExcelWriter(tmp_io, engine='openpyxl') as writer: template.to_excel(writer, index=False)
            st.download_button("📥 DOWNLOAD TEMPLATE", tmp_io.getvalue(), "Bulk_Template.xlsx")
            
            up_file = st.file_uploader("Upload Excel", type=["xlsx"])
            if up_file and st.button("RUN BULK UPLOAD"):
                bulk_df = pd.read_excel(up_file)
                for _, r in bulk_df.iterrows():
                    ws_inv.append_row([str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]), "Available/New", str(r[5]), "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                st.success("Done"); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        top1, top2 = st.columns([4, 1])
        with top1: q = st.text_input("🔍 Search Database")
        with top2:
            st.markdown("<br>", unsafe_allow_html=True)
            out = BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as writer: df.to_excel(writer, index=False)
            st.download_button("📥 EXCEL", out.getvalue(), "Inventory.xlsx")
        
        f_df = df[df.apply(lambda r: r.astype(str).str.contains(q, case=False).any(), axis=1)] if q else df
        st.dataframe(f_df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.dataframe(udf, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("new_u"):
                un, up = st.text_input("Name"), st.text_input("PIN")
                if st.form_submit_button("ADD TECHNICIAN"):
                    ws_u.append_row([un, up, "Standard"])
                    st.rerun()
        with c2:
            if not udf.empty:
                target = st.selectbox("Select User", udf['Username'].tolist())
                b1, b2 = st.columns(2)
                if b1.button("UPDATE PERMISSION"):
                    cell = ws_u.find(target)
                    ws_u.update_cell(cell.row, 3, "Bulk_Allowed")
                    st.success("Updated")
                if b2.button("REVOKE ACCESS"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
