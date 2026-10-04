import 'dart:async';
import 'package:flutter/foundation.dart';
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

  /// Creates a Razorpay Order through the backend for ₹199 Lifetime Premium.
  Future<Map<String, dynamic>?> createOrder() async {
    _isPurchasing = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _apiClient.createRazorpayOrder();
      if (res['success'] == true) {
        _isPurchasing = false;
        notifyListeners();
        return res;
      } else {
        _errorMessage = res['error'] ?? 'Could not initiate Razorpay order.';
        _isPurchasing = false;
        notifyListeners();
        return null;
      }
    } catch (e) {
      _errorMessage = 'Network connection failed while creating order.';
      _isPurchasing = false;
      notifyListeners();
      return null;
    }
  }

  /// Verifies Razorpay payment signature with backend and activates Lifetime Premium.
  Future<bool> verifyPayment({
    required String razorpayOrderId,
    required String razorpayPaymentId,
    required String razorpaySignature,
  }) async {
    _isPurchasing = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final res = await _apiClient.verifyRazorpayPayment(
        razorpayOrderId: razorpayOrderId,
        razorpayPaymentId: razorpayPaymentId,
        razorpaySignature: razorpaySignature,
      );

      if (res['success'] == true && res['is_premium'] == true) {
        await _authService.unlockPremium();
        _isPurchasing = false;
        notifyListeners();
        return true;
      } else {
        _errorMessage = res['error'] ?? 'Payment verification failed.';
        _isPurchasing = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _errorMessage = 'Network error during payment verification.';
      _isPurchasing = false;
      notifyListeners();
      return false;
    }
  }

  /// Restores / Reconciles premium status with the backend.
  Future<bool> restorePurchases() async {
    _isPurchasing = true;
    _errorMessage = null;
    notifyListeners();

    try {
      // 1. Check local storage
      final isPrem = await LocalStorage.isPremium();
      if (isPrem) {
        await _authService.unlockPremium();
      }

      // 2. Query authoritative backend status (Razorpay & Google Play endpoints)
      final statusData = await _apiClient.fetchPaymentStatus();
      if (statusData != null && statusData['is_premium'] == true) {
        await _authService.unlockPremium();
        _isPurchasing = false;
        notifyListeners();
        return true;
      }

      final billingData = await _apiClient.fetchBillingStatus();
      if (billingData != null && billingData['is_premium'] == true) {
        await _authService.unlockPremium();
        _isPurchasing = false;
        notifyListeners();
        return true;
      }

      final profile = await _apiClient.fetchProfile();
      if (profile != null && profile.isPremium) {
        await _authService.unlockPremium();
        _isPurchasing = false;
        notifyListeners();
        return true;
      }

      _isPurchasing = false;
      _errorMessage = "No active Inside Lifetime Premium found for this account.";
      notifyListeners();
      return isPrem;
    } catch (e) {
      _isPurchasing = false;
      _errorMessage = "Failed to sync purchases with server. Please check your connection.";
      notifyListeners();
      return false;
    }
  }
}

