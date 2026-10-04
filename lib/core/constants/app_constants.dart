class AppConstants {
  static const String appName = 'Inside';
  static const String appTagline = "Know what's inside.";
  static const String premiumProductId = 'inside_premium_lifetime';
  static const String premiumPrice = '₹199';
  static const String premiumTitle = 'Inside Premium — Lifetime';

  // API Config:
  // For physical Android device testing over local Wi-Fi, use your Windows PC's IPv4 address:
  // e.g. 'http://192.168.0.104:8000'
  // (Run 'ipconfig' in Windows PowerShell to see your IPv4 address if your Wi-Fi changes).
  //
  // You can also pass custom URL at build/run time:
  // flutter run --dart-define=API_BASE_URL=http://192.168.0.104:8000
  static const String defaultApiUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.0.104:8000',
  );
  static const String fallbackLocalApiUrl = 'http://127.0.0.1:8000';

  // Free Tier
  static const int freeScanLimit = 3;

  // Disclaimer
  static const String medicalDisclaimer =
      "This analysis is for informational purposes only. Ingredient formulations "
      "and manufacturing processes may change. Always verify the physical product label. "
      "For serious allergies, intolerances, or medical conditions, consult a qualified "
      "healthcare professional or the manufacturer.";
}
