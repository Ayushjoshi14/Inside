import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.app.config import settings

logger = logging.getLogger(__name__)

database_url = settings.DATABASE_URL

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

connect_args = {}

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def apply_db_migrations(target_engine=None):
    """Apply non-destructive database schema migrations."""
    eng = target_engine or engine

    try:
        inspector = inspect(eng)
        table_names = inspector.get_table_names()

        with eng.begin() as conn:
            if "users" in table_names:
                user_cols = {
                    col["name"]
                    for col in inspector.get_columns("users")
                }

                if "free_scans_used" not in user_cols:
                    logger.info(
                        "Migrating users: adding free_scans_used"
                    )
                    conn.execute(
                        text(
                            "ALTER TABLE users "
                            "ADD COLUMN free_scans_used INTEGER DEFAULT 0"
                        )
                    )

                conn.execute(
                    text("""
                        UPDATE users
                        SET free_scans_used = CASE
                            WHEN is_premium = TRUE THEN 0
                            WHEN scans_count < 3 THEN scans_count
                            ELSE 3
                        END
                        WHERE free_scans_used IS NULL
                           OR free_scans_used = 0
                    """)
                )

            if "scan_history" in table_names:
                scan_cols = {
                    col["name"]
                    for col in inspector.get_columns("scan_history")
                }

                migrations = {
                    "product_category": (
                        "ALTER TABLE scan_history "
                        "ADD COLUMN product_category "
                        "VARCHAR(100) DEFAULT 'Food Product'"
                    ),
                    "ingredient_count": (
                        "ALTER TABLE scan_history "
                        "ADD COLUMN ingredient_count INTEGER DEFAULT 0"
                    ),
                    "idempotency_key": (
                        "ALTER TABLE scan_history "
                        "ADD COLUMN idempotency_key VARCHAR(255)"
                    ),
                    "custom_product_name": (
                        "ALTER TABLE scan_history "
                        "ADD COLUMN custom_product_name VARCHAR(255)"
                    ),
                    "purchase_decision": (
                        "ALTER TABLE scan_history "
                        "ADD COLUMN purchase_decision VARCHAR(10)"
                    ),
                    "nutrition_facts": (
                        "ALTER TABLE scan_history "
                        "ADD COLUMN nutrition_facts TEXT DEFAULT '{}'"
                    ),
                }

                for column_name, sql in migrations.items():
                    if column_name not in scan_cols:
                        logger.info(
                            "Migrating scan_history: adding %s",
                            column_name,
                        )
                        conn.execute(text(sql))

                conn.execute(
                    text("""
                        UPDATE scan_history
                        SET product_category = 'Food Product'
                        WHERE product_category IS NULL
                           OR product_category = ''
                    """)
                )

    except Exception:
        logger.exception("Database migration failed")
        raise


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
