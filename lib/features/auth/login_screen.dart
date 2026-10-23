import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../services/auth_service.dart';
import 'signup_screen.dart';
import 'forgot_password_screen.dart';

class LoginScreen extends StatefulWidget {
  /// If [redirectAfterLogin] is true, pop this screen on success.
  /// If false, replace the entire navigator stack with MainNavigationShell.
  final bool redirectAfterLogin;

  const LoginScreen({super.key, this.redirectAfterLogin = false});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _passwordVisible = false;
  String? _errorMessage;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _errorMessage = null);

    final auth = Provider.of<AuthService>(context, listen: false);
    final success = await auth.login(
      _emailCtrl.text.trim(),
      _passCtrl.text,
    );

    if (!mounted) return;

    if (success) {
      if (widget.redirectAfterLogin) {
        Navigator.of(context).pop(true);
      } else {
        // Replace full stack with home
        Navigator.of(context).pushNamedAndRemoveUntil('/home', (_) => false);
      }
    } else {
      setState(() => _errorMessage = auth.lastError ?? 'Incorrect email or password.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthService>(context);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 32),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Back button (only when redirectAfterLogin)
                if (widget.redirectAfterLogin) ...[
                  IconButton(
                    icon: const Icon(Icons.arrow_back_rounded),
                    onPressed: () => Navigator.of(context).pop(false),
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    color: AppColors.textPrimary,
                  ),
                  const SizedBox(height: 24),
                ],

                // Logo + App name
                Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: BorderRadius.circular(11),
                      ),
                      child: const Icon(Icons.qr_code_scanner_rounded,
                          color: Colors.white, size: 22),
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'Inside',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w800,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 36),

                const Text(
                  'Welcome back',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Sign in to access your scans and history.',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 32),

                // Email field
                const Text(
                  'Email',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  autocorrect: false,
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Email is required';
                    if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v.trim())) {
                      return 'Enter a valid email';
                    }
                    return null;
                  },
                  decoration: const InputDecoration(
                    hintText: 'you@example.com',
                    prefixIcon: Icon(Icons.mail_outline_rounded, size: 20),
                  ),
                ),
                const SizedBox(height: 20),

                // Password field
                const Text(
                  'Password',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _passCtrl,
                  obscureText: !_passwordVisible,
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _submit(),
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Password is required';
                    return null;
                  },
                  decoration: InputDecoration(
                    hintText: '••••••••',
                    prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _passwordVisible
                            ? Icons.visibility_off_outlined
                            : Icons.visibility_outlined,
                        size: 20,
                        color: AppColors.textTertiary,
                      ),
                      onPressed: () =>
                          setState(() => _passwordVisible = !_passwordVisible),
                    ),
                  ),
                ),
                const SizedBox(height: 10),

                // Forgot password
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                            builder: (_) => const ForgotPasswordScreen()),
                      );
                    },
                    child: const Text(
                      'Forgot password?',
                      style: TextStyle(
                        color: AppColors.primaryDark,
                        fontWeight: FontWeight.w600,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 4),

                // Error message
                if (_errorMessage != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppColors.statusAvoidBg,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: AppColors.statusAvoid.withValues(alpha: 0.3)),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.error_outline_rounded,
                            color: AppColors.statusAvoid, size: 18),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _errorMessage!,
                            style: const TextStyle(
                              color: AppColors.statusAvoid,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Sign In button
                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: FilledButton(
                    onPressed: auth.isLoading ? null : _submit,
                    child: auth.isLoading
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2.5,
                            ),
                          )
                        : const Text(
                            'Sign In',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                  ),
                ),
                const SizedBox(height: 24),

                // Navigate to Sign Up
                Center(
                  child: GestureDetector(
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                            builder: (_) => SignUpScreen(
                                redirectAfterLogin:
                                    widget.redirectAfterLogin)),
                      );
                    },
                    child: RichText(
                      text: const TextSpan(
                        style: TextStyle(
                            fontSize: 14, color: AppColors.textSecondary),
                        children: [
                          TextSpan(text: "Don't have an account? "),
                          TextSpan(
                            text: 'Sign Up',
                            style: TextStyle(
                              color: AppColors.primaryDark,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),

                // Continue as guest
                if (!widget.redirectAfterLogin) ...[
                  const SizedBox(height: 20),
                  Center(
                    child: TextButton(
                      onPressed: () {
                        Navigator.of(context)
                            .pushNamedAndRemoveUntil('/home', (_) => false);
                      },
                      child: const Text(
                        'Continue without signing in',
                        style: TextStyle(
                          color: AppColors.textSecondary,
                          fontWeight: FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ),
                ],
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
