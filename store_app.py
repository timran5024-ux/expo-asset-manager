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

# ... [all your original imports and constants remain the same] ...

@st.cache_data(ttl=30)
def load_data():
    # [your original load_data() code remains unchanged]
    # ... (keep exactly as you had it)
    pass  # replace with your full load_data function

# ... [get_client, get_ws remain the same] ...

# Login section remains the same

else:
    df = load_data()
    ws_inv = get_ws("Sheet1")

    # Sidebar remains the same

    if nav == "DASHBOARD":
        # [your dashboard code remains unchanged]

    elif nav in ["ASSET CONTROL", "REGISTER ASSET"]:
        # ... keep your tabs logic ...

        # === PATCHED ADD ASSET (Admin + Technician) ===
        if st.session_state['role'] == "Admin" or nav == "REGISTER ASSET":
            with tabs[0]:
                with st.form("add_asset_f"):
                    c1, c2, c3 = st.columns(3)
                    at = c1.text_input("Asset Type")
                    br = c2.text_input("Brand")
                    md = c3.text_input("Model")
                    sn = c1.text_input("Serial Number (SN)")
                    mc = c2.text_input("MAC Address")
                    lo = c3.selectbox("Location", ["MOBILITY STORE-10", "BASEMENT", "TERRA"])
                    st_v = st.selectbox("Condition", ["Available/New", "Available/Used", "Faulty"])
                    if st.form_submit_button("REGISTER ASSET"):
                        if not sn.strip():
                            st.error("Serial Number is required")
                        elif ws_inv.find(sn.strip()):
                            st.error("❌ Serial Number already exists!")
                        else:
                            ws_inv.append_row([at, br, md, sn.strip(), mc, st_v, lo, "", "", datetime.now().strftime("%Y-%m-%d"), st.session_state['user']])
                            st.success("✅ Asset Registered!")
                            time.sleep(0.5)
                            st.rerun()

        # === PATCHED MODIFY ASSET (Admin only) ===
        if st.session_state['role'] == "Admin":
            with tabs[1]:
                sn_search = st.text_input("Enter Serial Number to Modify").strip()
                if sn_search:
                    cell = ws_inv.find(sn_search)
                    if cell:
                        row_num = cell.row
                        row_values = ws_inv.row_values(row_num)
                        with st.form("modify_asset"):
                            c1, c2, c3 = st.columns(3)
                            at = c1.text_input("Asset Type", value=row_values[0] if len(row_values)>0 else "")
                            br = c2.text_input("Brand", value=row_values[1] if len(row_values)>1 else "")
                            md = c3.text_input("Model", value=row_values[2] if len(row_values)>2 else "")
                            sn_new = c1.text_input("Serial Number (SN)", value=row_values[3] if len(row_values)>3 else "")
                            mc = c2.text_input("MAC Address", value=row_values[4] if len(row_values)>4 else "")
                            cond_options = ["Available/New", "Available/Used", "Faulty", "Issued"]
                            current_cond = row_values[5] if len(row_values)>5 else "Available/New"
                            st_v = c3.selectbox("Condition", cond_options, index=cond_options.index(current_cond) if current_cond in cond_options else 0)
                            loc_options = ["MOBILITY STORE-10", "BASEMENT", "TERRA"]
                            current_loc = row_values[6] if len(row_values)>6 else "MOBILITY STORE-10"
                            lo = c1.selectbox("Location", loc_options, index=loc_options.index(current_loc) if current_loc in loc_options else 0)
                            issued_to = c2.text_input("Issued To", value=row_values[7] if len(row_values)>7 else "")
                            # Safe date parsing
                            try:
                                issued_date_val = datetime.strptime(row_values[8], "%Y-%m-%d").date() if len(row_values)>8 and row_values[8] else date.today()
                            except (ValueError, TypeError, IndexError):
                                issued_date_val = date.today()
                            issued_date = c3.date_input("Issued Date", value=issued_date_val)
                            if st.form_submit_button("UPDATE ASSET"):
                                update_data = [at, br, md, sn_new.strip(), mc, st_v, lo, issued_to, issued_date.strftime("%Y-%m-%d"), row_values[9] if len(row_values)>9 else "", st.session_state['user']]
                                ws_inv.update(f'A{row_num}:K{row_num}', [update_data])
                                st.success("✅ Asset Updated!")
                                time.sleep(0.5)
                                st.rerun()
                    else:
                        st.error("❌ Serial Number not found.")

            # === PATCHED ISSUE ASSET (Admin) ===
            with tabs[2]:
                sn_issue = st.text_input("Enter Serial Number to Issue").strip()
                issued_to = st.text_input("Issued To")
                if st.button("ISSUE ASSET"):
                    if sn_issue:
                        cell = ws_inv.find(sn_issue)
                        if cell:
                            row_num = cell.row
                            row_values = ws_inv.row_values(row_num)
                            if row_values[5] in ['Available/New', 'Available/Used']:
                                ws_inv.update(f'F{row_num}:I{row_num}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                                st.success("✅ Asset Issued!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Asset not available.")
                        else:
                            st.error("❌ Serial Number not found.")
                    else:
                        st.error("Please enter Serial Number.")

            # === PATCHED RETURN + DELETE (similar ws.find pattern) ===
            # Apply the same pattern as Issue above for tabs[3] and tabs[4]
            # (Return uses ws_inv.find → check CONDITION=='Issued' → update)
            # Delete: ws_inv.delete_rows(cell.row)

    # === NEW ENHANCED ISSUE ASSET FOR TECHNICIANS ===
    elif nav == "ISSUE ASSET":
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.subheader("Issue Asset")

        mode = st.radio("How do you want to find the asset?",
                       ["Enter Full Serial", "Last 4 Digits", "Scan Photo (Mobile)"], horizontal=True)

        sn_issue = ""
        if mode == "Enter Full Serial":
            sn_issue = st.text_input("Serial Number").strip()

        elif mode == "Last 4 Digits":
            last4 = st.text_input("Enter last 4 digits of Serial Number").strip()
            if last4 and len(last4) == 4:
                matches = df[df['Serial Number'].astype(str).str.endswith(last4, na=False)]
                if not matches.empty:
                    options = [f"{r['Serial Number']} | {r['ASSET TYPE']} ({r['Brand']} {r['Model']})"
                              for _, r in matches.iterrows()]
                    selected = st.selectbox("Select matching asset", options)
                    if selected:
                        sn_issue = selected.split(" | ")[0]
                else:
                    st.warning("No asset found with these digits")
            else:
                st.info("Enter exactly 4 digits")

        elif mode == "Scan Photo (Mobile)":
            img_file = st.camera_input("Take photo of serial number / barcode")
            if img_file:
                st.image(img_file, caption="Scanned image", use_column_width=True)
                st.info("📷 Read the serial number from the photo and enter it manually below")
            sn_issue = st.text_input("Serial Number (read from photo)").strip()

        issued_to = st.text_input("Issued To")
        if st.button("ISSUE ASSET", type="primary"):
            if not sn_issue:
                st.error("Serial Number is required")
            else:
                cell = ws_inv.find(sn_issue)
                if cell:
                    row_num = cell.row
                    row_values = ws_inv.row_values(row_num)
                    if row_values[5] in ['Available/New', 'Available/Used']:
                        ws_inv.update(f'F{row_num}:I{row_num}', [["Issued", "", issued_to, datetime.now().strftime("%Y-%m-%d")]])
                        st.success(f"✅ Asset {sn_issue} issued to {issued_to}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Asset is not available (Issued or Faulty)")
                else:
                    st.error("❌ Serial Number not found in database.")
        st.markdown('</div>', unsafe_allow_html=True)

    # DATABASE and USER MANAGER remain the same 
