import 'package:flutter/material.dart';
import '../core/constants/app_colors.dart';
import 'ingredient_model.dart';

class ScanResult {
  final int? scanId;
  final String productName;
  final String productCategory;
  final String overallStatus; // 'GOOD', 'CAUTION', 'AVOID'
  final int score; // 0 to 100
  final String summary;
  final List<IngredientItem> ingredients;
  final List<String> warnings;
  final List<String> recommendations;
  final String? rawOcrText;
  final DateTime createdAt;
  final bool isCompatible;
  final String compatibilityStatus;
  final String? compatibilityMessage;
  final String? customProductName;
  final String? purchaseDecision;
  final Map<String, dynamic> nutritionFacts;
  // --- Phase 2 new fields ---
  final ScoreBreakdown? scoreBreakdown;
  final List<String> positiveFindings;

  ScanResult({
    this.scanId,
    required this.productName,
    this.productCategory = 'Food Product',
    required this.overallStatus,
    required this.score,
    required this.summary,
    required this.ingredients,
    this.warnings = const [],
    this.recommendations = const [],
    this.rawOcrText,
    DateTime? createdAt,
    this.isCompatible = true,
    this.compatibilityStatus = 'COMPATIBLE',
    this.compatibilityMessage,
    this.customProductName,
    this.purchaseDecision,
    this.nutritionFacts = const {},
    this.scoreBreakdown,
    this.positiveFindings = const [],
  }) : createdAt = createdAt ?? DateTime.now();

  String get displayName {
    if (customProductName != null && customProductName!.trim().isNotEmpty) {
      return customProductName!.trim();
    }
    return productName;
  }

  bool? get willBuy {
    if (purchaseDecision == 'YES') return true;
    if (purchaseDecision == 'NO') return false;
    return null;
  }

  String get assessmentLabel {
    if (scoreBreakdown != null && scoreBreakdown!.assessmentLabel.isNotEmpty) {
      return scoreBreakdown!.assessmentLabel;
    }
    return nutritionFacts.isNotEmpty
        ? 'Verified Ingredients & Nutrition Facts'
        : 'Ingredient-Based Assessment';
  }

  bool get isFullNutritionalAssessment {
    if (scoreBreakdown != null) {
      return scoreBreakdown!.assessmentType == 'FULL_NUTRITIONAL_AND_INGREDIENT';
    }
    return nutritionFacts.isNotEmpty;
  }

  ScanResult copyWith({
    int? scanId,
    String? productName,
    String? productCategory,
    String? overallStatus,
    int? score,
    String? summary,
    List<IngredientItem>? ingredients,
    List<String>? warnings,
    List<String>? recommendations,
    String? rawOcrText,
    DateTime? createdAt,
    bool? isCompatible,
    String? compatibilityStatus,
    String? compatibilityMessage,
    String? customProductName,
    String? purchaseDecision,
    Map<String, dynamic>? nutritionFacts,
    ScoreBreakdown? scoreBreakdown,
    List<String>? positiveFindings,
  }) {
    return ScanResult(
      scanId: scanId ?? this.scanId,
      productName: productName ?? this.productName,
      productCategory: productCategory ?? this.productCategory,
      overallStatus: overallStatus ?? this.overallStatus,
      score: score ?? this.score,
      summary: summary ?? this.summary,
      ingredients: ingredients ?? this.ingredients,
      warnings: warnings ?? this.warnings,
      recommendations: recommendations ?? this.recommendations,
      rawOcrText: rawOcrText ?? this.rawOcrText,
      createdAt: createdAt ?? this.createdAt,
      isCompatible: isCompatible ?? this.isCompatible,
      compatibilityStatus: compatibilityStatus ?? this.compatibilityStatus,
      compatibilityMessage: compatibilityMessage ?? this.compatibilityMessage,
      customProductName: customProductName ?? this.customProductName,
      purchaseDecision: purchaseDecision ?? this.purchaseDecision,
      nutritionFacts: nutritionFacts ?? this.nutritionFacts,
      scoreBreakdown: scoreBreakdown ?? this.scoreBreakdown,
      positiveFindings: positiveFindings ?? this.positiveFindings,
    );
  }

  factory ScanResult.fromJson(Map<String, dynamic> json) {
    return ScanResult(
      scanId: json['scan_id'],
      productName: json['product_name'] ?? 'Scanned Product',
      productCategory: json['product_category'] ?? json['productCategory'] ?? 'Food Product',
      overallStatus: (json['overall_status'] ?? 'GOOD').toString().toUpperCase(),
      score: json['score'] ?? 75,
      summary: json['summary'] ?? '',
      ingredients: (json['ingredients'] as List<dynamic>?)
              ?.map((e) => IngredientItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      warnings: (json['warnings'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      recommendations: (json['recommendations'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      rawOcrText: json['raw_ocr_text'],
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at']) ?? DateTime.now()
          : DateTime.now(),
      isCompatible: json['is_compatible'] ?? true,
      compatibilityStatus: json['compatibility_status'] ?? 'COMPATIBLE',
      compatibilityMessage: json['compatibility_message'],
      customProductName: json['custom_product_name'] ?? json['customProductName'],
      purchaseDecision: json['purchase_decision'] ?? json['purchaseDecision'],
      nutritionFacts: json['nutrition_facts'] is Map<String, dynamic>
          ? Map<String, dynamic>.from(json['nutrition_facts'])
          : (json['nutritionFacts'] is Map<String, dynamic>
              ? Map<String, dynamic>.from(json['nutritionFacts'])
              : const {}),
      scoreBreakdown: json['score_breakdown'] != null
          ? ScoreBreakdown.fromJson(json['score_breakdown'] as Map<String, dynamic>)
          : null,
      positiveFindings: (json['positive_findings'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'scan_id': scanId,
      'product_name': productName,
      'product_category': productCategory,
      'overall_status': overallStatus,
      'score': score,
      'summary': summary,
      'ingredients': ingredients.map((e) => e.toJson()).toList(),
      'warnings': warnings,
      'recommendations': recommendations,
      'raw_ocr_text': rawOcrText,
      'created_at': createdAt.toIso8601String(),
      'is_compatible': isCompatible,
      'compatibility_status': compatibilityStatus,
      'compatibility_message': compatibilityMessage,
      'custom_product_name': customProductName,
      'purchase_decision': purchaseDecision,
      'nutrition_facts': nutritionFacts,
      'score_breakdown': scoreBreakdown != null ? {
        'base_score': scoreBreakdown!.baseScore,
        'final_score': scoreBreakdown!.finalScore,
        'good_count': scoreBreakdown!.goodCount,
        'caution_count': scoreBreakdown!.cautionCount,
        'avoid_count': scoreBreakdown!.avoidCount,
        'nutrition_integrated': scoreBreakdown!.nutritionIntegrated,
        'disclaimer': scoreBreakdown!.disclaimer,
        'deductions': scoreBreakdown!.deductions.map((d) => {'label': d.label, 'points': d.points}).toList(),
        'bonuses': scoreBreakdown!.bonuses.map((b) => {'label': b.label, 'points': b.points}).toList(),
      } : null,
      'positive_findings': positiveFindings,
    };
  }

  Color get statusColor {
    switch (overallStatus) {
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
    switch (overallStatus) {
      case 'AVOID':
        return AppColors.statusAvoidBg;
      case 'CAUTION':
        return AppColors.statusCautionBg;
      case 'GOOD':
      default:
        return AppColors.statusGoodBg;
    }
  }

  String get statusBadgeText {
    switch (overallStatus) {
      case 'AVOID':
        return 'AVOID CONSUMING';
      case 'CAUTION':
        return 'CHECK INGREDIENTS';
      case 'GOOD':
      default:
        return 'GOOD TO CONSUME';
    }
  }

  String get statusEmoji {
    switch (overallStatus) {
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
