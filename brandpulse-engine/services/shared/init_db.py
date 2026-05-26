"""
BrandPulse Database Initialization Script
=========================================
Creates all tables and initializes the database schema

Run this script ONCE when setting up a new environment:
- Creates all tables defined in models.py
- Enables pgvector extension
- Initializes metrics table with default values
- Creates default admin account (optional)

Usage:
    # From inside Docker container
    python services/shared/init_db.py
    
    # From host (if PostgreSQL is exposed)
    cd brandpulse-engine
    python -m services.shared.init_db
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import text
import bcrypt

from services.shared.database import engine, get_db, check_database_health
from services.shared.models import (
    Base, 
    Admin, 
    Company, 
    GeneratedIdea,
    RunLog,
    EmailLog,
    Metric,
    CompanyStatusEnum,
    create_tables,
    init_metrics
)


# ==================================================================
# Database Initialization
# ==================================================================

def init_database(create_admin=True):
    """
    Initialize database schema and default data
    
    Steps:
        1. Check database connectivity
        2. Enable pgvector extension
        3. Create all tables
        4. Initialize metrics table
        5. Create default admin account (optional)
    
    Args:
        create_admin (bool): If True, create default admin account
    
    Returns:
        bool: True if initialization successful
    """
    print("=" * 70)
    print("BrandPulse Database Initialization")
    print("=" * 70)
    
    # Step 1: Check connectivity
    print("\n[1/5] Checking database connection...")
    if not check_database_health(engine):
        print("❌ Cannot connect to database. Check DATABASE_URL in .env")
        return False
    print("✅ Database connection successful")
    
    # Step 2: Enable pgvector extension
    print("\n[2/5] Enabling pgvector extension...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        print("✅ pgvector extension enabled")
    except Exception as e:
        print(f"❌ Failed to enable pgvector: {e}")
        return False
    
    # Step 3: Create tables
    print("\n[3/5] Creating database tables...")
    try:
        Base.metadata.create_all(engine)
        # Apply self-healing migration for missing region column
        try:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE company_profiles ADD COLUMN IF NOT EXISTS region VARCHAR(100) DEFAULT 'India';"))
                conn.commit()
        except Exception as migration_error:
            print(f"⚠️ Self-healing schema migration warning: {migration_error}")
            
        print("✅ Tables created successfully:")
        print("   - admins")
        print("   - companies")
        print("   - generated_ideas")
        print("   - run_logs")
        print("   - email_logs")
        print("   - metrics")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False
    
    # Step 4: Initialize metrics
    print("\n[4/5] Initializing metrics table...")
    try:
        db = next(get_db())
        try:
            existing_metric = db.query(Metric).first()
            if not existing_metric:
                metric = Metric(
                    total_insights=0,
                    pending_count=0,
                    approved_count=0,
                    rejected_count=0,
                    avg_processing_time=0.0,
                    total_tokens_used=0,
                    total_emails_sent=0,
                    total_apology_emails=0,
                    last_updated=datetime.utcnow()
                )
                db.add(metric)
                db.commit()
                print("✅ Metrics table initialized")
            else:
                print("ℹ️  Metrics table already exists")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Failed to initialize metrics: {e}")
        return False
    
    # Step 5: Create admin account
    if create_admin:
        print("\n[5/5] Creating default admin account...")
        try:
            admin_username = os.getenv("ADMIN_USERNAME", "admin")
            admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
            
            db = next(get_db())
            try:
                existing_admin = db.query(Admin).filter(Admin.username == admin_username).first()
                
                if not existing_admin:
                    # Hash password with bcrypt
                    password_hash = bcrypt.hashpw(
                        admin_password.encode('utf-8'), 
                        bcrypt.gensalt()
                    ).decode('utf-8')
                    
                    admin = Admin(
                        username=admin_username,
                        password_hash=password_hash,
                        created_at=datetime.utcnow()
                    )
                    db.add(admin)
                    db.commit()
                    
                    print(f"✅ Admin account created:")
                    print(f"   Username: {admin_username}")
                    print(f"   Password: {admin_password}")
                    print(f"   ⚠️  CHANGE PASSWORD AFTER FIRST LOGIN!")
                else:
                    print(f"ℹ️  Admin account '{admin_username}' already exists")
            finally:
                db.close()
        except Exception as e:
            print(f"❌ Failed to create admin account: {e}")
            return False
    else:
        print("\n[5/5] Skipping admin account creation")
    
    print("\n" + "=" * 70)
    print("✅ Database initialization complete!")
    print("=" * 70)
    return True


# ==================================================================
# Verification Function
# ==================================================================

def verify_database():
    """
    Verify database schema and show statistics
    
    Prints:
        - List of tables
        - Row counts
        - Sample data (if available)
    """
    print("\n" + "=" * 70)
    print("Database Verification")
    print("=" * 70)
    
    try:
        db = next(get_db())
        try:
            # Check tables exist
            print("\n📋 Tables:")
            tables = ['admins', 'companies', 'generated_ideas', 'run_logs', 'email_logs', 'metrics']
            for table in tables:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"   ✅ {table}: {count} rows")
                except Exception as e:
                    print(f"   ❌ {table}: Error - {e}")
            
            # Check pgvector
            result = db.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"))
            vector_info = result.fetchone()
            if vector_info:
                print(f"\n🔧 pgvector: v{vector_info[1]} installed")
            
            # Check admin accounts
            admins = db.query(Admin).all()
            if admins:
                print(f"\n👤 Admin Accounts:")
                for admin in admins:
                    print(f"   - {admin.username} (created: {admin.created_at})")
        finally:
            db.close()
    
    except Exception as e:
        print(f"❌ Verification failed: {e}")


# ==================================================================
# Sample Data Creation (For Testing)
# ==================================================================

def create_sample_data():
    """
    Create sample company data for testing
    
    Creates:
        - 2 sample companies
        - Next run times set to current time (for immediate scheduler testing)
    """
    print("\n" + "=" * 70)
    print("Creating Sample Data")
    print("=" * 70)
    
    try:
        db = next(get_db())
        try:
            # Sample Company 1
            company1 = Company(
                name="Acme Corporation",
                description="Leading provider of enterprise software solutions",
                email="insights@acme-corp.com",
                pdf_text="Acme Corp specializes in cloud-based enterprise software...",
                frequency_hours=24,
                status=CompanyStatusEnum.ACTIVE,
                next_run_time=datetime.utcnow(),  # Run immediately
                created_at=datetime.utcnow()
            )
            db.add(company1)
            
            # Sample Company 2
            company2 = Company(
                name="TechStart Industries",
                description="Innovative AI-powered analytics platform",
                email="reports@techstart.io",
                pdf_text="TechStart builds cutting-edge AI analytics tools...",
                frequency_hours=12,
                status=CompanyStatusEnum.ACTIVE,
                next_run_time=datetime.utcnow() + timedelta(hours=12),
                created_at=datetime.utcnow()
            )
            db.add(company2)
            db.commit()
            
            print("✅ Sample companies created:")
            print("   1. Acme Corporation (frequency: 24h)")
            print("   2. TechStart Industries (frequency: 12h)")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Failed to create sample data: {e}")


# ==================================================================
# Main Execution
# ==================================================================

def main():
    """
    Main initialization workflow
    
    Prompts user for:
        - Admin account creation
        - Sample data creation
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize BrandPulse database")
    parser.add_argument("--no-admin", action="store_true", help="Skip admin account creation")
    parser.add_argument("--sample-data", action="store_true", help="Create sample companies")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing database")
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_database()
        return
    
    # Initialize database
    success = init_database(create_admin=not args.no_admin)
    
    if not success:
        print("\n❌ Initialization failed!")
        sys.exit(1)
    
    # Verify
    verify_database()
    
    # Create sample data if requested
    if args.sample_data:
        create_sample_data()
    
    print("\n✅ All done! Database is ready for use.")
    print("\n📝 Next steps:")
    print("   1. Start the worker: docker-compose up worker")
    print("   2. Access dashboard: http://localhost:3000")
    print(f"   3. Login with username: {os.getenv('ADMIN_USERNAME', 'admin')}")


if __name__ == "__main__":
    main()
