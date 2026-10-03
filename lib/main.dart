import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'core/theme/app_theme.dart';
import 'core/storage/local_storage.dart';
import 'services/auth_service.dart';
import 'services/scanner_service.dart';
import 'services/billing_service.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/home/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Set Android status bar to clean transparent
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );

  // Initialize auth and cached storage
  final authService = AuthService();
  await authService.init();

  final isFirstLaunch = await LocalStorage.isFirstLaunch();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthService>.value(value: authService),
        ChangeNotifierProxyProvider<AuthService, ScannerService>(
          create: (ctx) => ScannerService(authService),
          update: (ctx, auth, previous) => previous ?? ScannerService(auth),
        ),
        ChangeNotifierProxyProvider<AuthService, BillingService>(
          create: (ctx) => BillingService(authService),
          update: (ctx, auth, previous) => previous ?? BillingService(auth),
        ),
      ],
      child: InsideApp(isFirstLaunch: isFirstLaunch),
    ),
  );
}

class InsideApp extends StatelessWidget {
  final bool isFirstLaunch;

  const InsideApp({super.key, required this.isFirstLaunch});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Inside',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: isFirstLaunch ? const OnboardingScreen() : const MainNavigationShell(),
    );
  }
}
