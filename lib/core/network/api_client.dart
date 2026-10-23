import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../constants/app_constants.dart';
import '../storage/local_storage.dart';
import '../../models/scan_result_model.dart';
import '../../models/user_profile_model.dart';
import '../../models/ingredient_model.dart';

import '../utils/product_compatibility_checker.dart';

class FreeScansExhaustedException implements Exception {
  final String message;
  FreeScansExhaustedException(this.message);
  @override
  String toString() => message;
}

class IncompatibleProductException implements Exception {
  final String title;
  final String message;
  final List<String> reasons;

  IncompatibleProductException({
    this.title = ProductCompatibilityChecker.incompatibleTitle,
    this.message = ProductCompatibilityChecker.incompatibleMessage,
    this.reasons = const [],
  });

  @override
  String toString() => message;
}

class UnableToIdentifyException implements Exception {
  final String title;
  final String message;
  final List<String> reasons;

  UnableToIdentifyException({
    this.title = ProductCompatibilityChecker.unreadableTitle,
    this.message = ProductCompatibilityChecker.unreadableMessage,
    this.reasons = const [],
  });

  @override
  String toString() => message;
}

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
  Future<ScanResult> analyzeText(
    String ocrText, {
    String? productName,
    String? productCategory,
  }) async {
    try {
      final Map<String, dynamic> body = {
        'ocr_text': ocrText,
      };
      if (productName != null && productName.trim().isNotEmpty) {
        body['product_name'] = productName.trim();
      }
      if (productCategory != null && productCategory.trim().isNotEmpty) {
        body['product_category'] = productCategory.trim();
      }

      final response = await http
          .post(
            Uri.parse('$baseUrl/scan'),
            headers: await _getHeaders(),
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final result = ScanResult.fromJson(data);
        await LocalStorage.saveScanToHistory(result);
        await LocalStorage.incrementScansCount();
        return result;
      } else if (response.statusCode == 403 || response.statusCode == 402) {
        final err = jsonDecode(response.body);
        final detail = err['detail'];
        final msg = detail is Map
            ? (detail['message'] ?? 'You have used all 3 free scans.')
            : (detail?.toString() ?? 'You have used all 3 free scans.');
        throw FreeScansExhaustedException(msg);
      } else if (response.statusCode == 422) {
        final err = jsonDecode(response.body);
        final detail = err['detail'];
        if (detail is Map) {
          final errType = detail['error']?.toString();
          final title = detail['title']?.toString();
          final msg = detail['message']?.toString();
          final reasons = (detail['reasons'] as List<dynamic>?)
                  ?.map((e) => e.toString())
                  .toList() ??
              [];

          if (errType == 'INCOMPATIBLE_PRODUCT') {
            throw IncompatibleProductException(
              title: title ?? ProductCompatibilityChecker.incompatibleTitle,
              message: msg ?? ProductCompatibilityChecker.incompatibleMessage,
              reasons: reasons,
            );
          } else if (errType == 'UNABLE_TO_IDENTIFY') {
            throw UnableToIdentifyException(
              title: title ?? ProductCompatibilityChecker.unreadableTitle,
              message: msg ?? ProductCompatibilityChecker.unreadableMessage,
              reasons: reasons,
            );
          }
        }
        throw UnableToIdentifyException(
          message: detail?.toString() ?? ProductCompatibilityChecker.unreadableMessage,
        );
      } else {
        final err = jsonDecode(response.body);
        throw Exception(err['detail'] ?? 'Analysis failed');
      }
    } on FreeScansExhaustedException {
      rethrow;
    } on IncompatibleProductException {
      rethrow;
    } on UnableToIdentifyException {
      rethrow;
    } catch (e) {
      // Offline fallback: Validate product compatibility first
      final compat = ProductCompatibilityChecker.evaluate(ocrText);
      if (compat.status == CompatibilityStatus.incompatible) {
        throw IncompatibleProductException(
          title: compat.title,
          message: compat.message,
          reasons: compat.reasons,
        );
      }
      if (compat.status == CompatibilityStatus.unreadable) {
        throw UnableToIdentifyException(
          title: compat.title,
          message: compat.message,
          reasons: compat.reasons,
        );
      }

      // Offline food analysis for verified food product only
      final fallbackResult = _generateOfflineAnalysis(
        ocrText,
        productName: productName,
        productCategory: productCategory,
      );
      await LocalStorage.saveScanToHistory(fallbackResult);
      await LocalStorage.incrementScansCount();
      return fallbackResult;
    }
  }

  // Razorpay Payments: Create Order
  Future<Map<String, dynamic>> createRazorpayOrder() async {
    final endpoint = '$baseUrl/payments/create-order';
    try {
      debugPrint('[ApiClient] POST $endpoint');
      final response = await http
          .post(
            Uri.parse(endpoint),
            headers: await _getHeaders(),
          )
          .timeout(const Duration(seconds: 12));

      debugPrint('[ApiClient] create-order status=${response.statusCode}: ${response.body}');
      final data = jsonDecode(response.body);
      if (response.statusCode == 200) {
        return {
          'success': true,
          'order_id': data['order_id'],
          'amount': data['amount'],
          'currency': data['currency'] ?? 'INR',
          'key_id': data['key_id'],
        };
      } else {
        final errorMsg = data is Map ? (data['detail'] ?? 'Could not create payment order') : 'Could not create payment order';
        return {
          'success': false,
          'error': errorMsg.toString(),
        };
      }
    } catch (e) {
      debugPrint('[ApiClient] create-order error: $e');
      return {
        'success': false,
        'error': 'Network connection error. Could not connect to $endpoint',
      };
    }
  }

  // Razorpay Payments: Verify Payment
  Future<Map<String, dynamic>> verifyRazorpayPayment({
    required String razorpayOrderId,
    required String razorpayPaymentId,
    required String razorpaySignature,
  }) async {
    final endpoint = '$baseUrl/payments/verify';
    try {
      debugPrint('[ApiClient] POST $endpoint');
      final response = await http
          .post(
            Uri.parse(endpoint),
            headers: await _getHeaders(),
            body: jsonEncode({
              'razorpay_order_id': razorpayOrderId,
              'razorpay_payment_id': razorpayPaymentId,
              'razorpay_signature': razorpaySignature,
            }),
          )
          .timeout(const Duration(seconds: 15));

      debugPrint('[ApiClient] verify status=${response.statusCode}: ${response.body}');
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['success'] == true) {
        await LocalStorage.setPremium(true);
        return {
          'success': true,
          'is_premium': true,
          'message': data['message'] ?? 'Premium unlocked successfully!',
        };
      } else {
        final errorMsg = data is Map ? (data['detail'] ?? 'Payment verification failed') : 'Payment verification failed';
        return {
          'success': false,
          'is_premium': false,
          'error': errorMsg.toString(),
        };
      }
    } catch (e) {
      debugPrint('[ApiClient] verify error: $e');
      return {
        'success': false,
        'is_premium': false,
        'error': 'Network error during payment verification. Please retry.',
      };
    }
  }

  // Razorpay Payments: Status
  Future<Map<String, dynamic>?> fetchPaymentStatus() async {
    final endpoint = '$baseUrl/payments/status';
    try {
      debugPrint('[ApiClient] GET $endpoint');
      final response = await http
          .get(
            Uri.parse(endpoint),
            headers: await _getHeaders(),
          )
          .timeout(const Duration(seconds: 8));

      debugPrint('[ApiClient] payments status response=${response.statusCode}: ${response.body}');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['is_premium'] == true) {
          await LocalStorage.setPremium(true);
        }
        return data;
      }
      return null;
    } catch (e) {
      debugPrint('[ApiClient] fetchPaymentStatus error: $e');
      return null;
    }
  }

  // Legacy Billing: Verify Purchase
  Future<Map<String, dynamic>> verifyPurchase({
    required String productId,
    required String purchaseToken,
    String? orderId,
  }) async {
    final endpoint = '$baseUrl/billing/verify';
    try {
      debugPrint('[ApiClient] POST $endpoint');
      final response = await http
          .post(
            Uri.parse(endpoint),
            headers: await _getHeaders(),
            body: jsonEncode({
              'product_id': productId,
              'purchase_token': purchaseToken,
              'order_id': orderId,
            }),
          )
          .timeout(const Duration(seconds: 12));

      debugPrint('[ApiClient] billing verify response=${response.statusCode}: ${response.body}');
      final data = jsonDecode(response.body);
      if (response.statusCode == 200 && data['success'] == true) {
        await LocalStorage.setPremium(true);
        return {'success': true, 'message': data['message']};
      } else {
        final errorMsg = data is Map ? (data['detail'] ?? 'Could not verify purchase') : 'Could not verify purchase';
        return {'success': false, 'error': errorMsg.toString()};
      }
    } catch (e) {
      debugPrint('[ApiClient] verifyPurchase error: $e');
      return {'success': false, 'error': 'Network error during purchase verification'};
    }
  }

  // Legacy Billing: Status
  Future<Map<String, dynamic>?> fetchBillingStatus() async {
    final endpoint = '$baseUrl/billing/status';
    try {
      debugPrint('[ApiClient] GET $endpoint');
      final response = await http
          .get(
            Uri.parse(endpoint),
            headers: await _getHeaders(),
          )
          .timeout(const Duration(seconds: 8));

      debugPrint('[ApiClient] billing status response=${response.statusCode}: ${response.body}');
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['is_premium'] == true) {
          await LocalStorage.setPremium(true);
        }
        return data;
      }
      return null;
    } catch (e) {
      debugPrint('[ApiClient] fetchBillingStatus error: $e');
      return null;
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

  // History: Update purchase decision and/or custom product name
  Future<Map<String, dynamic>> updateScanDecisionOrName({
    required int scanId,
    String? customProductName,
    String? purchaseDecision,
  }) async {
    final endpoint = '$baseUrl/history/$scanId';
    try {
      final Map<String, dynamic> body = {};
      if (customProductName != null) {
        body['custom_product_name'] = customProductName.trim();
      }
      if (purchaseDecision != null) {
        body['purchase_decision'] = purchaseDecision.trim().toUpperCase();
      }

      final response = await http
          .patch(
            Uri.parse(endpoint),
            headers: await _getHeaders(),
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return {'success': true, 'data': data};
      } else {
        final data = jsonDecode(response.body);
        final errorMsg = data is Map ? (data['detail'] ?? 'Could not update scan') : 'Could not update scan';
        return {'success': false, 'error': errorMsg.toString()};
      }
    } catch (e) {
      debugPrint('[ApiClient] updateScanDecisionOrName error: $e');
      return {'success': false, 'error': e.toString()};
    }
  }

  // Offline intelligent food analysis fallback with universal extraction
  ScanResult _generateOfflineAnalysis(
    String ocrText, {
    String? productName,
    String? productCategory,
  }) {
    final Map<String, dynamic> nutritionFacts = {};

    // 1. Extract Nutrition Facts
    final energyMatch = RegExp(r'\benergy(?:\s*value)?\s*(?:\(kcal\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*(?:kcal)?\b', caseSensitive: false).firstMatch(ocrText) ??
        RegExp(r'\b([0-9]+(?:\.[0-9]+)?)\s*kcal\b', caseSensitive: false).firstMatch(ocrText);
    if (energyMatch != null) {
      nutritionFacts['energy_kcal'] = double.tryParse(energyMatch.group(1) ?? '') ?? 0.0;
    }

    final proteinMatch = RegExp(r'\bprotein\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b', caseSensitive: false).firstMatch(ocrText);
    if (proteinMatch != null) {
      nutritionFacts['protein_g'] = double.tryParse(proteinMatch.group(1) ?? '') ?? 0.0;
    }

    final carbMatch = RegExp(r'\b(?:carbohydrates?|total\s*carbohydrates?|carbs?)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b', caseSensitive: false).firstMatch(ocrText);
    if (carbMatch != null) {
      nutritionFacts['carbohydrates_g'] = double.tryParse(carbMatch.group(1) ?? '') ?? 0.0;
    }

    final sugarMatch = RegExp(r'\b(?:total\s*sugars?|sugars?)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b', caseSensitive: false).firstMatch(ocrText);
    if (sugarMatch != null) {
      nutritionFacts['total_sugars_g'] = double.tryParse(sugarMatch.group(1) ?? '') ?? 0.0;
    }

    final fatMatch = RegExp(r'\b(?:total\s*fat|fat)\s*(?:\(g\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*g?\b', caseSensitive: false).firstMatch(ocrText);
    if (fatMatch != null) {
      nutritionFacts['total_fat_g'] = double.tryParse(fatMatch.group(1) ?? '') ?? 0.0;
    }

    final sodiumMatch = RegExp(r'\bsodium\s*(?:\(mg\))?[:\-\s]*([0-9]+(?:\.[0-9]+)?)\s*mg?\b', caseSensitive: false).firstMatch(ocrText);
    if (sodiumMatch != null) {
      nutritionFacts['sodium_mg'] = double.tryParse(sodiumMatch.group(1) ?? '') ?? 0.0;
    }

    // 2. Isolate Ingredient Section
    String textToSearch = ocrText;
    final headerMatch = RegExp(r'\b(?:ingredients|ingredients\s*used|ingredients\s*list|composition|contents)\s*[:\-\s]', caseSensitive: false).firstMatch(textToSearch);
    if (headerMatch != null) {
      textToSearch = textToSearch.substring(headerMatch.end);
    } else {
      final hasAdditives = RegExp(r'\b(?:ins|e)\s*\d{3,4}\b', caseSensitive: false).hasMatch(textToSearch);
      final commaCount = ','.allMatches(textToSearch).length;
      if (!hasAdditives && commaCount < 3) {
        throw UnableToIdentifyException(
          title: "Unable to Identify Ingredients",
          message: "No ingredient list was detected on this label. Please scan the 'Ingredients' section directly.",
        );
      }
    }

    // Cutoff at allergens, manufacturing, or packaging boilerplate
    final cutoffMatch = RegExp(
      r'\b(?:allergen\s+(?:advice|declaration|information)|contains\s*[:\-\s]|may\s+contain|manufactured\s+by|mfd|marketed\s+by|fssai|lic\.?\s*no|best\s+before|use\s+by|net\s*wt|mrp|nutrition)\b',
      caseSensitive: false,
    ).firstMatch(textToSearch);
    if (cutoffMatch != null && cutoffMatch.start > 0) {
      textToSearch = textToSearch.substring(0, cutoffMatch.start);
    }

    // 3. Parenthesis-aware Tokenizer
    final List<String> rawTokens = [];
    final StringBuffer currentToken = StringBuffer();
    int parenDepth = 0;

    for (int i = 0; i < textToSearch.length; i++) {
      final char = textToSearch[i];
      if (char == '(') {
        parenDepth++;
        currentToken.write(char);
      } else if (char == ')') {
        if (parenDepth > 0) parenDepth--;
        currentToken.write(char);
      } else if ((char == ',' || char == ';' || char == '•' || char == '\n' || char == '|') && parenDepth == 0) {
        final t = currentToken.toString().trim();
        if (t.isNotEmpty) rawTokens.add(t);
        currentToken.clear();
      } else {
        currentToken.write(char);
      }
    }
    final lastT = currentToken.toString().trim();
    if (lastT.isNotEmpty) rawTokens.add(lastT);

    // 4. Token Filtering
    final List<IngredientItem> items = [];
    int avoidCount = 0;
    int cautionCount = 0;

    final brandBlacklist = {
      'britannia', 'parle', 'nestle', 'cadbury', 'mondelez', 'lays', "lay's",
      'haldiram', 'haldirams', 'itc', 'sunfeast', 'oreo', 'kellogg', "kellogg's",
      'maggi', 'good day', 'thums up', 'coca-cola', 'pepsi', 'amul'
    };

    final headingBlacklist = {
      'biscuits', 'cookies', 'crackers', 'chips', 'potato chips', 'chocolate',
      'milk chocolate', 'soft drink', 'tomato ketchup', 'sauce'
    };

    for (final raw in rawTokens) {
      String cleaned = raw.replaceAll(RegExp(r'^[\s\d\.\-\*\•\:\,\;\|\~]+|[\s\.\,\;\:\-\*\|\~]+$'), '').trim();
      cleaned = cleaned.replaceAll(RegExp(r'^contains\s+(?:added\s+)?', caseSensitive: false), '').trim();
      final l = cleaned.toLowerCase();

      if (cleaned.length < 2 || !RegExp(r'[a-zA-Z]').hasMatch(cleaned)) continue;
      if (brandBlacklist.contains(l)) continue;
      if (headingBlacklist.contains(l)) continue;
      if (RegExp(r'^(?:energy|protein|fat|carbohydrate|sugars?|sodium|fssai|lic|net\s*wt|mrp|best\s*before)\b', caseSensitive: false).hasMatch(l)) continue;
      if (RegExp(r'^(?:100\%\s*(?:veg|vegetarian|real|natural|pure|whole\s*grain)|no\s*(?:added\s*preservatives|artificial\s*colours?|preservatives|trans\s*fat)|zero\s*(?:trans\s*fat|cholesterol|sugar|calories)|(?:high|rich\s*in)\s*(?:protein|fiber|fibre|iron|calcium)|serving\s*suggestion)$', caseSensitive: false).hasMatch(l)) continue;

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
        name: cleaned,
        normalizedName: cleaned,
        status: status,
        reason: reason,
        category: cat,
      ));
    }

    if (items.isEmpty) {
      throw UnableToIdentifyException(
        title: "Unable to Identify Ingredients",
        message: "No ingredient list was detected on this label. Please scan the 'Ingredients' section directly.",
      );
    }

    final score = (100 - (avoidCount * 28) - (cautionCount * 10)).clamp(15, 100);
    final overallStatus = avoidCount > 0
        ? 'AVOID'
        : (cautionCount >= 2 || score < 75 ? 'CAUTION' : 'GOOD');

    final warnings = <String>[];
    if (avoidCount > 0) warnings.add('⚠ Contains ingredients recommended to avoid');
    if (cautionCount > 0) warnings.add('⚠ Contains ingredients worth checking');
    if (warnings.isEmpty) warnings.add('✓ Clean formulation with no major additives detected');

    // Offline category and name resolution
    String resolvedCategory = productCategory ?? 'Food Product';
    String resolvedName = productName ?? 'Unknown Product';
    final lowerOcr = ocrText.toLowerCase();

    if (resolvedCategory == 'Food Product') {
      if (lowerOcr.contains('biscuit') || lowerOcr.contains('cookie') || (lowerOcr.contains('wheat flour') && lowerOcr.contains('palm oil'))) {
        resolvedCategory = 'Biscuits';
        if (resolvedName == 'Food Product' || resolvedName == 'Unknown Product') {
          resolvedName = 'Biscuits / Cookies';
        }
      } else if (lowerOcr.contains('carbonated') || lowerOcr.contains('cola') || lowerOcr.contains('soda')) {
        resolvedCategory = 'Soft Drink';
        if (resolvedName == 'Food Product' || resolvedName == 'Unknown Product') {
          resolvedName = 'Carbonated Soft Drink';
        }
      } else if (lowerOcr.contains('chip') || lowerOcr.contains('potato') || lowerOcr.contains('namkeen')) {
        resolvedCategory = 'Chips & Snacks';
        if (resolvedName == 'Food Product' || resolvedName == 'Unknown Product') {
          resolvedName = 'Savory Chips & Snacks';
        }
      } else if (lowerOcr.contains('cocoa') || lowerOcr.contains('chocolate')) {
        resolvedCategory = 'Chocolate';
        if (resolvedName == 'Food Product' || resolvedName == 'Unknown Product') {
          resolvedName = 'Chocolate Confectionery';
        }
      } else if (lowerOcr.contains('milk') || lowerOcr.contains('dairy')) {
        resolvedCategory = 'Milk Product';
        if (resolvedName == 'Food Product' || resolvedName == 'Unknown Product') {
          resolvedName = 'Milk Product';
        }
      }
    }

    if (resolvedName.isEmpty || resolvedName == 'Food Product') {
      resolvedName = 'Unknown Product';
    }

    return ScanResult(
      productName: resolvedName,
      productCategory: resolvedCategory,
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
      isCompatible: true,
      compatibilityStatus: 'COMPATIBLE',
      compatibilityMessage: 'Food product label verified.',
      nutritionFacts: nutritionFacts,
    );
  }
}
