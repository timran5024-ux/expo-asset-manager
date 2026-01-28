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
# 1. EXPO CITY DUBAI PROFESSIONAL THEME
# ==========================================
st.set_page_config(page_title="Asset Pro | Expo City", layout="wide", initial_sidebar_state="expanded")

# Background logic using your logo pattern
if os.path.exists("logo.png"):
    with open("logo.png", "rb") as f:
        bin_str = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: 800px;
            background-repeat: repeat;
            background-attachment: fixed;
        }}
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(255, 255, 255, 0.92); 
            backdrop-filter: blur(8px);
            z-index: -1;
        }}
        
        /* THE EXPO WHITE CARD - Solid and Professional */
        [data-testid="stVerticalBlock"] > div > div > div[data-testid="stVerticalBlock"] {{
            background: #FFFFFF !important;
            padding: 40px !important;
            border-radius: 12px !important;
            box-shadow: 0 10px 40px rgba(0,0,0,0.06) !important;
            border: 1px solid #F0F0F0 !important;
        }}

        /* CLEAN TYPOGRAPHY */
        h1, h2, h3, label p {{
            color: #1A1A1A !important;
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
            font-weight: 600 !important;
        }}

        /* INPUT BOXES: EXPO STYLE */
        .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
            border: 1px solid #E5E7EB !important;
            border-radius: 8px !important;
            height: 48px !important;
            background-color: #FAFAFA !important;
            color: #374151 !important;
        }}
        .stTextInput input:focus {{
            border-color: #C5A059 !important; /* Expo Gold Tint */
            box-shadow: 0 0 0 3px rgba(197, 160, 89, 0.1) !important;
        }}

        /* THE EXPO BLACK BUTTON */
        div.stButton > button {{
            background-color: #1A1A1A !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            height: 50px !important;
            border: none !important;
            font-weight: 600 !important;
            transition: all 0.3s ease;
        }}
        div.stButton > button:hover {{
            background-color: #333333 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }}
        div.stButton > button p {{ color: white !important; }}

        /* TABS STYLING */
        button[data-baseweb="tab"] {{
            background-color: #F9FAFB !important;
            border-radius: 8px 8px 0 0 !important;
            margin-right: 4px !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            background-color: #FFFFFF !important;
            border-bottom: 3px solid #1A1A1A !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"

# ==========================================
# 2. CORE UTILITIES
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
# 3. AUTHENTICATION (EXPO STYLE)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Use the logo in login if exists
        if os.path.exists("logo.png"):
            st.image("logo.png", width=120)
        st.markdown("## Sign In")
        st.markdown("<p style='color: #6B7280; margin-top:-15px;'>Enter your credentials to access the portal</p>", unsafe_allow_html=True)
        
        login_type = st.radio("Portal Type", ["Technician", "Admin"], horizontal=True, label_visibility="collapsed")
        
        with st.form("expo_login"):
            if login_type == "Technician":
                u = st.text_input("EMAIL ADDRESS", placeholder="name@expocity.ae")
                p = st.text_input("PASSWORD", type="password", placeholder="••••••••")
            else:
                p = st.text_input("ADMIN MASTER PASSWORD", type="password", placeholder="••••••••")
            
            if st.form_submit_button("Sign In"):
                if login_type == "Technician":
                    ws_u = get_ws("Users")
                    if any(str(r['Username'])==u and str(r['PIN'])==p for r in ws_u.get_all_records()):
                        st.session_state.update(logged_in=True, user=u, role="Technician")
                        st.rerun()
                    else: st.error("Access Denied")
                elif p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
else:
    if 'inventory_df' not in st.session_state: st.session_state['inventory_df'] = load_data()
    df = st.session_state['inventory_df']
    ws_inv = get_ws("Sheet1")

    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png", width=140)
        st.markdown(f"**{st.session_state['user']}**")
        st.divider()
        menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"] if st.session_state['role']=="Admin" else ["DASHBOARD", "ISSUE ASSET", "RETURN ASSET", "REGISTER ASSET"]
        nav = st.radio("Navigation", menu)
        st.markdown('<br>' * 8, unsafe_allow_html=True)
        if st.button("Logout System", use_container_width=True):
            st.session_state.clear(); st.rerun()

    st.markdown(f"<h1>{nav}</h1>", unsafe_allow_html=True)

    if nav == "DASHBOARD":
        if not df.empty:
            models = sorted([m for m in df['MODEL'].unique() if str(m).strip() != ""])
            cols = st.columns(3)
            for i, model in enumerate(models):
                sub = df[df['MODEL'] == model]
                with cols[i % 3]:
                    st.write(f"**{model}**")
                    fig = px.pie(sub, names='CONDITION', hole=0.7, color_discrete_sequence=["#1A1A1A", "#C5A059", "#E5E7EB"])
                    fig.update_layout(showlegend=False, height=180, margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True, key=f"expo_{model}_{i}")
        else: st.info("No data available.")

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        st.markdown("### Global Asset Management")
        t_ctrl = st.tabs(["Add Asset", "Modify Info", "Delete Permanent"])
        with t_ctrl[0]:
            with st.form("add_expo"):
                c1, c2, c3 = st.columns(3)
                at_v = c1.text_input("Asset Type")
                br_v = c2.text_input("Brand")
                md_v = c3.text_input("Model")
                sn_v = st.text_input("Serial Number")
                if st.form_submit_button("Commit to Database"):
                    if sn_v:
                        ws_inv.append_row([at_v, br_v, md_v, sn_v, "", "Available/New", "STORE-10", "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                        st.success("Asset added successfully"); time.sleep(1); st.rerun()
