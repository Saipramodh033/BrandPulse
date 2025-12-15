"""
Companies Management Page
========================
Add, edit, and monitor companies
"""

import streamlit as st
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.shared.database import SessionLocal
from services.shared.models import Company, CompanyStatusEnum
from services.dashboard.utils.auth import check_authentication


def show_companies_page():
    """Display companies management page"""
    
    if not check_authentication():
        st.error("🔒 Access Denied. Please login first.")
        st.stop()
    
    st.markdown("""
        <div style='margin-bottom: 2rem;'>
            <h1>Companies</h1>
            <p style='color: #64748b; font-size: 1rem;'>
                Manage monitored companies and configure insight generation
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    session = SessionLocal()
    
    try:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total = session.query(Company).count()
        active = session.query(Company).filter_by(status=CompanyStatusEnum.ACTIVE).count()
        paused = session.query(Company).filter_by(status=CompanyStatusEnum.PAUSED).count()
        
        with col1:
            st.metric("Total Companies", total)
        with col2:
            st.metric("Active", active)
        with col3:
            st.metric("Paused", paused)
        with col4:
            if st.button("➕ Add Company", use_container_width=True, type="primary"):
                st.session_state.show_add_form = True
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Add form
        if st.session_state.get('show_add_form', False):
            show_add_company_form()
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.show_add_form = False
                st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)
        
        # Companies list
        companies = session.query(Company).order_by(Company.created_at.desc()).all()
        
        if companies:
            for company in companies:
                with st.expander(
                    f"{'🟢' if company.status == CompanyStatusEnum.ACTIVE else '⏸️'} "
                    f"{company.name}"
                ):
                    st.markdown(f"**Status:** {company.status.value.upper()}")
                    st.markdown(f"**Email:** {company.email}")
                    st.markdown(f"**Frequency:** {company.frequency_hours} hours")
                    if company.next_run_time:
                        st.markdown(f"**Next Run:** {company.next_run_time.strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**Description:** {company.description or 'N/A'}")
        else:
            st.info("No companies added yet. Click 'Add Company' to get started!")
    
    finally:
        session.close()


def show_add_company_form():
    """Display form to add new company"""
    
    st.markdown("<h2>Add New Company</h2>", unsafe_allow_html=True)
    
    with st.form("add_company_form"):
        name = st.text_input("Company Name *", placeholder="e.g., Acme Corporation")
        email = st.text_input("Email *", placeholder="insights@company.com")
        description = st.text_area("Description", placeholder="Brief company description")
        
        col1, col2 = st.columns(2)
        with col1:
            frequency = st.number_input("Frequency (hours) *", min_value=0.016, 
                                       value=24.0, step=0.5)
        with col2:
            status = st.selectbox("Status", ["ACTIVE", "PAUSED"])
        
        pdf_file = st.file_uploader("Upload PDF (optional)", type=['pdf'])
        
        submitted = st.form_submit_button("💾 Save Company", type="primary", 
                                         use_container_width=True)
        
        if submitted:
            if not name or not email:
                st.error("❌ Name and email are required")
            else:
                session = SessionLocal()
                try:
                    pdf_text = ""
                    if pdf_file:
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        pdf_text = "\n".join([page.extract_text() for page in pdf_reader.pages])
                    
                    company = Company(
                        name=name,
                        email=email,
                        description=description,
                        pdf_text=pdf_text,
                        frequency_hours=frequency,
                        status=CompanyStatusEnum.ACTIVE if status == "ACTIVE" else CompanyStatusEnum.PAUSED,
                        next_run_time=datetime.utcnow(),
                        created_at=datetime.utcnow()
                    )
                    
                    session.add(company)
                    session.commit()
                    
                    st.success(f"✅ {name} added successfully!")
                    st.session_state.show_add_form = False
                    st.rerun()
                    
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ Error: {str(e)}")
                finally:
                    session.close()
