"""
BrandPulse Database Models
==========================
SQLAlchemy ORM models defining the data schema for:
- Admin: Dashboard authentication
- Company: Client registry with RAG embeddings
- Insight: Generated strategic content
- EmailLog: Email delivery tracking (insights + apologies)
- Metric: System performance tracking
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, Float,
    ForeignKey, Index, Boolean, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
import enum

Base = declarative_base()


# ==================================================================
# Enums (Controlled Vocabularies)
# ==================================================================

class CompanyStatusEnum(enum.Enum):
    """Company monitoring state"""
    ACTIVE = "active"      # Agent will process
    PAUSED = "paused"      # Skip during scheduler runs


class InsightStatusEnum(enum.Enum):
    """Insight approval workflow states"""
    PENDING = "pending"      # Awaiting admin review
    APPROVED = "approved"    # Admin approved, email sent
    REJECTED = "rejected"    # Admin rejected with feedback or auto-rejected
    REFINING = "refining"    # Admin requested changes, re-processing


class EmailTypeEnum(enum.Enum):
    """Types of emails sent by the system"""
    INSIGHT = "insight"      # Approved insight delivery
    APOLOGY = "apology"      # Auto-rejection apology notification


# ==================================================================
# Admin Model
# ==================================================================

class Admin(Base):
    """
    Dashboard administrator accounts
    
    Attributes:
        username: Unique login identifier
        password_hash: bcrypt hashed password (never store plaintext!)
        created_at: Account creation timestamp
    """
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<Admin(username='{self.username}')>"


# ==================================================================
# Company Model (RAG-Enabled)
# ==================================================================

class Company(Base):
    """
    Client company registry with semantic embeddings for RAG
    
    Attributes:
        name: Company name
        description: Brief company overview
        email: Delivery address for approved insights
        pdf_text: Extracted text from uploaded company profile PDF
        embedding: 768-dim vector for semantic search (pgvector)
        frequency_hours: How often to generate insights (positive integer)
        status: Active or paused monitoring
        next_run_time: When scheduler should next process this company
        
    Relationships:
        insights: All generated insights for this company (one-to-many)
        email_logs: All emails sent to this company (one-to-many)
    """
    __tablename__ = "companies"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Company Information
    name = Column(String(200), nullable=False)
    description = Column(Text)
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # RAG Components
    pdf_text = Column(Text)  # Full extracted PDF content
    embedding = Column(Vector(768))  # Google Gemini embedding dimension
    
    # Scheduling Configuration
    frequency_hours = Column(Integer, nullable=False, default=24)  # Positive integer hours
    status = Column(Enum(CompanyStatusEnum), nullable=False, default=CompanyStatusEnum.ACTIVE)
    next_run_time = Column(DateTime, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    insights = relationship(
        "Insight",
        back_populates="company",
        cascade="all, delete-orphan",  # Delete insights when company deleted
        lazy="dynamic"  # Don't load insights until accessed
    )
    
    email_logs = relationship(
        "EmailLog",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint('frequency_hours > 0', name='check_frequency_positive'),
        Index('idx_company_status_next_run', 'status', 'next_run_time'),  # Scheduler queries
        Index('idx_company_embedding', 'embedding', postgresql_using='ivfflat'),  # Vector search
    )
    
    def __repr__(self):
        return f"<Company(name='{self.name}', frequency={self.frequency_hours}h, status='{self.status.value}')>"


# ==================================================================
# Insight Model
# ==================================================================

class Insight(Base):
    """
    Generated strategic intelligence content
    
    Attributes:
        company_id: Foreign key to Company
        content: Generated insight text (Markdown formatted)
        status: Approval workflow state
        admin_feedback: Refinement instructions from admin or auto-rejection reason
        processing_time: Agent execution duration (seconds)
        token_count: LLM token usage for cost tracking
        email_sent: Whether delivery email was successfully sent
        
    Relationships:
        company: Parent company (many-to-one)
        email_logs: Emails related to this insight (one-to-many)
    """
    __tablename__ = "insights"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key Relationship
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Content
    content = Column(Text, nullable=False)
    
    # Workflow State
    status = Column(Enum(InsightStatusEnum), nullable=False, default=InsightStatusEnum.PENDING)
    admin_feedback = Column(Text)  # Populated when status = REFINING or auto-rejection reason
    
    # Performance Metrics
    processing_time = Column(Float)  # Seconds
    token_count = Column(Integer)  # LLM tokens used
    
    # Email Delivery (deprecated in favor of EmailLog, but kept for backward compatibility)
    email_sent = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="insights")
    email_logs = relationship(
        "EmailLog",
        back_populates="insight",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_insight_status', 'status'),  # Dashboard queries for pending insights
        Index('idx_insight_company_created', 'company_id', 'created_at'),  # History queries
        Index('idx_insight_company_status', 'company_id', 'status'),  # Check pending count
    )
    
    def __repr__(self):
        return f"<Insight(id={self.id}, company_id={self.company_id}, status='{self.status.value}')>"


# ==================================================================
# EmailLog Model
# ==================================================================

class EmailLog(Base):
    """
    Email delivery tracking for all system emails
    
    Tracks both:
    - Insight delivery emails (when admin approves)
    - Apology emails (when auto-rejection occurs)
    
    Attributes:
        company_id: Foreign key to Company (recipient)
        insight_id: Foreign key to Insight (null for apology emails)
        email_type: Type of email (INSIGHT or APOLOGY)
        recipient_email: Email address where sent
        subject: Email subject line
        sent_successfully: Delivery status
        sendgrid_message_id: SendGrid tracking ID
        error_message: Failure reason if not sent
    """
    __tablename__ = "email_logs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_id = Column(Integer, ForeignKey("insights.id", ondelete="SET NULL"), nullable=True)  # Null for apology emails
    
    # Email Details
    email_type = Column(Enum(EmailTypeEnum), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    
    # Delivery Status
    sent_successfully = Column(Boolean, default=False, nullable=False)
    sendgrid_message_id = Column(String(100))  # For tracking in SendGrid dashboard
    error_message = Column(Text)  # Populated if sent_successfully = False
    
    # Metadata
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="email_logs")
    insight = relationship("Insight", back_populates="email_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_email_company_type', 'company_id', 'email_type'),
        Index('idx_email_sent_at', 'sent_at'),
    )
    
    def __repr__(self):
        return f"<EmailLog(type='{self.email_type.value}', to='{self.recipient_email}', success={self.sent_successfully})>"


# ==================================================================
# Metric Model (System Performance)
# ==================================================================

class Metric(Base):
    """
    Aggregated system performance metrics
    
    Single-row table updated after each scheduler run
    Displayed in dashboard analytics page
    
    Attributes:
        total_insights: Cumulative insights generated
        pending_count: Current pending insights
        approved_count: Cumulative approved insights
        rejected_count: Cumulative rejected insights (manual + auto)
        avg_processing_time: Average agent execution time
        total_tokens_used: Cumulative LLM token usage
        total_emails_sent: Cumulative successful email deliveries
        last_scheduler_run: Timestamp of most recent scheduler execution
    """
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Insight Counts
    total_insights = Column(Integer, default=0, nullable=False)
    pending_count = Column(Integer, default=0, nullable=False)
    approved_count = Column(Integer, default=0, nullable=False)
    rejected_count = Column(Integer, default=0, nullable=False)
    
    # Performance
    avg_processing_time = Column(Float)  # Average seconds per insight
    total_tokens_used = Column(Integer, default=0, nullable=False)  # Cumulative LLM usage
    
    # Email Tracking
    total_emails_sent = Column(Integer, default=0, nullable=False)
    total_apology_emails = Column(Integer, default=0, nullable=False)
    
    # Scheduler Metadata
    last_scheduler_run = Column(DateTime)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        approval_rate = (self.approved_count / self.total_insights * 100) if self.total_insights > 0 else 0
        return f"<Metric(total={self.total_insights}, approval_rate={approval_rate:.1f}%)>"


# ==================================================================
# Helper Functions
# ==================================================================

def create_tables(engine):
    """
    Initialize database schema
    
    Creates all tables defined above + pgvector extension
    Called during first-time setup
    
    Args:
        engine: SQLAlchemy engine instance
    """
    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(engine)
    print("✅ Database schema created successfully")


def init_metrics(session):
    """
    Initialize metrics table with default row
    
    Creates single Metric row if none exists
    Called after create_tables()
    
    Args:
        session: SQLAlchemy session instance
    """
    metric = session.query(Metric).first()
    if not metric:
        metric = Metric(
            total_insights=0,
            pending_count=0,
            approved_count=0,
            rejected_count=0,
            total_tokens_used=0,
            total_emails_sent=0,
            total_apology_emails=0
        )
        session.add(metric)
        session.commit()
        print("✅ Metrics table initialized")
    else:
        print("ℹ️ Metrics table already exists")