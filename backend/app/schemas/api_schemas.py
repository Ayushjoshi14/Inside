from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# Auth
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: Optional[str] = "Friend"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    name: str
    is_premium: bool

# Profile
class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    diet_preference: Optional[str] = None  # NONE, VEGETARIAN, VEGAN
    avoid_ingredients: Optional[List[str]] = None
    allergens: Optional[List[str]] = None

class ProfileResponse(BaseModel):
    user_id: int
    email: str
    name: str
    diet_preference: str
    avoid_ingredients: List[str]
    allergens: List[str]
    is_premium: bool
    scans_count: int
    scans_left: int

# Ingredients & Analysis
class IngredientItemAnalysis(BaseModel):
    name: str
    normalized_name: str
    status: str  # GOOD, CAUTION, AVOID
    reason: str
    category: str
    vegetarian_status: Optional[str] = "YES"
    vegan_status: Optional[str] = "YES"
    allergen_info: Optional[str] = None

class ScanAnalysisResult(BaseModel):
    scan_id: Optional[int] = None
    product_name: str
    overall_status: str  # GOOD, CAUTION, AVOID
    score: int  # 0 to 100
    summary: str
    ingredients: List[IngredientItemAnalysis]
    warnings: List[str]
    recommendations: List[str]
    raw_ocr_text: Optional[str] = None
    created_at: Optional[str] = None

class ScanTextRequest(BaseModel):
    product_name: Optional[str] = "Food Product"
    ocr_text: str

class ScanImageRequest(BaseModel):
    product_name: Optional[str] = "Food Product"
    image_base64: str

# History
class HistoryItemResponse(BaseModel):
    id: int
    product_name: str
    overall_status: str
    overall_score: int
    summary: Optional[str]
    ingredient_count: int
    created_at: str

# Billing
class BillingVerifyRequest(BaseModel):
    product_id: str
    purchase_token: str
    order_id: Optional[str] = None

class BillingVerifyResponse(BaseModel):
    success: bool
    is_premium: bool
    message: str
    order_id: Optional[str] = None

class PremiumStatusResponse(BaseModel):
    is_premium: bool
    scans_count: int
    scans_left: int
    product_id: str = "premium_lifetime"
    price_inr: int = 199
