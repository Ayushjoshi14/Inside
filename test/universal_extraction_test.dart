import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:inside/models/scan_result_model.dart';
import 'package:inside/models/ingredient_model.dart';
import 'package:inside/core/network/api_client.dart';
import 'package:inside/features/analysis/result_screen.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Universal Extraction & Nutrition Facts Model Tests', () {
    test('ScanResult serialization and deserialization preserves nutritionFacts', () {
      final json = {
        'scan_id': 201,
        'product_name': 'Britannia Good Day Butter Cookies',
        'product_category': 'Biscuits',
        'overall_status': 'CAUTION',
        'score': 68,
        'summary': 'Moderate profile.',
        'ingredients': [
          {
            'name': 'Refined Wheat Flour (Maida) (58%)',
            'normalized_name': 'Wheat Flour',
            'status': 'GOOD',
            'reason': 'Cereal grain.',
            'category': 'Flour'
          },
          {
            'name': 'Palm Oil',
            'normalized_name': 'Palm Oil',
            'status': 'CAUTION',
            'reason': 'High in saturated fat.',
            'category': 'Fat/oil'
          }
        ],
        'warnings': ['Contains saturated fat'],
        'recommendations': ['Consume in moderation'],
        'raw_ocr_text': 'Wheat Flour, Palm Oil',
        'created_at': '2026-10-11T20:00:00Z',
        'nutrition_facts': {
          'per_unit': 'Per 100g',
          'energy_kcal': 492.0,
          'protein_g': 6.5,
          'carbohydrates_g': 69.5,
          'total_sugars_g': 22.0,
          'total_fat_g': 21.0,
          'sodium_mg': 350.0,
        }
      };

      final result = ScanResult.fromJson(json);

      expect(result.scanId, 201);
      expect(result.productName, 'Britannia Good Day Butter Cookies');
      expect(result.productCategory, 'Biscuits');
      expect(result.nutritionFacts['energy_kcal'], 492.0);
      expect(result.nutritionFacts['protein_g'], 6.5);
      expect(result.nutritionFacts['carbohydrates_g'], 69.5);
      expect(result.nutritionFacts['total_sugars_g'], 22.0);
      expect(result.nutritionFacts['sodium_mg'], 350.0);

      // Verify toJson includes nutrition_facts
      final serialized = result.toJson();
      expect(serialized['nutrition_facts'], isNotNull);
      expect(serialized['nutrition_facts']['energy_kcal'], 492.0);
      expect(serialized['nutrition_facts']['total_fat_g'], 21.0);
    });

    test('ScanResult.fromJson gracefully handles legacy records without nutrition_facts', () {
      final legacyJson = {
        'product_name': 'Old Scan Item',
        'product_category': 'Snacks',
        'overall_status': 'GOOD',
        'score': 90,
        'summary': 'Wholesome.',
        'ingredients': [],
      };

      final result = ScanResult.fromJson(legacyJson);
      expect(result.nutritionFacts, isEmpty);
      expect(result.productName, 'Old Scan Item');
      expect(result.productCategory, 'Snacks');
    });

    test('ScanResult.copyWith updates nutritionFacts accurately', () {
      final initial = ScanResult(
        productName: 'Sample Product',
        overallStatus: 'GOOD',
        score: 85,
        summary: 'Good',
        ingredients: [],
        nutritionFacts: {'energy_kcal': 200.0},
      );

      final updated = initial.copyWith(
        nutritionFacts: {'energy_kcal': 250.0, 'protein_g': 10.0},
      );

      expect(updated.nutritionFacts['energy_kcal'], 250.0);
      expect(updated.nutritionFacts['protein_g'], 10.0);
      expect(initial.nutritionFacts['energy_kcal'], 200.0);
    });
  });

  group('Universal Extraction Offline Analysis Fallback Tests', () {
    late ApiClient apiClient;

    setUp(() {
      apiClient = ApiClient();
    });

    test('Offline universal extraction separates nutrition facts and preserves nested parentheses', () async {
      const ocrText = '''
BRITANNIA GOOD DAY BUTTER COOKIES
INGREDIENTS: Refined Wheat Flour (Maida) (58%), Sugar, Edible Vegetable Oil (Palmolein, Antioxidant (INS 319)), Butter (2.5%), Raising Agents (INS 503(ii), INS 500(ii)), Salt.
ALLERGEN DECLARATION: CONTAINS WHEAT AND MILK.
NUTRITION INFORMATION Per 100g:
Energy 492 kcal
Protein 6.5g
Carbohydrates 69.5g
Total Sugars 22.0g
Total Fat 21.0g
Sodium 350mg
Manufactured by Britannia Industries Ltd.
''';

      // Will fall back to offline analysis when network endpoint is unavailable
      final result = await apiClient.analyzeText(ocrText);

      expect(result.isCompatible, isTrue);
      expect(result.ingredients, isNotEmpty);

      // Verify brand name is excluded
      final ingredientNames = result.ingredients.map((i) => i.name.toLowerCase()).toList();
      expect(ingredientNames.any((name) => name.contains('britannia')), isFalse);

      // Verify nutrition facts are isolated
      expect(result.nutritionFacts['energy_kcal'], 492.0);
      expect(result.nutritionFacts['protein_g'], 6.5);
      expect(result.nutritionFacts['carbohydrates_g'], 69.5);
      expect(result.nutritionFacts['total_sugars_g'], 22.0);
      expect(result.nutritionFacts['total_fat_g'], 21.0);
      expect(result.nutritionFacts['sodium_mg'], 350.0);

      // Verify no nutrition keywords are listed as ingredients
      for (final ing in result.ingredients) {
        expect(ing.name.toLowerCase().startsWith('energy'), isFalse);
        expect(ing.name.toLowerCase().startsWith('protein'), isFalse);
        expect(ing.name.toLowerCase().contains('kcal'), isFalse);
      }
    });

    test('Offline universal extraction throws UnableToIdentifyException for marketing-only box', () async {
      const marketingOnlyText = '''
CRUNCHY OAT FLAKES!
100% Whole Grain Goodness
High in Protein & Dietary Fiber
Zero Cholesterol, No Added Preservatives
Net Wt: 500g
Best Before 12 Months
MRP Rs 220
''';

      expect(
        () async => await apiClient.analyzeText(marketingOnlyText),
        throwsA(isA<UnableToIdentifyException>()),
      );
    });
  });

  group('ResultScreen Nutrition Facts UI Widget Tests', () {
    testWidgets('ResultScreen renders Nutrition Facts section when nutritionFacts data is available', (tester) async {
      final testResult = ScanResult(
        scanId: 999,
        productName: 'NutriChoice Digestive',
        productCategory: 'Biscuits',
        overallStatus: 'CAUTION',
        score: 65,
        summary: 'Contains palm oil and added sugars.',
        ingredients: [
          IngredientItem(
            name: 'Refined Wheat Flour',
            normalizedName: 'Wheat Flour',
            status: 'GOOD',
            reason: 'Whole grain flour.',
            category: 'Flour',
          ),
          IngredientItem(
            name: 'Palm Oil',
            normalizedName: 'Palm Oil',
            status: 'CAUTION',
            reason: 'High saturated fat.',
            category: 'Fat/oil',
          ),
        ],
        warnings: ['High saturated fat'],
        recommendations: ['Consume in moderation'],
        nutritionFacts: {
          'per_unit': 'Per 100g',
          'energy_kcal': 490.0,
          'protein_g': 8.0,
          'carbohydrates_g': 68.0,
          'total_sugars_g': 18.0,
          'total_fat_g': 20.0,
          'sodium_mg': 400.0,
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ResultScreen(result: testResult),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Nutrition Facts title is displayed
      expect(find.text('Nutrition Facts'), findsOneWidget);
      expect(find.text('Per 100g'), findsOneWidget);
      expect(find.text('Energy'), findsOneWidget);
      expect(find.text('490.0 kcal'), findsOneWidget);
      expect(find.text('Protein'), findsOneWidget);
      expect(find.text('8.0g'), findsOneWidget);
      expect(find.text('Carbs'), findsOneWidget);
      expect(find.text('68.0g'), findsOneWidget);

      // Verify Ingredients section is also separately displayed
      expect(find.text('Ingredients'), findsOneWidget);
      expect(find.text('Refined Wheat Flour'), findsOneWidget);
      expect(find.text('Palm Oil'), findsOneWidget);
    });

    testWidgets('ResultScreen hides Nutrition Facts section cleanly when nutritionFacts is empty', (tester) async {
      final testResult = ScanResult(
        scanId: 1000,
        productName: 'Simple Sugar Candy',
        productCategory: 'Confectionery',
        overallStatus: 'CAUTION',
        score: 55,
        summary: 'High sugar.',
        ingredients: [
          IngredientItem(
            name: 'Cane Sugar',
            normalizedName: 'Cane Sugar',
            status: 'CAUTION',
            reason: 'Refined sweetener.',
            category: 'Sweetener',
          ),
        ],
        nutritionFacts: {}, // No nutrition data
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ResultScreen(result: testResult),
        ),
      );
      await tester.pumpAndSettle();

      // Nutrition Facts title must NOT be present
      expect(find.text('Nutrition Facts'), findsNothing);

      // Ingredients must be present
      expect(find.text('Ingredients'), findsOneWidget);
      expect(find.text('Cane Sugar'), findsOneWidget);
    });
  });
}
