import 'package:flutter/material.dart';
import '../core/constants/app_colors.dart';

class IngredientItem {
  final String name;
  final String normalizedName;
  final String status; // 'GOOD', 'CAUTION', 'AVOID'
  final String reason;
  final String category;
  final String vegetarianStatus;
  final String veganStatus;
  final String? allergenInfo;
  final String? source; // 'local_db' | 'cache' | 'ai' — analysis source

  IngredientItem({
    required this.name,
    required this.normalizedName,
    required this.status,
    required this.reason,
    required this.category,
    this.vegetarianStatus = 'YES',
    this.veganStatus = 'YES',
    this.allergenInfo,
    this.source,
  });

  factory IngredientItem.fromJson(Map<String, dynamic> json) {
    return IngredientItem(
      name: json['name'] ?? '',
      normalizedName: json['normalized_name'] ?? json['name'] ?? '',
      status: (json['status'] ?? 'GOOD').toString().toUpperCase(),
      reason: json['reason'] ?? '',
      category: json['category'] ?? 'General',
      vegetarianStatus: json['vegetarian_status'] ?? 'YES',
      veganStatus: json['vegan_status'] ?? 'YES',
      allergenInfo: json['allergen_info'],
      source: json['source'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'normalized_name': normalizedName,
      'status': status,
      'reason': reason,
      'category': category,
      'vegetarian_status': vegetarianStatus,
      'vegan_status': veganStatus,
      'allergen_info': allergenInfo,
      'source': source,
    };
  }

  Color get statusColor {
    switch (status) {
      case 'AVOID':
        return AppColors.statusAvoid;
      case 'CAUTION':
        return AppColors.statusCaution;
      case 'GOOD':
      default:
        return AppColors.statusGood;
    }
  }

  Color get statusBgColor {
    switch (status) {
      case 'AVOID':
        return AppColors.statusAvoidBg;
      case 'CAUTION':
        return AppColors.statusCautionBg;
      case 'GOOD':
      default:
        return AppColors.statusGoodBg;
    }
  }

  String get statusEmoji {
    switch (status) {
      case 'AVOID':
        return '🔴';
      case 'CAUTION':
        return '🟡';
      case 'GOOD':
      default:
        return '🟢';
    }
  }
}

/// A single line item in the score breakdown (deduction or bonus).
class ScoreBreakdownItem {
  final String label;
  final int points;

  const ScoreBreakdownItem({required this.label, required this.points});

  factory ScoreBreakdownItem.fromJson(Map<String, dynamic> json) {
    return ScoreBreakdownItem(
      label: json['label'] ?? '',
      points: (json['points'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Transparent scoring breakdown returned by the backend.
class ScoreBreakdown {
  final int baseScore;
  final List<ScoreBreakdownItem> deductions;
  final List<ScoreBreakdownItem> bonuses;
  final int finalScore;
  final int goodCount;
  final int cautionCount;
  final int avoidCount;
  final bool nutritionIntegrated;
  final String assessmentType;
  final String assessmentLabel;
  final String disclaimer;

  const ScoreBreakdown({
    this.baseScore = 100,
    this.deductions = const [],
    this.bonuses = const [],
    required this.finalScore,
    this.goodCount = 0,
    this.cautionCount = 0,
    this.avoidCount = 0,
    this.nutritionIntegrated = false,
    this.assessmentType = 'FULL_NUTRITIONAL_AND_INGREDIENT',
    this.assessmentLabel = 'Verified Ingredients & Nutrition Facts',
    this.disclaimer = '',
  });

  factory ScoreBreakdown.fromJson(Map<String, dynamic> json) {
    return ScoreBreakdown(
      baseScore: (json['base_score'] as num?)?.toInt() ?? 100,
      deductions: (json['deductions'] as List<dynamic>?)
              ?.map((e) => ScoreBreakdownItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      bonuses: (json['bonuses'] as List<dynamic>?)
              ?.map((e) => ScoreBreakdownItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      finalScore: (json['final_score'] as num?)?.toInt() ?? 0,
      goodCount: (json['good_count'] as num?)?.toInt() ?? 0,
      cautionCount: (json['caution_count'] as num?)?.toInt() ?? 0,
      avoidCount: (json['avoid_count'] as num?)?.toInt() ?? 0,
      nutritionIntegrated: json['nutrition_integrated'] as bool? ?? false,
      assessmentType: json['assessment_type']?.toString() ?? 'FULL_NUTRITIONAL_AND_INGREDIENT',
      assessmentLabel: json['assessment_label']?.toString() ?? 'Verified Ingredients & Nutrition Facts',
      disclaimer: json['disclaimer']?.toString() ?? '',
    );
  }
}
