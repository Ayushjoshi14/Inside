import json
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database.session import engine, Base, SessionLocal, apply_db_migrations
from backend.app.models.entities import Ingredient
from backend.app.api.auth_router import router as auth_router
from backend.app.api.profile_router import router as profile_router
from backend.app.api.scan_router import router as scan_router
from backend.app.api.history_router import router as history_router
from backend.app.api.billing_router import router as billing_router
from backend.app.api.payment_router import router as payment_router
from backend.app.api.legal_router import router as legal_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inside")

def seed_database_if_needed():
    db = SessionLocal()
    try:
        # 1. Ensure default local/guest user exists
        default_user = db.query(User).filter(User.id == 1).first()
        if not default_user:
            default_user = db.query(User).filter(User.email == "user@insideapp.in").first()
        if not default_user:
            from backend.app.security.auth import hash_password
            default_user = User(
                id=1,
                email="user@insideapp.in",
                hashed_password=hash_password("inside_app_default_secure_pass"),
                is_active=True,
                is_premium=False,
                free_scans_used=0,
                scans_count=0
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            profile = UserProfile(
                user_id=default_user.id,
                name="Friend",
                diet_preference="NONE",
                avoid_ingredients="[]",
                allergens="[]"
            )
            db.add(profile)
            db.commit()
            logger.info("Initialized default user (id=1, email=user@insideapp.in)")

        # 2. Seed ingredients
        count = db.query(Ingredient).count()
        if count == 0:
            seed_file = os.path.join(os.path.dirname(__file__), "seed_data", "ingredients.json")
            if os.path.exists(seed_file):
                with open(seed_file, "r", encoding="utf-8") as f:
                    items = json.load(f)
                for item in items:
                    ing = Ingredient(
                        name=item["name"],
                        normalized_name=item["normalized_name"],
                        aliases=json.dumps(item.get("aliases", [])),
                        ins_number=item.get("ins_number"),
                        e_number=item.get("e_number"),
                        category=item.get("category", "General"),
                        description=item.get("description"),
                        common_uses=item.get("common_uses"),
                        vegetarian_status=item.get("vegetarian_status", "YES"),
                        vegan_status=item.get("vegan_status", "YES"),
                        allergen_info=item.get("allergen_info"),
                        caution_level=item.get("caution_level", "GOOD"),
                        explanation=item.get("explanation"),
                        source_ref=item.get("source_ref")
                    )
                    db.add(ing)
                db.commit()
                logger.info(f"Seeded {len(items)} structured ingredients into database.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed
    Base.metadata.create_all(bind=engine)
    apply_db_migrations()
    seed_database_if_needed()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Inside — AI Ingredient Scanner and Personalized Food Analysis API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(scan_router)
app.include_router(history_router)
app.include_router(billing_router)
app.include_router(payment_router)
app.include_router(payment_router, prefix="/api")
app.include_router(legal_router)

@app.get("/")
def root():
    return {
        "app": "Inside",
        "tagline": "Know what's inside.",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
