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
from googleapiclient.errors import HttpError
import traceback

# ==========================================
# 1. PROFESSIONAL ASSET MANAGEMENT SYSTEM (V2.0)
# ==========================================
st.set_page_config(
    page_title="Asset Management Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    footer, .stAppDeployButton, #MainMenu {{ visibility: hidden !important; }}
    /* PROFESSIONAL STYLING */
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
        text-align: center;
    }}
    .metric-title {{ font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-bottom: 10px; }}
    .hw-count {{ font-size: 15px; font-weight: 700; color: #111827; margin: 4px 0; text-align: left; }}
    .metric-value {{ font-size: 38px; font-weight: 900; }}
    .stDataFrame {{ border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
LOGO_URL = "https://gcdn.net/wp-content/uploads/2024/11/EXPO_CITY_DUBAI_LOGO_DUAL_HORIZONTAL_YELLOW-1024x576.png"

# ==========================================
# 2. CORE UTILITIES WITH ERROR HANDLING
# ==========================================
@st.cache_resource
def get_client():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip('"')
        return gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE))
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets client: {str(e)}")
        return None

def get_ws(name, retries=3):
    for attempt in range(retries):
        try:
            client = get_client()
            if not client:
                return None
            sh = client.open_by_key(SHEET_ID)
            try:
                return sh.worksheet(name)
            except gspread.exceptions.WorksheetNotFound:
                if name == "Users":
                    ws = sh.add_worksheet(title="Users", rows="100", cols="5")
                    ws.append_row(["Username", "PIN", "Permission"])
                    return ws
                return sh.sheet1
        except HttpError as e:
            if e.resp.status == 429:  # Rate limit
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                st.error(f"Google API Error: {str(e)}")
                return None
        except Exception as e:
            st.error(f"Error accessing worksheet: {str(e)}")
            return None
    return None

@st.cache_data(ttl=5)  # Cache for 5 seconds to reduce API calls
def load_data(refresh=False):
    """Load data from Google Sheets with retry logic"""
    try:
        ws = get_ws("Sheet1")
        if not ws:
            return pd.DataFrame()
        
        # Try to get all values
        vals = ws.get_all_values()
        
        if not vals:
            return pd.DataFrame(columns=[
                "ASSET TYPE", "Brand", "Model", "Serial Number", 
                "MAC Address", "CONDITION", "Location", "Issued To", 
                "Issued Date", "Registered Date", "Registered By"
            ])
        
        # Handle headers
        headers = vals[0]
        df = pd.DataFrame(vals[1:], columns=headers)
        
        # Ensure all expected columns exist
        expected_columns = [
            "ASSET TYPE", "Brand", "Model", "Serial Number", 
            "MAC Address", "CONDITION", "Location", "Issued To", 
            "Issued Date", "Registered Date", "Registered By"
        ]
        
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Clean up data
        df = df.fillna('')
        df = df.replace('', pd.NA)
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

def refresh_data():
    """Clear cache and reload data"""
    st.cache_data.clear()
    return load_data(refresh=True)

# ==========================================
# 3. INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

if not st.session_state['logged_in']:
    c1, mid, c3 = st.columns([1, 1.4, 1])
    with mid:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.image(LOGO_URL, width=150)
        mode = st.radio("GATEWAY", ["Technician", "Admin"], horizontal=True)
        with st.form("login"):
            u = st.text_input("Username") if mode == "Technician" else "Administrator"
            p = st.text_input("PIN / Password", type="password")
            if st.form_submit_button("SIGN IN"):
                if mode == "Admin" and p == ADMIN_PASSWORD:
                    st.session_state.update(logged_in=True, user="Administrator", role="Admin")
                    st.rerun()
                elif mode == "Technician":
                    ws_u = get_ws("Users")
                    if ws_u:
                        recs = ws_u.get_all_records()
                        if any(str(r.get('Username', '')).strip()==u.strip() and str(r.get('PIN', '')).strip()==p.strip() for r in recs):
                            permission = next((r.get('Permission', 'Standard') for r in recs if str(r.get('Username', '')).strip()==u.strip()), 'Standard')
                            st.session_state.update(logged_in=True, user=u, role="Technician", permission=permission)
                            st.rerun()
                        else: 
                            st.error("Access Refused: Invalid Technician Credentials")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- GUARANTEED SIDEBAR ---
    with st.sidebar:
        st.markdown(f'<div style="display: flex; justify-content: center;"><img src="{LOGO_URL}" width="200"></div>', unsafe_allow_html=True)
        st.markdown(f"**USER: {st.session_state['user']}**")
        st.divider()
        if st.session_state['role'] == "Admin":
            menu = ["DASHBOARD", "ASSET CONTROL", "DATABASE", "USER MANAGER"]
        else:
            menu = ["DASHBOARD", "ISSUE ASSET", "REGISTER ASSET", "DATABASE"]
        nav = st.radio("Navigation", menu)
        
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.session_state.df = refresh_data()
            st.success("Data refreshed!")
            time.sleep(0.5)
            st.rerun()
            
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        if st.button("Logout"): 
            st.session_state.clear()
            st.rerun()
    
    # Load data with error handling
    try:
        df = load_data()
        st.session_state.df = df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        df = st.session_state.df if not st.session_state.df.empty else pd.DataFrame()
    
    ws_inv = get_ws("Sheet1")
    
    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)
    
    if nav == "DASHBOARD":
        try:
            if df.empty:
                st.info("No assets registered yet.")
            else:
                # Safe string operations
                types = df['ASSET TYPE'].astype(str).str.upper()
                c_cam = len(df[types.str.contains('CAMERA', na=False)])
                c_rdr = len(df[types.str.contains('READER', na=False)])
                c_pnl = len(df[types.str.contains('PANEL', na=False)])
                c_lck = len(df[types.str.contains('LOCK|MAG', na=False, regex=True)])
                total_assets = len(df)
                
                # Safe condition checks
                new = len(df[df['CONDITION'].astype(str) == 'Available/New'])
                used = len(df[df['CONDITION'].astype(str) == 'Available/Used'])
                faulty = len(df[df['CONDITION'].astype(str) == 'Faulty'])
                issued = len(df[df['CONDITION'].astype(str) == 'Issued'])
                
                m1, m2, m3, m4, m5 = st.columns(5)
                with m1: 
                    st.markdown(f'<div class="exec-card"><p class="metric-title">Total Assets</p><p class="metric-value" style="color:#1F2937;">{total_assets}</p></div>', unsafe_allow_html=True)
                with m2: 
                    st.markdown(f'<div class="exec-card"><p class="metric-title">Available New</p><p class="metric-value" style="color:#28A745;">{new}</p></div>', unsafe_allow_html=True)
                with m3: 
                    st.markdown(f'<div class="exec-card"><p class="metric-title">Available Used</p><p class="metric-value" style="color:#FFD700;">{used}</p></div>', unsafe_allow_html=True)
                with m4: 
                    st.markdown(f'<div class="exec-card"><p class="metric-title">Faulty</p><p class="metric-value" style="color:#DC3545;">{faulty}</p></div>', unsafe_allow_html=True)
                with m5: 
                    st.markdown(f'<div class="exec-card"><p class="metric-title">Issued</p><p class="metric-value" style="color:#6C757D;">{issued}</p></div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                    st.markdown(f"""<p class="metric-title">Hardware Breakdown</p>
                        <p class="hw-count">📹 Cameras: {c_cam}</p>
                        <p class="hw-count">💳 Card Readers: {c_rdr}</p>
                        <p class="hw-count">🖥️ Access Panels: {c_pnl}</p>
                        <p class="hw-count">🧲 Mag Locks: {c_lck}</p>""", unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                with col2:
                    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                    try:
                        clr_map = {"Available/New": "#28A745", "Available/Used": "#FFD700", "Faulty": "#DC3545", "Issued": "#6C757D"}
                        fig_pie = px.pie(df, names='CONDITION', hole=0.4, color='CONDITION', color_discrete_map=clr_map)
                        fig_pie.update_layout(title="Asset Status Distribution", showlegend=True, height=400, 
                                             margin=dict(t=40,b=0,l=0,r=0), paper_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig_pie, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Could not generate pie chart: {str(e)}")
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                try:
                    type_counts = df['ASSET TYPE'].value_counts().reset_index()
                    type_counts.columns = ['ASSET TYPE', 'Count']
                    fig_bar = px.bar(type_counts, x='ASSET TYPE', y='Count', title="Assets by Type")
                    fig_bar.update_layout(height=400, paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_bar, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not generate bar chart: {str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                st.subheader("Recently Issued Assets")
                try:
                    df['Issued Date'] = pd.to_datetime(df['Issued Date'], errors='coerce')
                    recent_issued = df[df['CONDITION'] == 'Issued'].sort_values('Issued Date', ascending=False).head(10)
                    st.dataframe(recent_issued[['ASSET TYPE', 'Serial Number', 'Issued To', 'Issued Date']], use_container_width=True)
                except:
                    st.info("No issued assets or error loading data")
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Dashboard error: {str(e)}")
            st.info("Try refreshing the data or check your connection.")
    
    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        if st.session_state['role'] != "Admin" and nav == "ASSET CONTROL": 
            st.error("Access Denied")
            st.stop()
        
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        if st.session_state['role'] == "Admin":
            tabs = st.tabs(["➕ Add Asset", "📝 Modify Asset", "🚀 Issue Asset", "↩️ Return Asset", "❌ Delete Asset"])
        else:
            tabs = st.tabs(["➕ Register Asset"])
        
        if st.session_state['role'] == "Admin" or nav == "REGISTER ASSET":
            with tabs[0]:
                with st.form("add_asset_f"):
                    c1, c2, c3 = st.columns(3)
                    at = c1.text_input("Asset Type", key="add_type")
                    br = c2.text_input("Brand", key="add_brand")
                    md = c3.text_input("Model", key="add_model")
                    sn = c1.text_input("Serial Number (SN)", key="add_sn")
                    mc = c2.text_input("MAC Address", key="add_mac")
                    lo = c3.selectbox("Location", ["MOBILITY STORE-10", "BASEMENT", "TERRA"], key="add_location")
                    st_v = st.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"], key="add_condition")
                    
                    if st.form_submit_button("REGISTER ASSET"):
                        try:
                            ws_inv.append_row([at, br, md, sn, mc, st_v, lo, "", "", 
                                             datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                            st.success("Asset Registered!")
                            # Refresh data immediately after adding
                            df = refresh_data()
                            st.session_state.df = df
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to register asset: {str(e)}")
        
        if st.session_state['role'] == "Admin":
            with tabs[1]:  # Modify Asset
                st.info("🔍 Search for asset to modify")
                sn_search = st.text_input("Enter Serial Number to Modify", key="modify_search")
                
                if sn_search:
                    # Refresh data before searching to get latest
                    df = refresh_data()
                    st.session_state.df = df
                    
                    # Use exact match for serial number
                    matching_rows = df[df['Serial Number'].astype(str).str.strip() == sn_search.strip()]
                    
                    if not matching_rows.empty:
                        row_idx = matching_rows.index[0]
                        data = df.iloc[row_idx]
                        
                        with st.form("modify_asset"):
                            c1, c2, c3 = st.columns(3)
                            at = c1.text_input("Asset Type", value=str(data.get('ASSET TYPE', '')), key="mod_type")
                            br = c2.text_input("Brand", value=str(data.get('Brand', '')), key="mod_brand")
                            md = c3.text_input("Model", value=str(data.get('Model', '')), key="mod_model")
                            sn = c1.text_input("Serial Number (SN)", value=str(data.get('Serial Number', '')), key="mod_sn")
                            mc = c2.text_input("MAC Address", value=str(data.get('MAC Address', '')), key="mod_mac")
                            
                            condition_options = ["Available/New", "Available/Used", "Faulty", "Issued"]
                            current_condition = str(data.get('CONDITION', ''))
                            condition_index = condition_options.index(current_condition) if current_condition in condition_options else 0
                            st_v = c3.selectbox("Condition", condition_options, index=condition_index, key="mod_condition")
                            
                            location_options = ["MOBILITY STORE-10", "BASEMENT", "TERRA"]
                            current_location = str(data.get('Location', ''))
                            location_index = location_options.index(current_location) if current_location in location_options else 0
                            lo = c1.selectbox("Location", location_options, index=location_index, key="mod_location")
                            
                            issued_to = c2.text_input("Issued To", value=str(data.get('Issued To', '')), key="mod_issued_to")
                            
                            # Handle date input
                            issued_date_str = str(data.get('Issued Date', ''))
                            if issued_date_str:
                                try:
                                    issued_date = datetime.strptime(issued_date_str, "%Y-%m-%d")
                                except:
                                    issued_date = datetime.now()
                            else:
                                issued_date = datetime.now()
                            
                            issued_date_input = c3.date_input("Issued Date", value=issued_date, key="mod_issued_date")
                            
                            if st.form_submit_button("UPDATE ASSET"):
                                try:
                                    row_num = row_idx + 2  # +1 for header, +1 for 1-based
                                    ws_inv.update(f'A{row_num}:K{row_num}', [[
                                        at, br, md, sn, mc, st_v, lo, 
                                        issued_to, issued_date_input.strftime("%Y-%m-%d"), 
                                        str(data.get('Registered Date', '')), 
                                        st.session_state['user']
                                    ]])
                                    st.success("Asset Updated!")
                                    # Refresh data
                                    df = refresh_data()
                                    st.session_state.df = df
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to update asset: {str(e)}")
                    else:
                        st.error(f"Serial Number '{sn_search}' not found in database.")
            
            with tabs[2]:  # Issue Asset
                st.info("Issue an available asset to someone")
                col1, col2 = st.columns(2)
                with col1:
                    sn_issue = st.text_input("Enter Serial Number to Issue", key="issue_sn")
                with col2:
                    issued_to = st.text_input("Issued To", key="issue_to")
                
                if st.button("ISSUE ASSET", key="issue_btn"):
                    if not sn_issue or not issued_to:
                        st.error("Please fill in both fields")
                    else:
                        # Refresh data before operation
                        df = refresh_data()
                        st.session_state.df = df
                        
                        # Find the asset
                        matching_rows = df[
                            (df['Serial Number'].astype(str).str.strip() == sn_issue.strip()) & 
                            (df['CONDITION'].astype(str).isin(['Available/New', 'Available/Used']))
                        ]
                        
                        if not matching_rows.empty:
                            row_idx = matching_rows.index[0]
                            row_num = row_idx + 2
                            try:
                                ws_inv.update(f'F{row_num}:I{row_num}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                                st.success("Asset Issued!")
                                # Refresh data
                                df = refresh_data()
                                st.session_state.df = df
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to issue asset: {str(e)}")
                        else:
                            st.error("Asset not found or not available (must be 'Available/New' or 'Available/Used')")
            
            with tabs[3]:  # Return Asset
                st.info("Return an issued asset")
                sn_return = st.text_input("Enter Serial Number to Return", key="return_sn")
                return_status = st.selectbox("Return Condition", ["Available/Used", "Faulty"], key="return_condition")
                
                if st.button("RETURN ASSET", key="return_btn"):
                    if sn_return:
                        # Refresh data
                        df = refresh_data()
                        st.session_state.df = df
                        
                        matching_rows = df[
                            (df['Serial Number'].astype(str).str.strip() == sn_return.strip()) & 
                            (df['CONDITION'].astype(str) == 'Issued')
                        ]
                        
                        if not matching_rows.empty:
                            row_idx = matching_rows.index[0]
                            row_num = row_idx + 2
                            try:
                                ws_inv.update(f'F{row_num}:I{row_num}', [[return_status, "", "", ""]])
                                st.success("Asset Returned!")
                                # Refresh data
                                df = refresh_data()
                                st.session_state.df = df
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to return asset: {str(e)}")
                        else:
                            st.error("Asset not found or not currently issued")
            
            with tabs[4]:  # Delete Asset
                st.warning("⚠️ This action cannot be undone!")
                sn_del = st.text_input("Enter Serial Number to Delete", key="delete_sn")
                
                if st.button("DELETE ASSET", type="primary", key="delete_btn"):
                    if sn_del:
                        # Refresh data
                        df = refresh_data()
                        st.session_state.df = df
                        
                        matching_rows = df[df['Serial Number'].astype(str).str.strip() == sn_del.strip()]
                        
                        if not matching_rows.empty:
                            row_idx = matching_rows.index[0]
                            try:
                                ws_inv.delete_rows(row_idx + 2)
                                st.success("Asset Deleted!")
                                # Refresh data
                                df = refresh_data()
                                st.session_state.df = df
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to delete asset: {str(e)}")
                        else:
                            st.error("Serial Number not found.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif nav == "ISSUE ASSET":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.info("Issue an available asset")
        
        col1, col2 = st.columns(2)
        with col1:
            sn_issue = st.text_input("Enter Serial Number to Issue", key="tech_issue_sn")
        with col2:
            issued_to = st.text_input("Issued To", key="tech_issue_to")
        
        if st.button("ISSUE ASSET", key="tech_issue_btn"):
            if not sn_issue or not issued_to:
                st.error("Please fill in both fields")
            else:
                # Refresh data
                df = refresh_data()
                st.session_state.df = df
                
                matching_rows = df[
                    (df['Serial Number'].astype(str).str.strip() == sn_issue.strip()) & 
                    (df['CONDITION'].astype(str).isin(['Available/New', 'Available/Used']))
                ]
                
                if not matching_rows.empty:
                    row_idx = matching_rows.index[0]
                    row_num = row_idx + 2
                    try:
                        ws_inv.update(f'F{row_num}:I{row_num}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                        st.success("Asset Issued!")
                        # Refresh data
                        df = refresh_data()
                        st.session_state.df = df
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to issue asset: {str(e)}")
                else:
                    st.error("Asset not found or not available")
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        
        # Refresh button for database
        if st.button("🔄 Refresh Database View"):
            df = refresh_data()
            st.session_state.df = df
            st.success("Database refreshed!")
            time.sleep(0.5)
            st.rerun()
        
        search_term = st.text_input("Search Database (by Serial Number, Asset Type, etc.)", 
                                  placeholder="Type to search...")
        
        if search_term:
            try:
                # Convert all columns to string for searching
                filtered_df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
            except:
                filtered_df = df
        else:
            filtered_df = df
        
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True, height=400)
            
            # Excel Download
            output = BytesIO()
            try:
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='Assets')
                output.seek(0)
                
                st.download_button(
                    label="📥 Download Excel",
                    data=output,
                    file_name=f"assets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Failed to create Excel file: {str(e)}")
        else:
            st.info("No data to display")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif nav == "USER MANAGER":
        if st.session_state['role'] != "Admin":
            st.error("Access Denied")
            st.stop()
        
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        ws_u = get_ws("Users")
        if ws_u:
            try:
                udf = pd.DataFrame(ws_u.get_all_records())
            except:
                udf = pd.DataFrame(columns=["Username", "PIN", "Permission"])
        else:
            udf = pd.DataFrame(columns=["Username", "PIN", "Permission"])
        
        st.subheader("Personnel Directory")
        st.dataframe(udf, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            with st.form("new_tech"):
                un = st.text_input("Username")
                up = st.text_input("PIN", type="password")
                perm = st.selectbox("Permission", ["Standard", "Bulk_Allowed"])
                if st.form_submit_button("CREATE ACCOUNT"):
                    try:
                        ws_u.append_row([un, up, perm])
                        st.success("User Created")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create user: {str(e)}")
        
        with c2:
            if not udf.empty:
                target = st.selectbox("Select User", udf['Username'].tolist())
                new_p = st.selectbox("Update Permission", ["Standard", "Bulk_Allowed"])
                
                col1, col2 = st.columns(2)
                if col1.button("UPDATE PERMISSION"):
                    try:
                        cell = ws_u.find(target)
                        ws_u.update_cell(cell.row, 3, new_p)
                        st.success("Updated")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to update permission: {str(e)}")
                
                if col2.button("REVOKE ACCESS", type="secondary"):
                    try:
                        ws_u.delete_rows(ws_u.find(target).row)
                        st.success("Removed")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to remove user: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
