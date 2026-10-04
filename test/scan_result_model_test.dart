import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:inside/models/scan_result_model.dart';
import 'package:inside/models/ingredient_model.dart';
import 'package:inside/core/storage/local_storage.dart';

void main() {
  group('ScanResult Model Compatibility Tests', () {
    test('ScanResult.fromJson parses modern record with product_category', () {
      final json = {
        'scan_id': 101,
        'product_name': 'Britannia NutriChoice Digestive',
        'product_category': 'Biscuits',
        'overall_status': 'CAUTION',
        'score': 65,
        'summary': 'Contains ingredients worth checking.',
        'ingredients': [
          {
            'name': 'Refined Wheat Flour',
            'normalized_name': 'Wheat Flour',
            'status': 'GOOD',
            'reason': 'Cereal grain.',
            'category': 'Flour'
          }
        ],
        'warnings': ['Contains wheat'],
        'recommendations': ['Store in dry place'],
        'raw_ocr_text': 'Wheat Flour, Palm Oil',
        'created_at': '2026-10-04T19:11:00Z',
      };

      final result = ScanResult.fromJson(json);

      expect(result.scanId, 101);
      expect(result.productName, 'Britannia NutriChoice Digestive');
      expect(result.productCategory, 'Biscuits');
      expect(result.overallStatus, 'CAUTION');
      expect(result.score, 65);
      expect(result.ingredients.length, 1);
    });

    test('ScanResult.fromJson safely falls back to "Food Product" for legacy record without product_category', () {
      final legacyJson = {
        'product_name': 'Legacy Scanned Food',
        // No 'product_category' field
        'overall_status': 'GOOD',
        'score': 85,
        'summary': 'Safe profile.',
        'ingredients': [],
      };

      final result = ScanResult.fromJson(legacyJson);

      expect(result.productName, 'Legacy Scanned Food');
      expect(result.productCategory, 'Food Product');
      expect(result.overallStatus, 'GOOD');
      expect(result.score, 85);
    });

    test('ScanResult.toJson includes product_category', () {
      final scan = ScanResult(
        productName: 'Coca-Cola',
        productCategory: 'Soft Drink',
        overallStatus: 'AVOID',
        score: 40,
        summary: 'High sugar beverage.',
        ingredients: [],
      );

      final json = scan.toJson();

      expect(json['product_name'], 'Coca-Cola');
      expect(json['product_category'], 'Soft Drink');
      expect(json['overall_status'], 'AVOID');
    });
  });

  group('LocalStorage History Persistence Tests', () {
    setUp(() {
      TestWidgetsFlutterBinding.ensureInitialized();
      SharedPreferences.setMockInitialValues({});
    });

    test('saves ScanResult to history, retrieves it and verifies all fields', () async {
      // Step A: Clear history
      await LocalStorage.clearHistory();
      final initialHistory = await LocalStorage.getCachedHistory();
      expect(initialHistory, isEmpty);

      // Step B: Create a ScanResult with 7 ingredients
      final scan = ScanResult(
        scanId: 42,
        productName: 'Britannia NutriChoice Digestive',
        productCategory: 'Biscuits',
        overallStatus: 'CAUTION',
        score: 68,
        summary: 'Contains palm oil and added sugars.',
        ingredients: [
          IngredientItem(name: 'Refined Wheat Flour', normalizedName: 'Wheat Flour', status: 'GOOD', reason: 'Grain', category: 'Flour'),
          IngredientItem(name: 'Palm Oil', normalizedName: 'Palm Oil', status: 'CAUTION', reason: 'Saturated fat', category: 'Fat/oil'),
          IngredientItem(name: 'Sugar', normalizedName: 'Sugar', status: 'CAUTION', reason: 'Sweetener', category: 'Sugar'),
          IngredientItem(name: 'Wheat Bran', normalizedName: 'Wheat Bran', status: 'GOOD', reason: 'Fiber', category: 'Fiber'),
          IngredientItem(name: 'Invert Sugar', normalizedName: 'Invert Sugar', status: 'CAUTION', reason: 'Sweetener', category: 'Sugar'),
          IngredientItem(name: 'INS 500ii', normalizedName: 'Sodium Bicarbonate', status: 'GOOD', reason: 'Leavening', category: 'Raising agent'),
          IngredientItem(name: 'Salt', normalizedName: 'Salt', status: 'GOOD', reason: 'Mineral', category: 'General'),
        ],
        warnings: ['Contains palm oil'],
        recommendations: ['Check allergens'],
        rawOcrText: 'Refined Wheat Flour, Palm Oil, Sugar, Wheat Bran, Invert Sugar, INS 500ii, Salt.',
        createdAt: DateTime(2026, 10, 4, 19, 11),
      );

      // Step C: Save to history
      final saved = await LocalStorage.saveScanToHistory(scan);
      expect(saved, isTrue);

      // Step D: Retrieve history
      final history = await LocalStorage.getCachedHistory();
      expect(history.length, 1);

      // Step E: Verify record fields
      final retrieved = history.first;
      expect(retrieved.productName, 'Britannia NutriChoice Digestive');
      expect(retrieved.productCategory, 'Biscuits');
      expect(retrieved.ingredients.length, 7);
      expect(retrieved.overallStatus, 'CAUTION');
      expect(retrieved.score, 68);
      expect(retrieved.createdAt.year, 2026);
      expect(retrieved.createdAt.month, 10);
      expect(retrieved.createdAt.day, 4);

      // Step F: Test deleting item
      await LocalStorage.deleteScanFromHistory(0);
      final afterDelete = await LocalStorage.getCachedHistory();
      expect(afterDelete, isEmpty);
    });
  });
}
