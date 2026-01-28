import streamlit as st
import os
import base64

st.set_page_config(page_title="Elite Theme Preview", layout="wide")

# High-Visibility Enterprise Engine
if os.path.exists("logo.png"):
    with open("logo.png", "rb") as f:
        bin_str = base64.b64encode(f.read()).decode()
    st.markdown(f"""
    <style>
        /* The pattern stays in the background but is pushed back */
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: 600px;
            background-repeat: repeat;
            background-attachment: fixed;
        }}
        .stApp::before {{
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(240, 242, 245, 0.9); z-index: -1;
        }}
        
        /* THE SOLID WORKSPACE CARD - Blocks the pattern behind forms */
        .main-card {{
            background-color: #FFFFFF;
            padding: 50px;
            border-radius: 15px;
            border: 1px solid #E0E0E0;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            margin: auto;
        }}

        /* PROFESSIONAL INPUTS */
        .stTextInput input {{
            border: 1px solid #CED4DA !important;
            border-radius: 8px !important;
            height: 50px !important;
            font-size: 16px !important;
            padding-left: 15px !important;
        }}

        /* CORPORATE BUTTONS: Deep Black with Pure White Bold Text */
        div.stButton > button {{
            background-color: #000000 !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            height: 55px !important;
            width: 100% !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            border: none !important;
            transition: 0.3s;
        }}
        
        div.stButton > button:hover {{
            background-color: #333333 !important;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}

        /* FORCING LABEL BOLDNESS */
        label p {{
            font-weight: 700 !important;
            color: #333333 !important;
            font-size: 16px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #111; font-weight: 800; margin-bottom: 40px;'>SYSTEM AUTHENTICATION</h1>", unsafe_allow_html=True)

c1, mid, c3 = st.columns([1, 1.8, 1])
with mid:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    
    st.text_input("Username", placeholder="e.g. admin_pro")
    st.text_input("Access PIN", type="password", placeholder="••••")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("VERIFY AND LOGIN"):
        st.success("Theme Applied Successfully!")
        
    st.markdown('</div>', unsafe_allow_html=True)
