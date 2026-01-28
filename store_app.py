import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import plotly.express as px
import os
import base64
from io import BytesIO

# ==========================================
# 1. STABILITY & UI ENGINE (V2.2)
# ==========================================
st.set_page_config(
    page_title="Asset Pro | Expo City",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Background and Logo Utility
LOGO_URL = "https://gcdn.net/wp-content/uploads/2024/11/EXPO_CITY_DUBAI_LOGO_DUAL_HORIZONTAL_YELLOW-1024x576.png"

def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

st.markdown(f"""
<style>
    footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}
    
    /* EXPO BLACK BUTTONS */
    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 8px !important; height: 45px !important;
        font-weight: 700 !important; width: 100%;
    }}
    div.stButton > button p {{ color: white !important; font-size: 14px !important; font-weight: 800 !important; }}

    .exec-card {{
        background: rgba(255, 255, 255, 0.98) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 12px; padding: 20px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.05); margin-bottom: 20px;
    }}
    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; }}
    .metric-value {{ font-size: 32px; font-weight: 900; }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# ==========================================
# 2. CORE UTILITIES (WITH ERROR CATCHING)
# ==========================================
@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        return None

def get_ws(name):
    client = get_client()
    if not client: return None
    try:
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet(name)
    except gspread.exceptions.APIError as e:
        st.error("Google API Error: Check if you have shared the sheet with your Service Account email.")
        st.stop()
    except Exception:
        # Create Users sheet if it doesn't exist
        if name == "Users":
            sh = client.open_by_key(SHEET_ID)
            ws = sh.add_worksheet(title="Users", rows="100", cols="5")
            ws.append_row(["Username", "PIN", "Permission"])
            return ws
        return None

def load_data():
    ws = get_ws("Sheet1")
    if not ws: return pd.DataFrame()
    vals = ws.get_all_values()
    if len(vals) > 1:
        return pd.DataFrame(vals[1:], columns=vals[0])
    return pd.DataFrame()

# ==========================================
# 3. INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<div class="exec-card" style="margin-top:100px; text-align:center;">', unsafe_allow_html=True)
        st.image(LOGO_URL, width=150)
        mode = st.radio("GATEWAY", ["Technician", "Admin"], horizontal=True)
        with st.form("login"):
            u = st.text_input("Username") if mode == "Technician" else "Administrator"
            p = st.text_input("Password", type="password")
            if st.form_submit_button("SIGN IN"):
                if (mode == "Admin" and p == "admin123") or mode == "Technician":
                    st.session_state.update(logged_in=True, user=u, role=mode)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
else:
    df = load_data()
    ws_inv = get_ws("Sheet1")

    with st.sidebar:
        st.image(LOGO_URL, width=180)
        st.markdown(f"**SESSION: {st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "DATABASE"]
        nav = st.radio("Navigation", menu)
        if st.button("Logout"): st.session_state.clear(); st.rerun()

    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)

    if nav == "DASHBOARD":
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f'<div class="exec-card"><p class="metric-title">Inventory Total</p><p class="metric-value">{len(df)}</p></div>', unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{len(df[df["CONDITION"]=="Available/Used"]) if not df.empty else 0}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{len(df[df["CONDITION"]=="Faulty"]) if not df.empty else 0}</p></div>', unsafe_allow_html=True)

    elif nav == "ASSET CONTROL":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        tabs = st.tabs(["➕ Single Asset", "📊 Bulk Upload"])
        
        with tabs[0]:
            with st.form("manual_add"):
                c1, c2, c3 = st.columns(3)
                at, br, md = c1.text_input("Asset Type"), c2.text_input("Brand"), c3.text_input("Model")
                sn, mc, lo = c1.text_input("Serial (SN)"), c2.text_input("MAC Address"), c3.selectbox("Location", ["STORE-10", "BASEMENT"])
                st_v = st.selectbox("Status", ["Available/New", "Available/Used", "Faulty"])
                if st.form_submit_button("REGISTER ASSET"):
                    ws_inv.append_row([at, br, md, sn, mc, st_v, lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Asset Added"); time.sleep(1); st.rerun()

        with tabs[1]:
            st.markdown("### Bulk Excel Import")
            # Template Downloader
            template_df = pd.DataFrame(columns=["Asset Type", "Brand", "Model", "Serial", "MAC", "Status", "Location"])
            tmp_io = BytesIO()
            with pd.ExcelWriter(tmp_io, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False)
            st.download_button("📥 DOWNLOAD TEMPLATE", tmp_io.getvalue(), "Bulk_Import_Template.xlsx")
            
            up_file = st.file_uploader("Upload Completed Template", type=["xlsx", "csv"])
            if up_file and st.button("EXECUTE BULK UPLOAD"):
                try:
                    bulk_df = pd.read_excel(up_file) if up_file.name.endswith('.xlsx') else pd.read_csv(up_file)
                    for _, row in bulk_df.iterrows():
                        ws_inv.append_row([str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]), str(row[5]), str(row[6]), "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success(f"Added {len(bulk_df)} assets!"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Check your Excel columns match the template! Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        top_c1, top_c2 = st.columns([4, 1.2])
        with top_c1: q = st.text_input("🔍 Search Full Inventory")
        with top_c2:
            st.markdown("<br>", unsafe_allow_html=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 DOWNLOAD EXCEL", output.getvalue(), "Inventory_Master.xlsx", use_container_width=True)
        
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
                if st.form_submit_button("CREATE USER"):
                    ws_u.append_row([un, up, "Standard"])
                    st.rerun()
        with c2:
            if not udf.empty:
                target = st.selectbox("Select User", udf['Username'].tolist())
                # PARALLEL BUTTONS
                pb1, pb2 = st.columns(2)
                if pb1.button("UPDATE PERMISSION"):
                    cell = ws_u.find(target)
                    ws_u.update_cell(cell.row, 3, "Bulk_Allowed")
                    st.success("Updated")
                if pb2.button("REVOKE ACCESS"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
