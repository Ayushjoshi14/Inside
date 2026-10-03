import 'package:flutter/material.dart';
import '../core/storage/local_storage.dart';
import '../core/network/api_client.dart';
import '../models/user_profile_model.dart';

class AuthService extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  UserProfile? _profile;
  bool _isLoading = false;
  bool _isAuthenticated = false;

  UserProfile? get profile => _profile;
  bool get isLoading => _isLoading;
  bool get isAuthenticated => _isAuthenticated;
  bool get isPremium => _profile?.isPremium ?? false;
  int get scansLeft => _profile?.scansLeft ?? 5;

  Future<void> init() async {
    _isLoading = true;
    notifyListeners();

    final token = await LocalStorage.getToken();
    _isAuthenticated = token != null && token.isNotEmpty;

    // Load cached profile or create default
    _profile = await LocalStorage.getProfile();
    if (_profile == null) {
      final isPrem = await LocalStorage.isPremium();
      final scans = await LocalStorage.getScansCount();
      _profile = UserProfile(
        userId: 1,
        email: 'user@insideapp.in',
        name: 'Friend',
        isPremium: isPrem,
        scansCount: scans,
        scansLeft: isPrem ? 999999 : (5 - scans).clamp(0, 5),
      );
      await LocalStorage.saveProfile(_profile!);
    }

    _isLoading = false;
    notifyListeners();

    // Refresh from remote if connected
    if (_isAuthenticated) {
      _refreshRemoteProfile();
    }
  }

  Future<void> _refreshRemoteProfile() async {
    final remote = await _apiClient.fetchProfile();
    if (remote != null) {
      _profile = remote;
      notifyListeners();
    }
  }

  Future<bool> register(String email, String password, String name) async {
    _isLoading = true;
    notifyListeners();

    final res = await _apiClient.register(email, password, name);
    _isLoading = false;

    if (res['success'] == true) {
      _isAuthenticated = true;
      _profile = UserProfile(
        userId: res['data']['user_id'] ?? 1,
        email: email,
        name: name,
        isPremium: res['data']['is_premium'] ?? false,
      );
      await LocalStorage.saveProfile(_profile!);
      notifyListeners();
      return true;
    }
    notifyListeners();
    return false;
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();

    final res = await _apiClient.login(email, password);
    _isLoading = false;

    if (res['success'] == true) {
      _isAuthenticated = true;
      _profile = UserProfile(
        userId: res['data']['user_id'] ?? 1,
        email: email,
        name: res['data']['name'] ?? 'Friend',
        isPremium: res['data']['is_premium'] ?? false,
      );
      await LocalStorage.saveProfile(_profile!);
      notifyListeners();
      return true;
    }
    notifyListeners();
    return false;
  }

  Future<void> updatePreferences({
    String? name,
    String? dietPreference,
    List<String>? avoidIngredients,
    List<String>? allergens,
  }) async {
    if (_profile == null) return;
    final updated = _profile!.copyWith(
      name: name,
      dietPreference: dietPreference,
      avoidIngredients: avoidIngredients,
      allergens: allergens,
    );
    _profile = updated;
    await LocalStorage.saveProfile(updated);
    notifyListeners();
    _apiClient.updateProfile(updated);
  }

  Future<void> unlockPremium() async {
    if (_profile == null) return;
    _profile = _profile!.copyWith(isPremium: true, scansLeft: 999999);
    await LocalStorage.setPremium(true);
    await LocalStorage.saveProfile(_profile!);
    notifyListeners();
  }

  Future<void> decrementScan() async {
    if (_profile == null) return;
    await LocalStorage.incrementScansCount();
    final newCount = _profile!.scansCount + 1;
    final newLeft = _profile!.isPremium ? 999999 : (5 - newCount).clamp(0, 5);
    _profile = _profile!.copyWith(scansCount: newCount, scansLeft: newLeft);
    await LocalStorage.saveProfile(_profile!);
    notifyListeners();
  }

  Future<void> deleteAccount() async {
    _isLoading = true;
    notifyListeners();
    await _apiClient.deleteAccount();
    _profile = null;
    _isAuthenticated = false;
    _isLoading = false;
    await init();
  }
}
