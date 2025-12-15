"""
Insights Management Page
=======================
Review and approve AI-generated insights
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.shared.database import SessionLocal
from services.shared.models import Insight, Company, InsightStatusEnum
from services.dashboard.utils.auth import check_authentication


def show_insights_page():
    """Display insights review page"""
    
    if not check_authentication():
        st.error("🔒 Access Denied. Please login first.")
        st.stop()
    
    st.markdown("""
        <div style='margin-bottom: 2rem;'>
            <h1>Insights</h1>
            <p style='color: #64748b; font-size: 1rem;'>
                Review and approve AI-generated strategic insights
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    session = SessionLocal()
    
    try:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        pending = session.query(Insight).filter_by(status=InsightStatusEnum.PENDING).count()
        approved = session.query(Insight).filter_by(status=InsightStatusEnum.APPROVED).count()
        rejected = session.query(Insight).filter_by(status=InsightStatusEnum.REJECTED).count()
        refining = session.query(Insight).filter_by(status=InsightStatusEnum.REFINING).count()
        
        with col1:
            st.metric("⏳ Pending", pending)
        with col2:
            st.metric("✅ Approved", approved)
        with col3:
            st.metric("❌ Rejected", rejected)
        with col4:
            st.metric("🔄 Refining", refining)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs(["⏳ Pending", "✅ Approved", "❌ Rejected", "🔄 Refining"])
        
        with tab1:
            display_insights(session, InsightStatusEnum.PENDING)
        with tab2:
            display_insights(session, InsightStatusEnum.APPROVED)
        with tab3:
            display_insights(session, InsightStatusEnum.REJECTED)
        with tab4:
            display_insights(session, InsightStatusEnum.REFINING)
    
    finally:
        session.close()


def display_insights(session, status):
    """Display insights by status"""
    
    insights = session.query(Insight).filter_by(status=status).order_by(
        Insight.created_at.desc()
    ).all()
    
    if not insights:
        st.info(f"No {status.value} insights")
        return
    
    for insight in insights:
        company = session.query(Company).filter_by(id=insight.company_id).first()
        company_name = company.name if company else "Unknown"
        
        with st.expander(
            f"{company_name} - {insight.created_at.strftime('%Y-%m-%d %H:%M')}"
        ):
            st.markdown(f"**Company:** {company_name}")
            st.markdown(f"**Status:** {insight.status.value.upper()}")
            st.markdown(f"**Created:** {insight.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if insight.processing_time:
                st.markdown(f"**Processing Time:** {insight.processing_time:.2f}s")
            
            st.markdown("**Content:**")
            st.markdown(insight.content)
            
            if status == InsightStatusEnum.PENDING:
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"✅ Approve {insight.id}", use_container_width=True, 
                                type="primary"):
                        insight.status = InsightStatusEnum.APPROVED
                        session.commit()
                        st.success("Approved!")
                        st.rerun()
                
                with col2:
                    if st.button(f"❌ Reject {insight.id}", use_container_width=True):
                        feedback = st.text_input(f"Feedback for {insight.id}")
                        if feedback:
                            insight.status = InsightStatusEnum.REJECTED
                            insight.admin_feedback = feedback
                            session.commit()
                            st.rerun()
