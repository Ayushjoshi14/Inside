import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../services/auth_service.dart';
import '../premium/premium_paywall_screen.dart';
import 'edit_profile_screen.dart';
import 'legal_screen.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  void _confirmDeleteAccount(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text("Delete Account?", style: TextStyle(fontWeight: FontWeight.w700)),
        content: const Text(
          "This will permanently delete your account, your profile preferences, and all saved scan history per privacy regulations. This action cannot be undone.",
          style: TextStyle(fontSize: 14, color: AppColors.textPrimary, height: 1.4),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text("Cancel", style: TextStyle(color: AppColors.textSecondary)),
          ),
          FilledButton(
            onPressed: () async {
              Navigator.of(ctx).pop();
              final auth = Provider.of<AuthService>(context, listen: false);
              await auth.deleteAccount();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text("Account and data deleted successfully.")),
                );
              }
            },
            style: FilledButton.styleFrom(backgroundColor: AppColors.statusAvoid),
            child: const Text("Delete Everything"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthService>(context);
    final profile = auth.profile;
    final isPremium = auth.isPremium;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Profile'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // User Card
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      Container(
                        width: 52,
                        height: 52,
                        decoration: BoxDecoration(
                          color: AppColors.primaryLight,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.person_outline_rounded, color: AppColors.primaryDark, size: 28),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  profile?.name ?? 'Friend',
                                  style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.textPrimary,
                                  ),
                                ),
                                if (isPremium) ...[
                                  const SizedBox(width: 6),
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                    decoration: BoxDecoration(
                                      color: AppColors.primary,
                                      borderRadius: BorderRadius.circular(10),
                                    ),
                                    child: const Text(
                                      "PRO",
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w800,
                                        color: Colors.white,
                                      ),
                                    ),
                                  ),
                                ],
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              isPremium ? "Lifetime Premium Member" : "${auth.scansLeft} free scans left",
                              style: TextStyle(
                                fontSize: 13,
                                color: isPremium ? AppColors.primaryDark : AppColors.textSecondary,
                                fontWeight: isPremium ? FontWeight.w600 : FontWeight.w400,
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.edit_outlined, color: AppColors.textSecondary),
                        onPressed: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(builder: (_) => const EditProfileScreen()),
                          );
                        },
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  const Divider(color: AppColors.border, height: 1),
                  const SizedBox(height: 12),
                  // Preference summaries
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _metricBadge("Diet", profile?.dietPreference == "NONE" ? "Standard" : (profile?.dietPreference ?? "Standard")),
                      _metricBadge("Avoiding", "${profile?.avoidIngredients.length ?? 0}"),
                      _metricBadge("Allergens", "${profile?.allergens.length ?? 0}"),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Premium Banner if not subscribed
            if (!isPremium) ...[
              InkWell(
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const PremiumPaywallScreen()),
                  );
                },
                borderRadius: BorderRadius.circular(16),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: AppColors.primaryLight,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.workspace_premium_rounded, color: AppColors.primaryDark, size: 28),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: const [
                            Text(
                              "Upgrade to Inside Premium",
                              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.primaryDark),
                            ),
                            SizedBox(height: 2),
                            Text(
                              "₹199 Lifetime • Unlimited Scans & No Ads",
                              style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
                            ),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right_rounded, color: AppColors.primaryDark),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
            ],

            // Settings Items List
            _settingsTile(
              icon: Icons.tune_rounded,
              title: "Manage Preferences",
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const EditProfileScreen()),
                );
              },
            ),
            _settingsTile(
              icon: Icons.workspace_premium_outlined,
              title: isPremium ? "Inside Premium (Active)" : "Inside Premium (₹199)",
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const PremiumPaywallScreen()),
                );
              },
            ),
            _settingsTile(
              icon: Icons.privacy_tip_outlined,
              title: "Privacy Policy",
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const LegalScreen(docType: LegalDocType.privacy)),
                );
              },
            ),
            _settingsTile(
              icon: Icons.description_outlined,
              title: "Terms & Conditions",
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const LegalScreen(docType: LegalDocType.terms)),
                );
              },
            ),
            _settingsTile(
              icon: Icons.currency_rupee_rounded,
              title: "Refund Policy",
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const LegalScreen(docType: LegalDocType.refund)),
                );
              },
            ),
            _settingsTile(
              icon: Icons.health_and_safety_outlined,
              title: "Safety & Medical Disclaimer",
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const LegalScreen(docType: LegalDocType.disclaimer)),
                );
              },
            ),
            _settingsTile(
              icon: Icons.info_outline_rounded,
              title: "About Inside",
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const LegalScreen(docType: LegalDocType.about)),
                );
              },
            ),
            const SizedBox(height: 8),
            _settingsTile(
              icon: Icons.delete_forever_outlined,
              title: "Delete Account",
              textColor: AppColors.statusAvoid,
              onTap: () => _confirmDeleteAccount(context),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _metricBadge(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
        ),
      ],
    );
  }

  Widget _settingsTile({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
    Color? textColor,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
        child: Row(
          children: [
            Icon(icon, size: 22, color: textColor ?? AppColors.textSecondary),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                title,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: textColor ?? AppColors.textPrimary,
                ),
              ),
            ),
            Icon(Icons.chevron_right_rounded, size: 20, color: AppColors.textTertiary),
          ],
        ),
      ),
    );
  }
}
