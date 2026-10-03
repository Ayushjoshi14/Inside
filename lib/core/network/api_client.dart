import 'dart:convert';
import 'package:http/http.dart' as http;
import '../constants/app_constants.dart';
import '../storage/local_storage.dart';
import '../../models/scan_result_model.dart';
import '../../models/user_profile_model.dart';
import '../../models/ingredient_model.dart';

class ApiClient {
  String baseUrl = AppConstants.defaultApiUrl;

  ApiClient({String? customBaseUrl}) {
    if (customBaseUrl != null && customBaseUrl.isNotEmpty) {
      baseUrl = customBaseUrl;
    }
  }

  Future<Map<String, String>> _getHeaders({bool requireAuth = true}) async {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (requireAuth) {
      final token = await LocalStorage.getToken();
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    return headers;
  }

  // Auth: Register
  Future<Map<String, dynamic>> register(String email, String password, String name) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/register'),
            headers: await _getHeaders(requireAuth: false),
            body: jsonEncode({
              'email': email.trim(),
              'password': password,
              'name': name.trim(),
            }),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);
      if (response.statusCode == 200) {
        await LocalStorage.saveToken(data['access_token']);
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': data['detail'] ?? 'Registration failed'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Cannot connect to server. Running in local mode.'};
    }
  }

  // Auth: Login
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/auth/login'),
            headers: await _getHeaders(requireAuth: false),
            body: jsonEncode({
              'email': email.trim(),
              'password': password,
            }),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);
      if (response.statusCode == 200) {
        await LocalStorage.saveToken(data['access_token']);
        return {'success': true, 'data': data};
      } else {
        return {'success': false, 'error': data['detail'] ?? 'Login failed'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network connection error.'};
    }
  }

  // Profile: Get
  Future<UserProfile?> fetchProfile() async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/profile'),
            headers: await _getHeaders(),
          )
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final profile = UserProfile.fromJson(data);
        await LocalStorage.saveProfile(profile);
        return profile;
      }
      return await LocalStorage.getProfile();
    } catch (_) {
      return await LocalStorage.getProfile();
    }
  }

  // Profile: Update
  Future<bool> updateProfile(UserProfile profile) async {
    try {
      final response = await http
          .put(
            Uri.parse('$baseUrl/profile'),
            headers: await _getHeaders(),
            body: jsonEncode({
              'name': profile.name,
              'diet_preference': profile.dietPreference,
              'avoid_ingredients': profile.avoidIngredients,
              'allergens': profile.allergens,
            }),
          )
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        await LocalStorage.saveProfile(profile);
        return true;
      }
      return false;
    } catch (_) {
      await LocalStorage.saveProfile(profile);
      return true; // Saved locally
    }
  }

  // Profile: Delete Account
  Future<bool> deleteAccount() async {
    try {
      final response = await http
          .delete(
            Uri.parse('$baseUrl/account'),
            headers: await _getHeaders(),
          )
          .timeout(const Duration(seconds: 8));

      await LocalStorage.clearAll();
      return response.statusCode == 200;
    } catch (_) {
      await LocalStorage.clearAll();
      return true;
    }
  }

  // Scan & Analyze
  Future<ScanResult> analyzeText(String ocrText, {String productName = "Food Product"}) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/scan'),
            headers: await _getHeaders(),
            body: jsonEncode({
              'product_name': productName,
              'ocr_text': ocrText,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final result = ScanResult.fromJson(data);
        await LocalStorage.saveScanToHistory(result);
        await LocalStorage.incrementScansCount();
        return result;
      } else {
        final err = jsonDecode(response.body);
        throw Exception(err['detail'] ?? 'Analysis failed');
      }
    } catch (e) {
      // Offline fallback: Use client-side food science engine
      final fallbackResult = _generateOfflineAnalysis(ocrText, productName);
      await LocalStorage.saveScanToHistory(fallbackResult);
      await LocalStorage.incrementScansCount();
      return fallbackResult;
    }
  }

  // Billing: Verify Purchase
  Future<Map<String, dynamic>> verifyPurchase({
    required String productId,
    required String purchaseToken,
    String? orderId,
  }) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/billing/verify'),
            headers: await _getHeaders(),
            body: jsonEncode({
              'product_id': productId,
              'purchase_token': purchaseToken,
              'order_id': orderId,
            }),
          )
          .timeout(const Duration(seconds: 12));

      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['success'] == true) {
        await LocalStorage.setPremium(true);
        return {'success': true, 'message': data['message']};
      } else {
        return {'success': false, 'error': data['detail'] ?? 'Could not verify purchase'};
      }
    } catch (e) {
      return {'success': false, 'error': 'Network error during purchase verification'};
    }
  }

  // History: Get Remote
  Future<List<ScanResult>> fetchHistory() async {
    try {
      final response = await http
          .get(
            Uri.parse('$baseUrl/history'),
            headers: await _getHeaders(),
          )
          .timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        return await LocalStorage.getCachedHistory();
      }
      return await LocalStorage.getCachedHistory();
    } catch (_) {
      return await LocalStorage.getCachedHistory();
    }
  }

  // Offline intelligent food analysis fallback
  ScanResult _generateOfflineAnalysis(String ocrText, String productName) {
    final List<IngredientItem> items = [];
    int avoidCount = 0;
    int cautionCount = 0;

    final tokens = ocrText
        .replaceAll(RegExp(r'ingredients\s*:', caseSensitive: false), '')
        .split(RegExp(r'[,;•\n]'))
        .map((s) => s.trim())
        .where((s) => s.length > 1)
        .toList();

    for (final raw in tokens) {
      final l = raw.toLowerCase();
      String status = 'GOOD';
      String reason = 'Common food ingredient.';
      String cat = 'General';

      if (l.contains('palm oil') || l.contains('palmolein')) {
        status = 'CAUTION';
        reason = 'High in saturated fatty acids (~50% palmitic acid).';
        cat = 'Fat/oil';
        cautionCount++;
      } else if (l.contains('sugar') || l.contains('syrup') || l.contains('glucose') || l.contains('dextrose')) {
        status = 'CAUTION';
        reason = 'Added caloric sweetener with rapid glycemic response.';
        cat = 'Sugar';
        cautionCount++;
      } else if (l.contains('hydrogenated') || l.contains('trans fat')) {
        status = 'AVOID';
        reason = 'Trans-fatty acids with elevated cardiovascular health risk.';
        cat = 'Fat/oil';
        avoidCount++;
      } else if (l.contains('102') || l.contains('tartrazine') || l.contains('110') || l.contains('sunset yellow')) {
        status = 'AVOID';
        reason = 'Azo synthetic dye linked with hyperactivity and sensitivity.';
        cat = 'Artificial colour';
        avoidCount++;
      } else if (l.contains('322') || l.contains('lecithin')) {
        status = 'GOOD';
        reason = 'Natural emulsifier and source of choline.';
        cat = 'Emulsifier';
      } else if (l.contains('330') || l.contains('citric acid')) {
        status = 'GOOD';
        reason = 'Natural organic acidulant and preservative.';
        cat = 'Acidity regulator';
      } else if (l.contains('benzoate') || l.contains('211') || l.contains('sorbate') || l.contains('202')) {
        status = 'CAUTION';
        reason = 'Chemical preservative used to inhibit microbial spoilage.';
        cat = 'Preservative';
        cautionCount++;
      }

      items.add(IngredientItem(
        name: raw,
        normalizedName: raw,
        status: status,
        reason: reason,
        category: cat,
      ));
    }

    final score = (100 - (avoidCount * 28) - (cautionCount * 10)).clamp(15, 100);
    final overallStatus = avoidCount > 0
        ? 'AVOID'
        : (cautionCount >= 2 || score < 75 ? 'CAUTION' : 'GOOD');

    final warnings = <String>[];
    if (avoidCount > 0) warnings.add('⚠ Contains ingredients recommended to avoid');
    if (cautionCount > 0) warnings.add('⚠ Contains ingredients worth checking');
    if (warnings.isEmpty) warnings.add('✓ Clean formulation with no major additives detected');

    return ScanResult(
      productName: productName,
      overallStatus: overallStatus,
      score: score,
      summary: overallStatus == 'GOOD'
          ? 'Safe and clean ingredient profile.'
          : (overallStatus == 'CAUTION'
              ? 'Contains ingredients worth checking before frequent consumption.'
              : 'Contains ingredients flagged to avoid.'),
      ingredients: items,
      warnings: warnings,
      recommendations: [
        'Check product label for complete allergens and manufacturing details.',
      ],
      rawOcrText: ocrText,
    );
  }
}
