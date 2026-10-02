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
    ForeignKey, Index, Boolean, CheckConstraint, text
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
    """Legacy Insight approval workflow states - kept temporarily for migrations if needed"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFINING = "refining"


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
    frequency_hours = Column(Float, nullable=False, default=24.0)  # Supports fractional hours (e.g., 0.083 = 5 min)
    status = Column(Enum(CompanyStatusEnum), nullable=False, default=CompanyStatusEnum.ACTIVE)
    next_run_time = Column(DateTime, nullable=False)
    is_processing = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    email_logs = relationship(
        "EmailLog",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    generated_ideas = relationship(
        "GeneratedIdea",
        back_populates="company",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    company_profile = relationship(
        "CompanyProfile",
        back_populates="company",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint('frequency_hours >= 0.016', name='check_frequency_positive'),  # Min: ~1 minute
        Index('idx_company_status_next_run', 'status', 'next_run_time'),  # Scheduler queries
        Index('idx_company_embedding', 'embedding', postgresql_using='ivfflat'),  # Vector search
    )
    
    def __repr__(self):
        return f"<Company(name='{self.name}', frequency={self.frequency_hours}h, status='{self.status.value}')>"





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
    insight_id = Column(Integer, ForeignKey("generated_ideas.id", ondelete="SET NULL"), nullable=True)  # Null for apology emails
    
    # Email Details
    email_type = Column(Enum(EmailTypeEnum), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    
    # Delivery Status
    sent_successfully = Column(Boolean, default=False, nullable=False)
    sendgrid_message_id = Column(String(100))  # Message ID (Resend or legacy SendGrid)
    error_message = Column(Text)  # Populated if sent_successfully = False
    
    # Metadata
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="email_logs")
    generated_idea = relationship("GeneratedIdea", backref="email_logs")
    
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
# GeneratedIdea Model (Phase 1 — replaces Insight for new runs)
# ==================================================================

class IdeaStatusEnum(enum.Enum):
    """Idea review workflow states"""
    PENDING = "pending"      # Awaiting admin review
    APPROVED = "approved"    # Admin approved
    REJECTED = "rejected"    # Admin rejected
    REFINING = "refining"    # Admin requested changes


class GeneratedIdea(Base):
    """
    Structured content idea produced by the ideation engine.

    Each run produces 3-5 of these rows instead of one monolithic Insight.
    Replaces the Insight model for new runs (old Insight table kept for backward compatibility).
    """
    __tablename__ = "generated_ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    # Run linkage
    run_log_id = Column(Integer, ForeignKey("run_logs.id", ondelete="SET NULL"), nullable=True)
    evergreen = Column(Boolean, default=False, nullable=False)

    # Angle metadata (populated in Phase 2)
    angle_category = Column(String(100))
    angle_detail = Column(Text)
    is_wildcard = Column(Boolean, default=False)

    # Signal metadata (populated in Phase 3)
    signal_used = Column(Text)

    # Content
    idea_summary = Column(Text, nullable=False)  # 1-sentence hook
    hook = Column(Text)                           # Opening line
    body = Column(Text)                           # 2-3 sentence body
    cta = Column(Text)                            # Call to action
    full_content = Column(Text, nullable=False)   # Hook + body + CTA joined
    platform = Column(String(50), default='linkedin')
    implication_type = Column(String(50))         # product/audience/hiring/industry

    # Workflow
    status = Column(String(20), default='pending', nullable=False)
    admin_feedback = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="generated_ideas")
    run_log = relationship("RunLog", back_populates="ideas")

    __table_args__ = (
        Index('idx_ideas_company_created', 'company_id', 'created_at'),
        Index('idx_ideas_company_status', 'company_id', 'status'),
    )

    def __repr__(self):
        return f"<GeneratedIdea(id={self.id}, company_id={self.company_id}, platform='{self.platform}', status='{self.status}')>"



# ==================================================================
# CompanyProfile Model (Phase 2 — structured company intelligence)
# ==================================================================

class CompanyProfile(Base):
    """
    Cached structured profile extracted from company PDF.

    Populated by the profile_company node. Re-extracted only when
    the company record is updated (last_profiled_at < company.updated_at).
    """
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"),
                        nullable=False, unique=True)

    # Structured fields extracted from PDF
    space = Column(Text)          # Industry/market the company operates in
    audience = Column(Text)       # Primary target audience
    content_fit = Column(Text)    # What content topics resonate (JSON string)
    brand_voice = Column(Text)    # Tone and communication style
    key_differentiators = Column(Text)  # What makes them unique
    region = Column(String(100), default='India')  # Target geographic market for localized news searches

    # Cache control
    last_profiled_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    company = relationship("Company", back_populates="company_profile")

    def to_dict(self) -> dict:
        """Serialise for use in state."""
        return {
            'space': self.space,
            'audience': self.audience,
            'content_fit': self.content_fit,
            'brand_voice': self.brand_voice,
            'key_differentiators': self.key_differentiators,
            'region': self.region,
        }

    def __repr__(self):
        return f"<CompanyProfile(company_id={self.company_id})>"


# ==================================================================
# RunLog Model (Phase 5 — Execution trace storage)
# ==================================================================

from sqlalchemy.dialects.postgresql import JSONB

class RunLog(Base):
    """
    Execution trace of a single ideation run.
    Stores the full graph execution path and status.
    """
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    # Trace data
    trace = Column(JSONB, nullable=False)
    status = Column(String(50), nullable=False)  # "success", "error", etc.
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company")
    ideas = relationship("GeneratedIdea", back_populates="run_log", lazy="dynamic")

    __table_args__ = (
        Index('idx_runlog_company_created', 'company_id', 'created_at'),
    )

    def __repr__(self):
        return f"<RunLog(id={self.id}, company_id={self.company_id}, status='{self.status}')>"


# ==================================================================
# Helper Functions
# ==================================================================

def create_tables(engine):
    """
    Create all tables and enable pgvector extension
    
    Args:
        engine: SQLAlchemy engine instance
    """
    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Also create PromptConfig table from models_config
    try:
        from services.shared.models_config import PromptConfig
        PromptConfig.__table__.create(bind=engine, checkfirst=True)
    except Exception:
        pass  # Table might already exist
    
    print("✅ Database tables created successfully")


def init_metrics(session):
    """
    Initialize metrics table with default row
    
    Args:
        session: SQLAlchemy session instance
    """
    existing = session.query(Metric).first()
    
    if not existing:
        metric = Metric(
            total_insights=0,
            pending_count=0,
            approved_count=0,
            rejected_count=0,
            total_emails_sent=0,
            total_apology_emails=0,
            avg_processing_time=0.0,
            total_tokens_used=0,
            last_updated=datetime.utcnow()
        )
        session.add(metric)
        session.commit()
        print("✅ Metrics initialized")
    else:
        print("✅ Metrics already exist")