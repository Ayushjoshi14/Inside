import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../../models/scan_result_model.dart';
import '../../models/user_profile_model.dart';

class LocalStorage {
  static const String _keyToken = 'auth_token';
  static const String _keyProfile = 'user_profile';
  static const String _keyIsPremium = 'is_premium';
  static const String _keyScansCount = 'scans_count';
  static const String _keyHistory = 'cached_history';
  static const String _keyFirstLaunch = 'is_first_launch';

  static Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  // Auth Token
  static Future<void> saveToken(String token) async {
    final prefs = await _prefs;
    await prefs.setString(_keyToken, token);
  }

  static Future<String?> getToken() async {
    final prefs = await _prefs;
    return prefs.getString(_keyToken);
  }

  static Future<void> clearToken() async {
    final prefs = await _prefs;
    await prefs.remove(_keyToken);
  }

  // First Launch
  static Future<bool> isFirstLaunch() async {
    final prefs = await _prefs;
    return prefs.getBool(_keyFirstLaunch) ?? true;
  }

  static Future<void> setFirstLaunchCompleted() async {
    final prefs = await _prefs;
    await prefs.setBool(_keyFirstLaunch, false);
  }

  // Profile
  static Future<void> saveProfile(UserProfile profile) async {
    final prefs = await _prefs;
    await prefs.setString(_keyProfile, jsonEncode(profile.toJson()));
    await prefs.setBool(_keyIsPremium, profile.isPremium);
    await prefs.setInt(_keyScansCount, profile.scansCount);
  }

  static Future<UserProfile?> getProfile() async {
    final prefs = await _prefs;
    final jsonStr = prefs.getString(_keyProfile);
    if (jsonStr == null) return null;
    try {
      return UserProfile.fromJson(jsonDecode(jsonStr));
    } catch (_) {
      return null;
    }
  }

  // Premium
  static Future<bool> isPremium() async {
    final prefs = await _prefs;
    return prefs.getBool(_keyIsPremium) ?? false;
  }

  static Future<void> setPremium(bool val) async {
    final prefs = await _prefs;
    await prefs.setBool(_keyIsPremium, val);
  }

  // Scans Count
  static Future<int> getScansCount() async {
    final prefs = await _prefs;
    return prefs.getInt(_keyScansCount) ?? 0;
  }

  static Future<void> incrementScansCount() async {
    final prefs = await _prefs;
    final count = await getScansCount();
    await prefs.setInt(_keyScansCount, count + 1);
  }

  // Local History Cache
  static Future<void> saveScanToHistory(ScanResult scan) async {
    final prefs = await _prefs;
    final list = await getCachedHistory();
    // Prepend new scan to top
    list.insert(0, scan);
    // Keep max 50 items locally
    if (list.length > 50) {
      list.removeLast();
    }
    final jsonList = list.map((e) => e.toJson()).toList();
    await prefs.setString(_keyHistory, jsonEncode(jsonList));
  }

  static Future<List<ScanResult>> getCachedHistory() async {
    final prefs = await _prefs;
    final jsonStr = prefs.getString(_keyHistory);
    if (jsonStr == null) return [];
    try {
      final List<dynamic> raw = jsonDecode(jsonStr);
      return raw.map((e) => ScanResult.fromJson(e)).toList();
    } catch (_) {
      return [];
    }
  }

  static Future<void> deleteScanFromHistory(int index) async {
    final prefs = await _prefs;
    final list = await getCachedHistory();
    if (index >= 0 && index < list.length) {
      list.removeAt(index);
      final jsonList = list.map((e) => e.toJson()).toList();
      await prefs.setString(_keyHistory, jsonEncode(jsonList));
    }
  }

  static Future<void> clearHistory() async {
    final prefs = await _prefs;
    await prefs.remove(_keyHistory);
  }

  static Future<void> clearAll() async {
    final prefs = await _prefs;
    await prefs.clear();
  }
}
