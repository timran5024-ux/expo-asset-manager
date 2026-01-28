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
# 1. ENTERPRISE GRADE UI ENGINE (V152)
# ==========================================
st.set_page_config(page_title="Asset Management Pro", layout="wide", initial_sidebar_state="collapsed")

# Professional Background Logic
if os.path.exists("logo.png"):
    with open("logo.png", "rb") as f:
        bin_str = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-attachment: fixed;
        }}
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(255, 255, 255, 0.96); z-index: -1;
        }}
        
        /* FORCE WHITE TEXT ON ALL BLACK BUTTONS */
        div.stButton > button {{
            background-color: #000000 !important;
            color: #FFFFFF !important;
            border-radius: 12px !important;
            height: 55px !important;
            border: none !important;
            font-weight: 800 !important;
        }}
        div.stButton > button p {{ color: white !important; font-weight: 900 !important; }}

        /* PROFESSIONAL INPUT BOXES */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            background-color: #FFFFFF !important;
            border: 2px solid #111111 !important;
            border-radius: 12px !important;
            height: 50px !important;
            padding: 0 15px !important;
        }}

        /* SOLID CONTENT CARDS (Prevents background pattern overlap) */
        [data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {{
            background: #FFFFFF !important;
            padding: 30px !important;
            border-radius: 20px !important;
            box-shadow: 0 12px 30px rgba(0,0,0,0.1) !important;
            border: 1px solid #EEEEEE !important;
        }}

        .centered-title {{
            text-align: center; font-size: clamp(24px, 5vw, 42px); font-weight: 900; 
            color: #111111; margin-bottom: 45px; text-transform: uppercase;
        }}
    </style>
    """, unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"

# ==========================================
# 2. DATA CORE
# ==========================================
@st.cache_resource
def get_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
    return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]))

def get_ws(name):
    sh = get_client().open_by_key(SHEET_ID)
    try: return sh.worksheet(name)
    except: return sh.sheet1

def load_data():
    ws = get_ws("Sheet1")
    vals = ws.get_all_values()
    return pd.DataFrame(vals[1:], columns=vals[0]) if len(vals) > 1 else pd.DataFrame()

# ==========================================
# 3. DUAL LOGIN (TECH vs ADMIN)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown('<div class="centered-title">ASSET MANAGEMENT PRO</div>', unsafe_allow_html=True)
    c1, mid, c3 = st.columns([1, 2, 1])
    with mid:
        tab_log = st.tabs(["TECHNICIAN LOGIN", "ADMIN PORTAL"])
        with tab_log[0]:
            with st.form("tech_log_form"):
                u = st.text_input("Username")
                p = st.text_input("PIN", type="password")
                if st.form_submit_button("ENTER SYSTEM"):
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Denied")
        with tab_log[1]:
            with st.form("admin_log_form"):
                p = st.text_input("Master Password", type="password")
                if st.form_submit_button("AUTHENTICATE ADMIN"):
                    if p == ADMIN_PASSWORD:
                        st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                        st.rerun()
                    else: st.error("Incorrect Password")

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    st.markdown('<div class="centered-title">Asset Management</div>', unsafe_allow_html=True)
    
    # ACTION BAR
    h_nav, h_user, h_sync, h_out = st.columns([4, 2, 1, 1])
    with h_nav:
        opts = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role'] == "Admin" else ["ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.selectbox("", opts, label_visibility="collapsed")
    with h_user: st.markdown(f'<div style="text-align:right; font-weight:bold; padding-top:15px; color:black;">👤 {st.session_state["user"]}</div>', unsafe_allow_html=True)
    with h_sync:
        if st.button("SYNC", key="btn_sync"):
            st.session_state['inventory_df'] = load_data()
            st.rerun()
    with h_out:
        if st.button("LOGOUT", key="btn_logout"):
            st.session_state.clear(); st.rerun()

    st.markdown("---")

    if nav == "DASHBOARD":
        st.subheader("Performance Analytics")
        if not df.empty:
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.markdown(f"**{model}** (Total: {len(sub)})")
                    fig = px.pie(sub, names='CONDITION', hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
                    fig.update_layout(showlegend=False, height=220, margin=dict(t=0,b=0,l=0,r=0))
                    # FIX: Unique key for every chart
                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{model}_{i}")
        else: st.info("No data recorded yet.")

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.subheader("Global Inventory Control")
        t_ctrl = st.tabs(["➕ Add Asset", "📝 Modify Info", "❌ Delete Permanent"])
        
        with t_ctrl[0]:
            with st.form("add_asset_f"):
                c1, c2, c3 = st.columns(3)
                at, br, md = c1.text_input("Type"), c2.text_input("Brand"), c3.text_input("Model")
                sn, mc = c1.text_input("Serial"), c2.text_input("MAC")
                if st.form_submit_button("COMMIT TO DATABASE"):
                    if sn:
                        ws_inv.append_row([at, br, md, sn, mc, "Available/New", "MOBILITY STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("Successfully Registered")
                        time.sleep(1); st.rerun()

        with t_ctrl[1]:
            s_sn = st.text_input("Enter Serial to Modify", key="mod_search")
            if s_sn:
                match = df[df['SERIAL'] == s_sn]
                if not match.empty:
                    with st.form("mod_asset_f"):
                        n_br = st.text_input("Brand", value=match.iloc[0]['BRAND'])
                        n_md = st.text_input("Model", value=match.iloc[0]['MODEL'])
                        if st.form_submit_button("SAVE CHANGES"):
                            ridx = int(df.index[df['SERIAL'] == s_sn][0]) + 2
                            ws_inv.update_cell(ridx, 2, n_br); ws_inv.update_cell(ridx, 3, n_md)
                            st.success("Update Successful"); time.sleep(1); st.rerun()

        with t_ctrl[2]:
            d_sn = st.text_input("Serial for Permanent Deletion", key="del_search")
            if d_sn:
                if st.button("DELETE NOW", key="btn_del_confirm"):
                    idx = df.index[df['SERIAL'] == d_sn]
                    if not idx.empty:
                        ws_inv.delete_rows(int(idx[0]) + 2)
                        st.success("Asset Deleted Permanently"); time.sleep(1); st.rerun()

    elif nav == "DATABASE":
        st.subheader("Master Record Set")
        st.dataframe(df, use_container_width=True)
