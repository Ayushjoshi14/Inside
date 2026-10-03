import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../models/ingredient_model.dart';
import '../../widgets/status_badge.dart';

class IngredientDetailSheet extends StatelessWidget {
  final IngredientItem ingredient;

  const IngredientDetailSheet({super.key, required this.ingredient});

  static void show(BuildContext context, IngredientItem ingredient) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => IngredientDetailSheet(ingredient: ingredient),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Drag handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.divider,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Header with status badge
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      ingredient.name,
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      ingredient.category,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              StatusBadge(status: ingredient.status, isLarge: true),
            ],
          ),
          const SizedBox(height: 20),
          const Divider(color: AppColors.border),
          const SizedBox(height: 16),

          // Explanation / Reasoning
          const Text(
            "What is it & Why?",
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            ingredient.reason.isNotEmpty ? ingredient.reason : "Standard food ingredient or additive.",
            style: const TextStyle(
              fontSize: 14,
              color: AppColors.textPrimary,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 20),

          // Dietary Tags
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              children: [
                _dietaryRow(
                  "Vegetarian",
                  ingredient.vegetarianStatus == "YES"
                      ? "Suitable for vegetarians"
                      : (ingredient.vegetarianStatus == "NO"
                          ? "Animal-derived source"
                          : "Source may vary (check origin)"),
                  ingredient.vegetarianStatus == "YES"
                      ? Icons.check_circle_outline
                      : (ingredient.vegetarianStatus == "NO"
                          ? Icons.highlight_off_rounded
                          : Icons.help_outline_rounded),
                  ingredient.vegetarianStatus == "YES"
                      ? AppColors.statusGood
                      : (ingredient.vegetarianStatus == "NO"
                          ? AppColors.statusAvoid
                          : AppColors.statusCaution),
                ),
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Divider(color: AppColors.border, height: 1),
                ),
                _dietaryRow(
                  "Vegan",
                  ingredient.veganStatus == "YES"
                      ? "Suitable for vegans"
                      : (ingredient.veganStatus == "NO"
                          ? "Contains animal or dairy products"
                          : "Source may vary (check manufacturer)"),
                  ingredient.veganStatus == "YES"
                      ? Icons.check_circle_outline
                      : (ingredient.veganStatus == "NO"
                          ? Icons.highlight_off_rounded
                          : Icons.help_outline_rounded),
                  ingredient.veganStatus == "YES"
                      ? AppColors.statusGood
                      : (ingredient.veganStatus == "NO"
                          ? AppColors.statusAvoid
                          : AppColors.statusCaution),
                ),
                if (ingredient.allergenInfo != null) ...[
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Divider(color: AppColors.border, height: 1),
                  ),
                  _dietaryRow(
                    "Allergen Note",
                    ingredient.allergenInfo!,
                    Icons.warning_amber_rounded,
                    AppColors.statusCaution,
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Dismiss Button
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.surfaceVariant,
                foregroundColor: AppColors.textPrimary,
              ),
              child: const Text("Close"),
            ),
          ),
        ],
      ),
    );
  }

  Widget _dietaryRow(String title, String detail, IconData icon, Color iconColor) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: iconColor, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                detail,
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
