class AppConstants {
  static const String appName = 'Inside';
  static const String appTagline = "Know what's inside.";
  static const String premiumProductId = 'premium_lifetime';
  static const String premiumPrice = '₹199';
  static const String premiumTitle = 'Inside Premium — Lifetime';

  // API Config
  // 10.0.2.2 is the standard loopback IP to host machine from Android Emulator.
  // 127.0.0.1 for desktop/web or real device IP.
  static const String defaultApiUrl = 'http://10.0.2.2:8000';
  static const String fallbackLocalApiUrl = 'http://127.0.0.1:8000';

  // Free Tier
  static const int freeScanLimit = 5;

  // Disclaimer
  static const String medicalDisclaimer =
      "This analysis is for informational purposes only. Ingredient formulations "
      "and manufacturing processes may change. Always verify the physical product label. "
      "For serious allergies, intolerances, or medical conditions, consult a qualified "
      "healthcare professional or the manufacturer.";
}
