import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants/app_colors.dart';
import '../../services/auth_service.dart';

class SignUpScreen extends StatefulWidget {
  final bool redirectAfterLogin;
  const SignUpScreen({super.key, this.redirectAfterLogin = false});

  @override
  State<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends State<SignUpScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _confirmPassCtrl = TextEditingController();
  bool _passVisible = false;
  bool _confirmPassVisible = false;
  String? _errorMessage;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _passCtrl.dispose();
    _confirmPassCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _errorMessage = null);

    final auth = Provider.of<AuthService>(context, listen: false);
    final success = await auth.register(
      _emailCtrl.text.trim(),
      _passCtrl.text,
      _nameCtrl.text.trim().isEmpty ? 'Friend' : _nameCtrl.text.trim(),
    );

    if (!mounted) return;

    if (success) {
      if (widget.redirectAfterLogin) {
        Navigator.of(context).pop(true);
      } else {
        Navigator.of(context).pushNamedAndRemoveUntil('/home', (_) => false);
      }
    } else {
      setState(() =>
          _errorMessage = auth.lastError ?? 'Registration failed. Try again.');
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
                // Back button
                IconButton(
                  icon: const Icon(Icons.arrow_back_rounded),
                  onPressed: () => Navigator.of(context).pop(),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  color: AppColors.textPrimary,
                ),
                const SizedBox(height: 24),

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
                  'Create account',
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Save your scans and sync across sessions.',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 32),

                // Name field
                const Text('Name',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _nameCtrl,
                  textInputAction: TextInputAction.next,
                  textCapitalization: TextCapitalization.words,
                  decoration: const InputDecoration(
                    hintText: 'e.g. Alex',
                    prefixIcon: Icon(Icons.person_outline_rounded, size: 20),
                  ),
                ),
                const SizedBox(height: 20),

                // Email field
                const Text('Email',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary)),
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
                const Text('Password',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _passCtrl,
                  obscureText: !_passVisible,
                  textInputAction: TextInputAction.next,
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Password is required';
                    if (v.length < 6) return 'At least 6 characters';
                    return null;
                  },
                  decoration: InputDecoration(
                    hintText: 'Minimum 6 characters',
                    prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _passVisible
                            ? Icons.visibility_off_outlined
                            : Icons.visibility_outlined,
                        size: 20,
                        color: AppColors.textTertiary,
                      ),
                      onPressed: () =>
                          setState(() => _passVisible = !_passVisible),
                    ),
                  ),
                ),
                const SizedBox(height: 20),

                // Confirm password
                const Text('Confirm Password',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary)),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _confirmPassCtrl,
                  obscureText: !_confirmPassVisible,
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _submit(),
                  validator: (v) {
                    if (v == null || v.isEmpty) return 'Please confirm your password';
                    if (v != _passCtrl.text) return 'Passwords do not match';
                    return null;
                  },
                  decoration: InputDecoration(
                    hintText: 'Re-enter password',
                    prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _confirmPassVisible
                            ? Icons.visibility_off_outlined
                            : Icons.visibility_outlined,
                        size: 20,
                        color: AppColors.textTertiary,
                      ),
                      onPressed: () => setState(
                          () => _confirmPassVisible = !_confirmPassVisible),
                    ),
                  ),
                ),
                const SizedBox(height: 24),

                // Error
                if (_errorMessage != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 12),
                    decoration: BoxDecoration(
                      color: AppColors.statusAvoidBg,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color:
                              AppColors.statusAvoid.withValues(alpha: 0.3)),
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

                // Submit button
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
                            'Create Account',
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.w700),
                          ),
                  ),
                ),
                const SizedBox(height: 24),

                Center(
                  child: GestureDetector(
                    onTap: () => Navigator.of(context).pop(),
                    child: RichText(
                      text: const TextSpan(
                        style: TextStyle(
                            fontSize: 14, color: AppColors.textSecondary),
                        children: [
                          TextSpan(text: 'Already have an account? '),
                          TextSpan(
                            text: 'Sign In',
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
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
