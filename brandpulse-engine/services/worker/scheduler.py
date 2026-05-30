"""
BrandPulse Worker Scheduler
===========================
Entry point for starting the Celery Worker and Celery Beat.
"""

import os
import sys
import time
import logging
import signal
import subprocess

from services.shared.database import engine, check_database_health

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point: wait for DB, then launch Celery"""
    logger.info("🤖 BrandPulse Worker Starting (Celery)...")
    
    # Startup delay
    startup_delay = int(os.getenv('SCHEDULER_STARTUP_DELAY', 10))
    logger.info(f"⏳ Waiting {startup_delay}s for database...")
    time.sleep(startup_delay)
    
    # Health check
    if not check_database_health(engine):
        logger.error("❌ Database health check failed")
        sys.exit(1)
    logger.info("✅ Database healthy")
    
    # Auto-migrate: create all tables defined in models if they don't exist yet
    logger.info("🗄️ Running auto-migration (create_all)...")
    try:
        from services.shared.models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables synchronized")
    except Exception as e:
        logger.error(f"❌ Auto-migration failed: {e}")
    
    logger.info("🚀 Launching Celery Worker with embedded Beat...")
    
    # We use subprocess.run to execute the celery CLI
    # --beat runs the scheduler inside the same process
    try:
        subprocess.run(
            [
                "celery",
                "-A", "services.worker.celery_app",
                "worker",
                "--beat",
                "--loglevel=info"
            ],
            check=True
        )
    except KeyboardInterrupt:
        logger.info("✅ Celery stopped via keyboard interrupt")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Celery exited with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()