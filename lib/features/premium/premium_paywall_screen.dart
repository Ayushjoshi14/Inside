import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/app_constants.dart';
import '../../services/billing_service.dart';

class PremiumPaywallScreen extends StatefulWidget {
  const PremiumPaywallScreen({super.key});

  @override
  State<PremiumPaywallScreen> createState() => _PremiumPaywallScreenState();
}

class _PremiumPaywallScreenState extends State<PremiumPaywallScreen> {
  bool _isLoading = false;

  void _onPurchase() async {
    setState(() => _isLoading = true);
    final billing = Provider.of<BillingService>(context, listen: false);

    final success = await billing.purchaseLifetime();
    if (!mounted) return;
    setState(() => _isLoading = false);

    if (success) {
      _showSuccessDialog();
    } else {
      final msg = billing.errorMessage ?? "Purchase was not completed.";
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg), backgroundColor: AppColors.statusAvoid),
      );
    }
  }

  void _onRestore() async {
    setState(() => _isLoading = true);
    final billing = Provider.of<BillingService>(context, listen: false);

    final success = await billing.restorePurchases();
    if (!mounted) return;
    setState(() => _isLoading = false);

    if (success) {
      _showSuccessDialog(isRestore: true);
    } else {
      final msg = billing.errorMessage ?? "No past purchases found.";
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg)),
      );
    }
  }

  void _showSuccessDialog({bool isRestore = false}) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: const [
            Icon(Icons.check_circle_rounded, color: AppColors.primary, size: 28),
            SizedBox(width: 8),
            Text("Inside Premium", style: TextStyle(fontWeight: FontWeight.w700)),
          ],
        ),
        content: Text(
          isRestore
              ? "Your lifetime premium access has been verified and restored!"
              : "Thank you for unlocking Inside Lifetime Premium! Enjoy unlimited ingredient scans forever.",
          style: const TextStyle(fontSize: 14, color: AppColors.textPrimary, height: 1.4),
        ),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).pop();
            },
            child: const Text("Continue"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.close_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Crown badge
            Container(
              width: 68,
              height: 68,
              decoration: BoxDecoration(
                color: AppColors.primaryLight,
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.workspace_premium_rounded,
                color: AppColors.primaryDark,
                size: 38,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              AppConstants.premiumTitle,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              "One-time payment • Lifetime access",
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 24),

            // Price Pill Banner
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                color: AppColors.primaryLight,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: const [
                  Text(
                    AppConstants.premiumPrice,
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: AppColors.primaryDark,
                    ),
                  ),
                  SizedBox(width: 8),
                  Text(
                    "forever",
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: AppColors.primaryDark,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Benefits List
            _buildBenefitRow(Icons.all_inclusive_rounded, "Unlimited Scans", "Never run out of ingredient analyses."),
            _buildBenefitRow(Icons.health_and_safety_outlined, "Personalized Food Filter", "Automatic alerts matching your diet & allergens."),
            _buildBenefitRow(Icons.menu_book_outlined, "Deep Food Science Explanations", "Detailed breakdowns of every additive & INS code."),
            _buildBenefitRow(Icons.history_toggle_off_rounded, "Full Scan History", "Search, review, and retain past analyses anytime."),
            _buildBenefitRow(Icons.block_rounded, "100% Ad-Free Experience", "Fast, private, and distraction-free."),
            const SizedBox(height: 36),

            // Google Play Checkout Button
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _isLoading ? null : _onPurchase,
                child: _isLoading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: const [
                          Icon(Icons.shopping_bag_outlined, size: 20),
                          SizedBox(width: 8),
                          Text("Unlock for ₹199 with Google Play"),
                        ],
                      ),
              ),
            ),
            const SizedBox(height: 12),

            // Restore Purchases
            TextButton(
              onPressed: _isLoading ? null : _onRestore,
              child: const Text(
                "Restore Past Purchase",
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Google Play notice
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: const [
                Icon(Icons.lock_outline_rounded, size: 14, color: AppColors.textTertiary),
                SizedBox(width: 4),
                Text(
                  "Processed securely through Google Play Billing",
                  style: TextStyle(fontSize: 12, color: AppColors.textTertiary),
                ),
              ],
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _buildBenefitRow(IconData icon, String title, String subtitle) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: AppColors.primary, size: 20),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 13,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
