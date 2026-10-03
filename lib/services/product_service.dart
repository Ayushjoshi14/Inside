import 'dart:convert';
import 'package:http/http.dart' as http;

class ProductService {
  static Future<Map<String, dynamic>?> getProduct(String barcode) async {
    final url = Uri.parse(
      'https://world.openfoodfacts.org/api/v2/product/$barcode.json',
    );

    try {
      final response = await http.get(
        url,
        headers: {
          'User-Agent': 'InsideApp/1.0',
        },
      );

      if (response.statusCode != 200) {
        return null;
      }

      final data = jsonDecode(response.body);

      if (data['status'] != 1) {
        return null;
      }

      return data['product'];
    } catch (e) {
      print('Product API error: $e');
      return null;
    }
  }
}