"""
Authentication Utilities
=======================
Login, logout, and password management
"""

import streamlit as st
import bcrypt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.shared.database import SessionLocal
from services.shared.models import Admin


def check_authentication() -> bool:
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)


def login(username: str, password: str) -> bool:
    """
    Authenticate user credentials
    
    Args:
        username: Admin username
        password: Plain text password
        
    Returns:
        True if authenticated successfully
    """
    session = SessionLocal()
    
    try:
        admin = session.query(Admin).filter_by(username=username).first()
        
        if not admin:
            return False
        
        password_bytes = password.encode('utf-8')
        stored_hash = admin.password_hash.encode('utf-8')
        
        if bcrypt.checkpw(password_bytes, stored_hash):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.admin_id = admin.id
            return True
        
        return False
    
    finally:
        session.close()


def logout():
    """Logout current user"""
    from services.dashboard.utils.session import reset_session
    reset_session()
    st.rerun()
