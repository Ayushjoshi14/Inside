import datetime
import json
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    scans_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)
    premium_granted_at = Column(DateTime, nullable=True)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    scans = relationship("ScanHistory", back_populates="user", cascade="all, delete-orphan")
    purchases = relationship("PurchaseVerification", back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100), default="Friend")
    diet_preference = Column(String(50), default="NONE")  # NONE, VEGETARIAN, VEGAN
    avoid_ingredients = Column(Text, default="[]")  # JSON array of strings
    allergens = Column(Text, default="[]")  # JSON array of strings
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    user = relationship("User", back_populates="profile")

    @property
    def avoid_list(self):
        try:
            return json.loads(self.avoid_ingredients) if self.avoid_ingredients else []
        except Exception:
            return []

    @property
    def allergens_list(self):
        try:
            return json.loads(self.allergens) if self.allergens else []
        except Exception:
            return []

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    normalized_name = Column(String(255), index=True, nullable=False)
    aliases = Column(Text, default="[]")  # JSON array of alternate names
    ins_number = Column(String(50), index=True, nullable=True)
    e_number = Column(String(50), index=True, nullable=True)
    category = Column(String(100), nullable=False)  # Preservative, Sweetener, Emulsifier, etc.
    description = Column(Text, nullable=True)
    common_uses = Column(Text, nullable=True)
    vegetarian_status = Column(String(20), default="YES")  # YES, NO, MAYBE
    vegan_status = Column(String(20), default="YES")  # YES, NO, MAYBE
    allergen_info = Column(String(100), nullable=True)
    caution_level = Column(String(20), default="GOOD")  # GOOD, CAUTION, AVOID
    explanation = Column(Text, nullable=True)
    source_ref = Column(String(255), nullable=True)
    last_updated = Column(DateTime, default=get_utc_now)

class CachedIngredientAnalysis(Base):
    __tablename__ = "cached_ingredient_analyses"

    id = Column(Integer, primary_key=True, index=True)
    normalized_name = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(20), nullable=False)  # GOOD, CAUTION, AVOID
    reason = Column(Text, nullable=False)
    category = Column(String(100), default="General")
    created_at = Column(DateTime, default=get_utc_now)

class ScanHistory(Base):
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_name = Column(String(255), default="Scanned Food Product")
    raw_ocr_text = Column(Text, nullable=True)
    extracted_ingredients = Column(Text, default="[]")  # JSON array
    overall_status = Column(String(20), nullable=False)  # GOOD, CAUTION, AVOID
    overall_score = Column(Integer, default=70)
    summary = Column(Text, nullable=True)
    ingredient_details = Column(Text, default="[]")  # JSON array of structured items
    warnings = Column(Text, default="[]")  # JSON array of warning strings
    recommendations = Column(Text, default="[]")  # JSON array of recommendations
    created_at = Column(DateTime, default=get_utc_now, index=True)

    user = relationship("User", back_populates="scans")

class PurchaseVerification(Base):
    __tablename__ = "purchase_verifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(String(255), nullable=True)
    purchase_token = Column(String(1024), unique=True, nullable=False)
    product_id = Column(String(100), nullable=False)
    purchase_time_millis = Column(String(100), nullable=True)
    purchase_state = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    verification_payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    user = relationship("User", back_populates="purchases")
