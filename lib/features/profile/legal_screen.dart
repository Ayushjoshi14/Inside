import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/app_constants.dart';

enum LegalDocType { privacy, terms, refund, disclaimer, about }

class LegalScreen extends StatelessWidget {
  final LegalDocType docType;

  const LegalScreen({super.key, required this.docType});

  String get title {
    switch (docType) {
      case LegalDocType.privacy:
        return 'Privacy Policy';
      case LegalDocType.terms:
        return 'Terms & Conditions';
      case LegalDocType.refund:
        return 'Refund Policy';
      case LegalDocType.disclaimer:
        return 'Medical & Safety Disclaimer';
      case LegalDocType.about:
        return 'About Inside';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(title),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: _buildContent(),
        ),
      ),
    );
  }

  List<Widget> _buildContent() {
    switch (docType) {
      case LegalDocType.privacy:
        return [
          _paragraph("Last updated: October 2026"),
          _sectionTitle("1. Information We Collect"),
          _paragraph("Inside collects only information necessary to deliver personalized food ingredient analysis: user account email, dietary preferences (e.g. vegetarian, vegan), user-specified ingredients to avoid, and known allergens."),
          _sectionTitle("2. Image Processing & Retention"),
          _paragraph("Food packaging photos are processed strictly in temporary device memory for OCR text extraction and are discarded immediately after text extraction. We DO NOT store or upload your packaging photos to our servers."),
          _sectionTitle("3. Ingredient Analysis"),
          _paragraph("Extracted ingredient text is matched against our offline structured food additive database and secure AI services. No personal identifying information is transmitted during ingredient lookups."),
          _sectionTitle("4. Payments & Billing"),
          _paragraph("All purchases (₹199 Lifetime Premium) are handled directly through Google Play Billing. Inside never sees or stores card numbers or bank information."),
          _sectionTitle("5. Account & Data Deletion"),
          _paragraph("You can permanently delete your account, saved scans, and all profile preferences anytime under Profile → Delete Account."),
        ];
      case LegalDocType.terms:
        return [
          _paragraph("Last updated: October 2026"),
          _sectionTitle("1. Acceptance"),
          _paragraph("By installing or using Inside, you agree to these Terms and Conditions."),
          _sectionTitle("2. License & Lifetime Access"),
          _paragraph("Inside Lifetime Premium grants the purchasing Google Play account perpetual access to premium features for the lifetime of the application."),
          _sectionTitle("3. Educational Purpose"),
          _paragraph("Inside provides informational analyses based on publicly published food science standards and additive regulations. It does not constitute medical or clinical dietary advice."),
        ];
      case LegalDocType.refund:
        return [
          _sectionTitle("Google Play Refund Policy"),
          _paragraph("All purchases for Inside Premium are processed through Google Play."),
          _paragraph("Refunds are governed by standard Google Play Store policies. You may request a refund within 48 hours of purchase through your Google Play Order History or the Google Play Store app."),
        ];
      case LegalDocType.disclaimer:
        return [
          _sectionTitle("Medical & Safety Disclaimer"),
          _paragraph(AppConstants.medicalDisclaimer),
          const SizedBox(height: 16),
          _paragraph("Inside is not a substitute for clinical allergen tests, medical diagnoses, or direct verification from manufacturers."),
        ];
      case LegalDocType.about:
        return [
          Center(
            child: Column(
              children: [
                Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(Icons.qr_code_scanner_rounded, color: Colors.white, size: 36),
                ),
                const SizedBox(height: 12),
                const Text("Inside", style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
                const SizedBox(height: 4),
                const Text(AppConstants.appTagline, style: TextStyle(fontSize: 14, color: AppColors.textSecondary)),
                const SizedBox(height: 8),
                const Text("Version 1.0.0 (Production)", style: TextStyle(fontSize: 12, color: AppColors.textTertiary)),
              ],
            ),
          ),
          const SizedBox(height: 24),
          _sectionTitle("Our Mission"),
          _paragraph("Inside helps you make confident, informed food choices by instantly decoding ingredients labels, uncovering hidden additives, and checking dietary compatibility."),
          _sectionTitle("Support & Inquiries"),
          _paragraph("Email: support@insideapp.in\nWebsite: https://insideapp.in"),
        ];
    }
  }

  Widget _sectionTitle(String text) {
    return Padding(
      padding: const EdgeInsets.only(top: 20, bottom: 8),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
      ),
    );
  }

  Widget _paragraph(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text(
        text,
        style: const TextStyle(
          fontSize: 14,
          color: AppColors.textSecondary,
          height: 1.5,
        ),
      ),
    );
  }
}
