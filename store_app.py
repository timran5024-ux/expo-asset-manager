import streamlit as st
import os
import base64

st.set_page_config(page_title="Theme Preview", layout="wide")

# Applying the high-contrast CSS engine
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
            background-color: rgba(255, 255, 255, 0.97); z-index: -1;
        }}
        
        /* THE TUXEDO BUTTON: Black background, Bold White text */
        div.stButton > button {{
            background-color: #000000 !important;
            color: #FFFFFF !important;
            border: 2px solid #000000 !important;
            border-radius: 12px !important;
            height: 60px !important;
            width: 100% !important;
        }}
        
        /* FORCING TEXT VISIBILITY */
        div.stButton > button p, div.stButton > button span {{
            color: #FFFFFF !important;
            font-weight: 900 !important;
            font-size: 20px !important;
        }}

        /* SPACIOUS INPUT BOXES */
        .stTextInput input {{
            border: 2px solid #000000 !important;
            border-radius: 10px !important;
            height: 55px !important;
            font-weight: 700 !important;
        }}
        
        .card {{
            background-color: #FFFFFF;
            padding: 40px;
            border-radius: 20px;
            border: 2px solid #000000;
            box-shadow: 10px 10px 0px #000000;
        }}
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: black;'>THEME PREVIEW</h1>", unsafe_allow_html=True)

c1, mid, c3 = st.columns([1, 2, 1])
with mid:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Test Input Visibility")
    st.text_input("Enter Username", placeholder="This text should be bold and clear")
    st.text_input("Enter Password", type="password")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.subheader("Test Button Visibility")
    if st.button("LOGIN (THIS SHOULD BE WHITE TEXT)"):
        st.balloons()
    st.markdown('</div>', unsafe_allow_html=True)
