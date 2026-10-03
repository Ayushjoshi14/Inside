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

  IngredientItem({
    required this.name,
    required this.normalizedName,
    required this.status,
    required this.reason,
    required this.category,
    this.vegetarianStatus = 'YES',
    this.veganStatus = 'YES',
    this.allergenInfo,
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
