import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:inside/models/ingredient_model.dart';
import 'package:inside/models/scan_result_model.dart';
import 'package:inside/features/analysis/result_screen.dart';

void main() {
  group('ScoreBreakdown & ScoreBreakdownItem Model Tests', () {
    test('ScoreBreakdownItem.fromJson parses label and points correctly', () {
      final json = {'label': 'High added sugar (20g per 100g)', 'points': -5};
      final item = ScoreBreakdownItem.fromJson(json);
      expect(item.label, 'High added sugar (20g per 100g)');
      expect(item.points, -5);
    });

    test('ScoreBreakdown.fromJson parses full breakdown structure', () {
      final json = {
        'base_score': 100,
        'deductions': [
          {'label': '1 ingredient(s) to avoid', 'points': -25},
          {'label': 'Trans fat detected (0.5g per 100g)', 'points': -10},
          {'label': 'High sodium (700mg per 100g)', 'points': -5},
        ],
        'bonuses': [
          {'label': 'Clean-label formula reward', 'points': 5},
        ],
        'final_score': 65,
        'good_count': 3,
        'caution_count': 0,
        'avoid_count': 1,
        'nutrition_integrated': true,
        'disclaimer': 'Informational estimate only.',
      };

      final breakdown = ScoreBreakdown.fromJson(json);
      expect(breakdown.baseScore, 100);
      expect(breakdown.finalScore, 65);
      expect(breakdown.deductions.length, 3);
      expect(breakdown.deductions[0].label, '1 ingredient(s) to avoid');
      expect(breakdown.deductions[0].points, -25);
      expect(breakdown.bonuses.length, 1);
      expect(breakdown.goodCount, 3);
      expect(breakdown.avoidCount, 1);
      expect(breakdown.nutritionIntegrated, isTrue);
      expect(breakdown.disclaimer, 'Informational estimate only.');
    });

    test('ScanResult.fromJson and toJson roundtrips scoreBreakdown and positiveFindings', () {
      final json = {
        'product_name': 'Almond Granola',
        'product_category': 'Breakfast Cereal',
        'overall_status': 'GOOD',
        'score': 95,
        'summary': 'Wholesome breakfast.',
        'ingredients': [
          {
            'name': 'Rolled Oats',
            'normalized_name': 'Rolled Oats',
            'status': 'GOOD',
            'reason': 'Whole grain.',
            'category': 'Cereal',
            'source': 'local_db',
          }
        ],
        'score_breakdown': {
          'base_score': 100,
          'deductions': [],
          'bonuses': [
            {'label': 'Clean-label reward', 'points': 5}
          ],
          'final_score': 100,
          'good_count': 1,
          'caution_count': 0,
          'avoid_count': 0,
          'nutrition_integrated': false,
          'disclaimer': 'Informational estimate.',
        },
        'positive_findings': [
          'Contains whole grain Rolled Oats',
          'Clean-label formula with no synthetic additives'
        ],
      };

      final result = ScanResult.fromJson(json);
      expect(result.scoreBreakdown, isNotNull);
      expect(result.scoreBreakdown!.finalScore, 100);
      expect(result.positiveFindings.length, 2);
      expect(result.positiveFindings[0], 'Contains whole grain Rolled Oats');
      expect(result.ingredients[0].source, 'local_db');

      final serialized = result.toJson();
      expect(serialized['score_breakdown'], isNotNull);
      expect(serialized['score_breakdown']['final_score'], 100);
      expect(serialized['positive_findings'].length, 2);
    });
  });

  group('ResultScreen Score Breakdown & Positive Findings UI Tests', () {
    testWidgets('ResultScreen renders Score Breakdown and Positive Findings sections', (tester) async {
      final testResult = ScanResult(
        productName: 'Crunchy Muesli',
        productCategory: 'Breakfast Cereal',
        overallStatus: 'GOOD',
        score: 95,
        summary: 'Excellent breakfast choice.',
        ingredients: [
          IngredientItem(
            name: 'Oats',
            normalizedName: 'Oats',
            status: 'GOOD',
            reason: 'Whole grain goodness.',
            category: 'Cereal',
            source: 'local_db',
          ),
        ],
        positiveFindings: [
          'Rich in dietary fiber from whole Oats',
          'Free from artificial colours and flavours',
        ],
        scoreBreakdown: const ScoreBreakdown(
          baseScore: 100,
          deductions: [
            ScoreBreakdownItem(label: '1 ingredient(s) requiring caution', points: -8),
          ],
          bonuses: [
            ScoreBreakdownItem(label: 'Clean-label formula reward', points: 5),
          ],
          finalScore: 97,
          goodCount: 1,
          cautionCount: 1,
          avoidCount: 0,
          nutritionIntegrated: false,
          disclaimer: 'Informational estimate only.',
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ResultScreen(result: testResult),
        ),
      );
      await tester.pumpAndSettle();

      // Check Positive Findings card is displayed
      expect(find.text('Positive Findings'), findsOneWidget);
      expect(find.text('Rich in dietary fiber from whole Oats'), findsOneWidget);
      expect(find.text('Free from artificial colours and flavours'), findsOneWidget);

      // Check Score Breakdown card is displayed
      expect(find.text('Score Breakdown'), findsOneWidget);
      expect(find.text('Base score'), findsOneWidget);
      expect(find.text('1 ingredient(s) requiring caution'), findsOneWidget);
      expect(find.text('Clean-label formula reward'), findsOneWidget);
      expect(find.text('Final score'), findsOneWidget);
      expect(find.text('97/100'), findsOneWidget);
      expect(find.text('1 Good'), findsOneWidget);
      expect(find.text('1 Caution'), findsOneWidget);
    });

    testWidgets('ResultScreen shows premium unlock teaser when more than 2 deductions exist for free user', (tester) async {
      final testResult = ScanResult(
        productName: 'Processed Cookie',
        productCategory: 'Biscuits',
        overallStatus: 'AVOID',
        score: 45,
        summary: 'Contains harmful additives.',
        ingredients: [],
        scoreBreakdown: const ScoreBreakdown(
          baseScore: 100,
          deductions: [
            ScoreBreakdownItem(label: '2 ingredient(s) to avoid', points: -50),
            ScoreBreakdownItem(label: 'Trans fat detected (1.2g)', points: -10),
            ScoreBreakdownItem(label: 'High sodium (850mg)', points: -5),
            ScoreBreakdownItem(label: 'High added sugar (25g)', points: -5),
          ],
          bonuses: [],
          finalScore: 45,
          goodCount: 1,
          cautionCount: 0,
          avoidCount: 2,
          nutritionIntegrated: true,
          disclaimer: 'Informational estimate only.',
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ResultScreen(result: testResult),
        ),
      );
      await tester.pumpAndSettle();

      // Verify Score Breakdown card is displayed
      expect(find.text('Score Breakdown'), findsOneWidget);

      // Top 2 deductions should be visible
      expect(find.text('2 ingredient(s) to avoid'), findsOneWidget);
      expect(find.text('Trans fat detected (1.2g)'), findsOneWidget);

      // 3rd and 4th deductions should be hidden behind teaser
      expect(find.text('+2 more score factors'), findsOneWidget);
      expect(find.text('Unlock'), findsOneWidget);
    });
  });
}
