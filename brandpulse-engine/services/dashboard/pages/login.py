"""
Login Page - Clean Authentication Interface
==========================================
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.dashboard.utils.auth import login


def show_login_page():
    """Display professional login form"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style='text-align: center; padding: 3rem 0 2rem 0;'>
                <h1 style='font-size: 2.5rem; color: #0f172a; margin-bottom: 0.5rem;'>
                    🎯 BrandPulse
                </h1>
                <p style='color: #64748b; font-size: 1.125rem; margin: 0;'>
                    Strategic Intelligence Platform
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <div style='background: white; padding: 2.5rem; border-radius: 16px; 
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); 
                        border: 1px solid #e2e8f0;'>
        """, unsafe_allow_html=True)
        
        st.markdown("""
            <h2 style='text-align: center; color: #1e293b; margin-bottom: 2rem;'>
                Sign In
            </h2>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input(
                "Username",
                placeholder="Enter your username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            submit = st.form_submit_button("Sign In", use_container_width=True, 
                                          type="primary")
            
            if submit:
                if not username or not password:
                    st.error("⚠️ Please enter both username and password")
                else:
                    if login(username, password):
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        with st.expander("💡 Default Credentials"):
            st.markdown("""
                **Username:** `admin`  
                **Password:** `admin123`
                
                ⚠️ Change password after first login in Settings.
            """)
        
        st.markdown("""
            <div style='text-align: center; padding: 2rem 0; color: #94a3b8; 
                        font-size: 0.875rem;'>
                <p>© 2025 BrandPulse. All rights reserved.</p>
            </div>
        """, unsafe_allow_html=True)
