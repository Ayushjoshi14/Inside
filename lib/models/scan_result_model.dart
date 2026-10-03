import 'package:flutter/material.dart';
import '../core/constants/app_colors.dart';
import 'ingredient_model.dart';

class ScanResult {
  final int? scanId;
  final String productName;
  final String overallStatus; // 'GOOD', 'CAUTION', 'AVOID'
  final int score; // 0 to 100
  final String summary;
  final List<IngredientItem> ingredients;
  final List<String> warnings;
  final List<String> recommendations;
  final String? rawOcrText;
  final DateTime createdAt;

  ScanResult({
    this.scanId,
    required this.productName,
    required this.overallStatus,
    required this.score,
    required this.summary,
    required this.ingredients,
    this.warnings = const [],
    this.recommendations = const [],
    this.rawOcrText,
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();

  factory ScanResult.fromJson(Map<String, dynamic> json) {
    return ScanResult(
      scanId: json['scan_id'],
      productName: json['product_name'] ?? 'Scanned Product',
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
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'scan_id': scanId,
      'product_name': productName,
      'overall_status': overallStatus,
      'score': score,
      'summary': summary,
      'ingredients': ingredients.map((e) => e.toJson()).toList(),
      'warnings': warnings,
      'recommendations': recommendations,
      'raw_ocr_text': rawOcrText,
      'created_at': createdAt.toIso8601String(),
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
