import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../models/scan_result_model.dart';
import '../../widgets/score_indicator.dart';
import '../../widgets/status_badge.dart';
import '../../widgets/ingredient_card.dart';
import '../../widgets/disclaimer_banner.dart';
import 'ingredient_detail_sheet.dart';

class ResultScreen extends StatelessWidget {
  final ScanResult result;

  const ResultScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Product Analysis'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Top Status Hero Banner
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 20),
              decoration: BoxDecoration(
                color: result.statusBgColor,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: result.statusColor.withValues(alpha: 0.3),
                  width: 1.5,
                ),
              ),
              child: Column(
                children: [
                  StatusBadge(status: result.overallStatus, isLarge: true),
                  const SizedBox(height: 16),
                  ScoreIndicator(
                    score: result.score,
                    status: result.overallStatus,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    result.summary,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary.withValues(alpha: 0.85),
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Key Highlights & Warnings Section
            if (result.warnings.isNotEmpty) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Key Findings",
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 10),
                    ...result.warnings.map(
                      (w) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              w.startsWith("✓") ? "✓" : "⚠",
                              style: TextStyle(
                                color: w.startsWith("✓")
                                    ? AppColors.statusGood
                                    : (w.contains("avoid")
                                        ? AppColors.statusAvoid
                                        : AppColors.statusCaution),
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                w.replaceAll(RegExp(r'^[✓⚠]\s*'), ''),
                                style: const TextStyle(
                                  fontSize: 13,
                                  color: AppColors.textPrimary,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
            ],

            // Ingredients Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  "Ingredients",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  "${result.ingredients.length} items detected",
                  style: const TextStyle(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Ingredients List
            ...result.ingredients.map(
              (ing) => IngredientCard(
                ingredient: ing,
                onTap: () => IngredientDetailSheet.show(context, ing),
              ),
            ),
            const SizedBox(height: 24),

            // Action Buttons
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                icon: const Icon(Icons.qr_code_scanner_rounded, size: 20),
                label: const Text("Scan Another Product"),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ),
            const SizedBox(height: 20),

            // Mandatory Medical & Safety Disclaimer
            const DisclaimerBanner(),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
