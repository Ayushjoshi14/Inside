import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class ProductService {
  static const List<String> consumerCategories = [
    "Biscuits",
    "Chips & Snacks",
    "Chocolate",
    "Candy",
    "Soft Drink",
    "Juice",
    "Dairy",
    "Milk Product",
    "Breakfast Cereal",
    "Instant Food",
    "Noodles",
    "Sauces & Condiments",
    "Bakery",
    "Frozen Food",
    "Protein Product",
    "Beverage",
    "Tea & Coffee",
    "Ready-to-Eat",
    "Baby Food",
    "Other Food",
    "Food Product"
  ];

  static Future<Map<String, dynamic>?> getProduct(String barcode) async {
    final url = Uri.parse(
      'https://world.openfoodfacts.org/api/v2/product/$barcode.json',
    );

    try {
      final response = await http.get(
        url,
        headers: {
          'User-Agent': 'InsideApp/1.0 (contact@insideapp.in)',
        },
      ).timeout(const Duration(seconds: 6));

      if (response.statusCode != 200) {
        return null;
      }

      final data = jsonDecode(response.body);

      if (data['status'] != 1) {
        return null;
      }

      return data['product'] as Map<String, dynamic>?;
    } catch (e) {
      debugPrint('Product API error: $e');
      return null;
    }
  }

  /// Normalizes Open Food Facts category tags/strings into clean consumer categories
  static String normalizeCategory(String? rawCategory) {
    if (rawCategory == null || rawCategory.trim().isEmpty) {
      return "Food Product";
    }

    final lower = rawCategory
        .toLowerCase()
        .replaceAll(RegExp(r'\b[a-z]{2}:'), ' ')
        .replaceAll(RegExp(r'[\-_,;]+'), ' ');

    if (lower.contains('biscuit') || lower.contains('cookie') || lower.contains('cracker') || lower.contains('wafer') || lower.contains('rusk') || lower.contains('digestive')) {
      return 'Biscuits';
    }
    if (lower.contains('chip') || lower.contains('crisp') || lower.contains('nacho') || lower.contains('popcorn') || lower.contains('namkeen') || lower.contains('bhujia') || lower.contains('snack') || lower.contains('peanut')) {
      return 'Chips & Snacks';
    }
    if (lower.contains('chocolate') || lower.contains('cocoa') || lower.contains('praline') || lower.contains('truffle')) {
      return 'Chocolate';
    }
    if (lower.contains('candy') || lower.contains('gummy') || lower.contains('toffee') || lower.contains('lollipop') || lower.contains('marshmallow') || lower.contains('jelly') || lower.contains('gum')) {
      return 'Candy';
    }
    if (lower.contains('soft drink') || lower.contains('soda') || lower.contains('carbonated') || lower.contains('cola') || lower.contains('lemonade') || lower.contains('fizzy')) {
      return 'Soft Drink';
    }
    if (lower.contains('juice') || lower.contains('nectar') || lower.contains('smoothie') || lower.contains('squash')) {
      return 'Juice';
    }
    if (lower.contains('paneer') || lower.contains('curd') || lower.contains('yogurt') || lower.contains('yoghurt') || lower.contains('cheese') || lower.contains('butter') || lower.contains('ghee') || lower.contains('dairy') || lower.contains('dairies')) {
      return 'Dairy';
    }
    if (lower.contains('milk') || lower.contains('milkshake') || lower.contains('condensed milk')) {
      return 'Milk Product';
    }
    if (lower.contains('breakfast cereal') || lower.contains('cereal') || lower.contains('oat') || lower.contains('muesli') || lower.contains('granola') || lower.contains('flake')) {
      return 'Breakfast Cereal';
    }
    if (lower.contains('noodle') || lower.contains('ramen') || lower.contains('vermicelli') || lower.contains('pasta')) {
      return 'Noodles';
    }
    if (lower.contains('instant') || lower.contains('ready meal') || lower.contains('instant soup') || lower.contains('meal kit')) {
      return 'Instant Food';
    }
    if (lower.contains('sauce') || lower.contains('ketchup') || lower.contains('mayo') || lower.contains('condiment') || lower.contains('chutney') || lower.contains('pickle') || lower.contains('dressing')) {
      return 'Sauces & Condiments';
    }
    if (lower.contains('bread') || lower.contains('cake') || lower.contains('pastry') || lower.contains('muffin') || lower.contains('bun') || lower.contains('croissant') || lower.contains('bakery')) {
      return 'Bakery';
    }
    if (lower.contains('ice cream') || lower.contains('frozen') || lower.contains('kulfi') || lower.contains('gelato')) {
      return 'Frozen Food';
    }
    if (lower.contains('protein bar') || lower.contains('protein powder') || lower.contains('whey') || lower.contains('bcaa')) {
      return 'Protein Product';
    }
    if (lower.contains('tea') || lower.contains('coffee') || lower.contains('espresso') || lower.contains('cappuccino') || lower.contains('chai')) {
      return 'Tea & Coffee';
    }
    if (lower.contains('energy drink') || lower.contains('beverage') || lower.contains('isotonic') || lower.contains('drink')) {
      return 'Beverage';
    }
    if (lower.contains('baby food') || lower.contains('infant formula') || lower.contains('cerelac')) {
      return 'Baby Food';
    }
    if (lower.contains('ready to eat') || lower.contains('ready-to-eat')) {
      return 'Ready-to-Eat';
    }

    return 'Food Product';
  }

  /// Extracts the cleaned product name from Open Food Facts JSON
  static String? extractProductName(Map<String, dynamic>? product) {
    if (product == null) return null;
    final name = product['product_name'] ?? product['product_name_en'] ?? product['generic_name'];
    if (name is String && name.trim().isNotEmpty) {
      return name.trim();
    }
    return null;
  }

  /// Extracts the normalized consumer category from Open Food Facts JSON
  static String extractCategory(Map<String, dynamic>? product) {
    if (product == null) return 'Food Product';
    final categories = product['categories'] ?? product['categories_tags']?.toString();
    return normalizeCategory(categories?.toString());
  }
}