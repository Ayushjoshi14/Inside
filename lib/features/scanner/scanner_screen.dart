import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import '../../services/scanner_service.dart';
import '../analysis/result_screen.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  final ImagePicker _picker = ImagePicker();

  File? _capturedImage;
  bool _isAnalyzing = false;

  String _extractedText = '';
  int _score = 0;

  Future<void> _captureIngredientLabel() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 90,
      );

      if (photo == null) return;

      setState(() {
        _capturedImage = File(photo.path);
        _extractedText = '';
        _score = 0;
      });
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not open camera: $e'),
        ),
      );
    }
  }

  Future<void> _analyzeIngredients() async {
    if (_capturedImage == null) return;

    setState(() {
      _isAnalyzing = true;
    });

    try {
      // Create OCR recognizer
      final textRecognizer =
          TextRecognizer(script: TextRecognitionScript.latin);

      // Convert image to ML Kit input
      final inputImage = InputImage.fromFile(_capturedImage!);

      // Extract text
      final RecognizedText recognizedText =
          await textRecognizer.processImage(inputImage);

      await textRecognizer.close();

      final extractedText = recognizedText.text;

      if (extractedText.trim().isEmpty) {
        if (!mounted) return;

        setState(() {
          _isAnalyzing = false;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Could not read the ingredients. Please take a clearer photo.',
            ),
          ),
        );

        return;
      }

      // Process and analyze with backend / food science engine
      if (!mounted) return;
      final scannerService = Provider.of<ScannerService>(context, listen: false);
      final result = await scannerService.processImageAndAnalyze(
        imageFile: _capturedImage,
        directOcrText: extractedText,
      );

      final score = result?.score ?? _calculateScore(extractedText);

      if (!mounted) return;

      setState(() {
        _extractedText = extractedText;
        _score = score;
        _isAnalyzing = false;
      });

      if (result != null) {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => ResultScreen(result: result)),
        );
      } else {
        _showResult();
      }
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _isAnalyzing = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Analysis failed: $e'),
        ),
      );
    }
  }

  int _calculateScore(String text) {
    final ingredients = text.toLowerCase();

    int score = 100;

    // High sugar
    if (ingredients.contains('sugar') ||
        ingredients.contains('glucose syrup') ||
        ingredients.contains('fructose') ||
        ingredients.contains('maltose')) {
      score -= 15;
    }

    // Artificial sweeteners
    if (ingredients.contains('aspartame') ||
        ingredients.contains('sucralose') ||
        ingredients.contains('acesulfame')) {
      score -= 10;
    }

    // Artificial colors
    if (ingredients.contains('tartrazine') ||
        ingredients.contains('sunset yellow') ||
        ingredients.contains('brilliant blue') ||
        ingredients.contains('artificial colour')) {
      score -= 10;
    }

    // Preservatives
    if (ingredients.contains('sodium benzoate') ||
        ingredients.contains('potassium sorbate') ||
        ingredients.contains('preservative')) {
      score -= 10;
    }

    // Trans fat
    if (ingredients.contains('trans fat') ||
        ingredients.contains('hydrogenated oil')) {
      score -= 20;
    }

    // Palm oil
    if (ingredients.contains('palm oil')) {
      score -= 5;
    }

    // Positive ingredients
    if (ingredients.contains('whole grain') ||
        ingredients.contains('whole wheat') ||
        ingredients.contains('oats')) {
      score += 5;
    }

    if (ingredients.contains('protein')) {
      score += 5;
    }

    if (score < 0) score = 0;
    if (score > 100) score = 100;

    return score;
  }

  String _getScoreLabel() {
    if (_score >= 80) {
      return 'Excellent';
    } else if (_score >= 60) {
      return 'Good';
    } else if (_score >= 40) {
      return 'Average';
    } else if (_score >= 20) {
      return 'Poor';
    } else {
      return 'Very Poor';
    }
  }

  Color _getScoreColor() {
    if (_score >= 80) {
      return Colors.green;
    } else if (_score >= 60) {
      return Colors.lightGreen;
    } else if (_score >= 40) {
      return Colors.orange;
    } else {
      return Colors.red;
    }
  }

  void _showResult() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(28),
        ),
      ),
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.all(24),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Center(
                  child: Container(
                    width: 45,
                    height: 5,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade300,
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),

                const SizedBox(height: 25),

                const Center(
                  child: Text(
                    'Product Health Score',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),

                const SizedBox(height: 25),

                Center(
                  child: Container(
                    width: 130,
                    height: 130,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _getScoreColor(),
                    ),
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            '$_score',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 42,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const Text(
                            '/ 100',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 15),

                Center(
                  child: Text(
                    _getScoreLabel(),
                    style: TextStyle(
                      color: _getScoreColor(),
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),

                const SizedBox(height: 30),

                const Text(
                  'Extracted Ingredients / Text',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),

                const SizedBox(height: 10),

                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(15),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: Text(
                    _extractedText,
                    style: const TextStyle(
                      fontSize: 14,
                      height: 1.5,
                    ),
                  ),
                ),

                const SizedBox(height: 25),

                SizedBox(
                  width: double.infinity,
                  height: 52,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.pop(context);
                      _retake();
                    },
                    child: const Text(
                      'Scan Another Product',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 10),
              ],
            ),
          ),
        );
      },
    );
  }

  void _retake() {
    setState(() {
      _capturedImage = null;
      _extractedText = '';
      _score = 0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: const Text(
          'Scan Ingredients',
          style: TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: SafeArea(
        child: _capturedImage == null
            ? _buildCameraInstructions()
            : _buildCapturedImage(),
      ),
    );
  }

  Widget _buildCameraInstructions() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 280,
              height: 220,
              decoration: BoxDecoration(
                border: Border.all(
                  color: Colors.white,
                  width: 3,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Icon(
                Icons.document_scanner_outlined,
                color: Colors.white,
                size: 90,
              ),
            ),

            const SizedBox(height: 30),

            const Text(
              'Scan Ingredient Label',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            const Text(
              'Take a clear photo of the ingredients or nutrition label on the product.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white70,
                fontSize: 15,
              ),
            ),

            const SizedBox(height: 35),

            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton.icon(
                onPressed: _captureIngredientLabel,
                icon: const Icon(Icons.camera_alt),
                label: const Text(
                  'Open Camera',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCapturedImage() {
    return Column(
      children: [
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Image.file(
                _capturedImage!,
                width: double.infinity,
                fit: BoxFit.contain,
              ),
            ),
          ),
        ),

        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
          child: Column(
            children: [
              SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton.icon(
                  onPressed: _isAnalyzing
                      ? null
                      : _analyzeIngredients,
                  icon: _isAnalyzing
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.analytics_outlined),
                  label: Text(
                    _isAnalyzing
                        ? 'Reading Ingredients...'
                        : 'Analyze Ingredients',
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 10),

              SizedBox(
                width: double.infinity,
                height: 50,
                child: OutlinedButton.icon(
                  onPressed: _isAnalyzing ? null : _retake,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retake Photo'),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}