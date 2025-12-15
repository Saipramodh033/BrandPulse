"""
Session Management
=================
Initialize and manage Streamlit session state
"""

import streamlit as st


def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if 'admin_id' not in st.session_state:
        st.session_state.admin_id = None


def reset_session():
    """Clear all session state"""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.admin_id = None
    
    # Clear any other session keys
    keys_to_keep = ['authenticated', 'username', 'admin_id']
    keys_to_delete = [k for k in st.session_state.keys() if k not in keys_to_keep]
    for key in keys_to_delete:
        del st.session_state[key]
