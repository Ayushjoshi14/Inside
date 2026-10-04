import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/app_constants.dart';
import '../../services/auth_service.dart';
import '../../services/billing_service.dart';

class PremiumPaywallScreen extends StatefulWidget {
  const PremiumPaywallScreen({super.key});

  @override
  State<PremiumPaywallScreen> createState() => _PremiumPaywallScreenState();
}

class _PremiumPaywallScreenState extends State<PremiumPaywallScreen> {
  late Razorpay _razorpay;
  bool _isLoading = false;
  String? _pendingOrderId;

  @override
  void initState() {
    super.initState();
    _razorpay = Razorpay();
    _razorpay.on(Razorpay.EVENT_PAYMENT_SUCCESS, _handlePaymentSuccess);
    _razorpay.on(Razorpay.EVENT_PAYMENT_ERROR, _handlePaymentError);
    _razorpay.on(Razorpay.EVENT_EXTERNAL_WALLET, _handleExternalWallet);
  }

  @override
  void dispose() {
    _razorpay.clear();
    super.dispose();
  }

  void _onUnlockPremium() async {
    setState(() => _isLoading = true);
    final billing = Provider.of<BillingService>(context, listen: false);
    final auth = Provider.of<AuthService>(context, listen: false);
    final profile = auth.profile;

    final orderData = await billing.createOrder();
    if (!mounted) return;

    if (orderData == null) {
      setState(() => _isLoading = false);
      final msg = billing.errorMessage ?? "Could not initiate payment order.";
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg), backgroundColor: AppColors.statusAvoid),
      );
      return;
    }

    _pendingOrderId = orderData['order_id'];

    // Construct clean prefill map (avoid empty contact/email fields that can cause validation issues in Android SDK)
    final Map<String, dynamic> prefill = {};
    if (profile?.name != null && profile!.name.trim().isNotEmpty) {
      prefill['name'] = profile.name.trim();
    }
    if (profile?.email != null && profile!.email.trim().isNotEmpty) {
      prefill['email'] = profile.email.trim();
    }

    // Razorpay Standard Checkout Options for Flutter Android
    final options = <String, dynamic>{
      'key': orderData['key_id'],
      'amount': orderData['amount'], // in paise: 19900 = ₹199
      'currency': orderData['currency'] ?? 'INR',
      'name': 'Inside',
      'description': 'Inside Premium — Lifetime',
      'order_id': orderData['order_id'],
      'timeout': 180, // in seconds (3 minutes)
      'theme': {
        'color': '#16A34A', // Matches AppColors.primary
      },
      'retry': {
        'enabled': true,
        'max_count': 1,
      },
      'send_sms_hash': true,
      'external': {
        'wallets': ['paytm']
      }
    };

    if (prefill.isNotEmpty) {
      options['prefill'] = prefill;
    }

    debugPrint('[Razorpay] Opening Checkout with options: $options');

    try {
      _razorpay.open(options);
    } catch (e) {
      debugPrint('[Razorpay] Error calling _razorpay.open(): $e');
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to open Razorpay Checkout: $e'),
          backgroundColor: AppColors.statusAvoid,
        ),
      );
    }
  }

  void _handlePaymentSuccess(PaymentSuccessResponse response) async {
    debugPrint('[Razorpay] Payment SUCCESS received: orderId=${response.orderId}, paymentId=${response.paymentId}, signature=${response.signature}');
    final billing = Provider.of<BillingService>(context, listen: false);

    final orderId = response.orderId ?? _pendingOrderId ?? '';
    final paymentId = response.paymentId ?? '';
    final signature = response.signature ?? '';

    final success = await billing.verifyPayment(
      razorpayOrderId: orderId,
      razorpayPaymentId: paymentId,
      razorpaySignature: signature,
    );

    if (!mounted) return;
    setState(() => _isLoading = false);

    if (success) {
      _showSuccessDialog();
    } else {
      final msg = billing.errorMessage ?? "Payment verification failed.";
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(msg), backgroundColor: AppColors.statusAvoid),
      );
    }
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    debugPrint('==================== [RAZORPAY PAYMENT ERROR DEBUG] ====================');
    debugPrint('[Razorpay] Error Code: ${response.code}');
    debugPrint('[Razorpay] Error Message: ${response.message}');
    debugPrint('[Razorpay] Error Payload: ${response.error}');
    debugPrint('[Razorpay] Pending Order ID: $_pendingOrderId');
    debugPrint('========================================================================');

    if (!mounted) return;
    setState(() => _isLoading = false);

    final rawMessage = response.message ?? "No message provided";
    final errorCode = response.code?.toString() ?? "Unknown";
    final errorDetail = response.error?.toString() ?? "";

    // Show temporary debug dialog so all exact error information is immediately inspectable on screen
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: const [
            Icon(Icons.bug_report_rounded, color: AppColors.statusAvoid, size: 26),
            SizedBox(width: 8),
            Expanded(
              child: Text("Razorpay Debug Info", style: TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                "Razorpay Error: $rawMessage",
                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14, color: AppColors.textPrimary),
              ),
              const SizedBox(height: 8),
              Text(
                "Error Code: $errorCode",
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppColors.statusAvoid),
              ),
              if (_pendingOrderId != null) ...[
                const SizedBox(height: 6),
                Text(
                  "Order ID: $_pendingOrderId",
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
              ],
              if (errorDetail.isNotEmpty) ...[
                const SizedBox(height: 12),
                const Text("Raw Error Data:", style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12, color: AppColors.textSecondary)),
                const SizedBox(height: 4),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.textTertiary.withValues(alpha: 0.3)),
                  ),
                  child: SelectableText(
                    errorDetail,
                    style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: AppColors.textPrimary),
                  ),
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text("Close"),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              _onUnlockPremium();
            },
            child: const Text("Retry Payment"),
          ),
        ],
      ),
    );

    // Also display SnackBar with exact error message & code as requested
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("Razorpay Error: $rawMessage | Error Code: $errorCode"),
        backgroundColor: AppColors.statusAvoid,
        duration: const Duration(seconds: 8),
      ),
    );
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    debugPrint('[Razorpay] External Wallet selected: ${response.walletName}');
    if (!mounted) return;
    setState(() => _isLoading = false);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text("Redirecting to external wallet: ${response.walletName}")),
    );
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
      final msg = billing.errorMessage ?? "No active lifetime purchase found.";
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
          children: [
            const Icon(Icons.check_circle_rounded, color: AppColors.primary, size: 28),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                isRestore ? "Access Restored" : "Premium Activated",
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
              ),
            ),
          ],
        ),
        content: Text(
          isRestore
              ? "Your lifetime premium access has been verified and restored!"
              : "Thank you for unlocking Inside Lifetime Premium!\nUnlimited scans are now available.",
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
    final auth = Provider.of<AuthService>(context);
    final isPremium = auth.isPremium;

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
                color: isPremium ? AppColors.statusGoodBg : AppColors.primaryLight,
                shape: BoxShape.circle,
              ),
              child: Icon(
                isPremium ? Icons.verified_rounded : Icons.workspace_premium_rounded,
                color: isPremium ? AppColors.statusGood : AppColors.primaryDark,
                size: 38,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              isPremium ? "INSIDE PREMIUM" : AppConstants.premiumTitle,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: AppColors.textPrimary,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              isPremium ? "✓ Premium Active • Lifetime Access" : "One-time payment • Lifetime access",
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w500,
                color: isPremium ? AppColors.statusGood : AppColors.textSecondary,
              ),
            ),
            const SizedBox(height: 24),

            // Price Pill Banner
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
              decoration: BoxDecoration(
                color: isPremium ? AppColors.statusGoodBg : AppColors.primaryLight,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: (isPremium ? AppColors.statusGood : AppColors.primary).withValues(alpha: 0.3),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    isPremium ? "Active" : AppConstants.premiumPrice,
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: isPremium ? AppColors.statusGood : AppColors.primaryDark,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    "forever",
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: isPremium ? AppColors.statusGood : AppColors.primaryDark,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // Benefits List
            _buildBenefitRow(
              Icons.all_inclusive_rounded,
              isPremium ? "✓ Unlimited Scans" : "Unlimited Scans",
              "Never run out of ingredient analyses.",
            ),
            _buildBenefitRow(
              Icons.health_and_safety_outlined,
              isPremium ? "✓ Personalized Food Filter" : "Personalized Food Filter",
              "Automatic alerts matching your diet & allergens.",
            ),
            _buildBenefitRow(
              Icons.menu_book_outlined,
              isPremium ? "✓ Deep Food Science Explanations" : "Deep Food Science Explanations",
              "Detailed breakdowns of every additive & INS code.",
            ),
            _buildBenefitRow(
              Icons.history_toggle_off_rounded,
              isPremium ? "✓ Full Scan History" : "Full Scan History",
              "Search, review, and retain past analyses anytime.",
            ),
            _buildBenefitRow(
              Icons.workspace_premium_outlined,
              isPremium ? "✓ Lifetime Access" : "Lifetime Access",
              "No recurring subscriptions or renewals.",
            ),
            const SizedBox(height: 36),

            // Razorpay Checkout Button
            if (!isPremium)
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: _isLoading ? null : _onUnlockPremium,
                  child: _isLoading
                      ? const SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: const [
                            Icon(Icons.lock_open_rounded, size: 20),
                            SizedBox(width: 8),
                            Text("Unlock Premium — ₹199"),
                          ],
                        ),
                ),
              )
            else
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 14),
                decoration: BoxDecoration(
                  color: AppColors.statusGoodBg,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.statusGood.withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: const [
                    Icon(Icons.check_circle_rounded, color: AppColors.statusGood, size: 20),
                    SizedBox(width: 8),
                    Text(
                      "Lifetime Premium Active",
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: AppColors.statusGood,
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 12),

            // Restore / Sync Purchases
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

            // Razorpay notice
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: const [
                Icon(Icons.lock_outline_rounded, size: 14, color: AppColors.textTertiary),
                SizedBox(width: 6),
                Flexible(
                  child: Text(
                    "Processed securely via Razorpay (UPI, Cards, NetBanking)",
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 12, color: AppColors.textTertiary),
                  ),
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
