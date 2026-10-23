import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:inside/models/scan_result_model.dart';
import 'package:inside/models/ingredient_model.dart';
import 'package:inside/core/storage/local_storage.dart';

void main() {
  group('ScanResult Purchase Decision & Custom Naming Tests', () {
    test('displayName returns customProductName when provided', () {
      final scan = ScanResult(
        productName: 'Original Biscuits 200g',
        customProductName: 'My favourite biscuits',
        overallStatus: 'GOOD',
        score: 88,
        summary: 'Clean ingredients.',
        ingredients: [],
      );

      expect(scan.displayName, 'My favourite biscuits');
      expect(scan.productName, 'Original Biscuits 200g');
    });

    test('displayName falls back to productName when customProductName is null or empty', () {
      final scanNull = ScanResult(
        productName: 'Original Biscuits 200g',
        customProductName: null,
        overallStatus: 'GOOD',
        score: 88,
        summary: 'Clean ingredients.',
        ingredients: [],
      );

      final scanEmpty = ScanResult(
        productName: 'Original Biscuits 200g',
        customProductName: '   ',
        overallStatus: 'GOOD',
        score: 88,
        summary: 'Clean ingredients.',
        ingredients: [],
      );

      expect(scanNull.displayName, 'Original Biscuits 200g');
      expect(scanEmpty.displayName, 'Original Biscuits 200g');
    });

    test('willBuy helper returns correct boolean or null', () {
      final scanYes = ScanResult(
        productName: 'Product A',
        purchaseDecision: 'YES',
        overallStatus: 'GOOD',
        score: 90,
        summary: '',
        ingredients: [],
      );

      final scanNo = ScanResult(
        productName: 'Product B',
        purchaseDecision: 'NO',
        overallStatus: 'AVOID',
        score: 30,
        summary: '',
        ingredients: [],
      );

      final scanUndecided = ScanResult(
        productName: 'Product C',
        purchaseDecision: null,
        overallStatus: 'CAUTION',
        score: 60,
        summary: '',
        ingredients: [],
      );

      expect(scanYes.willBuy, isTrue);
      expect(scanNo.willBuy, isFalse);
      expect(scanUndecided.willBuy, isNull);
    });

    test('copyWith updates customProductName and purchaseDecision accurately', () {
      final original = ScanResult(
        scanId: 10,
        productName: 'Oats & Honey Granola',
        productCategory: 'Cereal',
        overallStatus: 'GOOD',
        score: 85,
        summary: 'Wholesome oats.',
        ingredients: [
          IngredientItem(name: 'Rolled Oats', normalizedName: 'Oats', status: 'GOOD', reason: 'Fiber', category: 'Grain'),
        ],
      );

      final updated = original.copyWith(
        purchaseDecision: 'YES',
        customProductName: 'Healthy Breakfast Granola',
      );

      expect(updated.scanId, 10);
      expect(updated.productName, 'Oats & Honey Granola');
      expect(updated.customProductName, 'Healthy Breakfast Granola');
      expect(updated.displayName, 'Healthy Breakfast Granola');
      expect(updated.purchaseDecision, 'YES');
      expect(updated.willBuy, isTrue);
      expect(updated.score, 85);
      expect(updated.ingredients.length, 1);
    });

    test('toJson and fromJson serialize and deserialize customProductName and purchaseDecision', () {
      final original = ScanResult(
        scanId: 25,
        productName: 'Almond Milk Drink',
        productCategory: 'Dairy Alternative',
        customProductName: 'Morning Coffee Milk',
        purchaseDecision: 'YES',
        overallStatus: 'GOOD',
        score: 82,
        summary: 'Enriched almond beverage.',
        ingredients: [],
        createdAt: DateTime(2026, 10, 11, 14, 30),
      );

      final json = original.toJson();
      expect(json['custom_product_name'], 'Morning Coffee Milk');
      expect(json['purchase_decision'], 'YES');

      final deserialized = ScanResult.fromJson(json);
      expect(deserialized.scanId, 25);
      expect(deserialized.productName, 'Almond Milk Drink');
      expect(deserialized.customProductName, 'Morning Coffee Milk');
      expect(deserialized.displayName, 'Morning Coffee Milk');
      expect(deserialized.purchaseDecision, 'YES');
      expect(deserialized.willBuy, isTrue);
      expect(deserialized.score, 82);
    });

    test('fromJson handles legacy records without purchaseDecision and customProductName without crashing', () {
      final legacyJson = {
        'product_name': 'Legacy Energy Bar',
        'overall_status': 'GOOD',
        'score': 78,
        'summary': 'Nutrient dense snack.',
        'ingredients': [],
      };

      final parsed = ScanResult.fromJson(legacyJson);
      expect(parsed.productName, 'Legacy Energy Bar');
      expect(parsed.customProductName, isNull);
      expect(parsed.purchaseDecision, isNull);
      expect(parsed.displayName, 'Legacy Energy Bar');
      expect(parsed.willBuy, isNull);
    });
  });

  group('LocalStorage Update Scan In History Tests', () {
    setUp(() {
      TestWidgetsFlutterBinding.ensureInitialized();
      SharedPreferences.setMockInitialValues({});
    });

    test('updateScanInHistory updates customProductName and purchaseDecision in place', () async {
      await LocalStorage.clearHistory();

      final initialScan = ScanResult(
        scanId: 101,
        productName: 'Britannia Good Day Butter Cookies',
        productCategory: 'Biscuits',
        overallStatus: 'CAUTION',
        score: 62,
        summary: 'Contains palm oil and sugar.',
        ingredients: [
          IngredientItem(name: 'Maida', normalizedName: 'Wheat Flour', status: 'GOOD', reason: 'Grain', category: 'Flour'),
        ],
        createdAt: DateTime(2026, 10, 11, 10, 0),
      );

      await LocalStorage.saveScanToHistory(initialScan);
      final historyBefore = await LocalStorage.getCachedHistory();
      expect(historyBefore.length, 1);
      expect(historyBefore.first.displayName, 'Britannia Good Day Butter Cookies');
      expect(historyBefore.first.purchaseDecision, isNull);

      // Now update with purchase decision YES and custom product name
      final updatedScan = initialScan.copyWith(
        purchaseDecision: 'YES',
        customProductName: 'Tea Time Butter Cookies',
      );

      final success = await LocalStorage.updateScanInHistory(updatedScan);
      expect(success, isTrue);

      final historyAfter = await LocalStorage.getCachedHistory();
      expect(historyAfter.length, 1, reason: 'Must not create duplicate entry');
      expect(historyAfter.first.scanId, 101);
      expect(historyAfter.first.productName, 'Britannia Good Day Butter Cookies');
      expect(historyAfter.first.customProductName, 'Tea Time Butter Cookies');
      expect(historyAfter.first.displayName, 'Tea Time Butter Cookies');
      expect(historyAfter.first.purchaseDecision, 'YES');
      expect(historyAfter.first.willBuy, isTrue);
      expect(historyAfter.first.score, 62, reason: 'Health score must remain identical');
    });

    test('updateScanInHistory matches by createdAt timestamp if scanId is null', () async {
      await LocalStorage.clearHistory();

      final timestamp = DateTime(2026, 10, 11, 12, 15);
      final offlineScan = ScanResult(
        scanId: null,
        productName: 'Local Bakery Bread',
        productCategory: 'Bakery',
        overallStatus: 'GOOD',
        score: 75,
        summary: 'Fresh whole wheat loaf.',
        ingredients: [],
        createdAt: timestamp,
      );

      await LocalStorage.saveScanToHistory(offlineScan);

      final updatedOfflineScan = offlineScan.copyWith(
        purchaseDecision: 'NO',
      );

      final success = await LocalStorage.updateScanInHistory(updatedOfflineScan);
      expect(success, isTrue);

      final history = await LocalStorage.getCachedHistory();
      expect(history.length, 1);
      expect(history.first.productName, 'Local Bakery Bread');
      expect(history.first.purchaseDecision, 'NO');
      expect(history.first.willBuy, isFalse);
    });
  });
}
