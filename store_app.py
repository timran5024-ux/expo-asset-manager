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
# 1. PROFESSIONAL ASSET MANAGEMENT SYSTEM
# ==========================================
st.set_page_config(
    page_title="Asset Management Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ... (keep all your CSS and styling the same as before) ...

# CONSTANTS
SHEET_ID = "1Jw4p9uppgJU3Cfquz19fDUJaZooic-aD-PBcIjBZ2WU"
ADMIN_PASSWORD = "admin123"
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
LOGO_URL = "https://gcdn.net/wp-content/uploads/2024/11/EXPO_CITY_DUBAI_LOGO_DUAL_HORIZONTAL_YELLOW-1024x576.png"

# ==========================================
# 2. CORE UTILITIES - SIMPLIFIED
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

def get_ws(name):
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
    except Exception as e:
        st.error(f"Error accessing worksheet: {str(e)}")
        return None

def load_data():
    """Load data from Google Sheets"""
    try:
        ws = get_ws("Sheet1")
        if not ws:
            return pd.DataFrame()
        
        # Get all values
        vals = ws.get_all_values()
        
        if not vals or len(vals) <= 1:
            return pd.DataFrame(columns=[
                "ASSET TYPE", "Brand", "Model", "Serial Number", 
                "MAC Address", "CONDITION", "Location", "Issued To", 
                "Issued Date", "Registered Date", "Registered By"
            ])
        
        # Create DataFrame
        headers = vals[0]
        data = vals[1:]
        
        # Ensure we have the right number of columns
        while len(data) > 0 and len(data[-1]) < len(headers):
            data[-1].append('')
        
        df = pd.DataFrame(data, columns=headers)
        
        # Ensure all expected columns exist
        expected_columns = [
            "ASSET TYPE", "Brand", "Model", "Serial Number", 
            "MAC Address", "CONDITION", "Location", "Issued To", 
            "Issued Date", "Registered Date", "Registered By"
        ]
        
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Clean serial numbers - strip whitespace
        if 'Serial Number' in df.columns:
            df['Serial Number'] = df['Serial Number'].astype(str).str.strip()
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# ==========================================
# 3. INTERFACE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

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
    # --- SIDEBAR ---
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
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("<br>" * 5, unsafe_allow_html=True)
        if st.button("Logout"): 
            st.session_state.clear()
            st.rerun()
    
    # Load data
    df = load_data()
    
    # DEBUG: Show what's in the dataframe
    if 'show_debug' not in st.session_state:
        st.session_state.show_debug = False
    
    if st.session_state.show_debug:
        st.write("DEBUG - Dataframe info:")
        st.write(f"Number of rows: {len(df)}")
        st.write(f"Columns: {df.columns.tolist()}")
        if not df.empty:
            st.write("First few serial numbers:")
            st.write(df['Serial Number'].head(10).tolist())
    
    ws_inv = get_ws("Sheet1")
    
    st.markdown(f"<h2>{nav}</h2>", unsafe_allow_html=True)
    
    if nav == "DASHBOARD":
        # ... (keep your dashboard code exactly as it was) ...
        pass
    
    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        if st.session_state['role'] != "Admin" and nav == "ASSET CONTROL": 
            st.error("Access Denied")
            st.stop()
        
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        
        # DEBUG toggle
        if st.checkbox("Show debug info", key="debug_toggle"):
            st.session_state.show_debug = True
            st.write("Current dataframe:")
            st.dataframe(df)
        else:
            st.session_state.show_debug = False
        
        if st.session_state['role'] == "Admin":
            tabs = st.tabs(["➕ Add Asset", "📝 Modify Asset", "🚀 Issue Asset", "↩️ Return Asset", "❌ Delete Asset"])
        else:
            tabs = st.tabs(["➕ Register Asset"])
        
        if st.session_state['role'] == "Admin" or nav == "REGISTER ASSET":
            with tabs[0]:
                with st.form("add_asset_f"):
                    c1, c2, c3 = st.columns(3)
                    at = c1.text_input("Asset Type *", key="add_type")
                    br = c2.text_input("Brand", key="add_brand")
                    md = c3.text_input("Model", key="add_model")
                    sn = c1.text_input("Serial Number (SN) *", key="add_sn")
                    mc = c2.text_input("MAC Address", key="add_mac")
                    lo = c3.selectbox("Location *", ["MOBILITY STORE-10", "BASEMENT", "TERRA", "OTHER"], key="add_location")
                    st_v = st.selectbox("Condition *", ["Available/New", "Available/Used", "Faulty"], key="add_condition")
                    
                    if st.form_submit_button("REGISTER ASSET"):
                        if not at or not sn:
                            st.error("Asset Type and Serial Number are required!")
                        else:
                            try:
                                # Check if serial number already exists
                                existing_sn = df['Serial Number'].astype(str).str.strip().tolist()
                                if sn.strip() in existing_sn:
                                    st.warning(f"Serial Number '{sn}' already exists in the database!")
                                else:
                                    ws_inv.append_row([
                                        at, br, md, sn.strip(), mc, st_v, lo, 
                                        "", "", datetime.now().strftime("%Y-%m-%d"), 
                                        st.session_state['user']
                                    ])
                                    st.success("Asset Registered!")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Failed to register asset: {str(e)}")
        
        if st.session_state['role'] == "Admin":
            with tabs[1]:  # Modify Asset
                st.info("🔍 Search for asset to modify")
                
                # Show current data summary
                if not df.empty:
                    st.write(f"📊 Found {len(df)} assets in database")
                    if 'Serial Number' in df.columns:
                        st.write(f"Sample serial numbers: {df['Serial Number'].head(5).tolist()}")
                
                sn_search = st.text_input("Enter Serial Number to Modify", key="modify_search")
                
                if sn_search:
                    # Strip the search term
                    sn_search_clean = sn_search.strip()
                    
                    # Convert dataframe serial numbers to clean strings
                    df_clean = df.copy()
                    df_clean['Serial Number'] = df_clean['Serial Number'].astype(str).str.strip()
                    
                    # Show what we're looking for
                    st.write(f"Looking for: '{sn_search_clean}'")
                    st.write(f"Available serial numbers (first 10): {df_clean['Serial Number'].head(10).tolist()}")
                    
                    # Try different search methods
                    # Method 1: Exact match
                    exact_matches = df_clean[df_clean['Serial Number'] == sn_search_clean]
                    
                    # Method 2: Case-insensitive match
                    ci_matches = df_clean[df_clean['Serial Number'].str.upper() == sn_search_clean.upper()]
                    
                    # Method 3: Contains match
                    contains_matches = df_clean[df_clean['Serial Number'].str.contains(sn_search_clean, case=False, na=False)]
                    
                    # Choose which matches to use (prefer exact)
                    if not exact_matches.empty:
                        matching_rows = exact_matches
                        st.success(f"Found exact match for '{sn_search_clean}'")
                    elif not ci_matches.empty:
                        matching_rows = ci_matches
                        st.success(f"Found case-insensitive match for '{sn_search_clean}'")
                    elif not contains_matches.empty:
                        matching_rows = contains_matches
                        st.success(f"Found partial match for '{sn_search_clean}'")
                    else:
                        matching_rows = pd.DataFrame()
                    
                    if not matching_rows.empty:
                        row_idx = matching_rows.index[0]
                        data = matching_rows.iloc[0]
                        
                        st.success(f"✅ Found: {data['ASSET TYPE']} - {data.get('Brand', '')} {data.get('Model', '')}")
                        
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
                            
                            location_options = ["MOBILITY STORE-10", "BASEMENT", "TERRA", "OTHER"]
                            current_location = str(data.get('Location', ''))
                            location_index = location_options.index(current_location) if current_location in location_options else 0
                            lo = c1.selectbox("Location", location_options, index=location_index, key="mod_location")
                            
                            issued_to = c2.text_input("Issued To", value=str(data.get('Issued To', '')), key="mod_issued_to")
                            
                            # Handle date input
                            issued_date_str = str(data.get('Issued Date', ''))
                            try:
                                if issued_date_str and issued_date_str != '' and issued_date_str != 'nan':
                                    issued_date = datetime.strptime(issued_date_str, "%Y-%m-%d")
                                else:
                                    issued_date = datetime.now()
                            except:
                                issued_date = datetime.now()
                            
                            issued_date_input = c3.date_input("Issued Date", value=issued_date, key="mod_issued_date")
                            
                            if st.form_submit_button("UPDATE ASSET"):
                                try:
                                    # Find the actual row in Google Sheets
                                    all_values = ws_inv.get_all_values()
                                    found_row = None
                                    for i, row in enumerate(all_values):
                                        if i == 0:
                                            continue  # Skip header
                                        if len(row) > 3 and str(row[3]).strip() == sn_search_clean:
                                            found_row = i + 1  # 1-based index for Google Sheets
                                            break
                                    
                                    if found_row:
                                        ws_inv.update(f'A{found_row}:K{found_row}', [[
                                            at, br, md, sn.strip(), mc, st_v, lo, 
                                            issued_to, issued_date_input.strftime("%Y-%m-%d"), 
                                            str(data.get('Registered Date', datetime.now().strftime("%Y-%m-%d"))), 
                                            str(data.get('Registered By', st.session_state['user']))
                                        ]])
                                        st.success("Asset Updated!")
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Could not find row in Google Sheets")
                                except Exception as e:
                                    st.error(f"Failed to update asset: {str(e)}")
                    else:
                        st.error(f"❌ Serial Number '{sn_search_clean}' not found in database.")
                        st.write("Try searching with a different case or check for typos.")
            
            with tabs[2]:  # Issue Asset
                st.info("Issue an available asset to someone")
                col1, col2 = st.columns(2)
                with col1:
                    sn_issue = st.text_input("Enter Serial Number to Issue", key="issue_sn")
                with col2:
                    issued_to = st.text_input("Issued To *", key="issue_to")
                
                if st.button("ISSUE ASSET", key="issue_btn"):
                    if not sn_issue or not issued_to:
                        st.error("Please fill in both fields")
                    else:
                        sn_issue_clean = sn_issue.strip()
                        
                        # Find the asset
                        all_values = ws_inv.get_all_values()
                        found_row = None
                        found_condition = None
                        
                        for i, row in enumerate(all_values):
                            if i == 0:
                                continue  # Skip header
                            if len(row) > 3 and str(row[3]).strip() == sn_issue_clean:
                                found_row = i + 1
                                if len(row) > 5:
                                    found_condition = str(row[5]).strip()
                                break
                        
                        if found_row:
                            if found_condition in ['Available/New', 'Available/Used']:
                                try:
                                    ws_inv.update(f'F{found_row}:I{found_row}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                                    st.success("Asset Issued!")
                                    st.cache_data.clear()
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to issue asset: {str(e)}")
                            else:
                                st.error(f"Asset is '{found_condition}', not available for issue.")
                        else:
                            st.error("Asset not found.")
            
            with tabs[3]:  # Return Asset
                st.info("Return an issued asset")
                sn_return = st.text_input("Enter Serial Number to Return", key="return_sn")
                return_status = st.selectbox("Return Condition", ["Available/Used", "Faulty"], key="return_condition")
                
                if st.button("RETURN ASSET", key="return_btn"):
                    if sn_return:
                        sn_return_clean = sn_return.strip()
                        
                        # Find the asset directly in Google Sheets
                        all_values = ws_inv.get_all_values()
                        found_row = None
                        
                        for i, row in enumerate(all_values):
                            if i == 0:
                                continue
                            if len(row) > 3 and str(row[3]).strip() == sn_return_clean:
                                found_row = i + 1
                                break
                        
                        if found_row:
                            try:
                                ws_inv.update(f'F{found_row}:I{found_row}', [[return_status, "", "", ""]])
                                st.success("Asset Returned!")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to return asset: {str(e)}")
                        else:
                            st.error("Asset not found.")
            
            with tabs[4]:  # Delete Asset
                st.warning("⚠️ This action cannot be undone!")
                sn_del = st.text_input("Enter Serial Number to Delete", key="delete_sn")
                
                if st.button("DELETE ASSET", type="primary", key="delete_btn"):
                    if sn_del:
                        sn_del_clean = sn_del.strip()
                        
                        # Find the asset directly in Google Sheets
                        all_values = ws_inv.get_all_values()
                        found_row = None
                        
                        for i, row in enumerate(all_values):
                            if i == 0:
                                continue
                            if len(row) > 3 and str(row[3]).strip() == sn_del_clean:
                                found_row = i + 1
                                break
                        
                        if found_row:
                            try:
                                ws_inv.delete_rows(found_row)
                                st.success("Asset Deleted!")
                                st.cache_data.clear()
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
            issued_to = st.text_input("Issued To *", key="tech_issue_to")
        
        if st.button("ISSUE ASSET", key="tech_issue_btn"):
            if not sn_issue or not issued_to:
                st.error("Please fill in both fields")
            else:
                sn_issue_clean = sn_issue.strip()
                
                # Find the asset directly in Google Sheets
                all_values = ws_inv.get_all_values()
                found_row = None
                found_condition = None
                
                for i, row in enumerate(all_values):
                    if i == 0:
                        continue
                    if len(row) > 3 and str(row[3]).strip() == sn_issue_clean:
                        found_row = i + 1
                        if len(row) > 5:
                            found_condition = str(row[5]).strip()
                        break
                
                if found_row:
                    if found_condition in ['Available/New', 'Available/Used']:
                        try:
                            ws_inv.update(f'F{found_row}:I{found_row}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                            st.success("Asset Issued!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to issue asset: {str(e)}")
                    else:
                        st.error(f"Asset is '{found_condition}', not available for issue.")
                else:
                    st.error("Asset not found.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    elif nav == "DATABASE":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        
        if st.button("🔄 Refresh Database"):
            st.cache_data.clear()
            df = load_data()
            st.success("Database refreshed!")
            st.rerun()
        
        search_term = st.text_input("Search Database (by Serial Number, Asset Type, etc.)", 
                                  placeholder="Type to search...")
        
        if search_term:
            try:
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
