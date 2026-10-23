import 'package:flutter_test/flutter_test.dart';
import 'package:inside/core/utils/product_compatibility_checker.dart';

void main() {
  group('ProductCompatibilityChecker', () {
    test('Scenario 1: Packaged biscuit with readable ingredient label is COMPATIBLE', () {
      const biscuitOcr =
          'Britannia Good Day Butter Cookies. '
          'INGREDIENTS: Refined Wheat Flour (Maida), Butter, Sugar, Palm Oil, '
          'Invert Sugar, Iodised Salt, Milk Solids, Raising Agents (INS 503(ii), INS 500(ii)), '
          'Emulsifier (INS 322). FSSAI Lic. No. 10015043001129. Net Wt: 120g. '
          'Best before 6 months from packaging.';

      final result = ProductCompatibilityChecker.evaluate(biscuitOcr);
      expect(result.status, CompatibilityStatus.compatible);
      expect(result.isCompatible, isTrue);
      expect(result.isFood, isTrue);
    });

    test('Scenario 2: Packaged snack with nutrition label is COMPATIBLE', () {
      const snackOcr =
          'Lays Classic Salted Potato Chips. '
          'NUTRITION FACTS Per 100g: Energy: 540 kcal, Protein: 7g, '
          'Carbohydrate: 53g, Total Sugars: 1.5g, Total Fat: 34g, Saturated Fat: 15g, Sodium: 520mg. '
          'Ingredients: Potato, Edible Vegetable Oil (Palmolein), Iodised Salt. '
          'FSSAI Lic No 10014064000435. Net Quantity: 52g. Store in a cool and dry place.';

      final result = ProductCompatibilityChecker.evaluate(snackOcr);
      expect(result.status, CompatibilityStatus.compatible);
      expect(result.isCompatible, isTrue);
      expect(result.isFood, isTrue);
    });

    test('Scenario 3: Book containing sugar and protein is INCOMPATIBLE', () {
      const bookOcr =
          'Chapter 4: The Biochemistry of Cellular Nutrition. '
          'In this chapter, the author examines sugar and protein transport across cellular membranes. '
          'Published by Oxford University Press. ISBN 978-0-19-850000-0. '
          'Copyright 2021. All rights reserved. Page 142.';

      final result = ProductCompatibilityChecker.evaluate(bookOcr);
      expect(result.status, CompatibilityStatus.incompatible);
      expect(result.isCompatible, isFalse);
      expect(result.title, 'Incompatible Product');
      expect(
        result.message,
        "This doesn't appear to be a food product. Inside can analyze food ingredients and nutrition labels only. Please scan a food package or ingredient label.",
      );
    });

    test('Scenario 4: Mobile phone is INCOMPATIBLE', () {
      const phoneOcr =
          'Samsung Galaxy Smartphone 5G. '
          '8GB RAM, 128GB ROM, 6.5 inch 120Hz AMOLED display, 64MP camera, '
          '5000mAh battery, Qualcomm Snapdragon 778G processor, Model SM-A526B. '
          'IMEI: 356987123456789.';

      final result = ProductCompatibilityChecker.evaluate(phoneOcr);
      expect(result.status, CompatibilityStatus.incompatible);
      expect(result.isCompatible, isFalse);
      expect(result.title, 'Incompatible Product');
    });

    test('Scenario 5: Blank or blurry scan is UNREADABLE', () {
      for (final blank in ['', '   \n\t  ', '... --- ...']) {
        final result = ProductCompatibilityChecker.evaluate(blank);
        expect(result.status, CompatibilityStatus.unreadable);
        expect(result.isCompatible, isFalse);
        expect(result.title, 'Unable to Identify Product');
        expect(
          result.message,
          'Please scan a clear image of the food package or ingredient label.',
        );
      }
    });

    test('Scenario 6: Food package with unreadable label is UNREADABLE', () {
      const unreadableOcr = 'qwjke rhkwe jhkr wjher kjhwe zzz mnp qrs 98234';

      final result = ProductCompatibilityChecker.evaluate(unreadableOcr);
      expect(result.status, CompatibilityStatus.unreadable);
      expect(result.isCompatible, isFalse);
      expect(result.title, 'Unable to Identify Product');
      expect(
        result.message,
        'Please scan a clear image of the food package or ingredient label.',
      );
    });
  });
}
