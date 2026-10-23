from typing import List, Optional, Dict, Any
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
    free_scans_used: int = 0
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
    source: Optional[str] = None  # "local_db" | "cache" | "ai" — analysis source

class ScoreBreakdownItem(BaseModel):
    label: str
    points: int

class ScoreBreakdown(BaseModel):
    base_score: int = 100
    assessment_type: Optional[str] = "FULL_NUTRITIONAL_AND_INGREDIENT"
    assessment_label: Optional[str] = "Verified Ingredients & Nutrition Facts"
    deductions: List[ScoreBreakdownItem] = []
    bonuses: List[ScoreBreakdownItem] = []
    final_score: int
    good_count: int = 0
    caution_count: int = 0
    avoid_count: int = 0
    nutrition_integrated: bool = False
    disclaimer: str = (
        "Score is an informational estimate based on ingredient safety classifications "
        "and available nutrition data. It is not a medical or clinical assessment."
    )

class ScanAnalysisResult(BaseModel):
    scan_id: Optional[int] = None
    product_name: str
    product_category: Optional[str] = "Food Product"
    ingredient_count: Optional[int] = 0
    overall_status: str  # GOOD, CAUTION, AVOID
    score: int  # 0 to 100
    score_breakdown: Optional[ScoreBreakdown] = None  # transparent scoring breakdown
    positive_findings: List[str] = []  # notable wholesome ingredients
    summary: str
    ingredients: List[IngredientItemAnalysis]
    warnings: List[str]
    recommendations: List[str]
    raw_ocr_text: Optional[str] = None
    created_at: Optional[str] = None
    is_compatible: bool = True
    compatibility_status: str = "COMPATIBLE"
    compatibility_message: Optional[str] = None
    custom_product_name: Optional[str] = None
    purchase_decision: Optional[str] = None
    nutrition_facts: Dict[str, Any] = {}
    assessment_type: Optional[str] = "INGREDIENT_ONLY"


class ScanTextRequest(BaseModel):
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    ocr_text: str
    idempotency_key: Optional[str] = None

class ScanImageRequest(BaseModel):
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    image_base64: str
    idempotency_key: Optional[str] = None

# History
class HistoryItemResponse(BaseModel):
    id: int
    product_name: str
    product_category: str = "Food Product"
    overall_status: str
    overall_score: int
    summary: Optional[str]
    ingredient_count: int
    created_at: str
    custom_product_name: Optional[str] = None
    purchase_decision: Optional[str] = None
    nutrition_facts: Optional[Dict[str, Any]] = None

class UpdateScanDecisionRequest(BaseModel):
    custom_product_name: Optional[str] = None
    purchase_decision: Optional[str] = None

# Razorpay Payments
class CreateOrderRequest(BaseModel):
    amount: Optional[int] = 19900  # in paise (minimum 100 paise)
    currency: Optional[str] = "INR"
    receipt: Optional[str] = None
    product: Optional[str] = "inside_premium_lifetime"

class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int  # in paise: 19900
    currency: str = "INR"
    key_id: str
    product: str = "inside_premium_lifetime"

class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class PaymentVerifyResponse(BaseModel):
    success: bool
    is_premium: bool
    message: str
    order_id: str
    payment_id: Optional[str] = None

class PremiumStatusResponse(BaseModel):
    is_premium: bool
    free_scans_used: int = 0
    scans_count: int
    scans_left: int
    product_id: str = "inside_premium_lifetime"
    price_inr: int = 199
    price_paise: int = 19900
    currency: str = "INR"
    key_id: Optional[str] = None

# Legacy Billing Verification (Optional)
class BillingVerifyRequest(BaseModel):
    product_id: str
    purchase_token: str
    order_id: Optional[str] = None

class BillingVerifyResponse(BaseModel):
    success: bool
    is_premium: bool
    message: str
    order_id: Optional[str] = None
