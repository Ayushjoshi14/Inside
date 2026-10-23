import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';

class ForgotPasswordScreen extends StatelessWidget {
  const ForgotPasswordScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('Forgot Password'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Icon
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  color: AppColors.primaryLight,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Icon(
                  Icons.mail_lock_outlined,
                  color: AppColors.primaryDark,
                  size: 30,
                ),
              ),
              const SizedBox(height: 24),

              const Text(
                'Password Reset',
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: 12),

              // Honest notice about email service
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.statusCautionBg,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                      color: AppColors.statusCaution.withValues(alpha: 0.4)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline_rounded,
                        color: AppColors.statusCaution, size: 20),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'Email-based password reset is not yet available — the email service has not been configured for this app.\n\n'
                        'If you\'ve forgotten your password, please create a new account using a different email address, or contact support.',
                        style: TextStyle(
                          fontSize: 14,
                          color: AppColors.textPrimary,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 32),

              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Go Back to Sign In'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
