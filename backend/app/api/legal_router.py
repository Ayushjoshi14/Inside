from fastapi import APIRouter

router = APIRouter(prefix="/legal", tags=["Legal & Policies"])

@router.get("/privacy-policy")
def get_privacy_policy():
    return {
        "title": "Privacy Policy",
        "last_updated": "October 2026",
        "app_name": "Inside",
        "sections": [
            {
                "heading": "1. Information We Collect",
                "content": "Inside collects information necessary to deliver personalized food ingredient analysis: user account email, dietary preferences (e.g. vegetarian, vegan), user-specified ingredients to avoid, and known allergens. When you scan an ingredient label, the image is processed to extract text."
            },
            {
                "heading": "2. Image Processing & Retention",
                "content": "By default, raw food packaging photos are processed strictly in temporary device memory for OCR text extraction and are discarded immediately after text extraction. We DO NOT store or upload your packaging photos to our servers unless explicitly requested."
            },
            {
                "heading": "3. Ingredient Data & AI Processing",
                "content": "Extracted text is matched against our offline structured food additive database. For unknown ingredients, text may be analyzed via secure AI services. No personal identifying information is transmitted during ingredient analysis."
            },
            {
                "heading": "4. Payments & Billing",
                "content": "All purchases (₹199 Lifetime Premium) are processed securely through Google Play Billing. Inside never sees, stores, or handles credit card, debit card, or UPI credentials. We only receive a cryptographic verification token from Google to unlock your premium access."
            },
            {
                "heading": "5. Account & Data Deletion",
                "content": "You can permanently delete your account, saved scans, and all associated profile preferences anytime directly inside the app under Profile → Delete Account."
            },
            {
                "heading": "6. Contact Support",
                "content": "If you have questions or data inquiries, contact us at: support@insideapp.in"
            }
        ]
    }

@router.get("/terms")
def get_terms_and_conditions():
    return {
        "title": "Terms and Conditions",
        "last_updated": "October 2026",
        "sections": [
            {
                "heading": "1. Acceptance of Terms",
                "content": "By downloading or using the Inside app, you agree to these Terms and Conditions."
            },
            {
                "heading": "2. License & Lifetime Access",
                "content": "Inside Lifetime Premium grants the purchasing Google Play account perpetual access to premium features for the lifetime of the application."
            },
            {
                "heading": "3. Informational Purposes Only",
                "content": "The application provides educational analysis based on publicly available food science and regulatory standards. It does not replace professional medical or nutritional advice."
            }
        ]
    }

@router.get("/disclaimer")
def get_disclaimer():
    return {
        "title": "Important Safety & Medical Disclaimer",
        "text": "This analysis is for informational purposes only. Ingredient formulations, packaging labels, and manufacturing facility cross-contamination risks may change without notice. Always verify the actual physical product label. For serious allergies, food intolerances, or clinical medical conditions, always consult a qualified healthcare professional or contact the manufacturer directly. Inside does not warrant 100% medical certainty."
    }

@router.get("/refund-policy")
def get_refund_policy():
    return {
        "title": "Refund Policy",
        "content": "All purchases of Inside Premium are processed through Google Play. Refunds are subject to Google Play's standard refund policies. You may request a refund directly through the Google Play Store or Order History within 48 hours of purchase."
    }
