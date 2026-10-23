import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/network/api_client.dart';
import '../../core/storage/local_storage.dart';
import '../../models/scan_result_model.dart';
import '../../models/ingredient_model.dart';
import '../../services/auth_service.dart';
import '../../widgets/score_indicator.dart';
import '../../widgets/status_badge.dart';
import '../../widgets/ingredient_card.dart';
import '../../widgets/disclaimer_banner.dart';
import '../premium/premium_paywall_screen.dart';
import 'ingredient_detail_sheet.dart';

class ResultScreen extends StatefulWidget {
  final ScanResult result;

  const ResultScreen({super.key, required this.result});

  @override
  State<ResultScreen> createState() => _ResultScreenState();
}

class _ResultScreenState extends State<ResultScreen> {
  late ScanResult _currentResult;

  @override
  void initState() {
    super.initState();
    _currentResult = widget.result;
  }

  Future<void> _handleDecisionNo() async {
    final updated = _currentResult.copyWith(purchaseDecision: 'NO');
    setState(() {
      _currentResult = updated;
    });
    await LocalStorage.updateScanInHistory(updated);
    if (updated.scanId != null) {
      ApiClient().updateScanDecisionOrName(
        scanId: updated.scanId!,
        purchaseDecision: 'NO',
      );
    }
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Decision saved: Won't buy"),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  Future<void> _handleDecisionYes() async {
    await _openNamingDialog(isEditing: false);
  }

  Future<void> _openNamingDialog({bool isEditing = false}) async {
    final initialName = isEditing
        ? (_currentResult.customProductName ?? _currentResult.displayName)
        : (_currentResult.customProductName ?? '');
    final controller = TextEditingController(text: initialName);
    String? errorMessage;

    final savedName = await showDialog<String>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            title: Text(
              isEditing ? "Rename Product" : "Give this product a name",
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: controller,
                  autofocus: true,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: InputDecoration(
                    hintText: "e.g., My favourite biscuits",
                    errorText: errorMessage,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: const BorderSide(color: AppColors.primary, width: 2),
                    ),
                  ),
                  onChanged: (_) {
                    if (errorMessage != null) {
                      setDialogState(() => errorMessage = null);
                    }
                  },
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(null),
                child: const Text("Cancel", style: TextStyle(color: AppColors.textSecondary)),
              ),
              FilledButton(
                onPressed: () {
                  final trimmed = controller.text.trim();
                  if (trimmed.isEmpty) {
                    setDialogState(() {
                      errorMessage = "Please enter a product name";
                    });
                    return;
                  }
                  Navigator.of(ctx).pop(trimmed);
                },
                child: const Text("Save"),
              ),
            ],
          );
        },
      ),
    );

    if (savedName != null && savedName.trim().isNotEmpty) {
      final updated = _currentResult.copyWith(
        purchaseDecision: 'YES',
        customProductName: savedName.trim(),
      );
      setState(() {
        _currentResult = updated;
      });
      await LocalStorage.updateScanInHistory(updated);
      if (updated.scanId != null) {
        ApiClient().updateScanDecisionOrName(
          scanId: updated.scanId!,
          customProductName: savedName.trim(),
          purchaseDecision: 'YES',
        );
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(isEditing ? "Product name updated!" : "Product name saved!"),
            backgroundColor: AppColors.primaryDark,
            duration: const Duration(seconds: 2),
          ),
        );
      }
    }
  }

  Widget _buildPurchaseDecisionCard() {
    final decision = _currentResult.purchaseDecision;

    if (decision == 'YES') {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.statusGoodBg,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: AppColors.statusGood.withValues(alpha: 0.35),
            width: 1.2,
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.statusGood,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.check_circle_rounded, size: 14, color: Colors.white),
                  SizedBox(width: 4),
                  Text(
                    "Will Buy",
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                _currentResult.displayName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            TextButton.icon(
              onPressed: () => _openNamingDialog(isEditing: true),
              icon: const Icon(Icons.edit_outlined, size: 15, color: AppColors.primaryDark),
              label: const Text(
                "Edit",
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryDark,
                ),
              ),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
            ),
          ],
        ),
      );
    }

    if (decision == 'NO') {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.statusAvoidBg,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: AppColors.statusAvoid.withValues(alpha: 0.3),
                ),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.close_rounded, size: 14, color: AppColors.statusAvoid),
                  SizedBox(width: 4),
                  Text(
                    "Won't Buy",
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppColors.statusAvoid,
                    ),
                  ),
                ],
              ),
            ),
            const Spacer(),
            TextButton(
              onPressed: _handleDecisionYes,
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text(
                "Change to Yes",
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryDark,
                ),
              ),
            ),
          ],
        ),
      );
    }

    // Default: Not decided yet -> Ask "Will you buy this product?"
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
        boxShadow: [AppColors.cardShadow],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.shopping_bag_outlined, size: 18, color: AppColors.primary),
              SizedBox(width: 8),
              Text(
                "Will you buy this product?",
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _handleDecisionNo,
                  icon: const Icon(Icons.close_rounded, size: 16, color: AppColors.statusAvoid),
                  label: const Text(
                    "No",
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: AppColors.border),
                    padding: const EdgeInsets.symmetric(vertical: 11),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _handleDecisionYes,
                  icon: const Icon(Icons.check_rounded, size: 16),
                  label: const Text(
                    "Yes",
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.statusGood,
                    padding: const EdgeInsets.symmetric(vertical: 11),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildNutritionFactsCard() {
    final facts = _currentResult.nutritionFacts;
    if (facts.isEmpty) return const SizedBox.shrink();

    final perUnit = facts['per_unit']?.toString() ?? 'Per 100g';
    final items = <MapEntry<String, String>>[];

    if (facts.containsKey('energy_kcal')) {
      items.add(MapEntry('Energy', '${facts['energy_kcal']} kcal'));
    }
    if (facts.containsKey('protein_g')) {
      items.add(MapEntry('Protein', '${facts['protein_g']}g'));
    }
    if (facts.containsKey('carbohydrates_g')) {
      items.add(MapEntry('Carbs', '${facts['carbohydrates_g']}g'));
    }
    if (facts.containsKey('total_sugars_g')) {
      items.add(MapEntry('Sugars', '${facts['total_sugars_g']}g'));
    }
    if (facts.containsKey('added_sugars_g')) {
      items.add(MapEntry('Added Sugars', '${facts['added_sugars_g']}g'));
    }
    if (facts.containsKey('total_fat_g')) {
      items.add(MapEntry('Total Fat', '${facts['total_fat_g']}g'));
    }
    if (facts.containsKey('saturated_fat_g')) {
      items.add(MapEntry('Sat. Fat', '${facts['saturated_fat_g']}g'));
    }
    if (facts.containsKey('trans_fat_g')) {
      items.add(MapEntry('Trans Fat', '${facts['trans_fat_g']}g'));
    }
    if (facts.containsKey('sodium_mg')) {
      items.add(MapEntry('Sodium', '${facts['sodium_mg']}mg'));
    }

    if (items.isEmpty) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.table_chart_outlined, size: 18, color: AppColors.primary),
                  SizedBox(width: 8),
                  Text(
                    "Nutrition Facts",
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
              Text(
                perUnit,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: items.map((e) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.background,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      e.key,
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 1),
                    Text(
                      e.value,
                      style: const TextStyle(
                        fontSize: 13,
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  /// Positive Findings section — shown when backend returns wholesome highlights.
  Widget _buildPositiveFindingsCard(List<String> findings) {
    if (findings.isEmpty) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.statusGoodBg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppColors.statusGood.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.thumb_up_alt_outlined, size: 16, color: AppColors.statusGood),
              SizedBox(width: 8),
              Text(
                "Positive Findings",
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppColors.statusGood,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...findings.map(
            (f) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "✓",
                    style: TextStyle(
                      color: AppColors.statusGood,
                      fontWeight: FontWeight.w700,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      f,
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
    );
  }

  /// Score Breakdown card — shows transparent scoring logic with safety-first premium gating.
  Widget _buildScoreBreakdownCard(ScoreBreakdown breakdown) {
    bool isPremium = false;
    try {
      isPremium = Provider.of<AuthService>(context, listen: false).isPremium;
    } catch (_) {
      isPremium = false;
    }

    // Safety & Fairness: Critical hazard deductions (Avoid, Trans-fat, Allergen) are NEVER hidden
    final List<ScoreBreakdownItem> visibleDeductions;
    final int hiddenCount;
    final bool hasHiddenDeductions;

    if (isPremium || breakdown.deductions.length <= 2) {
      visibleDeductions = breakdown.deductions;
      hiddenCount = 0;
      hasHiddenDeductions = false;
    } else {
      // Free users: Critical safety factors are always visible
      final critical = breakdown.deductions.where((d) {
        final l = d.label.toLowerCase();
        return l.contains('avoid') || l.contains('trans fat') || l.contains('allergen');
      }).toList();

      final nonCritical = breakdown.deductions.where((d) => !critical.contains(d)).toList();

      // Ensure total visible is at least critical, with non-critical filling remaining quota
      final int allowedNonCritical = (2 - critical.length).clamp(0, 2);
      final visibleNonCritical = nonCritical.take(allowedNonCritical).toList();

      visibleDeductions = [...critical, ...visibleNonCritical];
      hiddenCount = breakdown.deductions.length - visibleDeductions.length;
      hasHiddenDeductions = hiddenCount > 0;
    }

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.analytics_outlined, size: 18, color: AppColors.primary),
                  SizedBox(width: 8),
                  Text(
                    "Score Breakdown",
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
              if (isPremium)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppColors.statusGoodBg,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: const Text(
                    "Full Access",
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: AppColors.statusGood,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),

          // Base score row
          _breakdownRow(
            label: "Base score",
            points: breakdown.baseScore,
            isBase: true,
          ),

          // Deductions (gated safely for free users)
          ...visibleDeductions.map(
            (d) => _breakdownRow(
              label: d.label,
              points: d.points,
              isDeduction: true,
            ),
          ),

          // Hidden deductions upgrade teaser for free users
          if (hasHiddenDeductions)
            Container(
              margin: const EdgeInsets.only(top: 8, bottom: 4),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.primaryLight,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.2)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.lock_outline_rounded, size: 16, color: AppColors.primaryDark),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      "+$hiddenCount more score factor${hiddenCount > 1 ? 's' : ''}",
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primaryDark,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const PremiumPaywallScreen()),
                      );
                    },
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      backgroundColor: AppColors.primaryDark,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: const Text(
                      "Unlock",
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            ),

          // Bonuses
          ...breakdown.bonuses.map(
            (b) => _breakdownRow(
              label: b.label,
              points: b.points,
              isBonus: true,
            ),
          ),

          const Divider(height: 20, thickness: 1),

          // Final score row
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                "Final score",
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              Text(
                "${breakdown.finalScore}/100",
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  color: AppColors.primary,
                ),
              ),
            ],
          ),

          // Ingredient counts
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: [
              _countChip(
                label: "${breakdown.goodCount} Good",
                color: AppColors.statusGood,
                bgColor: AppColors.statusGoodBg,
              ),
              if (breakdown.cautionCount > 0)
                _countChip(
                  label: "${breakdown.cautionCount} Caution",
                  color: AppColors.statusCaution,
                  bgColor: AppColors.statusCautionBg,
                ),
              if (breakdown.avoidCount > 0)
                _countChip(
                  label: "${breakdown.avoidCount} Avoid",
                  color: AppColors.statusAvoid,
                  bgColor: AppColors.statusAvoidBg,
                ),
              if (breakdown.nutritionIntegrated)
                _countChip(
                  label: "Nutrition data used",
                  color: AppColors.primary,
                  bgColor: AppColors.primaryLight,
                ),
            ],
          ),

          // Disclaimer
          if (breakdown.disclaimer.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              breakdown.disclaimer,
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.textSecondary,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _breakdownRow({
    required String label,
    required int points,
    bool isBase = false,
    bool isDeduction = false,
    bool isBonus = false,
  }) {
    final Color pointColor = isBase
        ? AppColors.textSecondary
        : isDeduction
            ? AppColors.statusAvoid
            : AppColors.statusGood;
    final String sign = isBase
        ? ''
        : isDeduction
            ? '−'
            : '+';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 13,
                color: isBase ? AppColors.textSecondary : AppColors.textPrimary,
                fontWeight: isBase ? FontWeight.w500 : FontWeight.w500,
              ),
            ),
          ),
          Text(
            "$sign${points.abs()}",
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: pointColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _countChip({
    required String label,
    required Color color,
    required Color bgColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final result = _currentResult;
    final hasCustomName = result.customProductName != null &&
        result.customProductName!.trim().isNotEmpty;

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
                  if (result.displayName.isNotEmpty &&
                      result.displayName != 'Scanned Product' &&
                      result.displayName != 'Unknown Product') ...[
                    Text(
                      result.displayName,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    if (hasCustomName &&
                        result.productName.isNotEmpty &&
                        result.productName != result.displayName &&
                        result.productName != 'Scanned Product' &&
                        result.productName != 'Unknown Product') ...[
                      const SizedBox(height: 2),
                      Text(
                        "Original: ${result.productName}",
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                    const SizedBox(height: 2),
                    Text(
                      result.productCategory,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 4),
                  ],
                  Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          result.isFullNutritionalAssessment
                              ? Icons.verified_outlined
                              : Icons.article_outlined,
                          size: 13,
                          color: result.isFullNutritionalAssessment
                              ? AppColors.primary
                              : AppColors.textSecondary,
                        ),
                        const SizedBox(width: 5),
                        Text(
                          result.assessmentLabel,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: result.isFullNutritionalAssessment
                                ? AppColors.primaryDark
                                : AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 4),
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
            const SizedBox(height: 16),

            // Purchase Decision Section
            _buildPurchaseDecisionCard(),
            const SizedBox(height: 20),

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
              const SizedBox(height: 20),
            ],

            // ── Positive Findings (wholesome highlights from backend) ──
            _buildPositiveFindingsCard(result.positiveFindings),

            // ── Score Breakdown Card (with safety-first premium gating) ──
            if (result.scoreBreakdown != null)
              _buildScoreBreakdownCard(result.scoreBreakdown!),

            // Nutrition Facts Section (Separate from Ingredients)
            _buildNutritionFactsCard(),

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
