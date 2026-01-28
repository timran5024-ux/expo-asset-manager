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
# 1. PROFESSIONAL ASSET MANAGEMENT SYSTEM (V2.1)
# ==========================================
st.set_page_config(
    page_title="Asset Pro | Expo City Dubai",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Background and Logo Utility
LOGO_URL = "https://gcdn.net/wp-content/uploads/2024/11/EXPO_CITY_DUBAI_LOGO_DUAL_HORIZONTAL_YELLOW-1024x576.png"

def get_base64_bin(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Inject Professional CSS
bg_css = ""
if os.path.exists("logo.png"):
    try:
        bin_str = get_base64_bin("logo.png")
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: pass

st.markdown(f"""
<style>
    .stApp {{ {bg_css} background-size: 600px; background-repeat: repeat; background-attachment: fixed; }}
    .stApp::before {{ content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255, 255, 255, 0.96); backdrop-filter: blur(12px); z-index: -1; }}
    footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}
    
    /* EXPO BLACK BUTTONS */
    div.stButton > button {{
        background: #1A1A1A !important; color: #FFFFFF !important;
        border-radius: 8px !important; height: 45px !important;
        font-weight: 700 !important; width: 100%;
    }}
    .exec-card {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 12px; padding: 20px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.05); margin-bottom: 20px;
    }}
    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; }}
    .metric-value {{ font-size: 32px; font-weight: 900; }}
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
    if len(vals) > 1:
        return pd.DataFrame(vals[1:], columns=vals[0])
    return pd.DataFrame(columns=["ASSET TYPE", "Brand", "Model", "Serial Number", "MAC Address", "CONDITION", "Location", "Issued To", "Issued Date"])

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
        # Metric Cards
        m1, m2, m3 = st.columns(3)
        with m1: st.markdown(f'<div class="exec-card"><p class="metric-title">Inventory Total</p><p class="metric-value">{len(df)}</p></div>', unsafe_allow_html=True)
        with m2: st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{len(df[df["CONDITION"]=="Available/Used"])}</p></div>', unsafe_allow_html=True)
        with m3: st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty Assets</p><p class="metric-value" style="color:#DC3545;">{len(df[df["CONDITION"]=="Faulty"])}</p></div>', unsafe_allow_html=True)

        # Condition Pie Chart
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        clr_map = {"Available/New": "#28A745", "Available/Used": "#FFD700", "Faulty": "#DC3545", "Issued": "#6C757D"}
        fig = px.pie(df, names='CONDITION', hole=0.6, color='CONDITION', color_discrete_map=clr_map)
        fig.update_layout(showlegend=True, height=400, paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "ASSET CONTROL":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        tabs = st.tabs(["➕ Add Asset", "📊 Bulk Upload", "📝 Modify", "❌ Delete"])
        
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
            up_file = st.file_uploader("Upload Excel Template", type=["xlsx", "csv"])
            if up_file and st.button("EXECUTE BULK UPLOAD"):
                try:
                    bulk_df = pd.read_excel(up_file) if up_file.name.endswith('.xlsx') else pd.read_csv(up_file)
                    for _, row in bulk_df.iterrows():
                        ws_inv.append_row([row.get('Asset Type'), row.get('Brand'), row.get('Model'), row.get('Serial'), row.get('MAC'), row.get('Status'), row.get('Location'), "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                    st.success(f"Added {len(bulk_df)} assets!"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        # Search and Download Row
        top_c1, top_c2 = st.columns([4, 1])
        with top_c1: 
            q = st.text_input("🔍 Search Full Inventory")
        with top_c2:
            st.markdown("<br>", unsafe_allow_html=True)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 DOWNLOAD EXCEL", output.getvalue(), "Inventory_Master.xlsx")
        
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
                # Parallel Buttons
                pb1, pb2 = st.columns(2)
                if pb1.button("UPDATE PERMISSION"):
                    cell = ws_u.find(target)
                    ws_u.update_cell(cell.row, 3, "Bulk_Allowed")
                    st.success("Updated")
                if pb2.button("REVOKE ACCESS"):
                    ws_u.delete_rows(ws_u.find(target).row)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
