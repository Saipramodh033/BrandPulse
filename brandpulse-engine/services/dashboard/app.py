"""
BrandPulse Dashboard - Enterprise Strategic Intelligence Platform
================================================================
Main application entry point with professional UI/UX
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure page (must be first Streamlit command)
st.set_page_config(
    page_title="BrandPulse - Strategic Intelligence",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional CSS styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    #MainMenu, footer, header {
        visibility: hidden;
    }
    
    .main {
        padding: 0;
        background: #f8fafc;
    }
    
    .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    }
    
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
        background: transparent;
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        border-radius: 8px;
        color: #cbd5e1;
        transition: all 0.2s;
    }
    
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover {
        background: rgba(59, 130, 246, 0.2);
        color: #ffffff;
    }
    
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"] {
        background: #3b82f6;
        color: #ffffff;
        font-weight: 600;
    }
    
    /* Typography */
    h1 {
        color: #0f172a;
        font-weight: 700;
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    
    h2 {
        color: #1e293b;
        font-weight: 600;
        font-size: 1.5rem;
        margin-top: 2rem;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 700;
        color: #0f172a;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.875rem;
        font-weight: 500;
        color: #64748b;
        text-transform: uppercase;
    }
    
    /* Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s;
        border: none;
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* Inputs */
    .stTextInput input,
    .stTextArea textarea {
        border-radius: 8px;
        border: 2px solid #e2e8f0;
    }
    
    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: white;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

from services.dashboard.utils.session import init_session_state
from services.dashboard.utils.auth import check_authentication, logout
from services.dashboard.pages.login import show_login_page
from services.dashboard.pages.companies import show_companies_page
from services.dashboard.pages.insights import show_insights_page
from services.dashboard.pages.metrics import show_metrics_page
from services.dashboard.pages.settings import show_settings_page


def show_sidebar():
    """Display sidebar navigation"""
    with st.sidebar:
        # Branding
        st.markdown("""
            <div style='text-align: center; padding: 1rem 0 2rem 0;'>
                <h1 style='font-size: 1.8rem; margin: 0;'>🎯 BrandPulse</h1>
                <p style='color: #94a3b8; font-size: 0.875rem; margin: 0.5rem 0 0 0;'>
                    Strategic Intelligence
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # User info
        st.markdown(f"""
            <div style='background: rgba(255,255,255,0.1); padding: 0.75rem; 
                        border-radius: 8px; margin-bottom: 1.5rem;'>
                <p style='color: #cbd5e1; margin: 0; font-size: 0.875rem;'>Logged in as</p>
                <p style='color: #ffffff; margin: 0; font-weight: 600;'>
                    {st.session_state.get('username', 'Admin')}
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        st.markdown("""
            <h3 style='color: #ffffff; font-size: 0.875rem; text-transform: uppercase; 
                       letter-spacing: 0.1em; margin-bottom: 1rem;'>
                Navigation
            </h3>
        """, unsafe_allow_html=True)
        
        page = st.radio(
            "nav",
            ["📊 Dashboard", "🏢 Companies", "💡 Insights", "📈 Analytics", "⚙️ Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 1.5rem 0;'>", 
                   unsafe_allow_html=True)
        
        # Logout
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()
        
        return page


def show_dashboard_home():
    """Display dashboard home page"""
    from services.shared.database import SessionLocal
    from services.shared.models import Company, Insight, InsightStatusEnum, CompanyStatusEnum
    from datetime import datetime
    
    st.markdown("""
        <div style='margin-bottom: 2rem;'>
            <h1>Dashboard</h1>
            <p style='color: #64748b; font-size: 1rem;'>
                Monitor your strategic intelligence operations
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    session = SessionLocal()
    try:
        # Metrics
        total_companies = session.query(Company).count()
        active_companies = session.query(Company).filter_by(
            status=CompanyStatusEnum.ACTIVE
        ).count()
        pending_insights = session.query(Insight).filter_by(
            status=InsightStatusEnum.PENDING
        ).count()
        approved_insights = session.query(Insight).filter_by(
            status=InsightStatusEnum.APPROVED
        ).count()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Active Companies", active_companies, 
                     delta=f"{total_companies} total")
        with col2:
            st.metric("Pending Review", pending_insights)
        with col3:
            st.metric("Approved", approved_insights)
        with col4:
            total_insights = session.query(Insight).count()
            st.metric("Total Insights", total_insights)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Status
        if total_companies == 0:
            st.info("👋 Welcome! Add your first company to begin.")
        elif pending_insights > 0:
            st.warning(f"⚡ {pending_insights} insight(s) awaiting review.")
        else:
            st.success("✅ All caught up!")
        
        # Recent insights
        st.markdown("<h2>Recent Insights</h2>", unsafe_allow_html=True)
        
        recent = session.query(Insight).order_by(
            Insight.created_at.desc()
        ).limit(5).all()
        
        if recent:
            for insight in recent:
                company = session.query(Company).filter_by(
                    id=insight.company_id
                ).first()
                
                status_icons = {
                    InsightStatusEnum.PENDING: "⏳",
                    InsightStatusEnum.APPROVED: "✅",
                    InsightStatusEnum.REJECTED: "❌",
                    InsightStatusEnum.REFINING: "🔄"
                }
                
                icon = status_icons.get(insight.status, "•")
                company_name = company.name if company else "Unknown"
                date_str = insight.created_at.strftime('%b %d, %Y %H:%M')
                
                with st.expander(f"{icon} {company_name} - {date_str}"):
                    st.markdown(f"**Status:** {insight.status.value.upper()}")
                    if insight.processing_time:
                        st.markdown(f"**Processing:** {insight.processing_time:.2f}s")
                    preview = insight.content[:250] + "..." if len(insight.content) > 250 else insight.content
                    st.markdown(f"```\n{preview}\n```")
        else:
            st.info("No insights yet. Add companies to get started!")
    
    finally:
        session.close()


def main():
    """Main application entry point"""
    init_session_state()
    
    if not check_authentication():
        show_login_page()
        return
    
    # Authenticated - show navigation and content
    page = show_sidebar()
    
    if page == "📊 Dashboard":
        show_dashboard_home()
    elif page == "🏢 Companies":
        show_companies_page()
    elif page == "💡 Insights":
        show_insights_page()
    elif page == "📈 Analytics":
        show_metrics_page()
    elif page == "⚙️ Settings":
        show_settings_page()


if __name__ == "__main__":
    main()
