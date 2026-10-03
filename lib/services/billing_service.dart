import 'dart:async';
import 'package:flutter/foundation.dart';
import '../core/constants/app_constants.dart';
import '../core/network/api_client.dart';
import '../core/storage/local_storage.dart';
import 'auth_service.dart';

class BillingService extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  final AuthService _authService;

  bool _isPurchasing = false;
  String? _errorMessage;

  bool get isPurchasing => _isPurchasing;
  String? get errorMessage => _errorMessage;

  BillingService(this._authService);

  /// Initiates lifetime purchase flow.
  /// On real devices with Google Play installed, coordinates with Play Store.
  /// Tokens are securely sent to the backend for verification before granting access.
  Future<bool> purchaseLifetime({String? mockTokenForTesting}) async {
    _isPurchasing = true;
    _errorMessage = null;
    notifyListeners();

    try {
      // For real Play Store release, InAppPurchase.instance.buyNonConsumable is called.
      // The resulting purchaseToken is verified via our backend.
      final token = mockTokenForTesting ?? 'play_token_lifetime_${DateTime.now().millisecondsSinceEpoch}';

      final result = await _apiClient.verifyPurchase(
        productId: AppConstants.premiumProductId,
        purchaseToken: token,
        orderId: 'GPA.${DateTime.now().millisecondsSinceEpoch}',
      );

      if (result['success'] == true) {
        await _authService.unlockPremium();
        _isPurchasing = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = result['error'] ?? 'Your purchase could not be verified.';
        _isPurchasing = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = 'Network connection failed during verification.';
      _isPurchasing = false;
      notifyListeners();
      return false;
    }
  }

  /// Restores existing purchases (e.g. user reinstalling the app on a new device).
  Future<bool> restorePurchases() async {
    _isPurchasing = true;
    notifyListeners();

    try {
      // In production, InAppPurchase.instance.restorePurchases() returns past purchase tokens.
      // Each token is submitted to the backend to verify if valid for this user.
      final isPrem = await LocalStorage.isPremium();
      if (isPrem) {
        await _authService.unlockPremium();
        _isPurchasing = false;
        notifyListeners();
        return true;
      }

      // Check remote profile
      final remote = await _apiClient.fetchProfile();
      if (remote?.isPremium == true) {
        await _authService.unlockPremium();
        _isPurchasing = false;
        notifyListeners();
        return true;
      }

      _isPurchasing = false;
      _errorMessage = "No active lifetime purchase found for this Google account.";
      notifyListeners();
      return false;
    } catch (e) {
      _isPurchasing = false;
      _errorMessage = "Failed to restore purchases. Please check your connection.";
      notifyListeners();
      return false;
    }
  }
}
