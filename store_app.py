# ==========================================
# 🔍 DEBUG VERSION OF get_users_sheet
# ==========================================
def get_users_sheet():
    client = get_client()
    try: 
        sh = client.open_by_key(SHEET_ID)
        return sh.worksheet("Users")
    except Exception as e:
        # THIS WILL PRINT THE REAL ERROR ON YOUR SCREEN
        st.error(f"🛑 CRITICAL ERROR: {e}")
        st.info(f"Checking Sheet ID: {SHEET_ID}")
        st.info("Please screenshot this error and show me.")
        st.stop()
