import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.config import settings

logger = logging.getLogger(__name__)

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def apply_db_migrations(target_engine=None):
    """
    Applies non-destructive schema migrations for existing databases.
    Ensures:
    1. scan_history has product_category, ingredient_count, and idempotency_key columns.
    2. users has free_scans_used column with proper backfill.
    """
    eng = target_engine or engine
    try:
        inspector = inspect(eng)
        table_names = inspector.get_table_names()

        with eng.connect() as conn:
            if "users" in table_names:
                user_cols = [col["name"] for col in inspector.get_columns("users")]
                if "free_scans_used" not in user_cols:
                    logger.info("Migrating users table: adding free_scans_used column...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN free_scans_used INTEGER DEFAULT 0"))
                    conn.commit()
                # Backfill free_scans_used from scans_count where appropriate
                conn.execute(text("UPDATE users SET free_scans_used = CASE WHEN is_premium = 1 THEN 0 ELSE MIN(3, scans_count) END WHERE free_scans_used IS NULL OR free_scans_used = 0"))
                conn.commit()

            if "scan_history" in table_names:
                scan_cols = [col["name"] for col in inspector.get_columns("scan_history")]
                if "product_category" not in scan_cols:
                    logger.info("Migrating scan_history table: adding product_category column...")
                    conn.execute(text("ALTER TABLE scan_history ADD COLUMN product_category VARCHAR(100) DEFAULT 'Food Product'"))
                    conn.commit()
                if "ingredient_count" not in scan_cols:
                    logger.info("Migrating scan_history table: adding ingredient_count column...")
                    conn.execute(text("ALTER TABLE scan_history ADD COLUMN ingredient_count INTEGER DEFAULT 0"))
                    conn.commit()
                if "idempotency_key" not in scan_cols:
                    logger.info("Migrating scan_history table: adding idempotency_key column...")
                    conn.execute(text("ALTER TABLE scan_history ADD COLUMN idempotency_key VARCHAR(255)"))
                    conn.commit()

                conn.execute(text("UPDATE scan_history SET product_category = 'Food Product' WHERE product_category IS NULL OR product_category = ''"))
                conn.commit()
    except Exception as e:
        logger.warning(f"Database migration check notice: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

