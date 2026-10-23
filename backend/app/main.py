import json
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database.session import engine, Base, SessionLocal, get_db, apply_db_migrations
from backend.app.models.entities import Ingredient, User, UserProfile
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
        # Seed ingredients
        count = db.query(Ingredient).count()
        if count == 0:
            seed_file = os.path.join(
                os.path.dirname(__file__),
                "seed_data",
                "ingredients.json",
            )
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
                        source_ref=item.get("source_ref"),
                    )
                    db.add(ing)

                db.commit()
                logger.info(
                    "Seeded %s structured ingredients into database.",
                    len(items),
                )
    except Exception:
        logger.exception("Error seeding database")
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

# Direct aliases for standard web checkout endpoints
from backend.app.schemas.api_schemas import CreateOrderRequest, CreateOrderResponse, PaymentVerifyRequest, PaymentVerifyResponse
from backend.app.security.auth import get_current_user
from backend.app.api.payment_router import create_payment_order, verify_payment
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from typing import Optional

@app.post("/api/create-order", response_model=CreateOrderResponse, tags=["Razorpay Web Checkout"])
@app.post("/create-order", response_model=CreateOrderResponse, tags=["Razorpay Web Checkout"])
def api_create_order(
    request: Optional[CreateOrderRequest] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return create_payment_order(request=request, user=user, db=db)
    except HTTPException as e:
        # Standard web checkout specification: Razorpay API errors return 500
        if e.status_code == 502:
            raise HTTPException(status_code=500, detail=e.detail)
        raise e

@app.post("/api/verify-payment", response_model=PaymentVerifyResponse, tags=["Razorpay Web Checkout"])
@app.post("/verify-payment", response_model=PaymentVerifyResponse, tags=["Razorpay Web Checkout"])
def api_verify_payment(
    request: PaymentVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return verify_payment(request=request, user=user, db=db)

@app.get("/checkout", response_class=HTMLResponse, tags=["Razorpay Web Checkout"])
@app.get("/web/checkout", response_class=HTMLResponse, tags=["Razorpay Web Checkout"])
def checkout_page():
    """
    Serves the Razorpay Standard Web Checkout frontend page.
    """
    checkout_html_path = os.path.join(os.path.dirname(__file__), "static", "checkout.html")
    if os.path.exists(checkout_html_path):
        with open(checkout_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Checkout page not found</h1>", status_code=404)

@app.get("/")
def root():
    return {
        "app": "Inside",
        "tagline": "Know what's inside.",
        "status": "online",
        "version": "1.0.0",
        "checkout_url": "/checkout"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
@app.get("/privacy-policy", include_in_schema=False)
def privacy_policy():
    privacy_policy_path = os.path.join(
        os.path.dirname(__file__),
        "static",
        "privacy-policy.html",
    )

    if os.path.exists(privacy_policy_path):
        return FileResponse(
            privacy_policy_path,
            media_type="text/html",
        )

    return HTMLResponse(
        content="Privacy policy not found",
        status_code=404,
    )