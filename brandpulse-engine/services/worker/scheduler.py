"""
BrandPulse Worker Scheduler - Main Entry Point
==============================================
Orchestrates scheduled tasks using APScheduler
"""

import os
import sys
import time
import logging
import signal

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.shared.database import engine, SessionLocal, check_database_health
from services.worker.tasks.rejection_task import auto_reject_expired_insights
from services.worker.tasks.refinement_task import process_refinement_requests
from services.worker.tasks.generation_task import generate_new_insights
from services.worker.tasks.metrics_task import update_system_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

scheduler = None
shutdown_flag = False


def run_scheduled_tasks():
    """Execute all scheduled tasks in sequence"""
    logger.info("=" * 70)
    logger.info("🚀 Scheduler run started")
    logger.info("=" * 70)
    
    session = SessionLocal()
    
    try:
        # Execute tasks
        auto_reject_expired_insights(session)
        process_refinement_requests(session)
        generate_new_insights(session)
        update_system_metrics(session)
        
        logger.info("=" * 70)
        logger.info("✅ Scheduler run completed")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Scheduler run failed: {e}")
        session.rollback()
    finally:
        session.close()


def initialize_scheduler():
    """Initialize APScheduler"""
    global scheduler
    
    check_interval = int(os.getenv('SCHEDULER_CHECK_INTERVAL', 300))
    logger.info(f"⚙️ Initializing scheduler (interval: {check_interval}s)")
    
    scheduler = BlockingScheduler()
    scheduler.add_job(
        func=run_scheduled_tasks,
        trigger=IntervalTrigger(seconds=check_interval),
        id='main_scheduler_job',
        name='BrandPulse Tasks',
        replace_existing=True,
        misfire_grace_time=60
    )
    
    logger.info("✅ Scheduler initialized")
    return scheduler


def shutdown_handler(signum, frame):
    """Handle graceful shutdown"""
    global shutdown_flag, scheduler
    
    logger.info("\n⚠️ Shutdown signal received")
    shutdown_flag = True
    
    if scheduler:
        scheduler.shutdown(wait=False)
    
    logger.info("✅ Scheduler stopped")
    sys.exit(0)


def main():
    """Main entry point"""
    global scheduler
    
    logger.info("🤖 BrandPulse Worker Starting...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Startup delay
    startup_delay = int(os.getenv('SCHEDULER_STARTUP_DELAY', 10))
    logger.info(f"⏳ Waiting {startup_delay}s for database...")
    time.sleep(startup_delay)
    
    # Health check
    if not check_database_health(engine):
        logger.error("❌ Database health check failed")
        sys.exit(1)
    logger.info("✅ Database healthy")
    
    # Start scheduler
    try:
        scheduler = initialize_scheduler()
        logger.info("🔄 Scheduler running (Ctrl+C to stop)")
        scheduler.start()
    except KeyboardInterrupt:
        shutdown_handler(None, None)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()