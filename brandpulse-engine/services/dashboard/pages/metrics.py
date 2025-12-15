"""
Analytics/Metrics Page
=====================
System performance and usage metrics
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from services.shared.database import SessionLocal
from services.shared.models import Metric, Insight, Company
from services.dashboard.utils.auth import check_authentication


def show_metrics_page():
    """Display system metrics and analytics"""
    
    if not check_authentication():
        st.error("🔒 Access Denied. Please login first.")
        st.stop()
    
    st.markdown("""
        <div style='margin-bottom: 2rem;'>
            <h1>Analytics</h1>
            <p style='color: #64748b; font-size: 1rem;'>
                System performance and usage metrics
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    session = SessionLocal()
    
    try:
        # Get or create metrics
        metric = session.query(Metric).first()
        
        if not metric:
            from services.shared.models import init_metrics
            init_metrics(session)
            metric = session.query(Metric).first()
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Insights", metric.total_insights)
        
        with col2:
            approval_rate = (metric.approved_count / metric.total_insights * 100) if metric.total_insights > 0 else 0
            st.metric("Approval Rate", f"{approval_rate:.1f}%")
        
        with col3:
            st.metric("Avg Processing", f"{metric.avg_processing_time:.2f}s")
        
        with col4:
            st.metric("Emails Sent", metric.total_emails_sent)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Breakdown
        st.markdown("<h2>Insights Breakdown</h2>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("⏳ Pending", metric.pending_count)
        with col2:
            st.metric("✅ Approved", metric.approved_count)
        with col3:
            st.metric("❌ Rejected", metric.rejected_count)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Additional stats
        st.markdown("<h2>System Stats</h2>", unsafe_allow_html=True)
        
        companies_count = session.query(Company).count()
        insights_count = session.query(Insight).count()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 12px; 
                            border: 1px solid #e2e8f0;'>
                    <p style='color: #64748b; margin: 0;'>Total Companies</p>
                    <p style='color: #0f172a; font-size: 2rem; font-weight: 700; margin: 0;'>
                        {companies_count}
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
                <div style='background: white; padding: 1.5rem; border-radius: 12px; 
                            border: 1px solid #e2e8f0;'>
                    <p style='color: #64748b; margin: 0;'>Total Insights</p>
                    <p style='color: #0f172a; font-size: 2rem; font-weight: 700; margin: 0;'>
                        {insights_count}
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        if metric.last_scheduler_run:
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"📅 Last scheduler run: {metric.last_scheduler_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    finally:
        session.close()
