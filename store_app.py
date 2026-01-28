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
# 1. ENTERPRISE BULK UI ENGINE (V182)
# ==========================================
st.set_page_config(page_title="Asset Pro | Bulk Edition", layout="wide", initial_sidebar_state="expanded")

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
            background: rgba(255, 255, 255, 0.96); backdrop-filter: blur(12px); z-index: -1;
        }}
        """
    except: pass

st.markdown(f"""
<style>
    {bg_css}
    header, footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}

    /* EXPO BLACK BUTTONS */
    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 10px !important; height: 50px !important;
        border: none !important; font-weight: 700 !important; width: 100%;
    }}
    div.stButton > button p {{ color: white !important; font-size: 15px !important; font-weight: 800 !important; }}

    .exec-card {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 12px; padding: 20px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.05); margin-bottom: 20px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CORE UTILITIES
# ==========================================
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

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
# 3. INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # [Login logic remains stable as per V181]
    pass
else:
    df = load_data()
    ws_inv = get_ws("Sheet1")
    
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=130)
        st.markdown(f"**USER: {st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["DASHBOARD", "ASSET CONTROL", "DATABASE"]
        nav = st.radio("System Navigation", menu)
        if st.button("Logout"): st.session_state.clear(); st.rerun()

    if nav == "ASSET CONTROL":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.markdown("### Manual & Bulk Inventory Control")
        tabs = st.tabs(["➕ Single Asset", "📊 Bulk Upload", "📝 Modify", "❌ Delete"])
        
        with tabs[0]:
            with st.form("manual_add"):
                c1, c2, c3 = st.columns(3)
                at = c1.text_input("Asset Type")
                br = c2.text_input("Brand")
                md = c3.text_input("Model")
                sn = c1.text_input("Serial (SN)")
                mc = c2.text_input("MAC Address")
                lo = c3.selectbox("Location", ["MOBILITY STORE-10", "BASEMENT", "TERRA"])
                st_v = st.selectbox("Status", ["Available/New", "Available/Used", "Faulty"])
                if st.form_submit_button("REGISTER ASSET"):
                    ws_inv.append_row([at, br, md, sn, mc, st_v, lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success("Asset Saved Successfully"); time.sleep(1); st.rerun()

        with tabs[1]:
            st.markdown("#### Mass Upload Utility")
            st.info("Upload an Excel file with columns: Asset Type, Brand, Model, Serial, MAC, Status, Location")
            uploaded_file = st.file_uploader("Choose Excel/CSV file", type=["xlsx", "csv"])
            if uploaded_file and st.button("EXECUTE BULK UPLOAD"):
                try:
                    bulk_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    # Mapping data to sheet format
                    for _, row in bulk_df.iterrows():
                        ws_inv.append_row([row.get('Asset Type', ''), row.get('Brand', ''), row.get('Model', ''), 
                                           row.get('Serial', ''), row.get('MAC', ''), row.get('Status', 'Available/New'), 
                                           row.get('Location', 'STORE-10'), "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success(f"Successfully added {len(bulk_df)} items!"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "USER MANAGER":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        udf = pd.DataFrame(ws_u.get_all_records())
        st.dataframe(udf, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("new_user"):
                un, up = st.text_input("Name"), st.text_input("PIN")
                if st.form_submit_button("CREATE"):
                    ws_u.append_row([un, up, "Standard"])
                    st.success("User Added"); st.rerun()
        with c2:
            if not udf.empty:
                target = st.selectbox("Select User", udf['Username'].tolist())
                new_p = st.selectbox("Level", ["Standard", "Bulk_Allowed"])
                
                # PARALLEL BUTTONS
                b1, b2 = st.columns(2)
                if b1.button("UPDATE PERMISSION"):
                    cell = ws_u.find(target)
                    ws_u.update_cell(cell.row, 3, new_p)
                    st.success("Permission Set")
                if b2.button("REVOKE ACCESS"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.success("Revoked"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
