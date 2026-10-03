import 'package:flutter/material.dart';

class AppColors {
  // Primary brand accent: Clean, trustworthy emerald green
  static const Color primary = Color(0xFF0F9D58);
  static const Color primaryDark = Color(0xFF0B8043);
  static const Color primaryLight = Color(0xFFE6F4EA);

  // Background and surfaces
  static const Color background = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFF8F9FA);
  static const Color surfaceVariant = Color(0xFFF1F3F4);

  // Text
  static const Color textPrimary = Color(0xFF202124);
  static const Color textSecondary = Color(0xFF5F6368);
  static const Color textTertiary = Color(0xFF80868B);

  // Status Triad: Green, Yellow, Red
  static const Color statusGood = Color(0xFF1E8E3E);
  static const Color statusGoodBg = Color(0xFFE6F4EA);
  
  static const Color statusCaution = Color(0xFFF29900);
  static const Color statusCautionBg = Color(0xFFFEF7E0);
  
  static const Color statusAvoid = Color(0xFFD93025);
  static const Color statusAvoidBg = Color(0xFFFCE8E6);

  // Borders & Dividers
  static const Color border = Color(0xFFE8EAED);
  static const Color divider = Color(0xFFDADCE0);

  // Card shadow
  static BoxShadow cardShadow = BoxShadow(
    color: Colors.black.withValues(alpha: 0.04),
    blurRadius: 10,
    offset: const Offset(0, 2),
  );
}
